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
  // Il guinzaglio EU esiste in una misura sola: non c'e' niente da scegliere.
  assert.strictEqual(varianti.scegliVariante('guinzaglio_eu', null, { variantId: 4012 }), 4012);
  assert.strictEqual(varianti.scegliVariante('guinzaglio_eu', '', { variantId: 745 }), 745);
});

console.log('\nLa linea EU adesso ha piu\' di una taglia');

prova('la bandana EU grande non parte come piccola', function () {
  // Il difetto che questo coglie: prima bandana_eu non era in VARIANTI, quindi
  // scegliVariante ripiegava sul singolo id configurato e un cliente con un
  // cane da 35 kg riceveva la taglia per gatti.
  const config = { variantId: 16031 };  // la S, il vecchio valore fisso
  const id = varianti.scegliVariante('bandana_eu', 'L', config);
  assert.strictEqual(id, 16033, 'la L deve ordinare 16033, non ' + id);
  assert.notStrictEqual(id, config.variantId,
    'ha ripiegato sulla variante fissa: e\' esattamente il difetto');
});

prova('ogni taglia EU ha il suo id, bandana e collare', function () {
  const c = { variantId: 0 };
  assert.strictEqual(varianti.scegliVariante('bandana_eu', 'S', c), 16031);
  assert.strictEqual(varianti.scegliVariante('bandana_eu', 'M', c), 16032);
  assert.strictEqual(varianti.scegliVariante('bandana_eu', 'L', c), 16033);
  assert.strictEqual(varianti.scegliVariante('collare_eu', 'S', c), 19186);
  assert.strictEqual(varianti.scegliVariante('collare_eu', 'M', c), 19187);
  assert.strictEqual(varianti.scegliVariante('collare_eu', 'L', c), 19188);
  assert.strictEqual(varianti.scegliVariante('ciotola_eu', '32 oz', c), 16786);
});

prova('i titoli descrittivi portano allo stesso id della sigla', function () {
  // Su Shopify le opzioni saranno scritte per esteso, perche' "S" da sola non
  // dice a nessuno se il cane ci sta dentro.
  const c = { variantId: 0 };
  const coppie = [
    ['bandana_eu', 'L', 'L / Grande (64 cm)'],
    ['bandana_eu', 'M', 'Media (54 cm)'],
    ['collare_eu', 'L', 'L / Collo 38-60 cm'],
    ['ciotola_eu', '32 oz', 'Grande (950 ml)'],
  ];
  for (const [tipo, sigla, esteso] of coppie) {
    assert.strictEqual(varianti.scegliVariante(tipo, esteso, c),
      varianti.scegliVariante(tipo, sigla, c),
      tipo + ': "' + esteso + '" e "' + sigla + '" devono dare lo stesso id');
  }
});

prova('gli id EU esistono davvero nel catalogo Printful', function () {
  const file = { bandana_eu: '630.json', collare_eu: '749.json', ciotola_eu: '678.json' };
  for (const tipo of Object.keys(file)) {
    const percorso = path.join(__dirname, '..', 'printful-catalog', file[tipo]);
    const dati = JSON.parse(fs.readFileSync(percorso, 'utf8'));
    const esistenti = new Set(dati.variants.map(function (v) { return v.id; }));

    const mappa = varianti.VARIANTI[tipo];
    for (const titolo of Object.keys(mappa)) {
      assert.ok(esistenti.has(mappa[titolo]),
        tipo + ': l\'id ' + mappa[titolo] + ' (' + titolo + ') non esiste in ' + file[tipo]);
    }
    // E nessuna misura in catalogo deve restare senza mappatura, altrimenti
    // quella taglia si potrebbe mettere in vendita e poi fermerebbe l'ordine.
    const mappati = new Set(Object.values(mappa));
    for (const v of dati.variants) {
      assert.ok(mappati.has(v.id),
        tipo + ': la misura "' + v.size + '" (id ' + v.id + ') e\' in catalogo ' +
        'ma nessuna chiave la raggiunge');
    }
  }
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
    }

    // Ogni variante del blueprint deve avere ALMENO una chiave. Non si pretende
    // piu' che i titoli coincidano, ne' che il conto torni: da quando la mappa
    // porta anche i nomi italiani ci sono due chiavi per id, e il titolo
    // italiano per definizione non e' quello inglese del blueprint. Quello che
    // conta e' che nessuna taglia in vendita resti senza mappatura, perche'
    // quella fermerebbe l'ordine.
    const mappati = new Set(Object.values(mappa));
    for (const v of dati.variants || []) {
      assert.ok(mappati.has(v.id),
        tipo + ': la variante "' + v.title + '" (id ' + v.id + ') e\' nel blueprint ' +
        'ma nessuna chiave della mappa la raggiunge -- un ordine su quella taglia ' +
        'si fermerebbe');
    }
  }
});

prova('i nomi italiani portano allo stesso id di quelli inglesi', function () {
  const c = { variantId: 0 };
  const coppie = [
    ['cuccia', '28" × 18"', 'Piccola (71 x 46 cm)'],
    ['cuccia', '50" × 40"', 'Grande (127 x 102 cm)'],
    ['bandana', '20" × 10"', 'Piccola (51 x 25 cm)'],
    ['medaglietta', '1"', 'Unica (2,5 cm)'],
    ['collare', 'M / Gun Metal / TPU', 'M / Canna di fucile'],
    ['collare', 'XL / Vintage Brass / TPU', 'XL / Ottone anticato'],
  ];
  for (const [tipo, inglese, italiano] of coppie) {
    assert.strictEqual(
      varianti.scegliVariante(tipo, italiano, c),
      varianti.scegliVariante(tipo, inglese, c),
      tipo + ': "' + italiano + '" e "' + inglese + '" devono dare lo stesso id, ' +
      'altrimenti tradurre le opzioni su Shopify cambierebbe la taglia spedita');
  }
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
