'use strict';

// ROUND 48 -- la sveglia dell'editor.
//
// Quello che deve valere, e che qui si verifica una cosa per volta:
//
//   1. l'indirizzo della sveglia si ricava da quello del caricamento, cioe'
//      .../upload diventa .../health. Se si sbagliasse, il servizio non si
//      sveglierebbe e nessuno se ne accorgerebbe: la personalizzazione
//      tornerebbe sbagliata come prima, senza errori a video;
//   2. non si chiama niente al caricamento della pagina. Una chiamata per
//      ogni visita terrebbe il servizio sempre acceso e finirebbe le ore
//      gratuite di Render;
//   3. si chiama UNA volta sola, per quanti tocchi arrivino;
//   4. dove l'editor non c'e', o dove il servizio non e' configurato, non si
//      chiama e non si rompe niente;
//   5. il messaggio d'attesa compare solo a chi tocca l'editor, e sparisce
//      appena il servizio risponde;
//   6. quel messaggio NON e' [data-photo-status]. Quello lo scrive global.js
//      con setPhotoStatus: due mani sullo stesso paragrafo vuol dire messaggi
//      che si cancellano a vicenda.
//
// Il file del tema e' un IIFE che legge il DOM appena parte, quindi ogni
// scenario ricostruisce il finto documento e ricarica il modulo da zero.

const assert = require('assert');
const path = require('path');

const MODULO = path.join(__dirname, '..', 'theme', 'assets', 'perla-editor-sveglia.js');

let fatte = 0;
async function prova(nome, fn) {
  try {
    await fn();
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

/* ---- finto DOM, ridotto a quello che il file usa davvero ----------------- */

// Selettori usati dal file: '[attributo]', '.classe', e un solo discendente
// ('.pd-modal__body [data-fabric-viewport]'). Non serve altro.
function combacia(el, pezzo) {
  if (pezzo[0] === '[') return el.getAttribute(pezzo.slice(1, -1)) !== null;
  if (pezzo[0] === '.') return el.classList.contains(pezzo.slice(1));
  return el.nodeName === pezzo.toUpperCase();
}

function discendenti(el, fuori) {
  let out = [];
  el._figli.forEach(function (f) {
    if (!fuori) out.push(f);
    out = out.concat(discendenti(f, false));
  });
  return out;
}

function cerca(radice, sel) {
  const pezzi = sel.trim().split(/\s+/);
  let candidati = discendenti(radice, false);
  pezzi.forEach(function (pezzo, i) {
    candidati = candidati.filter(function (el) { return combacia(el, pezzo); });
    if (i < pezzi.length - 1) {
      let sotto = [];
      candidati.forEach(function (el) { sotto = sotto.concat(discendenti(el, false)); });
      candidati = sotto;
    }
  });
  return candidati;
}

function elemento(tag, attrs, classi) {
  const el = {
    nodeName: tag.toUpperCase(),
    _attrs: Object.assign({}, attrs),
    _figli: [],
    _classi: new Set(classi || []),
    style: {},
    textContent: '',
    parentNode: null,
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(this._attrs, n) ? this._attrs[n] : null;
    },
    setAttribute: function (n, v) { this._attrs[n] = v; },
    addEventListener: function () {},
    appendChild: function (c) { c.parentNode = this; this._figli.push(c); return c; },
    removeChild: function (c) {
      const i = this._figli.indexOf(c);
      if (i >= 0) { this._figli.splice(i, 1); c.parentNode = null; }
      return c;
    },
    closest: function (sel) {
      let n = this;
      while (n) { if (combacia(n, sel)) return n; n = n.parentNode; }
      return null;
    },
    querySelector: function (sel) { return cerca(this, sel)[0] || null; },
    querySelectorAll: function (sel) { return cerca(this, sel); },
  };
  el.classList = {
    add: function (c) { el._classi.add(c); },
    remove: function (c) { el._classi.delete(c); },
    contains: function (c) { return el._classi.has(c); },
  };
  // className non e' una proprieta' qualunque: assegnarla riscrive le classi.
  // Senza questo il finto DOM direbbe "nessuna classe" su un elemento che nel
  // browser vero ce le ha, e il test fallirebbe accusando il modulo.
  Object.defineProperty(el, 'className', {
    get: function () { return Array.from(el._classi).join(' '); },
    set: function (v) {
      el._classi = new Set(String(v).split(/\s+/).filter(Boolean));
    },
  });
  return el;
}

/**
 * @param {object} opt
 *   editor     c'e' un [data-photo-customizer] nella pagina
 *   endpoint   valore di data-upload-endpoint ('' = servizio non configurato)
 */
function scena(opt) {
  const body = elemento('body');
  const fuori = elemento('div', { 'data-qualcosa': '' });   // un pezzo di pagina non-editor
  body.appendChild(fuori);

  let editor = null;
  if (opt.editor !== false) {
    editor = elemento('div', {
      'data-photo-customizer': '',
      'data-upload-endpoint': opt.endpoint === undefined
        ? 'https://perla-upload.onrender.com/upload'
        : opt.endpoint,
    });
    body.appendChild(editor);
  }

  const chiamate = [];
  let risolvi = null;
  let rifiuta = null;

  global.fetch = function (url) {
    chiamate.push(url);
    return new Promise(function (ok, no) { risolvi = ok; rifiuta = no; });
  };

  global.document = {
    body: body,
    _ascoltatori: {},
    addEventListener: function (tipo, fn) {
      (this._ascoltatori[tipo] = this._ascoltatori[tipo] || []).push(fn);
    },
    createElement: function (tag) { return elemento(tag); },
    querySelector: function (sel) { return cerca(body, sel)[0] || null; },
    querySelectorAll: function (sel) { return cerca(body, sel); },
    documentElement: body,
  };

  global.window = {
    scrollY: 0,
    scrollTo: function () {},
    matchMedia: function () { return { matches: true }; },   // fingiamo un telefono
    MutationObserver: function () { return { observe: function () {} }; },
  };
  global.MutationObserver = global.window.MutationObserver;

  delete require.cache[require.resolve(MODULO)];
  require(MODULO);

  return {
    body: body,
    editor: editor,
    fuori: fuori,
    chiamate: chiamate,
    tocca: function (bersaglio) {
      (global.document._ascoltatori.pointerdown || []).forEach(function (fn) {
        fn({ target: bersaglio });
      });
    },
    rispondi: function () { risolvi({ ok: true }); return sfoga(); },
    fallisci: function () { rifiuta(new Error('giu')); return sfoga(); },
    attesa: function () { return editor ? editor.querySelector('.perla-attesa') : null; },
  };
}

// Le promesse di fetch si risolvono in microtask: due giri bastano per far
// arrivare il .then del modulo prima che il test guardi il risultato.
function sfoga() {
  return Promise.resolve().then(function () {}).then(function () {});
}

/* ---- le verifiche -------------------------------------------------------- */

(async function () {

  console.log('\nDove chiama, e quando');

  await prova('/upload diventa /health, senza portarsi dietro la query', async function () {
    const s = scena({ endpoint: 'https://perla-upload.onrender.com/upload?x=1' });
    s.tocca(s.fuori);
    assert.deepStrictEqual(s.chiamate, ['https://perla-upload.onrender.com/health']);
  });

  await prova('al caricamento della pagina non chiama niente', async function () {
    const s = scena({});
    assert.deepStrictEqual(s.chiamate, [],
      'una chiamata per ogni visita terrebbe il servizio sempre acceso');
  });

  await prova('basta un tocco qualunque sulla pagina del prodotto', async function () {
    const s = scena({});
    s.tocca(s.fuori);
    assert.strictEqual(s.chiamate.length, 1,
      'chi tocca la pagina sta guardando il prodotto: e\' il momento giusto per svegliare');
  });

  await prova('venti tocchi restano una chiamata sola', async function () {
    const s = scena({});
    for (let i = 0; i < 20; i++) s.tocca(s.editor);
    assert.strictEqual(s.chiamate.length, 1);
  });

  console.log('\nDove non deve entrare in gioco');

  await prova('pagina senza editor: nessuna chiamata', async function () {
    const s = scena({ editor: false });
    s.tocca(s.fuori);
    assert.deepStrictEqual(s.chiamate, []);
  });

  await prova('servizio non configurato: nessuna chiamata, nessun errore', async function () {
    const s = scena({ endpoint: '' });
    assert.doesNotThrow(function () { s.tocca(s.editor); });
    assert.deepStrictEqual(s.chiamate, []);
  });

  await prova('indirizzo scritto male: non chiama e non esplode', async function () {
    const s = scena({ endpoint: 'non-un-indirizzo' });
    assert.doesNotThrow(function () { s.tocca(s.editor); });
    assert.deepStrictEqual(s.chiamate, []);
  });

  console.log('\nL\'attesa detta, non nascosta');

  await prova('chi tocca fuori dall\'editor non vede nessun avviso', async function () {
    const s = scena({});
    s.tocca(s.fuori);
    assert.strictEqual(s.attesa(), null,
      'chi sta ancora scegliendo la taglia non va fatto preoccupare');
  });

  await prova('chi tocca l\'editor mentre e\' freddo lo legge', async function () {
    const s = scena({});
    s.tocca(s.editor);
    const p = s.attesa();
    assert.ok(p, 'nessun messaggio d\'attesa');
    assert.ok(/prepar/i.test(p.textContent), 'deve dire cosa sta succedendo: ' + p.textContent);
  });

  await prova('quando il servizio risponde, l\'avviso sparisce', async function () {
    const s = scena({});
    s.tocca(s.editor);
    assert.ok(s.attesa(), 'serve un avviso da far sparire');
    await s.rispondi();
    assert.strictEqual(s.attesa(), null, 'a servizio sveglio l\'avviso non ha piu\' senso');
  });

  await prova('un solo avviso anche toccando l\'editor dieci volte', async function () {
    const s = scena({});
    for (let i = 0; i < 10; i++) s.tocca(s.editor);
    assert.strictEqual(s.editor.querySelectorAll('.perla-attesa').length, 1);
  });

  await prova('l\'avviso non e\' [data-photo-status]: non litiga con global.js', async function () {
    const s = scena({});
    s.tocca(s.editor);
    const p = s.attesa();
    assert.strictEqual(p.getAttribute('data-photo-status'), null,
      'se fosse quello, setPhotoStatus lo sovrascriverebbe e viceversa');
  });

  console.log('\n' + fatte + ' verifiche superate.' +
    (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
})();
