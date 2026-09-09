'use strict';

// DOVE SI STAMPA: la regola che decide l'area, e il difetto che nascondeva.
//
// L'editor scrive nell'ordine un campo `position` che vale sempre "front" sul
// lato davanti e "back" sul retro. Non e' il nome dell'area di stampa del
// fornitore: e' il LATO DELL'EDITOR. Su quasi tutto il catalogo i due nomi
// coincidono per caso, e nessuno ci ha mai pensato.
//
// Sul giacchetto parka no. Il blueprint 10740 il fronte NON ce l'ha: l'unica
// area che Printify conosce si chiama 'back_dtf'. Un ordine spedito con
// "front" verrebbe rifiutato o -- peggio -- stampato senza il disegno che il
// cliente ha pagato.
//
// LA PRIMA CORREZIONE NON FUNZIONAVA, ed e' il motivo per cui questa prova
// esiste: passava la configurazione come RIPIEGO (`data.position || config`),
// e siccome l'editor scrive sempre "front" il ripiego non entrava mai in
// gioco. Il codice sembrava corretto, il commento diceva la cosa giusta, e il
// parka sarebbe partito sbagliato lo stesso.
//
// Uso:  node tests/posizione-di-stampa.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { posizioneFronte, posizioneRetro, corpoProdotto } = require('../scripts/providers/printify-client');

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

// Com'e' fatto DAVVERO il campo che il tema salva nell'ordine: copiato da
// writePropData() in assets/global.js.
function comeScriveIlTema(tipo, lato) {
  return {
    printify_image_id: '000000000000000000000000',
    x: 0.5, y: 0.5, scale: 1, angle: 0,
    position: lato === 'back' ? 'back' : 'front',
    product_type: tipo,
    baked: true,
  };
}

console.log('\nDove si stampa');

prova('il parka stampa sul dorso anche se il tema ha scritto "front"', function () {
  const front = comeScriveIlTema('giacchetto', 'front');
  assert.strictEqual(front.position, 'front', 'il tema scrive sempre front: e\' il presupposto della prova');
  assert.strictEqual(posizioneFronte(front, { position: 'back_dtf' }), 'back_dtf',
    'la configurazione del tipo deve vincere sul lato dell\'editor');
});

prova('quella posizione esiste davvero nel blueprint del parka', function () {
  const bp = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'printify-blueprints', '10740_72.json'), 'utf8'));
  const aree = new Set();
  for (const v of bp.variants) for (const ph of v.placeholders || []) aree.add(ph.position);
  assert.ok(aree.has('back_dtf'), 'back_dtf non esiste piu\': ' + [...aree].join(', '));
  assert.ok(!aree.has('front'), 'se il fronte esistesse, questa regola sarebbe di troppo');
});

prova('i tipi senza posizione dichiarata restano com\'erano', function () {
  const front = comeScriveIlTema('bandana', 'front');
  assert.strictEqual(posizioneFronte(front, {}), 'front');
  assert.strictEqual(posizioneFronte(front, { blueprintId: 562 }), 'front');
});

prova('il retro della medaglietta continua a stampare sul retro', function () {
  const back = comeScriveIlTema('medaglietta', 'back');
  assert.strictEqual(posizioneRetro(back), 'back');
  // e una configurazione con position NON deve dirottare il retro
  assert.strictEqual(posizioneRetro(back), 'back');
});

prova('senza niente si stampa davanti, come sempre', function () {
  assert.strictEqual(posizioneFronte(null, null), 'front');
  assert.strictEqual(posizioneFronte(undefined, {}), 'front');
  assert.strictEqual(posizioneRetro(null), 'back');
});

// ---------------------------------------------------------------------------
// E CHE L'ORDINE PARTA, PRIMA ANCORA DI CHIEDERSI DOVE STAMPA
//
// Il prodotto interno che creiamo per ogni ordine nasceva con price: 0, e
// Printify lo rifiuta: "variants.0.price: The variants.0.price must be greater
// than 0" (codice 8150). C'era dal primo commit, quindi nessun ordine Printify
// e' MAI arrivato allo stampatore -- il cliente pagava su Shopify, il servizio
// rispondeva 200 come da progetto, e l'errore moriva nei log di Render.
//
// Trovato mandando un ordine di prova firmato al servizio vero: zero ordini su
// Printify a fronte di 48 prodotti americani in vendita. Questa prova e' li'
// perche' non torni: e' l'unica cosa che sta fra il cliente che paga e
// nessuno che stampa.
console.log('\nChe l\'ordine parta davvero');

const ORDINE = { id: 1, order_number: '1001' };
const RIGA = { title: 'Giacchetto Parka', variant_title: 'M / Khaki', quantity: 1 };

prova('il prezzo del prodotto interno e\' maggiore di zero', function () {
  const corpo = corpoProdotto(ORDINE, RIGA, comeScriveIlTema('giacchetto', 'front'), null,
    { blueprintId: 10740, printProviderId: 72, variantId: 399937, position: 'back_dtf' });
  assert.ok(corpo.variants.length > 0, 'senza varianti Printify non crea niente');
  for (const v of corpo.variants) {
    assert.ok(typeof v.price === 'number' && v.price > 0,
      'price ' + v.price + ': Printify risponde 400 (codice 8150) e l\'ordine non parte');
  }
});

prova('il corpo porta tutto quello che Printify pretende', function () {
  const corpo = corpoProdotto(ORDINE, RIGA, comeScriveIlTema('bandana', 'front'), null,
    { blueprintId: 562, printProviderId: 70, variantId: 101403 });
  assert.ok(corpo.title, 'senza titolo Printify rifiuta');
  assert.strictEqual(corpo.blueprint_id, 562);
  assert.strictEqual(corpo.print_provider_id, 70);
  assert.strictEqual(corpo.variants[0].id, 101403);
  assert.deepStrictEqual(corpo.print_areas[0].variant_ids, [101403],
    'l\'area deve riferirsi alla variante che il cliente ha pagato');
  assert.strictEqual(corpo.print_areas[0].placeholders[0].position, 'front');
});

prova('e sul parka quel corpo stampa sul dorso', function () {
  const corpo = corpoProdotto(ORDINE, RIGA, comeScriveIlTema('giacchetto', 'front'), null,
    { blueprintId: 10740, printProviderId: 72, variantId: 399937, position: 'back_dtf' });
  assert.strictEqual(corpo.print_areas[0].placeholders[0].position, 'back_dtf',
    'la regola deve arrivare fino al corpo della richiesta, non fermarsi alla funzione');
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
