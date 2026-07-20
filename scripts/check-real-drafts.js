const fs = require('fs');
const path = require('path');
const https = require('https');
const CONFIG_PATH = path.join(__dirname, '..', 'config', 'printify.local.env');
function parseEnv() {
  const text = fs.readFileSync(CONFIG_PATH, 'utf8');
  function get(key) { const m = text.match(new RegExp('^' + key + '=([^\\r\\n]*)', 'm')); return m && m[1] ? m[1].trim() : ''; }
  return { apiKey: get('PRINTIFY_API_KEY'), shopId: get('PRINTIFY_SHOP_ID') };
}
function callPrintify(apiKey, apiPath) {
  return new Promise((resolve, reject) => {
    const req = https.get('https://api.printify.com/v1' + apiPath, { headers: { 'Authorization': 'Bearer ' + apiKey, 'User-Agent': 'perla-check/1.0' } }, (res) => {
      let data = ''; res.on('data', c => data += c);
      res.on('end', () => { if(res.statusCode>=200&&res.statusCode<300){try { resolve(JSON.parse(data)); } catch(e){ reject(e); }} else reject(new Error('HTTP '+res.statusCode+': '+data.slice(0,200))); });
    });
    req.on('error', reject);
  });
}
async function main() {
  const { apiKey, shopId } = parseEnv();
  let page = 1;
  const trueDrafts = [];
  const alreadyPublished = [];
  const neutral = [];
  for (;;) {
    const resp = await callPrintify(apiKey, `/shops/${shopId}/products.json?page=${page}&limit=50`);
    const items = resp.data || [];
    if (!items.length) break;
    for (const p of items) {
      const isNeutral = (p.tags || []).includes('tipo-neutro');
      const hasExternal = !!(p.external && p.external.id);
      const bucket = isNeutral ? neutral : (hasExternal ? alreadyPublished : trueDrafts);
      bucket.push({ id: p.id, title: p.title, tags: p.tags || [] });
    }
    page++;
    if (page > 20) break;
  }
  console.log('=== VERI DRAFT (nessun external.id) ===');
  console.log('Totale:', trueDrafts.length);
  trueDrafts.forEach((p,i) => console.log((i+1)+'. '+p.title+' | id='+p.id+' | tags='+p.tags.join(', ')));
  console.log('\n=== GIA PUBBLICATI (falsi positivi dello script vecchio) ===');
  console.log('Totale:', alreadyPublished.length);
  alreadyPublished.forEach(p => console.log('- '+p.title+' | id='+p.id));
  console.log('\n=== NEUTRI IN BOZZA (esclusi) ===');
  console.log('Totale:', neutral.length);
}
main().catch(e => { console.error('FATAL', e); process.exit(1); });
