'use strict';

// Verifica che un ordine arrivato da Facebook, Instagram o Shop senza
// personalizzazione non sparisca in silenzio.
//
// PERCHE' ESISTE
// Il webhook filtra le righe che hanno la proprieta' _Personalizzazione e
// butta via tutte le altre. Finche' si vendeva solo dal sito quel filtro era
// giusto: chi non aveva personalizzato non esisteva. Da quando i prodotti
// sono su Meta, un cliente puo' comprare senza mai vedere lo studio: la sua
// riga finisce nello stesso cestino, senza un log, e la titolare lo scopre
// dal cliente che chiede dov'e' il suo ordine.
//
// Uso:  node tests/righe-senza-personalizzazione.test.js

const assert = require('assert');
const modulo = require('../scripts/righe-senza-personalizzazione');

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

// Raccoglie i messaggi invece di sporcare l'output del test.
function raccoglitore() {
  const righe = [];
  const fn = function (msg) { righe.push(msg); };
  fn.righe = righe;
  return fn;
}

function riga(id, titolo, personalizzata, variante) {
  return {
    id: id,
    title: titolo,
    variant_title: variante || null,
    properties: personalizzata
      ? [{ name: '_Personalizzazione', value: '{"printify_image_id":"abc"}' }]
      : [],
  };
}

// Ricalca il filtro reale di perla-printify-order-sync.js, cosi' il test
// esercita la stessa divisione fra righe viste e righe scartate.
function personalizzate(order) {
  return (order.line_items || []).filter(function (item) {
    return (item.properties || []).some(function (p) {
      return (p.name === '_Personalizzazione' || p.name === '_Personalizzazione_Retro') && p.value;
    });
  });
}

console.log('\nOrdini dal sito: niente da segnalare');

prova('un ordine web personalizzato non produce rumore', function () {
  const order = {
    id: 1001,
    source_name: 'web',
    line_items: [riga(1, 'Collare Uliveto', true, 'M / Onice')],
  };
  const log = raccoglitore();
  const orfane = modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log);
  assert.deepStrictEqual(orfane, []);
  assert.strictEqual(log.righe.length, 0, 'nessun messaggio atteso');
});

prova('dal sito una riga senza personalizzazione VIENE segnalata', function () {
  // ROUND 45 -- questa verifica prima pretendeva il silenzio, col ragionamento
  // "sul sito lo studio c'e', quindi se manca la personalizzazione e' una
  // scelta del cliente".
  //
  // Quel ragionamento era sbagliato, ed e' costato il difetto peggiore del
  // sistema: nel tema, se il caricamento su /upload fallisce, il .catch svuota
  // il dato e "aggiungi al carrello" prosegue lo stesso. La riga arriva con
  // _Personalizzazione vuota, il filtro degli ordini la scarta, e questo
  // paracadute la ignorava perche' il canale era 'web'. Ordine pagato, niente
  // stampato, nessuna traccia.
  //
  // Meglio una segnalazione di troppo su un ordine strano che un ordine perso
  // in silenzio: e' lo stesso principio con cui il modulo tratta i canali
  // sconosciuti.
  const order = {
    id: 1002,
    source_name: 'web',
    line_items: [riga(1, 'Ciotola Marinara', false)],
  };
  const log = raccoglitore();
  const orfane = modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log);
  assert.strictEqual(orfane.length, 1, 'la riga orfana dal sito va segnalata');
  assert.strictEqual(orfane[0].title, 'Ciotola Marinara');
  assert.strictEqual(log.righe.length, 1, 'e deve lasciare un messaggio');
});

prova('l\'ordine compilato a mano e la vendita di persona non si segnalano', function () {
  for (const canale of ['shopify_draft_order', 'pos']) {
    const order = { id: 1003, source_name: canale, line_items: [riga(1, 'Bandana Lino', false)] };
    const log = raccoglitore();
    assert.deepStrictEqual(
      modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log), [],
      canale + ' non deve essere segnalato');
  }
});

console.log('\nOrdini da Meta: e\' questo il caso che prima spariva');

prova('una riga Instagram senza personalizzazione viene segnalata', function () {
  const order = {
    id: 2001,
    source_name: 'instagram',
    line_items: [riga(1, 'Collare Uliveto', false, 'M / Onice')],
  };
  const log = raccoglitore();
  const orfane = modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log);

  assert.strictEqual(orfane.length, 1, 'la riga deve essere segnalata, non scartata');
  assert.strictEqual(orfane[0].id, 1);
  assert.strictEqual(log.righe.length, 1, 'deve restare traccia nei log');
});

prova('il messaggio dice ordine, canale e cosa ha comprato il cliente', function () {
  const order = {
    id: 2002,
    source_name: 'facebook',
    line_items: [riga(7, 'Cuccia Damasco', false, 'Grande (127 x 102 cm)')],
  };
  const log = raccoglitore();
  modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log);

  const msg = log.righe[0];
  assert.ok(/2002/.test(msg), 'manca il numero d\'ordine: ' + msg);
  assert.ok(/facebook/.test(msg), 'manca il canale: ' + msg);
  assert.ok(/Cuccia Damasco/.test(msg), 'manca il prodotto: ' + msg);
  assert.ok(/Grande \(127 x 102 cm\)/.test(msg),
    'manca la taglia: senza, la titolare non sa cosa rifare a mano. ' + msg);
  assert.ok(/negozio online/.test(msg),
    'il messaggio deve dire come evitare che risucceda: ' + msg);
});

prova('si segnalano solo le righe orfane, non tutto l\'ordine', function () {
  // Caso misto: il cliente arriva da Instagram ma atterra sul sito per un
  // prodotto e non per l'altro.
  const order = {
    id: 2003,
    source_name: 'instagram',
    line_items: [
      riga(1, 'Collare Uliveto', true, 'M / Onice'),
      riga(2, 'Medaglietta Cammeo', false, 'Unica (2,5 cm)'),
    ],
  };
  const log = raccoglitore();
  const orfane = modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log);

  assert.strictEqual(orfane.length, 1);
  assert.strictEqual(orfane[0].id, 2, 'deve essere la medaglietta, non il collare');
  assert.ok(!/Collare Uliveto/.test(log.righe[0]),
    'la riga gia\' in stampa non va rimessa nella lista da fare a mano');
});

prova('un ordine Instagram tutto personalizzato non allarma', function () {
  // Col checkout sul negozio online e' questo il caso normale: il cliente
  // arriva da Instagram ma personalizza e paga sul sito.
  const order = {
    id: 2004,
    source_name: 'instagram',
    line_items: [
      riga(1, 'Collare Uliveto', true),
      riga(2, 'Bandana Toile', true),
    ],
  };
  const log = raccoglitore();
  assert.deepStrictEqual(
    modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log), [],
    'segnalare qui vorrebbe dire far ignorare i log alla titolare');
  assert.strictEqual(log.righe.length, 0);
});

console.log('\nCanali che oggi non esistono');

prova('un canale sconosciuto viene segnalato, non ignorato', function () {
  // Se domani si apre TikTok Shop, o Shopify cambia il nome di un canale,
  // il difetto deve ricomparire nei log da solo. L'elenco enumera i canali
  // SICURI proprio per questo.
  const order = {
    id: 3001,
    source_name: 'tiktok_shop_domani',
    line_items: [riga(1, 'Collare Uliveto', false)],
  };
  const log = raccoglitore();
  assert.strictEqual(
    modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log).length, 1);
});

prova('un ordine senza source_name non passa liscio', function () {
  const order = { id: 3002, line_items: [riga(1, 'Collare Uliveto', false)] };
  const log = raccoglitore();
  assert.strictEqual(
    modulo.segnalaRigheSenzaPersonalizzazione(order, personalizzate(order), log).length, 1);
  assert.ok(/sconosciuto/.test(log.righe[0]), 'il canale ignoto va detto: ' + log.righe[0]);
});

prova('un ordine senza righe non fa rumore ne\' esplode', function () {
  const log = raccoglitore();
  assert.deepStrictEqual(
    modulo.segnalaRigheSenzaPersonalizzazione({ id: 3003, source_name: 'instagram' }, [], log), []);
  assert.strictEqual(log.righe.length, 0);
});

console.log('\nIl difetto che questo test deve cogliere');

prova('senza la segnalazione la riga sparirebbe davvero', function () {
  // Il comportamento di prima: filtra e basta. Se qualcuno rimuovesse la
  // chiamata dal webhook, questa e' la riga che nessuno vedrebbe piu'.
  const order = {
    id: 4001,
    source_name: 'instagram',
    line_items: [riga(1, 'Cuccia Damasco', false, 'Grande (127 x 102 cm)')],
  };
  assert.strictEqual(personalizzate(order).length, 0,
    'il filtro del webhook la scarta: e\' il punto di partenza');
  assert.strictEqual(modulo.trovaRigheOrfane(order, personalizzate(order)).length, 1,
    'ed e\' esattamente quella che va recuperata');
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
