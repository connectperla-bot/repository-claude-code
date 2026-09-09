'use strict';

// CHE VERSIONE STA GIRANDO, E COSA LE MANCA.
//
// Nasce da una domanda a cui non si sapeva rispondere: Render dice "deploy
// failed", e il negozio sta servendo il codice vecchio o quello nuovo?
// Rispondere ha richiesto un ordine di prova vero mandato al servizio e
// un'ispezione su Printify di cosa fosse arrivato. Adesso e' una curl.
//
// Le due promesse che questa prova tiene ferme:
//   1. dalla risposta non esce MAI il valore di una variabile d'ambiente;
//   2. una variabile impostata alla stringa vuota conta come mancante --
//      e' l'errore di configurazione piu' difficile da vedere a occhio.
//
// Uso:  node tests/salute.test.js

const assert = require('assert');
const { salute, versione } = require('../scripts/salute');

let passati = 0;
function prova(descrizione, fn) {
  try {
    fn();
    passati++;
    console.log('  ok   ' + descrizione);
  } catch (err) {
    console.error('  FALLITO   ' + descrizione);
    console.error('        ' + err.message);
    process.exitCode = 1;
  }
}

console.log('\nLo stato di salute dei servizi');

prova('dice quale commit sta girando', function () {
  const v = versione({ RENDER_GIT_COMMIT: 'cc041bbeefac9ead2baba6c70aaa91023e755c2c',
                       RENDER_GIT_BRANCH: 'main', RENDER_INSTANCE_ID: 'srv-abc' });
  assert.strictEqual(v.commit, 'cc041bb', 'sette caratteri, come li scrive git');
  assert.strictEqual(v.ramo, 'main');
  assert.strictEqual(v.istanza, 'srv-abc');
});

prova('fuori da Render lo dice invece di inventarsi una versione', function () {
  const v = versione({});
  assert.strictEqual(v.commit, 'sconosciuto');
  assert.strictEqual(v.istanza, 'locale');
});

prova('con tutte le chiavi a posto risponde ok', function () {
  const r = salute({ A: 'x', B: 'y' }, 'servizio', ['A', 'B'], []);
  assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.mancanti, []);
  assert.strictEqual(r.servizio, 'servizio');
});

prova('una chiave che manca fa cadere ok e viene nominata', function () {
  const r = salute({ A: 'x' }, 'servizio', ['A', 'B'], []);
  assert.strictEqual(r.ok, false, 'senza una chiave richiesta il servizio non fa il suo mestiere');
  assert.deepStrictEqual(r.mancanti, ['B']);
});

prova('la stringa vuota conta come mancante', function () {
  // E' il caso che su Render non si vede: la variabile c'e', e non vale niente.
  const r = salute({ A: '', B: '   ' }, 'servizio', ['A', 'B'], []);
  assert.strictEqual(r.ok, false);
  assert.deepStrictEqual(r.mancanti.sort(), ['A', 'B']);
});

prova('le chiavi utili non fanno cadere ok, ma si vedono', function () {
  const r = salute({ A: 'x' }, 'servizio', ['A'], ['UTILE']);
  assert.strictEqual(r.ok, true, 'senza una chiave utile il servizio funziona lo stesso');
  assert.deepStrictEqual(r.mancantiUtili, ['UTILE'],
    'ma va detto: e\' il tipo di mancanza che si scopre solo quando serve');
  assert.strictEqual(r.configurazione.UTILE, false);
});

prova('NESSUN valore di variabile esce dalla risposta', function () {
  const segreti = {
    PRINTIFY_API_KEY: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.segretissimo',
    SHOPIFY_WEBHOOK_SECRET: 'shpss_abcdef0123456789',
    RENDER_GIT_COMMIT: 'cc041bbeefac9ead',
  };
  const r = salute(segreti, 'servizio', ['PRINTIFY_API_KEY', 'SHOPIFY_WEBHOOK_SECRET'], []);
  const testo = JSON.stringify(r);
  for (const valore of ['segretissimo', 'shpss_abcdef0123456789', segreti.PRINTIFY_API_KEY]) {
    assert.ok(!testo.includes(valore),
      'il valore di una chiave e\' finito nella risposta di /health: ' + valore.slice(0, 12));
  }
  // i NOMI invece devono esserci: stanno gia' in chiaro in render.yaml
  assert.strictEqual(r.configurazione.PRINTIFY_API_KEY, true);
});

prova('senza elenchi non esplode', function () {
  const r = salute({}, 'servizio');
  assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.mancanti, []);
  assert.deepStrictEqual(r.configurazione, {});
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
