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
 *   componendo        lo studio sta mostrando "Preparazione dell'immagine..."
 *   nomeInciso        cosa c'e' scritto sul riquadro (ROUND 48); il tema lo
 *                     riversa in [data-photo-prop-name-text] a ogni giro
 */
function form(opt) {
  const campi = opt.personalizzabile
    ? [{ value: opt.designPresente ? '{"printify_image_id":"abc"}' : '' }]
    : [];
  const stato = statoEditor(opt.editorInErrore);
  if (opt.componendo) stato.textContent = COMPONENDO;
  const nomi = opt.personalizzabile
    ? [{ value: opt.nomeInciso === undefined ? 'Rocky' : opt.nomeInciso }]
    : [];
  const btn = bottone();
  return {
    nodeName: 'FORM',
    _stato: stato,
    _btn: btn,
    getAttribute: function (n) { return n === 'action' ? '/cart/add' : null; },
    querySelectorAll: function (sel) {
      if (sel === '[data-photo-prop-data]') return campi;
      if (sel === '[data-photo-prop-name-text]') return nomi;
      if (sel === '[data-photo-status]') return [stato];
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

// ROUND 48 -- la guardia legge window.Perla.strings.composing per riconoscere
// "sto componendo" nella lingua della vetrina, con lo stesso ripiego di
// global.js. Qui si finge quel minimo: senza, il file del tema (che e' codice
// da browser, dove window esiste sempre) fallirebbe su una mancanza del
// finto ambiente, non su un suo difetto.
const COMPONENDO = 'Preparazione dell\'immagine...';
global.window = { Perla: { strings: { composing: COMPONENDO } } };

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

console.log('\nROUND 48 — comprare mentre il disegno si sta ancora preparando');

// La guardia `composing` di global.js, mentre un caricamento e' in volo,
// restituisce la promessa VECCHIA invece di comporre di nuovo: quando quella
// atterra scrive il suo composito e dice "Design pronto.". Comprare in quella
// finestra vuol dire pagare una cosa e riceverne un'altra.
prova('composizione in corso: si ferma, anche col design gia\' presente', function () {
  const f = form({ personalizzabile: true, designPresente: true, componendo: true });
  const e = invia(f);
  assert.strictEqual(e._prevenuto, true,
    'il design che c\'e\' adesso potrebbe essere quello di un attimo fa');
  assert.ok(/ancora preparando/.test(f._stato.textContent),
    'deve dire di aspettare, invece: ' + f._stato.textContent);
});

prova('finita la composizione si compra', function () {
  const f = form({ personalizzabile: true, designPresente: true, componendo: false });
  assert.strictEqual(invia(f)._prevenuto, false);
});

console.log('\nROUND 48 — il segnaposto "Testo" mai sostituito');

// "+ Testo" crea il livello gia' pieno: new fabric.IText("Testo", ...). Chi lo
// aggiunge e non ci scrive dentro manda in stampa la parola "Testo".
prova('nome inciso ancora "Testo": si ferma e si spiega cosa fare', function () {
  const f = form({ personalizzabile: true, designPresente: true, nomeInciso: 'Testo' });
  const e = invia(f);
  assert.strictEqual(e._prevenuto, true, '"Testo" verrebbe stampato davvero');
  assert.ok(/riquadro di testo/.test(f._stato.textContent),
    'deve dire come rimediare, invece: ' + f._stato.textContent);
});

// Il caso che una ricerca sull'intera stringa si perderebbe: nome scritto sul
// primo riquadro, segnaposto dimenticato sul secondo. collectNameText() li
// unisce con " / ".
prova('"Rocky / Testo": il segnaposto dimenticato sul secondo riquadro si vede', function () {
  const f = form({ personalizzabile: true, designPresente: true, nomeInciso: 'Rocky / Testo' });
  assert.strictEqual(invia(f)._prevenuto, true);
});

prova('un nome vero passa', function () {
  const f = form({ personalizzabile: true, designPresente: true, nomeInciso: 'Rocky' });
  assert.strictEqual(invia(f)._prevenuto, false);
});

prova('un nome che CONTIENE la parola passa: si guarda il pezzo intero', function () {
  const f = form({ personalizzabile: true, designPresente: true, nomeInciso: 'Testolina' });
  assert.strictEqual(invia(f)._prevenuto, false,
    '"Testolina" e\' un nome, non il segnaposto');
});

prova('nessun testo sul riquadro non e\' un motivo per fermarsi', function () {
  const f = form({ personalizzabile: true, designPresente: true, nomeInciso: '' });
  assert.strictEqual(invia(f)._prevenuto, false,
    'si puo\' personalizzare con una foto e nessuna scritta');
});

console.log('\n' + fatte + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
