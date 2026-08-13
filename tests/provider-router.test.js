'use strict';

// Verifica la regola che decide QUALE fornitore evade una riga d'ordine.
// Nessuna chiamata di rete: si controlla solo chooseProviderName(), che e'
// separata apposta da chooseClient() per poter essere provata senza API vere.
//
// Uso:  node tests/provider-router.test.js

const assert = require('assert');
const router = require('../scripts/provider-router');

const ordineIT = { shipping_address: { country_code: 'IT' } };
const ordineUS = { shipping_address: { country_code: 'US' } };
const ordineSenzaIndirizzo = {};

const senzaChiavi = {};
const conPrintful = { PRINTFUL_API_KEY: 'x' };

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

console.log('\nTipi EU (_eu): Printful solo in EU e solo con la chiave');

prova('collare_eu in EU con chiave Printful va su Printful', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineIT, conPrintful), 'printful');
});

// Fuori dall'EU il motivo per usare Printful (evitare la dogana al cliente
// europeo) non esiste piu': si torna su Printify.
prova('collare_eu fuori EU va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineUS, conPrintful), 'printify');
});

prova('collare_eu senza chiave Printful va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineIT, senzaChiavi), 'printify');
});

prova('tutti e quattro i tipi _eu si comportano allo stesso modo', function () {
  Object.keys(router.EU_CAPABLE_TYPES).forEach(function (tipo) {
    assert.strictEqual(router.chooseProviderName(tipo, ordineIT, conPrintful), 'printful', tipo + ' (IT)');
    assert.strictEqual(router.chooseProviderName(tipo, ordineUS, conPrintful), 'printify', tipo + ' (US)');
  });
});

console.log('\nI tipi gia\' in vendita non cambiano mai fornitore');

// E' il motivo per cui i tipi _eu sono prodotti Shopify distinti: attivare
// Printful non deve spostare un solo prodotto di quelli gia' online.
prova('collare/bandana/cuccia/guinzaglio restano su Printify anche con Printful attivo', function () {
  ['collare', 'bandana', 'cuccia', 'guinzaglio', 'ciotola', 'medaglietta', 'tappetino'].forEach(function (tipo) {
    assert.strictEqual(router.chooseProviderName(tipo, ordineIT, conPrintful), 'printify', tipo + ' (IT)');
    assert.strictEqual(router.chooseProviderName(tipo, ordineUS, conPrintful), 'printify', tipo + ' (US)');
  });
});

console.log('\nCasi limite');

prova('tipo sconosciuto va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('qualcosa_di_nuovo', ordineIT, conPrintful), 'printify');
});

prova('ordine senza indirizzo di spedizione non e\' EU', function () {
  assert.strictEqual(router.isEuShipping(ordineSenzaIndirizzo), false);
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineSenzaIndirizzo, conPrintful), 'printify');
});

prova('chooseClient restituisce un client con fulfillOrder per ogni fornitore', function () {
  ['collare_eu', 'collare'].forEach(function (tipo) {
    const client = router.chooseClient(tipo, ordineIT, conPrintful);
    assert.strictEqual(typeof client.fulfillOrder, 'function', tipo);
  });
});

console.log('\n' + passati + ' verifiche superate.' + (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
