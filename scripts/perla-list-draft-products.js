#!/usr/bin/env node
'use strict';

/**
 * perla-list-draft-products.js
 *
 * Script di SOLA LETTURA: elenca tutti i prodotti in stato "draft" su
 * Printify, esclusi quelli taggati tipo-neutro (quelli si gestiscono a
 * parte, vedi perla-create-neutral-products.js). Non pubblica, non
 * modifica, non cancella nulla.
 *
 * Motivo per cui esiste come passo separato: pubblicare in blocco prodotti
 * Printify li rende visibili sullo store reale. Prima di farlo bisogna
 * vedere l'elenco esatto (quanti sono, quali titoli) e confermarlo --
 * uno script di pubblicazione vero verra' scritto SOLO dopo aver
 * controllato questo elenco insieme.
 *
 * Uso:
 *   node scripts/perla-list-draft-products.js
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
      headers: { 'Authorization': 'Bearer ' + apiKey, 'User-Agent': 'perla-list-drafts/1.0' },
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
  const { apiKey, shopId } = parseEnv();
  let page = 1;
  const drafts = [];
  const neutral = [];

  for (;;) {
    const resp = await callPrintify(apiKey, `/shops/${shopId}/products.json?page=${page}&limit=50`);
    const items = resp.data || [];
    if (!items.length) break;
    for (const p of items) {
      if (p.visible === false || p.is_locked === false) {
        // fallthrough, Printify draft state is tracked separately below
      }
    }
    for (const p of items) {
      const isNeutral = (p.tags || []).includes('tipo-neutro');
      // Printify products are "draft" (not published) when they have no
      // linked external (Shopify) publish, i.e. p.visible === false or
      // there is no entry in p.external / not is_published.
      const isDraft = !p.is_locked && (!p.external || p.visible === false || !p.published_at);
      if (isNeutral) { if (isDraft) neutral.push(p); continue; }
      if (isDraft) drafts.push(p);
    }
    if (!resp.next_page_url && items.length < 50) break;
    page++;
    if (page > 20) break; // safety cap
  }

  console.log(`\n=== Prodotti Printify in bozza (esclusi i ${neutral.length} tipo-neutro) ===\n`);
  if (!drafts.length) {
    console.log('Nessun prodotto in bozza trovato (a parte gli eventuali neutri, gestiti a parte).');
  } else {
    drafts.forEach((p, i) => {
      console.log(`${i + 1}. ${p.title}`);
      console.log(`   id=${p.id} | tags=${(p.tags || []).join(', ')}`);
    });
    console.log(`\nTotale: ${drafts.length} prodotti in bozza.`);
  }
  console.log(`\n(${neutral.length} prodotti tipo-neutro in bozza esclusi da questo elenco -- gestiti separatamente.)`);
  console.log('\nQuesto script NON ha pubblicato o modificato nulla. Solo lettura.');
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
