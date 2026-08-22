'use strict';

// Il consigliatore di taglia: peso e razza entrano, la pastiglia giusta si
// seleziona da sola.
//
// Le due cose che DEVONO essere vere, e che a occhio non si vedono:
//
// 1. Selezionare la pastiglia non basta: il tema aggiorna prezzo, immagine e
//    id della variante ascoltando l'evento 'change'. Senza quell'evento
//    cambierebbe solo il pallino, e nel carrello finirebbe la taglia
//    sbagliata -- il difetto peggiore possibile per una funzione che nasce
//    per far scegliere bene.
// 2. Fuori tabella si dice, non si tira a indovinare. Un chihuahua ha il collo
//    di 21 cm e il collare piu' piccolo parte da 30: consigliargli la S
//    sarebbe vendergli qualcosa che non si chiude.
//
// Come per tests/guardia-carrello.test.js: il file del tema e' un IIFE che
// parla con document, quindi qui si finge un document ridotto all'osso.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

let fatte = 0;
function prova(nome, fn) {
  try {
    fn();
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

// ---- finto DOM ------------------------------------------------------------

function nodo(attrs) {
  const a = attrs || {};
  const el = {
    _attr: Object.assign({}, a.attributi),
    value: a.value === undefined ? '' : a.value,
    checked: !!a.checked,
    textContent: '',
    childNodes: [],
    _hidden: !!a.hidden,
    _ascolti: {},
    _eventi: [],
    getAttribute(k) { return this._attr[k] === undefined ? null : this._attr[k]; },
    setAttribute(k, v) { this._attr[k] = String(v); },
    hasAttribute(k) { return k === 'hidden' ? this._hidden : this._attr[k] !== undefined; },
    removeAttribute(k) { if (k === 'hidden') this._hidden = false; else delete this._attr[k]; },
    appendChild(c) { this.childNodes.push(c); return c; },
    addEventListener(ev, fn) { (this._ascolti[ev] = this._ascolti[ev] || []).push(fn); },
    dispatchEvent(e) { this._eventi.push(e.type); (this._ascolti[e.type] || []).forEach((f) => f(e)); return true; },
    click() { (this._ascolti.click || []).forEach((f) => f({})); },
    classList: { toggle() {}, add() {}, remove() {} },
    remove() { this._rimosso = true; },
  };
  el.setAttribute('hidden', undefined);
  delete el._attr.hidden;
  return el;
}

function scena(opzioni) {
  const o = opzioni || {};
  const valori = o.valori || ['S', 'M', 'L'];
  const pastiglie = valori.map((v) => nodo({ value: v }));

  // Le pastiglie sono radio con lo stesso name: selezionarne una deseleziona
  // le altre. Senza riprodurlo qui la prova segnalava due taglie scelte
  // insieme e sembrava un difetto del codice, mentre era il finto DOM a essere
  // troppo finto.
  pastiglie.forEach((p, i) => {
    let stato = i === 0;
    Object.defineProperty(p, 'checked', {
      get() { return stato; },
      set(v) {
        stato = !!v;
        if (stato) pastiglie.forEach((altra) => { if (altra !== p) altra.checked = false; });
      },
    });
  });

  const peso = nodo({});
  const razza = nodo({});
  const collo = o.collo ? nodo({}) : null;
  const esito = nodo({ hidden: true });
  const calcola = nodo({});
  const elencoRazze = nodo({});

  const radice = nodo({ attributi: {
    'data-tipo': o.tipo,
    'data-testo-ok': 'Taglia [taglia]: selezionata, [perche].',
    'data-testo-vuoto': 'Serve il peso o la razza.',
    'data-testo-fuori': 'Nessuna taglia calza bene.',
  } });

  const dentro = {
    '[data-taglia-peso]': peso,
    '[data-taglia-razza]': razza,
    '[data-taglia-collo]': collo,
    '[data-taglia-esito]': esito,
    '[data-taglia-calcola]': calcola,
    '[data-taglia-razze]': elencoRazze,
    '[data-taglia-apri]': null,
    '[data-taglia-corpo]': null,
  };
  radice.querySelector = (sel) => (sel in dentro ? dentro[sel] : null);

  const gruppo = { parentNode: { insertBefore() {} } };
  const modulo = {
    querySelector: (sel) => (sel === '.variant-group' ? gruppo : null),
    querySelectorAll: (sel) => (sel.indexOf('variant-pills') >= 0 ? pastiglie : []),
  };

  global.document = {
    readyState: 'complete',
    querySelector: (sel) => (sel === '[data-product-form]' ? modulo : null),
    querySelectorAll: (sel) => (sel === '[data-consiglia-taglia]' ? [radice] : []),
    addEventListener() {},
    createElement: () => nodo({}),
  };
  global.window = {};
  global.Event = function (tipo) { this.type = tipo; };

  delete require.cache[require.resolve(SORGENTE)];
  require(SORGENTE);

  return { radice, pastiglie, peso, razza, collo, esito, calcola, elencoRazze };
}

const SORGENTE = path.join(__dirname, '..', 'theme', 'assets', 'perla-taglia.js');

function selezionata(pastiglie) {
  const p = pastiglie.filter((x) => x.checked);
  return p.length === 1 ? p[0].value : '(' + p.length + ' selezionate)';
}

// ---- le prove -------------------------------------------------------------

console.log('\nConsiglio della taglia');

prova('il peso sceglie la cuccia giusta', () => {
  const s = scena({ tipo: 'cuccia', valori: ['28" × 18"', '40" × 30"', '50" × 40"'] });
  s.peso.value = '20';
  s.calcola.click();
  assert.strictEqual(selezionata(s.pastiglie), '40" × 30"');
});

prova('la razza basta da sola quando il peso manca', () => {
  const s = scena({ tipo: 'collare_eu', collo: true });
  s.razza.value = 'Jack Russell';
  s.calcola.click();
  assert.strictEqual(selezionata(s.pastiglie), 'S');
});

prova('la misura del collo batte peso e razza', () => {
  const s = scena({ tipo: 'collare_eu', collo: true });
  s.razza.value = 'Jack Russell';   // da solo direbbe S
  s.peso.value = '7';
  s.collo.value = '50';             // ma il metro dice un collo grosso
  s.calcola.click();
  assert.strictEqual(selezionata(s.pastiglie), 'L');
});

prova("la pastiglia emette 'change', se no il carrello prende la taglia vecchia", () => {
  const s = scena({ tipo: 'cuccia', valori: ['28" × 18"', '40" × 30"', '50" × 40"'] });
  s.peso.value = '40';
  s.calcola.click();
  const grande = s.pastiglie[2];
  assert.ok(grande.checked, 'la piu\' grande doveva essere selezionata');
  assert.ok(grande._eventi.indexOf('change') >= 0, "manca l'evento change");
});

prova('non tocca niente se non emette change su una pastiglia gia\' giusta', () => {
  const s = scena({ tipo: 'cuccia', valori: ['28" × 18"', '40" × 30"', '50" × 40"'] });
  s.peso.value = '5';               // la prima e' gia' selezionata
  s.calcola.click();
  assert.strictEqual(selezionata(s.pastiglie), '28" × 18"');
  assert.strictEqual(s.pastiglie[0]._eventi.length, 0, 'change inutile su una scelta invariata');
});

prova('a cavallo fra due taglie vince la piu\' grande', () => {
  const s = scena({ tipo: 'bandana', valori: ['20" × 10"', '27" × 13"'] });
  s.peso.value = '12';              // confine esatto fra le due
  s.calcola.click();
  assert.strictEqual(selezionata(s.pastiglie), '27" × 13"');
});

prova('fuori tabella lo dice invece di consigliare a caso', () => {
  const s = scena({ tipo: 'collare_eu', collo: true });
  s.collo.value = '21';             // collo da chihuahua, la S parte da 30
  s.calcola.click();
  assert.strictEqual(s.esito.textContent, 'Nessuna taglia calza bene.');
  assert.strictEqual(selezionata(s.pastiglie), 'S', 'non doveva cambiare la selezione');
});

prova('senza dati chiede i dati', () => {
  const s = scena({ tipo: 'cuccia', valori: ['28" × 18"', '40" × 30"', '50" × 40"'] });
  s.calcola.click();
  assert.strictEqual(s.esito.textContent, 'Serve il peso o la razza.');
});

prova('la risposta dice sempre da dove viene il consiglio', () => {
  const s = scena({ tipo: 'collare_eu', collo: true });
  s.peso.value = '25';
  s.calcola.click();
  assert.ok(/stimata dal peso/.test(s.esito.textContent),
    'la stima dal peso va dichiarata: era "' + s.esito.textContent + '"');
});

prova('un tipo senza tabella misure si toglie di mezzo', () => {
  const s = scena({ tipo: 'medaglietta', valori: ['1"', '2"'] });
  assert.ok(s.radice._rimosso, 'il pannello doveva sparire');
});

prova("l'elenco razze viene riempito da qui, non dal markup", () => {
  const s = scena({ tipo: 'cuccia', valori: ['28" × 18"', '40" × 30"', '50" × 40"'] });
  assert.ok(s.elencoRazze.childNodes.length > 50,
    'razze trovate: ' + s.elencoRazze.childNodes.length);
});

console.log('\n' + fatte + ' verifiche superate.\n');
