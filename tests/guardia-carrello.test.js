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
  b.classList = {
    add: function (c) { b._c.add(c); },
    remove: function (c) { b._c.delete(c); },
    // ROUND 50: l'osservatore chiede se il pulsante e' tornato a riposo.
    contains: function (c) { return b._c.has(c); },
  };
  // ROUND 50: la larghezza si prende prima che il tema cambi la scritta.
  b.style = { width: '' };
  b.getBoundingClientRect = function () { return { width: 220 }; };
  return b;
}

// ROUND 50 -- una radice dell'editor foto. Il tema le mette addosso
// __perlaEnsureComposed quando Fabric.js ha finito di caricare; la guardia la
// sostituisce con una che ha un limite di attesa.
function radiceEditor(componi) {
  return { __perlaEnsureComposed: componi };
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
    _campi: campi,
    _radici: opt.radici || [],
    querySelectorAll: function (sel) {
      if (sel === '[data-photo-prop-data]') return campi;
      if (sel === '[data-photo-prop-name-text]') return nomi;
      if (sel === '[data-photo-status]') return [stato];
      if (sel === '[data-photo-customizer]') return opt.radici || [];
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
// ROUND 50 -- i tempi sotto controllo. Il limite di attesa e' di venti
// secondi: una prova che li aspetta davvero non la esegue piu' nessuno.
// Quindi setTimeout non fa passare il tempo, lo mette in fila, e la prova
// decide quando far scattare cosa.
const inFila = [];
let contatore = 0;
global.setTimeout = function (fn, ms) {
  inFila.push({ id: ++contatore, fn: fn, ms: ms });
  return contatore;
};
global.clearTimeout = function (id) {
  for (let i = 0; i < inFila.length; i++) {
    if (inFila[i].id === id) { inFila.splice(i, 1); return; }
  }
};
function scatta(ms) {
  const pronti = inFila.filter(function (t) { return t.ms === ms; });
  pronti.forEach(function (t) { global.clearTimeout(t.id); t.fn(); });
  return pronti.length;
}

// Il finto MutationObserver: la guardia lo usa per sapere quando il pulsante
// e' tornato a riposo. Qui si tiene l'elenco di quelli accesi, cosi' si puo'
// anche verificare che si stacchino -- un osservatore mai staccato e'
// esattamente il difetto che si sta cercando altrove nel sito.
let accesi = [];
global.MutationObserver = function (cb) {
  const self = this;
  this.observe = function () { accesi.push(self); };
  this.disconnect = function () {
    accesi = accesi.filter(function (o) { return o !== self; });
  };
  this.scatta = function () { cb([]); };
};

require(path.join(__dirname, '..', 'theme', 'assets', 'perla-guardia-carrello.js'));

// Lascia girare le promesse gia' risolte: setImmediate non e' stato
// sostituito, quindi arriva dopo tutti i microtask in coda.
function turno() {
  return new Promise(function (r) { setImmediate(r); });
}

async function provaAsync(nome, fn) {
  try {
    await fn();
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

async function rifiuta(promessa) {
  try {
    await promessa;
  } catch (e) {
    return e;
  }
  throw new Error('la promessa ha RISOLTO: la riga sarebbe finita in carrello');
}

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

// ---- ROUND 50 -------------------------------------------------------------
//
// Il buco che i controlli qui sopra non potevano vedere: e' il clic su
// "Aggiungi al carrello" a far partire la composizione, quindi quando la
// guardia guarda il campo del design la composizione non e' ancora avvenuta.
// Se fallisce li' dentro, composeAndUpload() si mangia l'errore, la promessa
// risolve lo stesso, e il tema manda in carrello una riga senza disegno.

function formConEditor(componi, opt) {
  opt = opt || {};
  // Banco pulito a ogni prova: i timer e gli osservatori di quella prima
  // restano in fila apposta (e' cosi' che si vede se qualcuno non li spegne),
  // ma contarli ha senso solo se sono i propri.
  inFila.length = 0;
  accesi = [];
  return form({
    personalizzabile: true,
    designPresente: opt.designPresente !== false,
    editorInErrore: false,
    radici: [radiceEditor(componi)],
  });
}

// Rifa' cio' che fa il .catch di composeAndUpload in global.js:
//     bakedImageId = ""; writePropData(); setPhotoStatus(status, errore, true)
function laComposizioneFallisce(f) {
  f._campi[0].value = '';
  f._stato._c.add('product-personalize__status--error');
}

(async function () {
  console.log('\nROUND 50 — l\'attesa senza fondo');

  await provaAsync('composizione che non finisce mai: dopo il limite si rifiuta, e il carrello non parte', async function () {
    const f = formConEditor(function () { return new Promise(function () {}); });
    assert.strictEqual(invia(f)._prevenuto, false, 'al momento del clic non c\'era niente da fermare');
    const p = f._radici[0].__perlaEnsureComposed();
    assert.strictEqual(scatta(20000), 1, 'doveva esserci un limite di attesa in fila');
    const err = await rifiuta(p);
    assert.strictEqual(err.description, 'Disegno non pronto',
      'il tema scrive err.description sul pulsante: senza, comparirebbe l\'errore generico');
    assert.ok(/troppo/.test(err.perlaDettaglio),
      'il messaggio lungo deve dire che ci sta mettendo troppo, invece: ' + err.perlaDettaglio);
    scatta(0);
  });

  await provaAsync('composizione svelta: passa, e il limite viene tolto dalla fila', async function () {
    const f = formConEditor(function () { return Promise.resolve('fatto'); });
    invia(f);
    const p = f._radici[0].__perlaEnsureComposed();
    assert.strictEqual(await p, 'fatto', 'una composizione riuscita deve arrivare in fondo');
    assert.strictEqual(scatta(20000), 0,
      'il limite doveva essere annullato: un timer lasciato acceso e\' una perdita');
    scatta(0);
  });

  console.log('\nROUND 50 — il ricontrollo DOPO la composizione');

  await provaAsync('la composizione finisce ma lascia il campo vuoto: si rifiuta lo stesso', async function () {
    let f = null;
    f = formConEditor(function () {
      laComposizioneFallisce(f);          // e' quello che fa il .catch del tema
      return Promise.resolve();           // ...e poi risolve comunque
    });
    assert.strictEqual(invia(f)._prevenuto, false,
      'al clic il design c\'era ancora: nessun controllo di prima poteva accorgersene');
    const err = await rifiuta(f._radici[0].__perlaEnsureComposed());
    assert.strictEqual(err.description, 'Disegno non pronto');
    assert.ok(/non è stato caricato/.test(f._stato.textContent),
      'sotto l\'editor deve comparire il perche\', invece: ' + f._stato.textContent);
    scatta(0);
  });

  await provaAsync('composizione riuscita e campo pieno: si compra', async function () {
    const f = formConEditor(function () { return Promise.resolve('ok'); });
    invia(f);
    assert.strictEqual(await f._radici[0].__perlaEnsureComposed(), 'ok');
    scatta(0);
  });

  console.log('\nROUND 50 — fuori dal carrello non si tocca niente');

  // L'anteprima "mockup reale" chiama la stessa __perlaEnsureComposed. Li' un
  // rifiuto non c'entra: quel pulsante ha un suo messaggio d'errore.
  await provaAsync('l\'anteprima mockup non eredita ne\' limite ne\' ricontrollo', async function () {
    let f = null;
    f = formConEditor(function () {
      laComposizioneFallisce(f);
      return Promise.resolve('anteprima');
    });
    invia(f);
    scatta(0);                            // finito l'invio, la finestra si chiude
    const valore = await f._radici[0].__perlaEnsureComposed();
    assert.strictEqual(valore, 'anteprima',
      'fuori dall\'invio del form la funzione deve comportarsi come prima');
  });

  console.log('\nROUND 50 — il pulsante che diventa enorme');

  await provaAsync('la larghezza viene fissata prima che il tema cambi la scritta', async function () {
    const f = formConEditor(function () { return Promise.resolve(); });
    invia(f);
    assert.strictEqual(f._btn.style.width, '220px',
      'senza la misura fissata, "Preparazione dell\'immagine..." allarga il pulsante');
    scatta(0);
  });

  await provaAsync('quando il pulsante torna a riposo la misura si libera e l\'osservatore si stacca', async function () {
    const f = formConEditor(function () { return Promise.resolve(); });
    invia(f);
    assert.strictEqual(accesi.length, 1, 'doveva mettersi in ascolto del pulsante');
    f._btn.classList.remove('is-loading');
    accesi[0].scatta();
    assert.strictEqual(f._btn.style.width, '',
      'la misura non deve restare incollata: ruotando il telefono sborderebbe');
    assert.strictEqual(accesi.length, 0, 'l\'osservatore deve staccarsi da solo');
    scatta(0);
  });

  await provaAsync('e se l\'osservatore non arriva mai, la rete di sicurezza libera comunque', async function () {
    const f = formConEditor(function () { return Promise.resolve(); });
    invia(f);
    assert.strictEqual(scatta(25000), 1, 'doveva esserci una rete di sicurezza in fila');
    assert.strictEqual(f._btn.style.width, '');
    assert.strictEqual(accesi.length, 0);
    scatta(0);
  });

  await provaAsync('finche\' il pulsante e\' occupato la misura resta', async function () {
    const f = formConEditor(function () { return Promise.resolve(); });
    invia(f);
    accesi[0].scatta();                   // is-loading c'e' ancora
    assert.strictEqual(f._btn.style.width, '220px',
      'liberarla mentre il pulsante sta ancora lavorando lo farebbe saltare');
    scatta(0);
  });

  await turno();
  console.log('\n' + fatte + ' verifiche superate.' +
    (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
})();
