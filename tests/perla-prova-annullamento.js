'use strict';

// Collaudo dell'annullamento ordine, con Shopify, Printify e Printful finti.
//
// Qui non si puo' annullare un ordine vero per provare: si rimpiazza fetch e si
// guarda cosa il modulo CHIEDE ai tre servizi e in che ordine. E' proprio
// l'ordine la cosa da verificare -- prima si ferma la stampa, poi si rimborsa.
// Al contrario si restituirebbero i soldi di un pezzo che si stampa lo stesso.
//
//     NODE_PATH=./scripts/node_modules node tests/perla-prova-annullamento.js

const http = require('http');
const annulla = require('../scripts/perla-annulla-ordine.js');

const ENV = {
  SHOPIFY_SHOP_DOMAIN: 'esempio.myshopify.com',
  SHOPIFY_ADMIN_TOKEN: 'finto',
  PRINTIFY_API_KEY: 'finto',
  PRINTIFY_SHOP_ID: '1',
  PRINTFUL_API_KEY: 'finto',
};

// --- i tre servizi finti ----------------------------------------------------

let chiamate = [];
const fetchVero = global.fetch;

function fingiServizi(scenario) {
  chiamate = [];
  global.fetch = async function (url, opzioni) {
    const metodo = (opzioni && opzioni.method) || 'GET';
    chiamate.push(metodo + ' ' + String(url).split('?')[0]);

    if (String(url).includes('/admin/api/')) {
      const corpo = JSON.parse(opzioni.body);
      if (corpo.query.includes('TrovaOrdine')) {
        return risposta(200, { data: { orders: { nodes: scenario.ordiniShopify } } });
      }
      if (scenario.shopifyRifiuta) {
        return risposta(200, { data: { orderCancel: { orderCancelUserErrors: [{ message: 'Non rimborsabile' }] } } });
      }
      return risposta(200, { data: { orderCancel: { job: { id: 'gid://job/1' }, orderCancelUserErrors: [] } } });
    }
    if (String(url).includes('api.printful.com')) {
      if (metodo === 'DELETE') return risposta(200, { code: 200 });
      if (!scenario.printful) return risposta(404, {});
      return risposta(200, { result: scenario.printful });
    }
    if (String(url).includes('api.printify.com')) {
      if (String(url).includes('/cancel.json')) return risposta(200, {});
      return risposta(200, { data: scenario.printify ? [scenario.printify] : [] });
    }
    throw new Error('chiamata inattesa: ' + url);
  };
}

function risposta(stato, corpo) {
  const testo = JSON.stringify(corpo);
  return { ok: stato >= 200 && stato < 300, status: stato,
           text: async function () { return testo; },
           json: async function () { return corpo; } };
}

const ORDINE_APERTO = {
  id: 'gid://shopify/Order/555',
  name: '#1042',
  email: 'mario@example.it',
  cancelledAt: null,
  displayFulfillmentStatus: 'UNFULFILLED',
  displayFinancialStatus: 'PAID',
  totalPriceSet: { shopMoney: { amount: '54.99', currencyCode: 'EUR' } },
};

// --- un server vero, cosi' si prova il router come lo vede il browser -------

function avvia() {
  const express = require('express');
  const app = express();
  app.use(annulla.costruisciRouter(ENV));
  return new Promise(function (ok) {
    const srv = app.listen(0, function () { ok(srv); });
  });
}

function chiedi(porta, percorso, corpo) {
  return new Promise(function (ok, ko) {
    const dati = JSON.stringify(corpo);
    const req = http.request(
      { host: '127.0.0.1', port: porta, path: percorso, method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(dati) } },
      function (res) {
        let testo = '';
        res.on('data', function (c) { testo += c; });
        res.on('end', function () { ok({ stato: res.statusCode, corpo: JSON.parse(testo) }); });
      }
    );
    req.on('error', ko);
    req.end(dati);
  });
}

// --- le prove ---------------------------------------------------------------

const PROVE = [
  {
    nome: 'stato: ordine in attesa, si puo\' annullare',
    scenario: { ordiniShopify: [ORDINE_APERTO], printful: { id: 9, status: 'draft' } },
    percorso: '/ordine/stato',
    corpo: { numero: '#1042', email: 'Mario@Example.it' },
    attesa: function (r) { return r.stato === 200 && r.corpo.annullabile === true && r.corpo.numero === '#1042'; },
  },
  {
    nome: 'stato: stampa gia\' partita, non si annulla',
    scenario: { ordiniShopify: [ORDINE_APERTO], printful: { id: 9, status: 'inprocess' } },
    percorso: '/ordine/stato',
    corpo: { numero: '1042', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 200 && r.corpo.annullabile === false && /stampa/i.test(r.corpo.messaggio); },
  },
  {
    nome: 'stato: email che non corrisponde -> stessa risposta di "non esiste"',
    scenario: { ordiniShopify: [ORDINE_APERTO] },
    percorso: '/ordine/stato',
    corpo: { numero: '1042', email: 'ladro@example.it' },
    attesa: function (r) { return r.stato === 404 && r.corpo.esito === 'non_trovato'; },
  },
  {
    nome: 'stato: ordine inesistente -> identico, non si capisce la differenza',
    scenario: { ordiniShopify: [] },
    percorso: '/ordine/stato',
    corpo: { numero: '9999', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 404 && r.corpo.esito === 'non_trovato'; },
  },
  {
    nome: 'stato: numero malformato respinto prima di chiamare Shopify',
    scenario: { ordiniShopify: [ORDINE_APERTO] },
    percorso: '/ordine/stato',
    corpo: { numero: '1042 OR 1=1', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 400 && chiamate.length === 0; },
  },
  {
    nome: 'annulla: prima il fornitore, poi Shopify',
    scenario: { ordiniShopify: [ORDINE_APERTO], printful: { id: 9, status: 'pending' } },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) {
      const iFornitore = chiamate.indexOf('DELETE https://api.printful.com/orders/@555');
      const iShopify = chiamate.lastIndexOf('POST https://esempio.myshopify.com/admin/api/2025-07/graphql.json');
      return r.stato === 200 && r.corpo.esito === 'annullato' &&
             iFornitore !== -1 && iShopify !== -1 && iFornitore < iShopify;
    },
  },
  {
    nome: 'annulla: stampa partita -> rifiutato, e Shopify non viene toccato',
    scenario: { ordiniShopify: [ORDINE_APERTO], printful: { id: 9, status: 'inprocess' } },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) {
      const annullamenti = chiamate.filter(function (c) { return c.startsWith('DELETE') || c.includes('/cancel.json'); });
      return r.stato === 409 && r.corpo.esito === 'non_annullabile' && annullamenti.length === 0;
    },
  },
  {
    nome: 'annulla: ordine gia\' spedito -> rifiutato',
    scenario: { ordiniShopify: [Object.assign({}, ORDINE_APERTO, { displayFulfillmentStatus: 'FULFILLED' })] },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 409 && /partito/i.test(r.corpo.messaggio); },
  },
  {
    nome: 'annulla: ordine gia\' annullato -> rifiutato',
    scenario: { ordiniShopify: [Object.assign({}, ORDINE_APERTO, { cancelledAt: '2026-08-01T10:00:00Z' })] },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 409 && /già stato annullato/i.test(r.corpo.messaggio); },
  },
  {
    nome: 'annulla: Printify trovato per external_id e annullato',
    scenario: { ordiniShopify: [ORDINE_APERTO], printify: { id: 'pf1', external_id: '555', status: 'on-hold' } },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) {
      return r.stato === 200 &&
             chiamate.some(function (c) { return c.includes('/orders/pf1/cancel.json'); });
    },
  },
  {
    nome: 'annulla: se Shopify rifiuta il rimborso, si risponde errore (non "fatto")',
    scenario: { ordiniShopify: [ORDINE_APERTO], printful: { id: 9, status: 'draft' }, shopifyRifiuta: true },
    percorso: '/ordine/annulla',
    corpo: { numero: '#1042', email: 'mario@example.it' },
    attesa: function (r) { return r.stato === 502 && r.corpo.esito === 'errore'; },
  },
];

(async function () {
  const srv = await avvia();
  const porta = srv.address().port;
  let ko = 0;
  for (const prova of PROVE) {
    // il tetto ai tentativi conta per IP e qui tutte le prove arrivano da
    // 127.0.0.1: senza azzerare, dalla ventunesima in poi risponderebbe 429
    annulla.azzeraTentativi();
    fingiServizi(prova.scenario);
    let esito;
    try {
      const r = await chiedi(porta, prova.percorso, prova.corpo);
      esito = prova.attesa(r);
      if (!esito) console.log('    risposta: ' + JSON.stringify(r).slice(0, 200) + '\n    chiamate: ' + JSON.stringify(chiamate));
    } catch (err) {
      esito = false;
      console.log('    eccezione: ' + err.message);
    }
    if (!esito) ko++;
    console.log((esito ? 'OK  ' : 'KO  ') + prova.nome);
  }
  global.fetch = fetchVero;
  srv.close();
  console.log(ko ? '\nFALLITE: ' + ko + ' su ' + PROVE.length : '\n--- tutte passate (' + PROVE.length + ')');
  process.exit(ko ? 1 : 0);
})();
