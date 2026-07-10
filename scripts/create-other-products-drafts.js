#!/usr/bin/env node
'use strict';

/**
 * create-other-products-drafts.js
 * 
 * Crea bozze per bandane, tag, cucce con:
 * - Pattern full coverage (x=0.5 y=0.5 scale=1.0)
 * - Solo Perla Italia
 * - Colori speciali
 * - Alta qualità
 * - Adattato all'oggetto
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
  if (!apiKey || !shopId) throw new Error('Credenziali mancanti');
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
        else reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(parsed).slice(0,300)}`));
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
  return res.id;
}

async function createProduct(apiKey, shopId, config) {
  const body = {
    title: config.title,
    description: config.description,
    blueprint_id: config.blueprintId,
    print_provider_id: config.providerId,
    variants: config.variants,
    print_areas: config.printAreas,
    tags: ['perla-italia', 'luxury-pet', config.type]
  };

  const product = await callPrintify(apiKey, 'POST', `/shops/${shopId}/products.json`, body);
  console.log(`  ✓ ${config.title} → ${product.id}`);
  return product;
}

async function main() {
  const { apiKey, shopId } = parseEnv();
  console.log(`\n=== Creazione bozze per Bandane, Tag, Cucce (Shop ${shopId}) ===\n`);

  // Bandana - usa 101403 (20x10), abilita anche 101404 se vogliamo
  const bandanaFiles = fs.readdirSync(DESIGNS_DIR).filter(f => f.startsWith('bandana-') && f.endsWith('-perla.jpg')).sort();
  for (const file of bandanaFiles) {
    const base = file.replace('bandana-', '').replace('-perla.jpg', '').replace(/-/g, ' ');
    const title = `Perla Italia - Bandana ${base.charAt(0).toUpperCase() + base.slice(1)}`;
    console.log(`\n→ ${title}`);
    try {
      const imageId = await uploadImage(apiKey, path.join(DESIGNS_DIR, file), file);
      await createProduct(apiKey, shopId, {
        title,
        description: `Your dog deserves style. This custom bandana combines Italian design with premium fabric — full coverage, comfortable. As loved by Aron & Mia.\n\n- Soft breathable fabric\n- Vibrant full print\n- Sizes: 20"×10" and 27"×13"\n\nPersonalize with your pet's name.\n\nUSA: 3-8 days, FREE over $59.\n\nCountry of Origin varies. Complies with U.S. textile regs. Personalized final sale.`,
        blueprintId: 562,
        providerId: 70,
        variants: [
          { id: 101403, price: 1899, is_enabled: true },
          { id: 101404, price: 2299, is_enabled: true }  // abilita entrambe le taglie
        ],
        printAreas: [
          { variant_ids: [101403, 101404], placeholders: [{ position: 'front', images: [{ id: imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] }
        ],
        type: 'bandana'
      });
    } catch (e) { console.error('  Errore:', e.message); }
  }

  // Tag
  const tagFiles = fs.readdirSync(DESIGNS_DIR).filter(f => f.startsWith('tag-') && f.endsWith('-perla.jpg')).sort();
  for (const file of tagFiles) {
    const base = file.replace('tag-', '').replace('-perla.jpg', '').replace(/-/g, ' ');
    const title = `Perla Italia - Tag ${base.charAt(0).toUpperCase() + base.slice(1)}`;
    console.log(`\n→ ${title}`);
    try {
      const imageId = await uploadImage(apiKey, path.join(DESIGNS_DIR, file), file);
      await createProduct(apiKey, shopId, {
        title,
        description: `Stylish ID tag with your pet's name. Elegant metal, Italian design. Legible and durable.\n\n- 1" round metal tag\n- Print on both sides\n- Includes clip\n\nPersonalize name + contact.\n\nUSA: 3-8 days, FREE over $59.\n\nComplies with U.S. safety standards. Final sale if personalized.`,
        blueprintId: 566,
        providerId: 70,
        variants: [{ id: 70870, price: 1499, is_enabled: true }],
        printAreas: [{ variant_ids: [70870], placeholders: [{ position: 'front', images: [{ id: imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] }],
        type: 'tag'
      });
    } catch (e) { console.error('  Errore:', e.message); }
  }

  // Cuccia - usa 61436 (28x18) come principale, abilita altre se vogliamo
  const cucciaFiles = fs.readdirSync(DESIGNS_DIR).filter(f => f.startsWith('cuccia-') && f.endsWith('-perla.jpg')).sort();
  for (const file of cucciaFiles) {
    const base = file.replace('cuccia-', '').replace('-perla.jpg', '').replace(/-/g, ' ');
    const title = `Perla Italia - Cuccia ${base.charAt(0).toUpperCase() + base.slice(1)}`;
    console.log(`\n→ ${title}`);
    try {
      const imageId = await uploadImage(apiKey, path.join(DESIGNS_DIR, file), file);
      await createProduct(apiKey, shopId, {
        title,
        description: `Luxury rest for your dog. Orthopedic support, premium materials, Italian design. Perfect for all ages. As tested by Aron & Mia.\n\n- Orthopedic foam\n- Removable washable cover\n- Non-slip bottom\n- Multiple sizes\n\nUSA: 3-8 days, FREE over $59.\n\nComplies with U.S. safety regs. Non-toxic.`,
        blueprintId: 419,
        providerId: 10,
        variants: [
          { id: 61436, price: 4999, is_enabled: true }, // 28x18 main
          { id: 61437, price: 6999, is_enabled: true }  // 40x30
        ],
        printAreas: [
          { variant_ids: [61436, 61437], placeholders: [{ position: 'front', images: [{ id: imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] }
        ],
        type: 'cuccia'
      });
    } catch (e) { console.error('  Errore:', e.message); }
  }

  console.log('\n=== Completato ===');
  console.log('Vai su Printify > Products e cerca "Perla Italia" per vedere le nuove bozze.');
  console.log('Pattern adattati all\'oggetto, full coverage, alta qualità.');
}

main().catch(console.error);
