#!/usr/bin/env node
'use strict';

/**
 * perla-publish-drafts.js
 *
 * Pubblica su Printify (che a sua volta spinge il prodotto sullo store
 * Shopify collegato) una lista esplicita di product id passati come
 * argomenti da riga di comando. Non elenca né sceglie nulla da solo:
 * la lista dei prodotti da pubblicare è stata concordata a parte dopo
 * aver verificato quali bozze sono davvero mai state pubblicate
 * (nessun campo "external") e quali sono doppioni/generazioni superate.
 *
 * Uso:
 *   node scripts/perla-publish-drafts.js <id1> <id2> ...
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

function callPrintify(apiKey, method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const req = https.request('https://api.printify.com/v1' + apiPath, {
      method,
      headers: {
        Authorization: 'Bearer ' + apiKey,
        'User-Agent': 'perla-publish-drafts/1.0',
        'Content-Type': 'application/json',
        ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(data ? JSON.parse(data) : {}); } catch (e) { resolve({ raw: data }); }
        } else {
          reject(new Error('HTTP ' + res.statusCode + ': ' + data.slice(0, 300)));
        }
      });
    });
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function main() {
  const ids = process.argv.slice(2);
  if (!ids.length) {
    console.error('Uso: node scripts/perla-publish-drafts.js <id1> <id2> ...');
    process.exit(1);
  }
  const { apiKey, shopId } = parseEnv();
  const publishBody = {
    title: true,
    description: true,
    images: true,
    variants: true,
    tags: true,
    keyFeatures: true,
    shipping_template: true,
  };

  for (const id of ids) {
    try {
      const before = await callPrintify(apiKey, 'GET', `/shops/${shopId}/products/${id}.json`);
      if (before.external && before.external.id) {
        console.log(`SKIP ${id} (${before.title}) — ha gia' un external.id (${before.external.id}), non lo tocco.`);
        continue;
      }
      await callPrintify(apiKey, 'POST', `/shops/${shopId}/products/${id}/publish.json`, publishBody);
      console.log(`OK pubblicato: ${id} (${before.title})`);
    } catch (err) {
      console.error(`ERRORE su ${id}: ${err.message}`);
    }
  }
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
