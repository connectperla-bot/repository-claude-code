#!/usr/bin/env node
'use strict';

/**
 * create-full-variants-drafts.js
 * 
 * Crea prodotti in bozza su Printify con:
 * - SOLO pattern + logo "Perla Italia" (nessun altro brand)
 * - TUTTE le taglie e colori abilitati per il collare
 * 
 * Uso: node scripts/create-full-variants-drafts.js
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const DESIGNS_DIR = path.join(ROOT, 'generated-designs');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');

function parseEnv() {
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  const apiKey = (text.match(/PRINTIFY_API_KEY=([^\r\n]+)/) || [])[1]?.trim();
  const shopId = (text.match(/PRINTIFY_SHOP_ID=(\d+)/) || [])[1];
  if (!apiKey || !shopId) throw new Error('Credenziali Printify mancanti');
  return { apiKey, shopId };
}

function callPrintify(apiKey, method, apiPath, body) {
  const data = body ? JSON.stringify(body) : null;
  const options = {
    method,
    hostname: 'api.printify.com',
    path: '/v1' + apiPath,
    headers: {
      'Authorization': 'Bearer ' + apiKey,
      'Content-Type': 'application/json'
    }
  };
  if (data) options.headers['Content-Length'] = Buffer.byteLength(data);

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', c => chunks += c);
      res.on('end', () => {
        let parsed; try { parsed = JSON.parse(chunks); } catch { parsed = chunks; }
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(parsed);
        else reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(parsed).slice(0,400)}`));
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function uploadImage(apiKey, filePath, fileName) {
  const base64 = fs.readFileSync(filePath).toString('base64');
  const res = await callPrintify(apiKey, 'POST', '/uploads/images.json', {
    file_name: fileName,
    contents: base64
  });
  console.log(`    Uploaded: ${fileName} → ${res.id}`);
  return res.id;
}

async function createFullCollarProduct(apiKey, shopId, design) {
  // Tutti i 12 variant IDs del collare (da fetch reale)
  const S = [74897, 74898, 74900];
  const M = [74901, 74902, 74904];
  const L = [74905, 74906, 74908];
  const XL = [74909, 74910, 74912];

  const variants = [...S, ...M, ...L, ...XL].map(id => ({
    id,
    price: 2499,
    is_enabled: true
  }));

  const print_areas = [
    { variant_ids: S,   placeholders: [{ position: 'front', images: [{ id: design.imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] },
    { variant_ids: M,   placeholders: [{ position: 'front', images: [{ id: design.imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] },
    { variant_ids: L,   placeholders: [{ position: 'front', images: [{ id: design.imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] },
    { variant_ids: XL,  placeholders: [{ position: 'front', images: [{ id: design.imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] }
  ];

  const body = {
    title: design.title,
    description: design.description + '\n\nYour best friend deserves the best. This personalized collar combines Italian elegance with premium materials — clean lines, soft durable fabric or leather, secure buckle. As loved by real pets Aron & Mia.\n\n- Premium materials: soft, resistant, easy to clean\n- Secure hardware: rust-resistant buckle, strong D-ring\n- Comfort padding\n- Sizes: S, M, L, XL (fits small to large breeds)\n\nPersonalize with your dog\'s name at checkout.\n\nShips within the USA in 3-8 business days. FREE over $59.\n\nCountry of Origin: varies by provider. Complies with applicable U.S. consumer product safety regulations. Always supervise your pet. Personalized items are final sale.',
    blueprint_id: 784,
    print_provider_id: 93,
    variants,
    print_areas,
    tags: ['perla-italia', 'luxury-pet', 'collar', 'pattern']
  };

  const product = await callPrintify(apiKey, 'POST', `/shops/${shopId}/products.json`, body);
  console.log(`    ✓ DRAFT creato: ${design.title} → id=${product.id}`);
  return product;
}

async function main() {
  const { apiKey, shopId } = parseEnv();
  console.log(`\n=== Creazione bozze COLLARI con TUTTE le taglie/colori (Shop ${shopId}) ===\n`);

  // Nuovi design ad alta qualità - circa 10 varianti
  // Solo pattern + Perla Italia, full coverage, colori particolari
  const collarFiles = fs.readdirSync(DESIGNS_DIR)
    .filter(f => f.startsWith('collar-') && f.endsWith('-perla.jpg'))
    .sort();

  const collarDesigns = collarFiles.map((file, idx) => {
    const base = file.replace('collar-', '').replace('-perla.jpg', '');
    const niceName = base.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    return {
      file,
      title: `Perla Italia - Collare ${niceName}`,
      description: `Exclusive ${niceName} design with full edge-to-edge coverage, no white margins. Only Perla Italia monogram. High resolution, pattern fills the entire product. Designed in Italy, curated with Italian taste. Ships USA 3-8 days FREE over $59. Complies with U.S. safety standards (CPSIA/Prop 65 where applicable). Personalized items final sale. Tested on Aron & Mia.`
    };
  });

  for (const d of collarDesigns) {
    const filePath = path.join(DESIGNS_DIR, d.file);
    if (!fs.existsSync(filePath)) {
      console.log(`  ! File mancante: ${d.file} — salto`);
      continue;
    }

    console.log(`\n→ ${d.title}`);
    try {
      const imageId = await uploadImage(apiKey, filePath, d.file);
      d.imageId = imageId;
      await createFullCollarProduct(apiKey, shopId, d);
    } catch (e) {
      console.error(`   Errore: ${e.message}`);
    }
  }

  console.log('\n=== Completato ===');
  console.log('Vai su Printify > Products e cerca "Perla Italia - Collare"');
  console.log('Ogni prodotto ha tutte le 12 varianti (S/M/L/XL × 3 colori) abilitate.');
  console.log('Apri i prodotti per vedere i mockup e regolare se necessario.');
}

main().catch(console.error);
