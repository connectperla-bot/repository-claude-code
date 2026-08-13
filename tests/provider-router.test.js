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

// Ambienti tipici: nessuna chiave, solo Printful, solo Contrado, tutte.
const senzaChiavi = {};
const conPrintful = { PRINTFUL_API_KEY: 'x' };
const conContrado = { CONTRADO_API_KEY: 'x' };
const conTutte = { PRINTFUL_API_KEY: 'x', CONTRADO_API_KEY: 'x' };

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

console.log('\nTipi Contrado (_lux): sempre Contrado, in ogni paese');

prova('cuccia_lux con spedizione in Italia va su Contrado', function () {
  assert.strictEqual(router.chooseProviderName('cuccia_lux', ordineIT, conTutte), 'contrado');
});

// Il caso che distingue Contrado dai tipi _eu: fuori dall'EU NON si ripiega
// su Printify, perche' il prodotto premium esiste solo su Contrado.
prova('cuccia_lux con spedizione negli Stati Uniti va comunque su Contrado', function () {
  assert.strictEqual(router.chooseProviderName('cuccia_lux', ordineUS, conTutte), 'contrado');
});

prova('guinzaglio_lux senza chiave Contrado resta su Contrado (errore esplicito, non ripiego)', function () {
  assert.strictEqual(router.chooseProviderName('guinzaglio_lux', ordineIT, senzaChiavi), 'contrado');
});

prova('tutti i sei tipi _lux vanno su Contrado', function () {
  Object.keys(router.CONTRADO_TYPES).forEach(function (tipo) {
    assert.strictEqual(router.chooseProviderName(tipo, ordineIT, conTutte), 'contrado', tipo);
  });
});

console.log('\nTipi EU (_eu): Printful solo in EU e solo con la chiave');

prova('collare_eu in EU con chiave Printful va su Printful', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineIT, conPrintful), 'printful');
});

prova('collare_eu fuori EU va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineUS, conPrintful), 'printify');
});

prova('collare_eu senza chiave Printful va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineIT, senzaChiavi), 'printify');
});

console.log('\nNessuna regressione: i tipi gia\' in vendita non cambiano fornitore');

// Il punto dell'intera separazione dei tipi: aggiungere Contrado non deve
// spostare un solo prodotto di quelli gia' online.
prova('collare/bandana/cuccia/guinzaglio restano su Printify anche con Contrado attivo', function () {
  ['collare', 'bandana', 'cuccia', 'guinzaglio', 'ciotola', 'medaglietta', 'tappetino'].forEach(function (tipo) {
    assert.strictEqual(router.chooseProviderName(tipo, ordineIT, conTutte), 'printify', tipo + ' (IT)');
    assert.strictEqual(router.chooseProviderName(tipo, ordineUS, conTutte), 'printify', tipo + ' (US)');
  });
});

prova('i tipi _eu con Contrado attivo si comportano esattamente come prima', function () {
  ['collare_eu', 'bandana_eu', 'ciotola_eu', 'guinzaglio_eu'].forEach(function (tipo) {
    assert.strictEqual(router.chooseProviderName(tipo, ordineIT, conTutte), 'printful', tipo + ' (IT)');
    assert.strictEqual(router.chooseProviderName(tipo, ordineUS, conTutte), 'printify', tipo + ' (US)');
  });
});

console.log('\nCasi limite');

prova('tipo sconosciuto va su Printify', function () {
  assert.strictEqual(router.chooseProviderName('qualcosa_di_nuovo', ordineIT, conTutte), 'printify');
});

prova('ordine senza indirizzo di spedizione non e\' EU', function () {
  assert.strictEqual(router.isEuShipping(ordineSenzaIndirizzo), false);
  assert.strictEqual(router.chooseProviderName('collare_eu', ordineSenzaIndirizzo, conPrintful), 'printify');
});

// Anche senza indirizzo un _lux deve andare su Contrado: il paese non c'entra.
prova('ordine senza indirizzo per un tipo _lux va comunque su Contrado', function () {
  assert.strictEqual(router.chooseProviderName('bandana_lux', ordineSenzaIndirizzo, conContrado), 'contrado');
});

prova('chooseClient restituisce un client con fulfillOrder per ogni fornitore', function () {
  ['cuccia_lux', 'collare_eu', 'collare'].forEach(function (tipo) {
    const client = router.chooseClient(tipo, ordineIT, conTutte);
    assert.strictEqual(typeof client.fulfillOrder, 'function', tipo);
  });
});

console.log('\n' + passati + ' verifiche superate.' + (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
