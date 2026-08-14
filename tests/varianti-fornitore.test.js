'use strict';

// Verifica che allo stampatore arrivi la taglia che il cliente ha scelto.
//
// PERCHE' ESISTE
// Prima di ROUND 42 handleCustomItem mandava un id di variante fisso per tipo
// prodotto, letto da una variabile d'ambiente e uguale per ogni ordine: chi
// comprava una cuccia 50"x40" a 119,99 EUR riceveva la variante configurata,
// e sul collare si perdevano insieme taglia e finitura. Nessun test se ne
// accorgeva perche' nessuno guardava item.variant_title.
//
// Uso:  node tests/varianti-fornitore.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const varianti = require('../scripts/varianti-fornitore');

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

console.log('\nLa taglia scelta arriva allo stampatore');

prova('la cuccia grande non diventa la piccola', function () {
  const config = { variantId: 61436 };   // la piccola, il vecchio valore fisso
  const id = varianti.scegliVariante('cuccia', '50" × 40"', config);
  assert.strictEqual(id, 61435, 'la 50x40 deve ordinare 61435, non ' + id);
  assert.notStrictEqual(id, config.variantId,
    'ha ripiegato sulla variante fissa: e\' esattamente il difetto');
});

prova('ogni taglia di cuccia ha il suo id', function () {
  const c = { variantId: 0 };
  assert.strictEqual(varianti.scegliVariante('cuccia', '28" × 18"', c), 61436);
  assert.strictEqual(varianti.scegliVariante('cuccia', '40" × 30"', c), 61437);
  assert.strictEqual(varianti.scegliVariante('cuccia', '50" × 40"', c), 61435);
});

prova('sul collare non si perde ne\' la taglia ne\' la finitura', function () {
  const c = { variantId: 0 };
  assert.strictEqual(varianti.scegliVariante('collare', 'S / Black Onyx / TPU', c), 74897);
  assert.strictEqual(varianti.scegliVariante('collare', 'XL / Vintage Brass / TPU', c), 74912);
  // stessa taglia, finitura diversa: devono essere id diversi
  assert.notStrictEqual(
    varianti.scegliVariante('collare', 'M / Gun Metal / TPU', c),
    varianti.scegliVariante('collare', 'M / Black Onyx / TPU', c));
});

console.log('\nTitoli scritti in modo diverso');

prova('la x al posto del segno di moltiplicazione va bene lo stesso', function () {
  const c = { variantId: 0 };
  assert.strictEqual(varianti.scegliVariante('cuccia', '50" x 40"', c), 61435);
});

prova('virgolette tipografiche e spazi doppi non fanno fallire un ordine buono', function () {
  const c = { variantId: 0 };
  assert.strictEqual(varianti.scegliVariante('cuccia', ' 50”  ×  40” ', c), 61435);
});

console.log('\nQuando qualcosa non torna');

prova('un titolo sconosciuto ferma la riga invece di spedire la taglia sbagliata', function () {
  assert.throws(
    function () { varianti.scegliVariante('cuccia', 'Taglia Media', { variantId: 61436 }); },
    function (err) {
      assert.ok(/non riconosciuta/.test(err.message), 'messaggio inatteso: ' + err.message);
      assert.ok(/varianti-fornitore\.js/.test(err.message),
        'il messaggio deve dire dove intervenire');
      return true;
    });
});

prova('i tipi a variante unica usano la configurazione, senza mappa', function () {
  // tutta la linea EU: un solo prodotto Shopify, una sola variante
  assert.strictEqual(varianti.scegliVariante('collare_eu', null, { variantId: 4012 }), 4012);
  assert.strictEqual(varianti.scegliVariante('bandana_eu', '', { variantId: 630 }), 630);
});

console.log('\nGli id combaciano con i blueprint salvati');

prova('ogni id nella mappa esiste davvero nel blueprint di Printify', function () {
  const file = {
    collare: '784_93.json',
    cuccia: '419_10.json',
    bandana: '562_70.json',
    medaglietta: '566_70.json',
  };
  for (const tipo of Object.keys(file)) {
    const percorso = path.join(__dirname, '..', 'printify-blueprints', file[tipo]);
    const dati = JSON.parse(fs.readFileSync(percorso, 'utf8'));
    const perId = {};
    for (const v of dati.variants || []) perId[v.id] = v.title;

    const mappa = varianti.VARIANTI[tipo];
    for (const titolo of Object.keys(mappa)) {
      const id = mappa[titolo];
      assert.ok(perId[id],
        tipo + ': l\'id ' + id + ' (' + titolo + ') non esiste in ' + file[tipo]);
      assert.strictEqual(
        varianti.normalizza(perId[id]), varianti.normalizza(titolo),
        tipo + ': l\'id ' + id + ' e\' "' + perId[id] + '" nel blueprint ma "' +
        titolo + '" nella mappa');
    }
    assert.strictEqual(Object.keys(mappa).length, (dati.variants || []).length,
      tipo + ': la mappa ha ' + Object.keys(mappa).length + ' varianti, il blueprint ' +
      (dati.variants || []).length + ' -- una taglia in vendita senza mappatura ' +
      'fermerebbe l\'ordine');
  }
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
