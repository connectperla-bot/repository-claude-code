#!/usr/bin/env node
'use strict';

/**
 * perla-create-neutral-products.js
 *
 * Crea su Printify 6 prodotti DRAFT "neutri" (tipo 3: da personalizzare da
 * zero), ciascuno col solo logo Perla Italia (perla + scritta) piccolo
 * nell'angolo, come da richiesta del merchant. Non tocca nessun prodotto
 * esistente. Esclude il guinzaglio su istruzione esplicita del merchant.
 *
 * Riusa lo stesso pattern di scripts/create-draft-designs.js (upload
 * immagine + creazione prodotto draft), con blueprint/provider/variante presi
 * dagli stessi ID gia' usati in render.yaml / config/printify.local.env per
 * lo studio di personalizzazione, cosi' il prodotto neutro e' compatibile
 * con lo stesso flusso ordini.
 *
 * Uso:
 *   node scripts/perla-create-neutral-products.js
 *
 * Dopo l'esecuzione:
 *   1. Vai su Printify > Products, apri ciascuna bozza "Perla Italy — Neutro ..."
 *      e pubblicala su Shopify quando sei pronto (o lasciala in bozza per ora).
 *   2. Copia il "printify_product_id" stampato per ciascun tipo e impostalo
 *      come metafield printify_custom.printify_product_id sul prodotto
 *      Shopify corrispondente (tag personalizzabile + tipo-neutro).
 *   3. Copia l'IMAGE ID del logo stampato all'inizio e impostalo come
 *      variabile PERLA_LOGO_IMAGE_ID sul servizio perla-printify-order-sync
 *      su Render — cosi' lo stesso logo viene aggiunto automaticamente anche
 *      agli ordini personalizzati con foto/nome.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const LOGO_PATH = path.join(ROOT, 'generated-designs', 'perla-combined-logo.png');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');

function parseEnv() {
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  function get(key, fallback) {
    const m = text.match(new RegExp('^' + key + '=([^\\r\\n]*)', 'm'));
    const v = m && m[1] ? m[1].trim() : '';
    return v || fallback;
  }
  const apiKey = get('PRINTIFY_API_KEY', '');
  const shopId = get('PRINTIFY_SHOP_ID', '');
  if (!apiKey || !shopId) throw new Error('PRINTIFY_API_KEY o PRINTIFY_SHOP_ID mancanti in config/printify.local.env');
  return { apiKey, shopId, get };
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
      'User-Agent': 'perla-neutral-products/1.0',
    },
  };
  if (data) options.headers['Content-Length'] = Buffer.byteLength(data);

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', (c) => (chunks += c));
      res.on('end', () => {
        const status = res.statusCode;
        let parsed;
        try { parsed = JSON.parse(chunks); } catch (_) { parsed = chunks; }
        if (status >= 200 && status < 300) resolve(parsed);
        else reject(new Error(`HTTP ${status}: ${JSON.stringify(parsed).slice(0, 500)}`));
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
    contents: base64,
  });
  console.log(`  Uploaded ${fileName} -> image id = ${res.id}`);
  return res.id;
}

async function createNeutralProduct(apiKey, shopId, def, logoImageId) {
  const body = {
    title: `Perla Italy — ${def.label} Neutro (personalizza il tuo design)`,
    description:
      'Base neutra Perla Italia: crea il tuo design da zero nello studio di personalizzazione del sito — foto, testo e adesivi a tua scelta. ' +
      'Il piccolo marchio Perla Italia resta sempre visibile per garantire l\'autenticita\' del prodotto.\n\n' +
      'Materiali premium, spedizione tracciata. Prodotto personalizzato: vendita finale.',
    blueprint_id: def.blueprintId,
    print_provider_id: def.providerId,
    variants: [{ id: def.variantId, price: def.price, is_enabled: true }],
    print_areas: [
      {
        variant_ids: [def.variantId],
        placeholders: [
          {
            position: 'front',
            images: [
              {
                id: logoImageId,
                x: 0.82,
                y: 0.82,
                scale: 0.12,
                angle: 0,
              },
            ],
          },
        ],
      },
    ],
    tags: ['perla-italy', 'personalizzabile', 'tipo-neutro', def.tag],
  };
  const product = await callPrintify(apiKey, 'POST', `/shops/${shopId}/products.json`, body);
  console.log(`  Created DRAFT: ${def.label} -> printify_product_id = ${product.id}`);
  return product;
}

async function main() {
  const { apiKey, shopId, get } = parseEnv();
  if (!fs.existsSync(LOGO_PATH)) {
    throw new Error('Logo non trovato: ' + LOGO_PATH + ' (generated-designs/perla-combined-logo.png)');
  }

  console.log(`\n=== Creazione 6 prodotti neutri Perla Italia (Shop ${shopId}) ===\n`);

  console.log('1. Carico il logo su Printify...');
  const logoImageId = await uploadImage(apiKey, LOGO_PATH, 'perla-combined-logo.png');
  console.log(`\n   >>> PERLA_LOGO_IMAGE_ID = ${logoImageId}`);
  console.log('   Imposta questo valore come variabile PERLA_LOGO_IMAGE_ID sul servizio');
  console.log('   perla-printify-order-sync su Render, cosi\' il logo compare anche sugli');
  console.log('   ordini personalizzati con foto/nome.\n');

  // Esclude il guinzaglio su istruzione esplicita del merchant.
  const defs = [
    { key: 'COLLARE', label: 'Collare', tag: 'collare', price: 2499 },
    { key: 'BANDANA', label: 'Bandana', tag: 'bandana', price: 2299 },
    { key: 'MEDAGLIETTA', label: 'Medaglietta', tag: 'medaglietta', price: 1899 },
    { key: 'CIOTOLA', label: 'Ciotola', tag: 'ciotola', price: 2799 },
    { key: 'CUCCIA', label: 'Cuccia', tag: 'cuccia', price: 6999 },
    { key: 'TAPPETINO', label: 'Tappetino', tag: 'tappetino', price: 3499 },
  ];

  console.log('2. Creo i 6 prodotti draft...\n');
  const results = [];
  for (const d of defs) {
    const blueprintId = Number(get(d.key + '_BLUEPRINT_ID', ''));
    const providerId = Number(get(d.key + '_PROVIDER_ID', ''));
    const variantId = Number(get(d.key + '_VARIANT_ID', ''));
    if (!blueprintId || !providerId || !variantId) {
      console.warn(`  ! ${d.label}: blueprint/provider/variante non configurati in config/printify.local.env — salto.`);
      console.warn(`    Imposta ${d.key}_VARIANT_ID (vedi config/printify.env.example).`);
      continue;
    }
    try {
      const product = await createNeutralProduct(apiKey, shopId, { ...d, blueprintId, providerId, variantId }, logoImageId);
      results.push({ type: d.tag, printify_product_id: product.id });
    } catch (err) {
      console.error(`  ERRORE su ${d.label}: ${err.message}`);
    }
  }

  console.log('\n=== FINE ===');
  console.log('Riepilogo da incollare per collegare i metafield Shopify:\n');
  console.log(JSON.stringify(results, null, 2));
  console.log('\nNessun prodotto esistente e\' stato modificato. I nuovi prodotti sono in bozza su Printify.');
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
