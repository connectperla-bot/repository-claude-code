#!/usr/bin/env node
'use strict';

/**
 * perla-list-product-mockups.js
 *
 * Script di SOLA LETTURA: stampa le immagini mockup che Printify ha gia'
 * generato per una lista di printify_product_id, cosi' si possono usare
 * come immagini prodotto su Shopify senza doverle scaricare/ricaricare a
 * mano. Non crea, modifica o pubblica nulla su Printify o Shopify.
 *
 * Uso:
 *   node scripts/perla-list-product-mockups.js <id1> <id2> ...
 *
 * Esempio (i 5 prodotti neutri appena creati):
 *   node scripts/perla-list-product-mockups.js 6a5181523a9be4cece034a42 6a5181550077243f5804f726 6a518156c25325ab6a024442 6a5181580077243f5804f727 6a5181599813f5e64306ce2e
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');

function parseEnv() {
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  function get(key) {
    const m = text.match(new RegExp('^' + key + '=([^\\r\\n]*)', 'm'));
    return m && m[1] ? m[1].trim() : '';
  }
  const apiKey = get('PRINTIFY_API_KEY');
  const shopId = get('PRINTIFY_SHOP_ID');
  if (!apiKey || !shopId) throw new Error('PRINTIFY_API_KEY o PRINTIFY_SHOP_ID mancanti in config/printify.local.env');
  return { apiKey, shopId };
}

function callPrintify(apiKey, apiPath) {
  return new Promise((resolve, reject) => {
    const req = https.get('https://api.printify.com/v1' + apiPath, {
      headers: { 'Authorization': 'Bearer ' + apiKey, 'User-Agent': 'perla-list-mockups/1.0' },
    }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
        } else {
          reject(new Error('HTTP ' + res.statusCode + ': ' + data.slice(0, 300)));
        }
      });
    });
    req.on('error', reject);
  });
}

async function main() {
  const ids = process.argv.slice(2);
  if (!ids.length) {
    console.error('Uso: node scripts/perla-list-product-mockups.js <printify_product_id> [altri...]');
    process.exit(1);
  }
  const { apiKey, shopId } = parseEnv();

  for (const id of ids) {
    console.log(`\n=== ${id} ===`);
    try {
      const product = await callPrintify(apiKey, `/shops/${shopId}/products/${id}.json`);
      console.log('Titolo:', product.title);
      (product.images || []).forEach((img, i) => {
        console.log(`  [${i}] ${img.src}${img.is_default ? '  (default)' : ''}`);
      });
      if (!product.images || !product.images.length) {
        console.log('  Nessuna immagine mockup trovata (Printify potrebbe non averle ancora generate).');
      }
    } catch (err) {
      console.error('  ERRORE:', err.message);
    }
  }
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
