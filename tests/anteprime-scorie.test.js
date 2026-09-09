'use strict';

// LE ANTEPRIME TEMPORANEE CHE NESSUNO HA CANCELLATO
//
// /generate-mockup crea su Printify un prodotto usa-e-getta e lo cancella
// dieci minuti dopo, con un setTimeout: prima non si puo', perche' Printify
// serve le immagini del mockup finche' il prodotto esiste e cancellarlo
// subito spegnerebbe l'anteprima sotto gli occhi del cliente.
//
// Ma un setTimeout vive quanto il processo, e il servizio gira sul piano
// gratuito di Render, che lo addormenta dopo un quarto d'ora senza richieste.
// Visto succedere il 9 settembre 2026: tre anteprime generate per una prova,
// tre prodotti rimasti nel catalogo Printify. Da qui la spazzata all'avvio.
//
// IL RISCHIO E' L'OPPOSTO, ED E' PEGGIORE. Una scoria in piu' non fa danno a
// nessuno; buttare l'anteprima che un cliente sta GUARDANDO gli spegne la
// foto in faccia mentre decide se comprare. Per questo la regola sta in un
// file suo, staccata dalla chiamata di rete, e per questo si prova qui.
//
// Uso:  node tests/anteprime-scorie.test.js

const assert = require('assert');
const scorie = require('../scripts/anteprime-scorie');

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

function prodotto(titolo, minutiFa) {
  return {
    id: 'x', title: titolo,
    created_at: new Date(Date.now() - minutiFa * 60000).toISOString(),
  };
}

console.log('\nLe anteprime temporanee rimaste indietro');

prova('quella vecchia si butta', function () {
  const trovate = scorie.scorieDaButtare([prodotto(scorie.ANTEPRIMA_TITOLO, 60)], Date.now());
  assert.strictEqual(trovate.length, 1, 'un\'anteprima di un\'ora fa non la guarda piu\' nessuno');
});

prova('quella che un cliente sta guardando adesso NON si tocca', function () {
  const appena = scorie.scorieDaButtare([prodotto(scorie.ANTEPRIMA_TITOLO, 1)], Date.now());
  assert.strictEqual(appena.length, 0, 'un minuto fa: e\' ancora sullo schermo di qualcuno');
  const sottoSoglia = scorie.scorieDaButtare(
    [prodotto(scorie.ANTEPRIMA_TITOLO, scorie.ANTEPRIMA_ETA_MIN - 1)], Date.now());
  assert.strictEqual(sottoSoglia.length, 0, 'sotto la soglia non si tocca');
});

prova('i prodotti veri del negozio non si toccano mai', function () {
  const veri = [
    prodotto('Bandana “Nobile”', 600),
    prodotto('Collare in Pelle “Crea il Tuo Design”', 6000),
    // somiglia ma non e' lo stesso titolo: deve restare
    prodotto('Perla - Anteprima temporanea di prova', 600),
    prodotto('perla - anteprima temporanea', 600),
  ];
  assert.strictEqual(scorie.scorieDaButtare(veri, Date.now()).length, 0,
    'il titolo deve combaciare esatto, non per somiglianza');
});

prova('una data illeggibile vale "lascia stare"', function () {
  const rotti = [
    { id: 'a', title: scorie.ANTEPRIMA_TITOLO, created_at: 'boh' },
    { id: 'b', title: scorie.ANTEPRIMA_TITOLO },
    { id: 'c', title: scorie.ANTEPRIMA_TITOLO, created_at: null },
  ];
  assert.strictEqual(scorie.scorieDaButtare(rotti, Date.now()).length, 0,
    'nel dubbio non si cancella: cancellare non si disfa');
});

prova('un elenco vuoto, assente o sporco non fa saltare niente', function () {
  assert.strictEqual(scorie.scorieDaButtare([], Date.now()).length, 0);
  assert.strictEqual(scorie.scorieDaButtare(undefined, Date.now()).length, 0);
  assert.strictEqual(scorie.scorieDaButtare([null, undefined, {}], Date.now()).length, 0);
});

prova('fra tante ne sceglie solo quelle giuste', function () {
  const misto = [
    prodotto('Bandana “Nobile”', 6000),
    prodotto(scorie.ANTEPRIMA_TITOLO, 2),      // troppo giovane
    prodotto(scorie.ANTEPRIMA_TITOLO, 30),     // da buttare
    prodotto(scorie.ANTEPRIMA_TITOLO, 1440),   // da buttare
    prodotto('Cuccia “Tribale”', 30),
  ];
  assert.strictEqual(scorie.scorieDaButtare(misto, Date.now()).length, 2);
});

prova('legge la data nel formato che manda davvero Printify', function () {
  // Non ISO: lo spazio al posto della T. Preso da una risposta vera del
  // 9 settembre 2026. Se questa prova diventa rossa, la spazzata smette di
  // buttare qualsiasi cosa senza dirlo a nessuno.
  const comeprintify = [{ id: 'x', title: scorie.ANTEPRIMA_TITOLO,
                          created_at: '2026-09-09 20:04:20+00:00' }];
  const dopo = new Date('2026-09-09T21:00:00Z').getTime();
  assert.strictEqual(scorie.scorieDaButtare(comeprintify, dopo).length, 1,
    'un\'anteprima di quasi un\'ora prima va buttata');
  const subito = new Date('2026-09-09T20:05:00Z').getTime();
  assert.strictEqual(scorie.scorieDaButtare(comeprintify, subito).length, 0,
    'quaranta secondi dopo no: qualcuno la sta guardando');
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
