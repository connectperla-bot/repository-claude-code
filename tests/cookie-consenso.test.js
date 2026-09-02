'use strict';

// ROUND 49 -- il banner dei cookie.
//
// Quello che deve valere, e che qui si verifica una cosa per volta:
//
//   1. non si registra MAI un consenso da soli. Un banner che manda
//      setTrackingConsent al caricamento e' peggio di nessun banner: dice a
//      Shopify che il cliente ha detto di si' quando il cliente non ha
//      nemmeno guardato la pagina;
//   2. "Accetta" e "Rifiuta" mandano la forma giusta -- e "Rifiuta" manda
//      false, non "niente". Non rispondere e rispondere di no sono due stati
//      diversi per l'API e vanno tenuti diversi;
//   3. chi ha gia' scelto non rivede la barra;
//   4. chi non ha mai scelto la vede ANCHE se shouldShowBanner() dice di no.
//      Quel metodo risponde false finche' nessuno ha configurato le regioni
//      nel pannello Shopify: fidarsi solo di lui vorrebbe dire spedire un
//      banner che non compare a nessuno e sembra funzionare;
//   5. se in pagina c'e' il banner nativo di Shopify, il nostro tace. Due
//      barre di consenso nello stesso angolo sono il difetto che stiamo
//      togliendo, non uno da aggiungere;
//   6. chiudere le preferenze senza scegliere non vale come un si': la barra
//      torna;
//   7. riaprendo le preferenze gli interruttori mostrano lo stato VERO, non
//      "tutto acceso". Altrimenti un "salva" distratto riaccende cio' che era
//      stato spento.
//
// Il file del tema e' un IIFE che legge il DOM appena parte, quindi ogni
// scenario ricostruisce il finto documento e ricarica il modulo da zero.
//
// Uso:  node tests/cookie-consenso.test.js

const assert = require('assert');
const path = require('path');

const MODULO = path.join(__dirname, '..', 'theme', 'assets', 'perla-cookie.js');

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

/* ---- finto DOM, ridotto a quello che il file usa davvero ----------------- */

// Selettori usati dal file: '[attributo]', '[attributo="valore"]', '.classe'
// e '#id'. Non serve altro, e aggiungerne non renderebbe la prova piu' vera.
function combacia(el, sel) {
  if (sel[0] === '#') return el._attrs.id === sel.slice(1);
  if (sel[0] === '.') return el._classi.has(sel.slice(1));
  if (sel[0] === '[') {
    const dentro = sel.slice(1, -1);
    const eq = dentro.indexOf('=');
    if (eq === -1) return el.getAttribute(dentro) !== null;
    const nome = dentro.slice(0, eq);
    const valore = dentro.slice(eq + 1).replace(/^["']|["']$/g, '');
    return el.getAttribute(nome) === valore;
  }
  return el.nodeName === sel.toUpperCase();
}

function discendenti(el) {
  let out = [];
  el._figli.forEach(function (f) {
    out.push(f);
    out = out.concat(discendenti(f));
  });
  return out;
}

function cerca(radice, sel) {
  return discendenti(radice).filter(function (el) { return combacia(el, sel.trim()); });
}

function elemento(tag, attrs, classi) {
  const el = {
    nodeName: tag.toUpperCase(),
    _attrs: Object.assign({}, attrs),
    _figli: [],
    _classi: new Set(classi || []),
    _clic: [],
    hidden: false,
    checked: false,
    disabled: false,
    parentNode: null,
    getAttribute: function (n) {
      return Object.prototype.hasOwnProperty.call(this._attrs, n) ? this._attrs[n] : null;
    },
    setAttribute: function (n, v) { this._attrs[n] = v; },
    addEventListener: function (tipo, fn) { if (tipo === 'click') this._clic.push(fn); },
    appendChild: function (c) { c.parentNode = this; this._figli.push(c); return c; },
    querySelector: function (sel) { return cerca(this, sel)[0] || null; },
    querySelectorAll: function (sel) { return cerca(this, sel); },
    focus: function () { global.document.activeElement = this; },
  };
  return el;
}

/**
 * @param {object} opt
 *   consenso    {analytics,marketing,preferences} come li torna Shopify:
 *               '' = non ha risposto, 'yes'/'no' = ha risposto
 *   mostrare    cosa risponde shouldShowBanner()
 *   nativo      'elemento' | 'oggetto' | false -- il banner di Shopify in pagina
 *   riapri      c'e' il collegamento [data-perla-cookie-apri] (pagina Cookie Policy)
 */
function scena(opt) {
  opt = opt || {};
  const body = elemento('body');

  const radice = elemento('div', { 'data-perla-cookie': '' });
  radice.hidden = true;
  const barra = elemento('div', { 'data-perla-cookie-barra': '' });
  barra.hidden = true;
  const pannello = elemento('div', { 'data-perla-cookie-pannello': '' });
  pannello.hidden = true;

  const bottoni = {};
  ['accetta', 'rifiuta', 'preferenze', 'salva', 'chiudi'].forEach(function (n) {
    bottoni[n] = elemento('button', { 'data-cookie': n });
  });
  const analisi = elemento('input', { 'data-cookie-segnale': 'analytics' });
  const marketing = elemento('input', { 'data-cookie-segnale': 'marketing' });

  barra.appendChild(bottoni.accetta);
  barra.appendChild(bottoni.rifiuta);
  barra.appendChild(bottoni.preferenze);
  pannello.appendChild(bottoni.chiudi);
  pannello.appendChild(analisi);
  pannello.appendChild(marketing);
  pannello.appendChild(bottoni.salva);
  radice.appendChild(barra);
  radice.appendChild(pannello);
  body.appendChild(radice);

  let riapri = null;
  if (opt.riapri) {
    riapri = elemento('a', { 'data-perla-cookie-apri': '' });
    body.appendChild(riapri);
  }

  if (opt.nativo === 'elemento') {
    body.appendChild(elemento('div', { id: 'shopify-pc__banner' }));
  }

  const stato = {
    consenso: Object.assign({ analytics: '', marketing: '', preferences: '', sale_of_data: '' },
      opt.consenso || {}),
  };
  const registrate = [];

  global.document = {
    body: body,
    activeElement: null,
    _tasti: [],
    addEventListener: function (tipo, fn) { if (tipo === 'keydown') this._tasti.push(fn); },
    querySelector: function (sel) { return cerca(body, sel)[0] || null; },
    querySelectorAll: function (sel) { return cerca(body, sel); },
  };

  global.window = {
    privacyBanner: opt.nativo === 'oggetto' ? {} : undefined,
    Shopify: {
      loadFeatures: function (_, cb) { cb(null); },
      customerPrivacy: {
        shouldShowBanner: function () { return !!opt.mostrare; },
        currentVisitorConsent: function () { return stato.consenso; },
        setTrackingConsent: function (scelta, cb) {
          registrate.push(scelta);
          // Come fa Shopify: la scelta diventa subito lo stato corrente, ed e'
          // per questo che riaprendo le preferenze si rivede cio' che si e'
          // scelto e non "tutto acceso".
          ['analytics', 'marketing', 'preferences'].forEach(function (k) {
            if (Object.prototype.hasOwnProperty.call(scelta, k)) {
              stato.consenso[k] = scelta[k] ? 'yes' : 'no';
            }
          });
          if (cb) cb();
        },
      },
    },
  };

  delete require.cache[require.resolve(MODULO)];
  require(MODULO);

  return {
    radice: radice, barra: barra, pannello: pannello,
    bottoni: bottoni, analisi: analisi, marketing: marketing, riapri: riapri,
    registrate: registrate, stato: stato,
    clic: function (el) {
      el._clic.forEach(function (fn) { fn({ preventDefault: function () {} }); });
    },
    tasto: function (key, shift) {
      global.document._tasti.forEach(function (fn) {
        fn({ key: key, shiftKey: !!shift, preventDefault: function () {} });
      });
    },
  };
}

/* ---- le prove ------------------------------------------------------------ */

console.log('\nBanner dei cookie');

prova('al caricamento non si registra nessun consenso', function () {
  const s = scena({ mostrare: true });
  assert.strictEqual(s.registrate.length, 0,
    'ha registrato una scelta che il cliente non ha fatto: ' + JSON.stringify(s.registrate));
});

prova('a chi non ha ancora scelto la barra si mostra', function () {
  const s = scena({ mostrare: true });
  assert.strictEqual(s.radice.hidden, false);
  assert.strictEqual(s.barra.hidden, false);
  assert.strictEqual(s.pannello.hidden, true, 'il pannello si apre solo su richiesta');
});

prova('"Accetta" manda tutti e tre i segnali a vero', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.accetta);
  assert.deepStrictEqual(s.registrate, [{ analytics: true, marketing: true, preferences: true }]);
  assert.strictEqual(s.radice.hidden, true, 'dopo la scelta la barra sparisce');
});

prova('"Rifiuta" manda false, non silenzio', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.rifiuta);
  assert.deepStrictEqual(s.registrate, [{ analytics: false, marketing: false, preferences: false }]);
  assert.strictEqual(s.stato.consenso.analytics, 'no',
    'un rifiuto deve restare registrato come rifiuto: "" vorrebbe dire "non ha ancora risposto"');
});

prova('chi ha gia' + '’' + ' scelto non rivede la barra', function () {
  const s = scena({ mostrare: false, consenso: { analytics: 'no', marketing: 'no', preferences: 'no' } });
  assert.strictEqual(s.radice.hidden, true);
  assert.strictEqual(s.barra.hidden, true);
});

// Il ripiego che tiene in piedi tutto: senza, il banner non comparirebbe a
// nessuno finche' non si configurano le regioni nel pannello Shopify.
prova('shouldShowBanner falso ma nessuna scelta: la barra si mostra lo stesso', function () {
  const s = scena({ mostrare: false });
  assert.strictEqual(s.barra.hidden, false,
    'con le regioni non configurate shouldShowBanner risponde sempre false');
});

prova('col banner nativo di Shopify in pagina il nostro tace (elemento)', function () {
  const s = scena({ mostrare: true, nativo: 'elemento' });
  assert.strictEqual(s.radice.hidden, true);
  assert.strictEqual(s.barra.hidden, true);
});

prova('col banner nativo di Shopify in pagina il nostro tace (window.privacyBanner)', function () {
  const s = scena({ mostrare: true, nativo: 'oggetto' });
  assert.strictEqual(s.radice.hidden, true);
});

prova('"Preferenze" apre il pannello e chiude la barra', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.preferenze);
  assert.strictEqual(s.pannello.hidden, false);
  assert.strictEqual(s.barra.hidden, true);
  assert.strictEqual(global.document.activeElement, s.analisi,
    'aprendo un dialogo il fuoco ci deve entrare dentro');
});

prova('"Salva" manda esattamente quello che dicono gli interruttori', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.preferenze);
  s.analisi.checked = true;
  s.marketing.checked = false;
  s.clic(s.bottoni.salva);
  assert.deepStrictEqual(s.registrate, [{ analytics: true, marketing: false, preferences: true }]);
});

prova('chiudere le preferenze senza scegliere fa tornare la barra', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.preferenze);
  s.clic(s.bottoni.chiudi);
  assert.strictEqual(s.pannello.hidden, true);
  assert.strictEqual(s.barra.hidden, false, 'chiudere non e' + '’' + ' una risposta');
  assert.strictEqual(s.registrate.length, 0, 'e soprattutto non registra niente');
});

prova('Esc chiude il pannello', function () {
  const s = scena({ mostrare: true });
  s.clic(s.bottoni.preferenze);
  s.tasto('Escape');
  assert.strictEqual(s.pannello.hidden, true);
});

prova('riaprendo le preferenze gli interruttori mostrano lo stato vero', function () {
  const s = scena({ mostrare: true, riapri: true });
  s.clic(s.bottoni.preferenze);
  s.analisi.checked = true;
  s.marketing.checked = false;
  s.clic(s.bottoni.salva);
  assert.strictEqual(s.radice.hidden, true, 'salvato, sparisce');

  s.clic(s.riapri);
  assert.strictEqual(s.pannello.hidden, false, 'dalla Cookie Policy si deve poter tornare a scegliere');
  assert.strictEqual(s.analisi.checked, true, 'analisi era acceso e deve restare acceso');
  assert.strictEqual(s.marketing.checked, false,
    'marketing era spento: mostrarlo acceso farebbe riaccendere per distrazione');
});

prova('senza il blocco in pagina non si aggancia e non si rompe niente', function () {
  const body = elemento('body');
  global.document = {
    body: body,
    activeElement: null,
    _tasti: [],
    addEventListener: function (tipo, fn) { if (tipo === 'keydown') this._tasti.push(fn); },
    querySelector: function (sel) { return cerca(body, sel)[0] || null; },
    querySelectorAll: function (sel) { return cerca(body, sel); },
  };
  let registrate = 0;
  global.window = {
    Shopify: {
      loadFeatures: function (_, cb) { cb(null); },
      customerPrivacy: {
        shouldShowBanner: function () { return true; },
        currentVisitorConsent: function () { return {}; },
        setTrackingConsent: function () { registrate++; },
      },
    },
  };
  delete require.cache[require.resolve(MODULO)];
  require(MODULO);
  assert.strictEqual(registrate, 0);
  assert.strictEqual(global.document._tasti.length, 0,
    'senza banner non si lascia in giro un ascoltatore della tastiera');
});

console.log('\n  ' + fatte + ' verifiche\n');
