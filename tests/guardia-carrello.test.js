'use strict';

// ROUND 45 -- la guardia che impedisce l'ordine fantasma.
//
// Il caso che deve cogliere: il caricamento del design fallisce, il tema
// svuota il campo, e "aggiungi al carrello" prosegue lo stesso. Il cliente
// paga e non si stampa niente.
//
// Il caso che NON deve toccare, ed e' il motivo per cui la guardia guarda due
// segnali invece di uno: chi non vuole personalizzare niente lascia il campo
// vuoto di proposito. Bloccarlo sarebbe peggio del difetto che si sta
// chiudendo.
//
// Il file del tema e' un IIFE che si registra su document: qui si finge un
// document, si cattura l'ascoltatore, e lo si chiama con eventi finti.

const assert = require('assert');
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

// ---- finto DOM, ridotto a quello che la guardia usa davvero --------------

function elemento(attrs, classi) {
  return {
    nodeName: 'INPUT',
    value: (attrs && attrs.value) || '',
    _classi: new Set(classi || []),
    classList: {
      add: function (c) { this._c.add(c); },
      remove: function (c) { this._c.delete(c); },
    },
    textContent: '',
    disabled: false,
  };
}

function statoEditor(inErrore) {
  const el = {
    nodeName: 'P',
    textContent: '',
    _c: new Set(inErrore ? ['product-personalize__status--error'] : []),
  };
  el.classList = {
    add: function (c) { el._c.add(c); },
    remove: function (c) { el._c.delete(c); },
  };
  return el;
}

function bottone() {
  const b = { nodeName: 'BUTTON', disabled: true, _c: new Set(['is-loading']) };
  b.classList = { add: function (c) { b._c.add(c); }, remove: function (c) { b._c.delete(c); } };
  return b;
}

/**
 * @param {object} opt
 *   personalizzabile  il form ha i campi del design
 *   designPresente    quei campi hanno un valore
 *   editorInErrore    lo studio sta mostrando l'errore di caricamento
 */
function form(opt) {
  const campi = opt.personalizzabile
    ? [{ value: opt.designPresente ? '{"printify_image_id":"abc"}' : '' }]
    : [];
  const stato = statoEditor(opt.editorInErrore);
  const btn = bottone();
  return {
    nodeName: 'FORM',
    _stato: stato,
    _btn: btn,
    getAttribute: function (n) { return n === 'action' ? '/cart/add' : null; },
    querySelectorAll: function (sel) {
      if (sel === '[data-photo-prop-data]') return campi;
      return [];
    },
    querySelector: function (sel) {
      if (sel === '[data-photo-status].product-personalize__status--error') {
        return stato._c.has('product-personalize__status--error') ? stato : null;
      }
      if (sel === '[data-photo-status]') return stato;
      if (sel === '[data-add-btn]') return btn;
      return null;
    },
  };
}

// ---- caricamento del file del tema ---------------------------------------

let handler = null;
global.document = {
  addEventListener: function (tipo, fn, cattura) {
    assert.strictEqual(tipo, 'submit');
    assert.strictEqual(cattura, true,
      'deve stare in fase di CATTURA, altrimenti il gestore del tema parte comunque');
    handler = fn;
  },
};
require(path.join(__dirname, '..', 'theme', 'assets', 'perla-guardia-carrello.js'));

function invia(f) {
  const e = { target: f, _prevenuto: false, _fermato: false };
  e.preventDefault = function () { e._prevenuto = true; };
  e.stopImmediatePropagation = function () { e._fermato = true; };
  handler(e);
  return e;
}

// ---- le verifiche ---------------------------------------------------------

console.log('\nSi registra nel modo giusto');

prova('l\'ascoltatore e\' in fase di cattura su document', function () {
  assert.strictEqual(typeof handler, 'function', 'nessun ascoltatore registrato');
});

console.log('\nIl caso da bloccare');

prova('design vuoto E editor in errore: l\'aggiunta al carrello si ferma', function () {
  const f = form({ personalizzabile: true, designPresente: false, editorInErrore: true });
  const e = invia(f);
  assert.strictEqual(e._prevenuto, true, 'doveva chiamare preventDefault');
  assert.strictEqual(e._fermato, true,
    'senza stopImmediatePropagation il gestore del tema aggiunge la riga lo stesso');
});

prova('e il cliente vede perche\', col pulsante di nuovo utilizzabile', function () {
  const f = form({ personalizzabile: true, designPresente: false, editorInErrore: true });
  invia(f);
  assert.ok(/non è stato caricato/.test(f._stato.textContent),
    'il messaggio deve dire cosa e\' successo, invece: ' + f._stato.textContent);
  assert.strictEqual(f._btn.disabled, false, 'il pulsante non deve restare bloccato');
  assert.strictEqual(f._btn._c.has('is-loading'), false,
    'il pulsante non deve restare a girare per sempre');
});

console.log('\nI casi che NON vanno toccati');

prova('design vuoto ma nessun errore: e\' una scelta del cliente, passa', function () {
  const f = form({ personalizzabile: true, designPresente: false, editorInErrore: false });
  const e = invia(f);
  assert.strictEqual(e._prevenuto, false,
    'chi non vuole personalizzare deve poter comprare lo stesso');
});

prova('design presente: passa', function () {
  const f = form({ personalizzabile: true, designPresente: true, editorInErrore: false });
  assert.strictEqual(invia(f)._prevenuto, false);
});

prova('design presente anche se un errore vecchio e\' rimasto: passa', function () {
  const f = form({ personalizzabile: true, designPresente: true, editorInErrore: true });
  assert.strictEqual(invia(f)._prevenuto, false,
    'se il design c\'e\', si compra: la classe d\'errore da sola non basta a bloccare');
});

prova('prodotto non personalizzabile: la guardia non entra mai in gioco', function () {
  const f = form({ personalizzabile: false, designPresente: false, editorInErrore: true });
  assert.strictEqual(invia(f)._prevenuto, false);
});

prova('un form che non e\' quello del carrello viene ignorato', function () {
  const f = form({ personalizzabile: true, designPresente: false, editorInErrore: true });
  f.getAttribute = function () { return '/search'; };
  assert.strictEqual(invia(f)._prevenuto, false);
});

prova('un submit senza form non fa esplodere niente', function () {
  const e = { target: null, preventDefault: function () {}, stopImmediatePropagation: function () {} };
  assert.doesNotThrow(function () { handler(e); });
});

console.log('\n' + fatte + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
