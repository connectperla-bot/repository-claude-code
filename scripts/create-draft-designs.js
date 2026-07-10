#!/usr/bin/env node
'use strict';

/**
 * create-draft-designs.js
 * 
 * Carica immagini generate su Printify e crea PRODOTTI IN BOZZA (draft).
 * Non tocca nessun prodotto esistente.
 * 
 * Uso:
 *   node scripts/create-draft-designs.js
 * 
 * Dopo l'esecuzione vai su Printify > Products e vedrai le bozze.
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
  if (!apiKey || !shopId) throw new Error('PRINTIFY_API_KEY o SHOP_ID mancanti');
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
      'Content-Type': 'application/json',
      'User-Agent': 'perla-draft-creator/1.0'
    }
  };
  if (data) options.headers['Content-Length'] = Buffer.byteLength(data);

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', c => chunks += c);
      res.on('end', () => {
        const status = res.statusCode;
        let parsed;
        try { parsed = JSON.parse(chunks); } catch (_) { parsed = chunks; }
        if (status >= 200 && status < 300) {
          resolve(parsed);
        } else {
          reject(new Error(`HTTP ${status}: ${JSON.stringify(parsed).slice(0, 500)}`));
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function uploadImage(apiKey, filePath, fileName) {
  const buffer = fs.readFileSync(filePath);
  const base64 = buffer.toString('base64');

  const res = await callPrintify(apiKey, 'POST', '/uploads/images.json', {
    file_name: fileName,
    contents: base64
  });
  console.log(`  ✓ Uploaded: ${fileName} → id=${res.id}`);
  return res.id;
}

async function createDraftProduct(apiKey, shopId, design) {
  const body = {
    title: design.title,
    description: (design.description || 'Exclusive Perla Italy design.') + '\n\nDesigned in Italy, curated with Italian taste. Premium materials. As loved by Aron & Mia.\n\nUSA: 3-8 days, FREE over $59.\n\nComplies with U.S. safety standards. Country of Origin varies. Personalized final sale.',
    blueprint_id: design.blueprintId,
    print_provider_id: design.providerId,
    variants: [
      {
        id: design.variantId,
        price: design.price || 2499,   // 24.99 € in centesimi (modifica se vuoi)
        is_enabled: true
      }
    ],
    print_areas: [
      {
        variant_ids: [design.variantId],
        placeholders: [
          {
            position: design.position || 'front',
            images: [
              {
                id: design.imageId,
                x: design.x !== undefined ? design.x : 0.5,
                y: design.y !== undefined ? design.y : 0.5,
                scale: design.scale !== undefined ? design.scale : 1.0,
                angle: 0
              }
            ]
          }
        ]
      }
    ],
    // tags opzionale
    tags: ['perla-italy', 'luxury', 'pet', design.tag || 'design']
  };

  const product = await callPrintify(apiKey, 'POST', `/shops/${shopId}/products.json`, body);
  console.log(`  ✓ Created DRAFT: ${design.title} → id=${product.id}`);
  return product;
}

async function main() {
  const { apiKey, shopId } = parseEnv();
  console.log(`\n=== Creazione bozze Printify (Shop ${shopId}) ===\n`);

  // === DEFINISCI QUI I DESIGN DA CREARE ===
  // Usa le dimensioni reali dal catalogo
  const designsToCreate = [
    // === 2 COLLARI ===
    {
      file: 'collar-damask-gold-burgundy.jpg',
      title: 'Perla Italy Luxury - Collare Damasco Oro Borgogna',
      blueprintId: 784,
      providerId: 93,
      variantId: 74897,           // S / Black Onyx / TPU
      position: 'front',
      x: 0.5,
      y: 0.5,
      scale: 1.0,
      description: 'Elegant damask with subtle Perla Italia monogram. Italian elegance, premium. Full coverage collar.\n\nUSA: 3-8 days FREE over $59.\n\nComplies with U.S. regs. Final sale if personalized.',
      tag: 'collar'
    },
    {
      file: 'collar-botanical-olive-gold.jpg',
      title: 'Perla Italy Luxury - Collare Botanico Ulivo Oro',
      blueprintId: 784,
      providerId: 93,
      variantId: 74897,           // S / Black Onyx
      position: 'front',
      x: 0.5,
      y: 0.5,
      scale: 1.0,
      description: 'Botanical olive with Perla Italia monogram. Minimal luxury. Full coverage collar.\n\nUSA: 3-8 days FREE over $59.\n\nComplies with U.S. regs. Final sale if personalized.',
      tag: 'collar'
    },

    // === BANDANA ===
    {
      file: 'bandana-damask-monogram.jpg',
      title: 'Perla Italy Luxury - Bandana Damasco Monogramma',
      blueprintId: 562,
      providerId: 70,
      variantId: 101403,          // 20" × 10"
      position: 'front',
      x: 0.5,
      y: 0.5,
      scale: 1.0,
      description: 'Coordinated damask bandana with Perla Italia monogram. Premium fabric, full coverage.\n\nUSA: 3-8 days FREE over $59.\n\nComplies with U.S. textile regs. Final sale if personalized.',
      tag: 'bandana'
    },

    // === MEDAGLIETTA ===
    {
      file: 'medaglietta-tag-luxury.jpg',
      title: 'Perla Italy Luxury - Medaglietta Monogramma',
      blueprintId: 566,
      providerId: 70,
      variantId: 70870,
      position: 'front',
      x: 0.5,
      y: 0.5,
      scale: 1.0,
      description: 'Elegant tag with Perla Italia monogram. Minimal legible design.\n\nUSA: 3-8 days FREE over $59.\n\nComplies with U.S. safety. Final sale if personalized.',
      tag: 'tag'
    },

    // === CUCCIA ===
    {
      file: 'cuccia-bed-damask.jpg',
      title: 'Perla Italy Luxury - Cuccia Damasco Elegante',
      blueprintId: 419,
      providerId: 10,
      variantId: 61436,           // 28" × 18"
      position: 'front',
      x: 0.5,
      y: 0.5,
      scale: 1.0,
      description: 'Luxury bed with damask pattern. Premium, full coverage.\n\nUSA: 3-8 days FREE over $59.\n\nComplies with U.S. safety. Non-toxic.',
      tag: 'bed'
    }
  ];

  for (const d of designsToCreate) {
    const filePath = path.join(DESIGNS_DIR, d.file);
    if (!fs.existsSync(filePath)) {
      console.warn(`  ! File non trovato: ${d.file} — salto`);
      continue;
    }

    console.log(`\n→ Processing: ${d.title}`);
    try {
      // 1. Upload
      const imageId = await uploadImage(apiKey, filePath, d.file);

      // 2. Create draft product
      d.imageId = imageId;
      const product = await createDraftProduct(apiKey, shopId, d);

      console.log(`   Dashboard link (approx): https://printify.com/app/product/${product.id}  (o cerca nel dashboard)`);
    } catch (err) {
      console.error(`   ERRORE: ${err.message}`);
    }
  }

  console.log('\n=== FINE ===');
  console.log('Vai su Printify Dashboard → Products');
  console.log('Dovresti vedere le nuove bozze con titolo "Perla Italy Luxury - ..."');
  console.log('Puoi aprirle, regolare il posizionamento, cambiare variante/colore e pubblicare quando vuoi.');
  console.log('\nNessun prodotto esistente è stato modificato.');
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
