#!/usr/bin/env node
'use strict';

/**
 * fetch-printify-blueprint.js
 * 
 * Scarica blueprint, print providers, print_areas (dimensioni esatte area di stampa),
 * varianti e metadati da Printify Catalog API.
 * 
 * Uso:
 *   node scripts/fetch-printify-blueprint.js --blueprint 784 --provider 93
 *   node scripts/fetch-printify-blueprint.js --blueprint 562 --provider 70 --save
 *
 * Output:
 *   - Stampa info dettagliate su console
 *   - Se --save: salva JSON in printify-blueprints/<blueprint>_<provider>.json
 *   - Scarica anche le immagini mockup di esempio (se --download-mockups)
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');
const OUT_DIR = path.join(ROOT, 'printify-blueprints');

function parseEnv() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('Config non trovato:', CONFIG_PATH);
    process.exit(1);
  }
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  const keyMatch = text.match(/PRINTIFY_API_KEY=([^\r\n]+)/);
  const shopMatch = text.match(/PRINTIFY_SHOP_ID=(\d+)/);
  if (!keyMatch) throw new Error('PRINTIFY_API_KEY mancante in config');
  return {
    apiKey: keyMatch[1].trim(),
    shopId: shopMatch ? shopMatch[1].trim() : null
  };
}

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

async function callPrintify(apiKey, apiPath) {
  const url = 'https://api.printify.com/v1' + apiPath;
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'User-Agent': 'printify-blueprint-fetcher/1.0'
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
        } else {
          reject(new Error('HTTP ' + res.statusCode + ': ' + data.slice(0, 400)));
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    https.get(url, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error('Download failed ' + res.statusCode));
        return;
      }
      res.pipe(file);
      file.on('finish', () => file.close(() => resolve(destPath)));
    }).on('error', reject);
  });
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { blueprint: null, provider: null, save: false, downloadMockups: false, list: false, search: null };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--blueprint' || args[i] === '-b') out.blueprint = args[++i];
    else if (args[i] === '--provider' || args[i] === '-p') out.provider = args[++i];
    else if (args[i] === '--save' || args[i] === '-s') out.save = true;
    else if (args[i] === '--download-mockups' || args[i] === '-m') out.downloadMockups = true;
    else if (args[i] === '--list' || args[i] === '-l') out.list = true;
    else if (args[i] === '--search' || args[i] === '-q') out.search = args[++i];
    else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Uso: node scripts/fetch-printify-blueprint.js [options]

Opzioni:
  --blueprint 784, -b 784     Blueprint ID (es. 784 = collare)
  --provider 93,  -p 93       Print provider ID (opzionale ma raccomandato)
  --save, -s                  Salva JSON completo nella cartella printify-blueprints/
  --download-mockups, -m      Scarica le immagini mockup ufficiali di Printify
  --list, -l                  Elenca tutti i blueprint disponibili (senza provider)

Esempi:
  node scripts/fetch-printify-blueprint.js -b 784 -p 93 --save
  node scripts/fetch-printify-blueprint.js -b 562 -p 70 --save --download-mockups
`);
      process.exit(0);
    }
  }
  return out;
}

async function main() {
  const args = parseArgs();
  const { apiKey } = parseEnv();

  ensureDir(OUT_DIR);

  if (args.list) {
    console.log('Fetching full blueprint catalog...');
    const list = await callPrintify(apiKey, '/catalog/blueprints.json');
    console.log(`Trovati ${list.length} blueprints nel catalogo.`);
    list.slice(0, 30).forEach(bp => {
      console.log(`  ${bp.id} | ${bp.title} | ${bp.brand || ''} ${bp.model || ''}`);
    });
    if (list.length > 30) console.log(`  ... +${list.length - 30} altri`);
    return;
  }

  if (args.search) {
    console.log('Searching blueprints for:', args.search);
    const list = await callPrintify(apiKey, '/catalog/blueprints.json');
    const q = args.search.toLowerCase();
    const matches = list.filter(bp => (bp.title + ' ' + (bp.description || '')).toLowerCase().includes(q));
    console.log(`Trovati ${matches.length} match per \"${args.search}\":`);
    matches.slice(0, 15).forEach(bp => console.log(`  ${bp.id} - ${bp.title}`));
    return;
  }

  if (!args.blueprint) {
    console.error('Specifica --blueprint ID. Usa --list per vedere la lista.');
    console.error('Esempi noti dal progetto: 784(collare), 562(bandana), 566(medaglietta), 570(ciotola), 419(cuccia), 855(tappetino), 2791(guinzaglio)');
    process.exit(1);
  }

  const bpId = args.blueprint;
  const ppId = args.provider;

  console.log(`\n=== FETCHING BLUEPRINT ${bpId} ${ppId ? 'PROVIDER ' + ppId : ''} ===`);

  // 1. Blueprint base
  const blueprint = await callPrintify(apiKey, `/catalog/blueprints/${bpId}.json`);
  console.log('Title:', blueprint.title);
  console.log('Brand / Model:', blueprint.brand, blueprint.model);
  console.log('Description (first 300 chars):', (blueprint.description || '').replace(/\s+/g, ' ').slice(0, 300));

  // 2. Providers disponibili
  const providers = await callPrintify(apiKey, `/catalog/blueprints/${bpId}/print_providers.json`);
  console.log('\nPrint providers disponibili:');
  providers.forEach(p => console.log(`  - ${p.id}: ${p.title} (location: ${p.location || 'n/a'})`));

  let ppDetail = null;
  let variants = null;

  if (ppId) {
    // 3. Dettaglio provider (contiene spesso print_areas con dimensioni)
    try {
      ppDetail = await callPrintify(apiKey, `/catalog/blueprints/${bpId}/print_providers/${ppId}.json`);
      console.log('\n--- PRINT PROVIDER DETAIL ---');
      console.log('Title:', ppDetail.title);

      if (ppDetail.print_areas && Array.isArray(ppDetail.print_areas)) {
        console.log('\n*** PRINT AREAS (dimensioni esatte area di stampa) ***');
        ppDetail.print_areas.forEach((area, idx) => {
          console.log(`\n  Print Area #${idx}`);
          console.log('    position / name:', area.position || area.name || area.placeholder);
          if (area.print_area) {
            console.log('    print_area dimensions:', JSON.stringify(area.print_area));
            // Typical: { width: XXX, height: YYY, dpi: 300 }
          }
          if (area.placeholders) {
            area.placeholders.forEach(ph => {
              console.log('    placeholder:', ph.position, '-> width:', ph.width, 'height:', ph.height);
            });
          }
          // Sometimes "width", "height" directly on area
          if (area.width || area.height) {
            console.log('    area width/height:', area.width, area.height);
          }
        });
      } else {
        console.log('Nessun print_areas esplicito. Struttura risposta:');
        console.dir(Object.keys(ppDetail));
      }
    } catch (e) {
      console.warn('Impossibile ottenere /print_providers/... .json :', e.message);
    }

    // 4. Varianti (Printify sometimes wraps as {variants: [...] } or returns array directly)
    try {
      const variantsResp = await callPrintify(apiKey, `/catalog/blueprints/${bpId}/print_providers/${ppId}/variants.json`);
      variants = Array.isArray(variantsResp) ? variantsResp : (variantsResp.variants || variantsResp);
      console.log(`\n--- VARIANTS (${(variants || []).length} totali) ---`);
      const sample = (variants || []).slice(0, 4);
      sample.forEach(v => {
        const ph = (v.placeholders && v.placeholders[0]) || {};
        console.log(`  id=${v.id} | ${v.title || v.variant_title} | ${ph.width || '?'}x${ph.height || '?'} px`);
      });
      if ((variants || []).length > 4) console.log(`  ... +${(variants || []).length-4} altri`);

      // Print summary of unique print sizes
      const sizes = {};
      (variants || []).forEach(v => {
        const ph = (v.placeholders && v.placeholders[0]) || {};
        const key = `${ph.width}x${ph.height}`;
        if (!sizes[key]) sizes[key] = { count: 0, examples: [] };
        sizes[key].count++;
        if (sizes[key].examples.length < 2) sizes[key].examples.push(v.title);
      });
      console.log('\n  Unique print area sizes from placeholders:');
      Object.keys(sizes).forEach(k => console.log(`    ${k} px : ${sizes[k].count} variants e.g. ${sizes[k].examples.join(', ')}`));
    } catch (e) {
      console.warn('Variants fetch failed:', e.message);
    }
  }

  // 5. Salva JSON completo
  if (args.save) {
    const outFile = path.join(OUT_DIR, `${bpId}${ppId ? '_' + ppId : ''}.json`);
    const payload = {
      fetchedAt: new Date().toISOString(),
      blueprint,
      providers,
      printProviderDetail: ppDetail,
      variants: variants || []
    };
    fs.writeFileSync(outFile, JSON.stringify(payload, null, 2), 'utf8');
    console.log('\n[Saved]', outFile);
  }

  // 6. Download mockups (immagini di esempio dal blueprint)
  if (args.downloadMockups && blueprint.images && blueprint.images.length) {
    const mockDir = path.join(OUT_DIR, `mockups_${bpId}`);
    ensureDir(mockDir);
    console.log('\nDownloading mockups...');
    for (let i = 0; i < Math.min(blueprint.images.length, 5); i++) {
      const img = blueprint.images[i];
      const ext = (img.src || '').split('.').pop().split('?')[0] || 'jpg';
      const dest = path.join(mockDir, `mockup_${i}.${ext}`);
      try {
        await downloadFile(img.src, dest);
        console.log('  Downloaded:', dest);
      } catch (e) {
        console.warn('  Failed download', img.src, e.message);
      }
    }
  }

  // 7. Riassunto tecnico per la generazione di prompt Flux
  console.log('\n=== RIASSUNTO PER PROMPT FLUX ===');
  console.log('Prodotto:', blueprint.title);
  if (variants && variants.length) {
    const firstPh = variants[0].placeholders && variants[0].placeholders[0];
    if (firstPh) {
      console.log(`Dimensione area di stampa tipica (placeholder): ${firstPh.width}x${firstPh.height} px`);
    }
  }
  console.log('\nPer generare design perfetti:');
  console.log('  node scripts/generate-flux-design.js --product collar --prompt "il tuo motivo..."');
  console.log('  (o specifica --width --height con i valori sopra)');
  console.log('\nSuggerimento per template trasparente:');
  console.log('- Vai su Printify Catalog > apri il prodotto > scarica "Print file template" (PNG con area trasparente).');
  console.log('- In alternativa usa le dimensioni esatte sopra per generare a pixel precisi.');
  console.log('- Il file generato va caricato come immagine di design (non mockup).');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
