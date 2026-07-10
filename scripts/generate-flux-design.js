#!/usr/bin/env node
'use strict';

/**
 * generate-flux-design.js
 *
 * Genera design usando Fal.ai (Flux Pro / Dev) e salva localmente.
 * Usa le dimensioni esatte dai blueprint Printify per prompt perfetti.
 *
 * Prerequisiti:
 *   - FAL_API_KEY (o --key)
 *     La chiave Fal.ai (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
 *
 * Uso:
 *   node scripts/generate-flux-design.js --product collar --prompt "..." 
 *   node scripts/generate-flux-design.js --product bandana --width 3150 --height 1691 --prompt "..."
 *
 * Poi carica il PNG risultante su Printify usando gli script esistenti o upload.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const { URL } = require('url');

const ROOT = path.join(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'generated-designs');
const BLUEPRINTS_DIR = path.join(ROOT, 'printify-blueprints');

// Known product specs (from Printify API + config)
const PRODUCT_SPECS = {
  collar: {
    name: 'Dog Collar',
    blueprintId: 784,
    providerId: 93,
    defaultVariant: 74897, // S / Black Onyx
    printAreas: [
      { label: 'S', width: 5764, height: 229, aspect: '25:1 approx' },
      { label: 'M', width: 7257, height: 338, aspect: '21.5:1' },
      { label: 'L', width: 8318, height: 338 },
      { label: 'XL', width: 9519, height: 338 },
    ],
    tips: 'Design must be extremely wide panoramic strip. Use repeating patterns, long text, or continuous artwork that wraps around the collar. High detail on the thin band. Dye-sublimation friendly, vector-like or crisp illustration.'
  },
  bandana: {
    name: 'Pet Bandana',
    blueprintId: 562,
    providerId: 70,
    defaultVariant: 101403,
    printAreas: [
      { label: '20x10', width: 3150, height: 1691, aspect: '~1.86:1' },
      { label: '27x13', width: 4275, height: 2325 },
    ],
    tips: 'Triangular or square-ish bandana shape when worn. Design the full printable rectangle. Front side only usually. Fun pet-themed motifs, names, patterns that look good folded.'
  },
  tag: {
    name: 'Pet Tag / Medaglietta',
    blueprintId: 566,
    providerId: 70,
    defaultVariant: 70870,
    printAreas: [
      { label: '1inch', width: 810, height: 900, aspect: '0.9:1' },
    ],
    tips: 'Small round-ish metal tag. Design must be legible at small physical size. Bold, high contrast, simple icons + short text (name/phone). Both sides sometimes printable.'
  },
  bed: {
    name: 'Pet Bed / Cuccia',
    blueprintId: 419,
    providerId: 10,
    defaultVariant: 61436, // 28x18
    printAreas: [
      { label: '28x18', width: 8850, height: 5850, aspect: '1.51:1' },
      { label: '40x30', width: 12750, height: 9750 },
      { label: '50x40', width: 15600, height: 12600 },
    ],
    tips: 'Large fabric surface. Full bleed or with margins. Cute pet patterns, monograms, large illustrations that read well from distance. Very high resolution needed.'
  }
};

function ensureDir(d) { if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true }); }

function getFalKey(cliKey) {
  if (cliKey) return cliKey;
  if (process.env.FAL_API_KEY) return process.env.FAL_API_KEY;
  if (process.env.FAL_KEY) return process.env.FAL_KEY;

  // Try to read from local config if user put it there
  const localEnv = path.join(ROOT, 'config', 'fal.local.env');
  if (fs.existsSync(localEnv)) {
    const txt = fs.readFileSync(localEnv, 'utf8');
    const m = txt.match(/FAL_API_KEY=([^\r\n]+)/);
    if (m) return m[1].trim();
  }
  return null;
}

async function falGenerate({ prompt, width, height, model = 'flux-pro', apiKey, numImages = 1, guidanceScale, steps }) {
  // Fal.ai queue endpoint for flux-pro
  // Models: fal-ai/flux-pro , fal-ai/flux-pro/v1.1-ultra , fal-ai/flux/dev etc.
  const modelPath = model === 'flux-pro' || model === 'flux' ? 'fal-ai/flux-pro' : `fal-ai/${model}`;

  const payload = {
    prompt: prompt,
    image_size: (width && height) ? { width: Number(width), height: Number(height) } : 'landscape_16_9',
    num_images: numImages,
    enable_safety_checker: false,
  };
  if (guidanceScale) payload.guidance_scale = guidanceScale;
  if (steps) payload.num_inference_steps = steps;

  const body = JSON.stringify(payload);

  return new Promise((resolve, reject) => {
    const options = {
      method: 'POST',
      hostname: 'queue.fal.run',
      path: '/' + modelPath,
      headers: {
        'Authorization': 'Key ' + apiKey,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', async () => {
        if (res.statusCode === 200) {
          try {
            const json = JSON.parse(data);
            // For queue, sometimes it returns request_id and you poll, but for sync small jobs fal often gives direct.
            // Check for images or request id.
            if (json.images && json.images.length) return resolve(json);
            if (json.request_id) {
              // Poll status
              return resolve(await pollFalResult(modelPath, json.request_id, apiKey));
            }
            resolve(json);
          } catch (e) { reject(new Error('Bad JSON: ' + data.slice(0,300))); }
        } else if (res.statusCode === 202) {
          // Accepted - poll
          try {
            const j = JSON.parse(data);
            resolve(await pollFalResult(modelPath, j.request_id, apiKey));
          } catch (_) { reject(new Error('202 without request_id: ' + data)); }
        } else {
          reject(new Error('Fal error ' + res.statusCode + ': ' + data));
        }
      });
    });

    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function pollFalResult(modelPath, requestId, apiKey, maxWaitMs = 180000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    await sleep(1200);
    const status = await new Promise((resolve, reject) => {
      const opts = {
        method: 'GET',
        hostname: 'queue.fal.run',
        path: `/${modelPath}/requests/${requestId}/status`,
        headers: { 'Authorization': 'Key ' + apiKey }
      };
      https.get(opts, (r) => {
        let d = '';
        r.on('data', c => d += c);
        r.on('end', () => resolve({ statusCode: r.statusCode, body: d }));
      }).on('error', reject).end();
    });

    if (status.statusCode === 200) {
      const j = JSON.parse(status.body);
      if (j.status === 'COMPLETED') {
        // fetch the result
        const result = await new Promise((res, rej) => {
          const opts = { headers: { Authorization: 'Key ' + apiKey } };
          https.get(`https://queue.fal.run/${modelPath}/requests/${requestId}`, opts, (r2) => {
            let dd = '';
            r2.on('data', c=>dd+=c);
            r2.on('end', () => res(JSON.parse(dd)));
          }).on('error', rej).end();
        });
        return result;
      }
      if (j.status === 'FAILED') throw new Error('Generation failed: ' + JSON.stringify(j));
      // IN_PROGRESS or IN_QUEUE -> continue polling
    }
  }
  throw new Error('Timeout polling Fal result');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function downloadImage(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (res) => {
      if (res.statusCode !== 200) { reject(new Error('DL ' + res.statusCode)); return; }
      res.pipe(file);
      file.on('finish', () => file.close(() => resolve(dest)));
    }).on('error', reject);
  });
}

function parseCli() {
  const argv = process.argv.slice(2);
  const opts = { product: null, prompt: null, width: null, height: null, model: 'flux/dev', key: null, outName: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--product' || a === '-p') opts.product = argv[++i];
    else if (a === '--prompt') opts.prompt = argv[++i];
    else if (a === '--width') opts.width = parseInt(argv[++i], 10);
    else if (a === '--height') opts.height = parseInt(argv[++i], 10);
    else if (a === '--model') opts.model = argv[++i]; // flux-pro | flux-dev | flux/schnell etc.
    else if (a === '--key') opts.key = argv[++i];
    else if (a === '--name') opts.outName = argv[++i];
    else if (a === '--help' || a === '-h') {
      console.log(`
Generatore Flux via Fal.ai + Printify specs

Uso:
  node scripts/generate-flux-design.js --product collar --prompt "un motivo floreale elegante per collare cani, stile luxury, colori oro e bordeaux, seamless lungo la fascia"
  node scripts/generate-flux-design.js --width 3150 --height 1691 --prompt "..." --model flux-pro

Prodotti conosciuti: collar, bandana, tag, bed

Il prompt verrà automaticamente arricchito con le specifiche tecniche del prodotto (dimensioni + tips per dye-sublimation).
`);
      process.exit(0);
    }
  }
  return opts;
}

function buildExcellentPrompt(basePrompt, spec, targetSize) {
  const sizeDesc = targetSize ? `${targetSize.width}x${targetSize.height}px` : 'high resolution';
  const tips = spec ? spec.tips : '';

  // Excellent prompt engineering for Flux (detailed, subject, style, technical constraints)
  let full = basePrompt.trim();

  // Add technical guardrails for POD / dye sublimation
  full += `, high resolution print-ready design for dye-sublimation on fabric, crisp sharp lines, vibrant colors, professional pet product quality, no text overflow, excellent contrast`;

  if (tips) full += `, ${tips}`;

  // Mention exact canvas if known (helps composition)
  if (targetSize) {
    full += `, designed exactly for a printable area of ${targetSize.width} by ${targetSize.height} pixels`;
    if (targetSize.width / targetSize.height > 4) {
      full += `, very wide panoramic composition, long horizontal layout, seamless or continuous pattern across the full width`;
    }
  }

  // Flux loves quality boosters
  full += `, 8k detail, intricate, best quality, award winning design`;

  return full;
}

async function main() {
  const opts = parseCli();
  const apiKey = getFalKey(opts.key);
  if (!apiKey) {
    console.error('FAL_API_KEY mancante. Passa --key "..." oppure imposta variabile d\'ambiente FAL_API_KEY o FAL_KEY.');
    console.error('La chiave la trovi su https://fal.ai/dashboard/keys');
    process.exit(1);
  }

  ensureDir(OUT_DIR);

  let spec = null;
  let targetW = opts.width;
  let targetH = opts.height;

  if (opts.product && PRODUCT_SPECS[opts.product]) {
    spec = PRODUCT_SPECS[opts.product];
    console.log(`\n=== PRODUCT: ${spec.name} (blueprint ${spec.blueprintId}) ===`);
    console.log('Print areas disponibili:');
    spec.printAreas.forEach(a => console.log(`  ${a.label}: ${a.width}x${a.height}px`));

    // pick first / default size if not specified
    if (!targetW || !targetH) {
      const first = spec.printAreas[0];
      targetW = first.width;
      targetH = first.height;
      console.log(`\nUsando dimensione di default: ${targetW}x${targetH} (usa --width --height per altra taglia)`);
    }
  } else if (!targetW || !targetH) {
    console.log('Nessun --product e nessuna --width/--height. Uso aspect landscape predefinito.');
  }

  if (!opts.prompt) {
    console.error('Devi fornire --prompt "descrizione del design"');
    process.exit(1);
  }

  const finalPrompt = buildExcellentPrompt(opts.prompt, spec, (targetW && targetH) ? { width: targetW, height: targetH } : null);

  // Dry run mode: only build prompt, no API call (useful when no balance)
  if (process.argv.includes('--dry-run')) {
    console.log('\n[DRY RUN] Prompt eccellente pronto per Flux:\n');
    console.log(finalPrompt);
    console.log('\nCopia questo prompt su fal.ai o usa --model dopo aver ricaricato il credito.');
    return;
  }

  console.log('\n--- PROMPT FLUX (arricchito) ---');
  console.log(finalPrompt);
  console.log('\nGenerazione in corso con Fal.ai (' + opts.model + ') ...');

  let result;
  try {
    result = await falGenerate({
      prompt: finalPrompt,
      width: targetW,
      height: targetH,
      model: opts.model,
      apiKey,
      numImages: 1
    });
  } catch (e) {
    console.error('Errore generazione Fal:', e.message);
    // Fallback suggestion
    console.log('\nSuggerimento: prova con un aspect ratio più piccolo (es. width 1920 height 80 per collar) se il modello rifiuta dimensioni estreme.');
    process.exit(1);
  }

  const images = result.images || (result.output && result.output.images) || [];
  if (!images.length) {
    console.error('Nessuna immagine restituita. Risposta:', JSON.stringify(result).slice(0, 500));
    process.exit(1);
  }

  const img = images[0];
  const imgUrl = img.url || img.image?.url || img;
  if (!imgUrl) {
    console.error('URL immagine non trovato nella risposta.');
    process.exit(1);
  }

  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const safeName = (opts.outName || (opts.product || 'design') + '-' + ts).replace(/[^a-z0-9_-]/gi, '');
  const ext = (imgUrl.split('?')[0].split('.').pop() || 'png').toLowerCase();
  const destPath = path.join(OUT_DIR, `${safeName}.${ext}`);

  console.log('Download immagine da:', imgUrl);
  await downloadImage(imgUrl, destPath);

  console.log('\n✅ Salvata:', destPath);
  console.log('Dimensione target Printify:', targetW ? `${targetW}x${targetH}` : 'default');

  // Print instructions for next step
  console.log('\n--- PROSSIMI PASSI ---');
  console.log('1. Verifica l\'immagine (usa un editor per ritagliare/riscalare esattamente alla dimensione target se necessario).');
  console.log('2. Caricala su Printify con l\'upload esistente (scripts/perla-upload-endpoint.js o direttamente via API).');
  console.log('3. Crea il prodotto Printify usando il blueprint_id e le print_areas con i placeholder corretti (x,y,scale,angle normalizzati).');
  console.log('\nPer caricare velocemente:');
  console.log('  node scripts/perla-upload-endpoint.js   (in un altro terminale)');
  console.log('  Poi POST /upload con il file.');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
