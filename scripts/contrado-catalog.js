#!/usr/bin/env node
'use strict';

// Ricognizione del negozio Contrado: legge catalogo, varianti, spedizioni e
// paesi serviti, li stampa in chiaro e li salva in contrado-catalog/.
// SOLA LETTURA: nessuna chiamata di questo script crea o modifica qualcosa.
//
// API "Helix" di Contrado, specifica ufficiale:
//   https://api.contrado.app/helix/swagger/v1/swagger.json
//   (la pagina /helix/docs e' solo il visualizzatore, non leggibile a riga di
//   comando -- il JSON vero e' all'indirizzo qui sopra)
//
// COSA QUESTA API NON FA, ed e' la cosa piu' importante da sapere.
// Il catalogo e' di SOLA LETTURA: gli scope esistenti sono StoresRead,
// StoresCollectionRead, StoreProductsRead, StoreOrdersRead, StoreOrdersWrite.
// Non esiste nessuno scope di scrittura sui prodotti e nessun endpoint per
// caricare un file di stampa. I design si caricano e diventano prodotti solo
// dentro Contrado Store Account. Questo script serve quindi a LEGGERE quello
// che e' gia' stato creato li' e a ricavarne gli id da mettere in
// config/printify.local.env.
//
// Uso:
//   node scripts/contrado-catalog.js --tutto
//   node scripts/contrado-catalog.js --prodotti
//   node scripts/contrado-catalog.js --varianti 591879
//   node scripts/contrado-catalog.js --spedizioni
//   node scripts/contrado-catalog.js --paesi

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');
const OUT_DIR = path.join(ROOT, 'contrado-catalog');

const HOST = 'api.contrado.app';
const BASE = '/helix/v1';

// 100 richieste al minuto dichiarate nella guida ufficiale. Qui si sta
// larghi: 700ms tra una chiamata e l'altra sono ~85/minuto, e nessuna
// ricognizione ha fretta.
const PAUSA_MS = 700;

function leggiConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('Config non trovato:', CONFIG_PATH);
    console.error('Copia config/printify.env.example in config/printify.local.env e inserisci CONTRADO_API_KEY.');
    process.exit(1);
  }
  const testo = fs.readFileSync(CONFIG_PATH, 'utf8');
  function campo(nome) {
    const m = testo.match(new RegExp('^' + nome + '=([^\\r\\n]*)', 'm'));
    return m ? m[1].trim() : '';
  }
  const apiKey = campo('CONTRADO_API_KEY');
  if (!apiKey) {
    console.error('CONTRADO_API_KEY vuota in ' + CONFIG_PATH + '.');
    console.error('Il token si genera in Contrado Store Account -> API Integration.');
    process.exit(1);
  }
  return {
    apiKey,
    storeId: campo('CONTRADO_STORE_ID'),
    cultureCode: campo('CONTRADO_CULTURE_CODE') || 'it-IT',
  };
}

function attendi(ms) {
  return new Promise(function (r) { setTimeout(r, ms); });
}

// Ogni risposta Helix e' incartata in {success, message, data, error}. Qui si
// srotola l'involucro e si restituisce solo `data`, cosi' il resto dello
// script non deve ricordarsene.
function chiama(cfg, percorso, headerExtra) {
  const opzioni = {
    host: HOST,
    path: BASE + percorso,
    method: 'GET',
    headers: Object.assign({
      'X-API-KEY': cfg.apiKey,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    }, cfg.storeId ? { 'X-Store-Id': cfg.storeId } : {}, headerExtra || {}),
  };
  return new Promise(function (risolvi, rifiuta) {
    const req = https.request(opzioni, function (res) {
      let corpo = '';
      res.on('data', function (c) { corpo += c; });
      res.on('end', function () {
        // 401/403 sono i due errori che capitano davvero all'inizio: token
        // sbagliato, oppure token senza lo scope giusto. Vale la pena dirlo
        // invece di stampare il JSON grezzo.
        if (res.statusCode === 401) {
          return rifiuta(new Error('401 non autorizzato: CONTRADO_API_KEY non valida o scaduta.'));
        }
        if (res.statusCode === 403) {
          return rifiuta(new Error('403 vietato: al token manca lo scope per ' + percorso + ' (servono StoresRead, StoreProductsRead, StoreOrdersRead, StoreOrdersWrite).'));
        }
        if (res.statusCode === 429) {
          return rifiuta(new Error('429 troppe richieste: superato il limite di 100 al minuto, riprova tra un minuto.'));
        }
        let json = null;
        try { json = JSON.parse(corpo); } catch (e) { /* gestito sotto */ }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          const msg = json && json.message ? json.message : corpo.slice(0, 300);
          return rifiuta(new Error('HTTP ' + res.statusCode + ' su ' + percorso + ': ' + msg));
        }
        if (!json) return rifiuta(new Error('Risposta non JSON da ' + percorso + ': ' + corpo.slice(0, 200)));
        if (json.success === false) {
          return rifiuta(new Error('Contrado ha rifiutato ' + percorso + ': ' + (json.message || 'nessun messaggio')));
        }
        risolvi(json.data !== undefined ? json.data : json);
      });
    });
    req.on('error', rifiuta);
    req.end();
  });
}

function salva(nome, dati) {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const file = path.join(OUT_DIR, nome + '.json');
  fs.writeFileSync(file, JSON.stringify(dati, null, 2), 'utf8');
  console.log('  [salvato] ' + path.relative(ROOT, file));
  return file;
}

// L'API pagina i prodotti; qui si scorre fino in fondo invece di fermarsi
// alla prima pagina, altrimenti un catalogo di 30 prodotti ne mostrerebbe 10.
async function tuttiIProdotti(cfg) {
  const tutti = [];
  let pagina = 1;
  for (;;) {
    const dati = await chiama(cfg, '/stores/products?PageNumber=' + pagina + '&PageSize=50');
    const elenco = Array.isArray(dati) ? dati : (dati && (dati.items || dati.products || dati.data)) || [];
    tutti.push.apply(tutti, elenco);
    if (elenco.length < 50) break;
    pagina++;
    await attendi(PAUSA_MS);
  }
  return tutti;
}

async function mostraNegozi(cfg) {
  console.log('\n=== NEGOZI ===');
  const negozi = await chiama(cfg, '/stores');
  const elenco = Array.isArray(negozi) ? negozi : [negozi];
  elenco.forEach(function (s) {
    console.log('  storeId=' + (s.storeId || s.id) + ' | ' + (s.storeName || s.name || '?') + ' | ' + (s.storeURL || ''));
  });
  salva('negozi', negozi);
  return elenco;
}

async function mostraProdotti(cfg) {
  console.log('\n=== PRODOTTI NEL NEGOZIO CONTRADO ===');
  const prodotti = await tuttiIProdotti(cfg);
  if (!prodotti.length) {
    console.log('  Nessun prodotto.');
    console.log('  Il catalogo Contrado si popola da Contrado Store Account (caricando i');
    console.log('  design e creando i prodotti li\'): questa API non puo\' crearli.');
    salva('prodotti', prodotti);
    return prodotti;
  }
  prodotti.forEach(function (p) {
    console.log('  storeProductId=' + p.storeProductId +
      ' | ' + (p.storeProductName || '?') +
      (p.isOutOfStock ? ' | ESAURITO' : '') +
      (p.productionTime ? ' | produzione: ' + p.productionTime : ''));
  });
  console.log('\n  ' + prodotti.length + ' prodotti in totale.');
  salva('prodotti', prodotti);
  return prodotti;
}

// Le varianti portano rrp = prezzo al pubblico consigliato. Il prezzo di
// costo per il rivenditore NON e' esposto da questa API: si legge solo in
// Contrado Store Account. Lo script lo dice invece di far finta che rrp sia
// il costo, perche' scambiarli significherebbe calcolare margini sbagliati.
async function mostraVarianti(cfg, storeProductId) {
  console.log('\n=== VARIANTI prodotto ' + storeProductId + ' ===');
  const dati = await chiama(cfg, '/stores/products/' + storeProductId + '/option-variants',
    { 'X-Culture-Code': cfg.cultureCode });

  const opzioni = (dati && dati.productOptions) || [];
  if (opzioni.length) {
    console.log('  Opzioni disponibili:');
    opzioni.forEach(function (o) {
      const valori = (o.optionValues || o.values || []).map(function (v) {
        return (v.optionValueName || v.name) + '(' + (v.optionValueId || v.id) + ')';
      });
      console.log('    optionId=' + (o.optionId || o.id) + ' ' + (o.optionName || o.name) + ': ' + valori.join(', '));
    });
  }

  const varianti = (dati && dati.productVariants) || [];
  console.log('  Varianti (' + varianti.length + '):');
  varianti.forEach(function (v) {
    const opz = (v.variantOptions || []).map(function (o) {
      return o.optionName + '=' + o.optionValueName;
    }).join(', ');
    console.log('    variantId=' + v.variantId +
      ' | sku=' + (v.sku || '-') +
      ' | rrp=' + (v.formattedRRP || v.rrp || '?') +
      (opz ? ' | ' + opz : ''));
  });
  console.log('\n  Nota: rrp e\' il prezzo al pubblico CONSIGLIATO, non il costo.');
  console.log('  Il costo per il rivenditore si legge in Contrado Store Account.');
  salva('varianti-' + storeProductId, dati);
  return dati;
}

// La domanda che conta per un negozio italiano: quanto costa spedire in
// Italia e chi paga la dogana. Contrado produce nel Regno Unito, quindi la
// risposta non e' scontata.
async function mostraSpedizioni(cfg) {
  console.log('\n=== SPEDIZIONI (' + cfg.cultureCode + ') ===');
  const dati = await chiama(cfg, '/shipping/' + encodeURIComponent(cfg.cultureCode));
  const gruppi = Array.isArray(dati) ? dati : (dati && (dati.shippingPriceGroups || dati.items)) || [];
  gruppi.forEach(function (g) {
    console.log('  gruppo ' + (g.shippingPriceGroupId || g.id) + ': ' + (g.name || g.groupName || ''));
    (g.regions || g.shippingRegions || []).forEach(function (r) {
      console.log('    ' + (r.regionName || r.name || '?') + ' -> ' + (r.formattedPrice || r.price || '?') +
        (r.deliveryTime ? ' | ' + r.deliveryTime : ''));
    });
  });
  salva('spedizioni-' + cfg.cultureCode, dati);
  console.log('\n  La dogana NON e\' un dato di questa API: Contrado dichiara');
  console.log('  "customs duties paid to most countries" sul sito, ma per l\'Italia');
  console.log('  va confermato per iscritto a integrations@contrado.com prima di vendere.');
  return dati;
}

async function mostraPaesi(cfg) {
  console.log('\n=== PAESI SERVITI ===');
  const dati = await chiama(cfg, '/countries');
  const paesi = Array.isArray(dati) ? dati : (dati && (dati.countries || dati.items)) || [];
  const italia = paesi.filter(function (p) {
    return /^IT$/i.test(p.countryCode || p.code || '') || /italy|italia/i.test(p.countryName || p.name || '');
  });
  console.log('  ' + paesi.length + ' paesi. Italia presente: ' + (italia.length ? 'si' : 'NO'));
  salva('paesi', dati);
  return dati;
}

function aiuto() {
  console.log(`
Ricognizione del negozio Contrado (sola lettura).

Uso:
  node scripts/contrado-catalog.js --tutto           negozi + prodotti + spedizioni + paesi
  node scripts/contrado-catalog.js --negozi
  node scripts/contrado-catalog.js --prodotti
  node scripts/contrado-catalog.js --varianti <storeProductId>
  node scripts/contrado-catalog.js --spedizioni
  node scripts/contrado-catalog.js --paesi

Richiede CONTRADO_API_KEY in config/printify.local.env.
Tutto quello che legge finisce anche in contrado-catalog/*.json.
`);
}

async function main() {
  const args = process.argv.slice(2);
  if (!args.length || args.indexOf('--help') !== -1 || args.indexOf('-h') !== -1) {
    aiuto();
    return;
  }
  const cfg = leggiConfig();
  const tutto = args.indexOf('--tutto') !== -1;

  if (tutto || args.indexOf('--negozi') !== -1) {
    await mostraNegozi(cfg);
    await attendi(PAUSA_MS);
  }

  let prodotti = [];
  if (tutto || args.indexOf('--prodotti') !== -1) {
    prodotti = await mostraProdotti(cfg);
    await attendi(PAUSA_MS);
  }

  const iVar = args.indexOf('--varianti');
  if (iVar !== -1) {
    const id = args[iVar + 1];
    if (!id) {
      console.error('--varianti richiede uno storeProductId. Trovali con --prodotti.');
      process.exit(1);
    }
    await mostraVarianti(cfg, id);
    await attendi(PAUSA_MS);
  } else if (tutto && prodotti.length) {
    // Con --tutto si scaricano anche le varianti, che sono il dato da cui
    // escono i prezzi: senza, la ricognizione sarebbe monca.
    for (const p of prodotti) {
      await mostraVarianti(cfg, p.storeProductId);
      await attendi(PAUSA_MS);
    }
  }

  if (tutto || args.indexOf('--spedizioni') !== -1) {
    await mostraSpedizioni(cfg);
    await attendi(PAUSA_MS);
  }
  if (tutto || args.indexOf('--paesi') !== -1) {
    await mostraPaesi(cfg);
  }
}

main().catch(function (err) {
  console.error('\nErrore:', err.message);
  process.exit(1);
});
