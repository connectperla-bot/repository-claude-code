#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const DESIGNS = path.join(ROOT, 'generated-designs');
const env = fs.readFileSync(path.join(ROOT, 'config/printify.local.env'), 'utf8');
const API_KEY = env.match(/PRINTIFY_API_KEY=([^\r\n]+)/)[1].trim();
const SHOP = '27790439';

function post(path, body) {
  const d = JSON.stringify(body);
  return new Promise((resolve, reject) => {
    const req = https.request({
      method: 'POST',
      hostname: 'api.printify.com',
      path: '/v1' + path,
      headers: { 'Authorization': 'Bearer ' + API_KEY, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(d) }
    }, (res) => {
      let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b)));
    });
    req.on('error', reject); req.write(d); req.end();
  });
}

async function main() {
  console.log('Creazione bandane con pattern full coverage e colori speciali...\n');

  const newBandanas = [
    { file: 'bandana-damask-burgundy-perla.jpg', title: 'Perla Italia - Bandana Damasco Borgogna', desc: 'Complete damask pattern full coverage, no white cuts. Perla Italia monogram only. Special burgundy gold color. Premium Italian design for your pet. USA 3-8 days FREE over $59. Complies with U.S. textile safety standards. Personalized final sale.' },
    { file: 'bandana-botanical-emerald-perla.jpg', title: 'Perla Italia - Bandana Botanico Smeraldo', desc: 'Botanical full coverage edge to edge pattern. Perla Italia monogram. Emerald cream luxury palette. Italian elegance. Ships USA 3-8 days FREE over $59. Meets U.S. regs. Final sale if personalized.' }
  ];

  for (const b of newBandanas) {
    const b64 = fs.readFileSync(path.join(DESIGNS, b.file)).toString('base64');
    const up = await post('/uploads/images.json', { file_name: b.file, contents: b64 });
    console.log('Uploaded:', b.file, '->', up.id);
    const prod = await post(`/shops/${SHOP}/products.json`, {
      title: b.title,
      description: b.desc + ' Premium Italian design, full coverage. USA 3-8 days FREE over $59. Complies with U.S. regs. Personalized final sale.',
      blueprint_id: 562, print_provider_id: 70,
      variants: [{ id: 101403, price: 1899, is_enabled: true }],
      print_areas: [{ variant_ids: [101403], placeholders: [{ position: 'front', images: [{ id: up.id, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }] }] }]
    });
    console.log('DRAFT:', b.title, '->', prod.id);
  }

  console.log('\nFatto bandane! Cerca nel dashboard.');
}

main().catch(console.error);
