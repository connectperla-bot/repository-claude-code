'use strict';

// ROUND 34 -- il nome che esce dall'area di stampa, e il tasto doppio.
//
// IL DIFETTO CHE QUESTE PROVE CHIUDONO
// In assets/global.js il guardiano dei bordi (keepLogoInBounds) e' agganciato
// da installLogo, che si usa solo sul marchio; dentro se stesso guarda solo la
// variabile logoLayer. Nome, testi aggiuntivi, foto e adesivi non avevano
// quindi nessun limite: si trascinavano fuori dal riquadro e ci restavano.
// Quello che sta fuori non viene stampato, e il cliente lo scopre col pacco in
// mano -- un collare col nome ordinato, un collare senza nome ricevuto.
//
// COME SI PROVA
// assets/perla-studio-ui.js e' un IIFE che si aggancia a fabric.js avvolgendo
// renderAll. Qui si finge un fabric minimo -- una tela con getWidth/getHeight
// e oggetti con getBoundingRect -- si lascia che il file si agganci, e poi si
// trascinano i livelli fuori a mano. Non serve nessun browser: la regola dei
// limiti e' aritmetica pura.
//
// Le misure delle tele non sono inventate: 330x14 e' il collare EU su un
// telefono in verticale (rapporto 22,76:1), 300x300 la medaglietta.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const SORGENTE = path.join(__dirname, '..', 'theme', 'assets', 'perla-studio-ui.js');

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

// ---- finto fabric, ridotto a quello che il file usa davvero ---------------

function fintoFabric() {
  // StaticCanvas e' l'antenato di Canvas anche in fabric vero: la catena serve,
  // perche' il file del tema aggancia la risoluzione sull'antenato e i limiti
  // sul discendente.
  function StaticCanvas() {}
  StaticCanvas.prototype.toDataURL = function (opz) {
    const m = (opz && opz.multiplier) || 1;
    const w = Math.round(this.getWidth() * m);
    const h = Math.round(this.getHeight() * m);
    this.__ultimo = { w: w, h: h, multiplier: m };
    // Un finto payload proporzionale ai pixel: serve solo perche' il budget in
    // byte si misura sulla lunghezza vera della stringa.
    const car = Math.max(1, Math.round(w * h * (this.__bytePerPixel || 0) / 0.75));
    return 'data:image/png;base64,' + 'A'.repeat(car);
  };
  function Canvas() {}
  Canvas.prototype = Object.create(StaticCanvas.prototype);
  Canvas.prototype.constructor = Canvas;
  Canvas.prototype.renderAll = function () { return this; };

  // IText: la parte che ci interessa e' solo la textarea nascosta. In fabric
  // 5.3 il metodo che la sposta si chiama `updateTextareaPosition`, SENZA
  // trattino basso -- il finto usa quel nome e nessun altro, cosi' se qualcuno
  // torna ad avvolgere solo `_updateTextareaPosition` la prova cade.
  function IText() {}
  IText.prototype.initHiddenTextarea = function () {
    this.hiddenTextarea = { style: {} };
    this.hiddenTextarea.style.cssText =
      'position: absolute; top: 1394px; left: 1077px; width: 0; height: 0;';
    this.hiddenTextarea.style.position = 'absolute';
    this.hiddenTextarea.style.top = '1394px';
    this.hiddenTextarea.style.left = '1077px';
    this.hiddenTextarea.style.fontSize = '1px';
  };
  IText.prototype.updateTextareaPosition = function () {
    // com'e' scritta in fabric: rimette la textarea sotto il cursore, in
    // coordinate del DOCUMENTO -- ed e' esattamente cio' che allarga la pagina
    this.hiddenTextarea.style.left = '1311px';
    this.hiddenTextarea.style.top = '1394px';
  };
  return { Canvas: Canvas, StaticCanvas: StaticCanvas, IText: IText };
}

function tela(fabric, larghezza, altezza, tondo) {
  const fc = new fabric.Canvas();
  fc._ev = {};
  fc._objs = [];
  fc.getWidth = () => larghezza;
  fc.getHeight = () => altezza;
  fc.getObjects = () => fc._objs;
  fc.requestRenderAll = () => {};
  fc.on = (nome, fn) => { (fc._ev[nome] = fc._ev[nome] || []).push(fn); };
  fc.emetti = (nome, e) => (fc._ev[nome] || []).forEach((fn) => fn(e));
  // Il file legge data-product-type dal contenitore per capire se il prodotto
  // e' tondo: qui lo si finge risalendo dal canvas.
  fc.lowerCanvasEl = {
    closest: () => (tondo ? { getAttribute: () => 'medaglietta' } : null),
  };
  return fc;
}

// I livelli veri (nome, testo, foto, adesivi) hanno tutti originX/originY
// "center": left e top sono il CENTRO, non l'angolo. Il finto fa lo stesso, se
// no si proverebbe una geometria che nel negozio non esiste.
function livello(kind, left, top, w, h) {
  const o = { __perlaKind: kind, left: left, top: top, _ev: {} };
  o.on = (nome, fn) => { (o._ev[nome] = o._ev[nome] || []).push(fn); };
  o.muovi = () => (o._ev.moving || []).forEach((fn) => fn());
  o.setCoords = () => {};
  o.getBoundingRect = () => ({ left: o.left - w / 2, top: o.top - h / 2, width: w, height: h });
  o.riquadro = () => o.getBoundingRect();
  return o;
}

// ---- si carica il file del tema una volta sola ---------------------------

function caricaTema(fabric, doc) {
  const ascoltatori = {};
  global.window = {
    fabric: fabric,
    addEventListener: () => {},
    matchMedia: () => ({ matches: false }),
  };
  global.document = doc || {
    readyState: 'complete',
    documentElement: { lang: 'it' },
    addEventListener: (n, fn) => { ascoltatori[n] = fn; },
    querySelector: () => null,
    querySelectorAll: () => [],
    fonts: null,
  };
  global.MutationObserver = function () { this.observe = () => {}; };
  delete require.cache[SORGENTE];
  // Il file e' un IIFE senza module.exports: si valuta e basta.
  new Function('window', 'document', 'MutationObserver',
    fs.readFileSync(SORGENTE, 'utf8'))(global.window, global.document, global.MutationObserver);
}

function nuovaTela(larghezza, altezza, tondo) {
  const fabric = fintoFabric();
  caricaTema(fabric);
  const fc = tela(fabric, larghezza, altezza, tondo);
  fc.renderAll();          // e' la chiamata che consegna la tela al guardiano
  return fc;
}

function aggiungi(fc, obj) {
  fc._objs.push(obj);
  fc.emetti('object:added', { target: obj });
  return obj;
}

function dentro(riq, sinistra, alto, destra, basso) {
  const eps = 0.001;
  assert.ok(riq.left >= sinistra - eps, 'esce a sinistra: ' + riq.left + ' < ' + sinistra);
  assert.ok(riq.top >= alto - eps, 'esce in alto: ' + riq.top + ' < ' + alto);
  assert.ok(riq.left + riq.width <= destra + eps, 'esce a destra: ' + (riq.left + riq.width) + ' > ' + destra);
  assert.ok(riq.top + riq.height <= basso + eps, 'esce in basso: ' + (riq.top + riq.height) + ' > ' + basso);
}

// ---- le prove ------------------------------------------------------------

function testNomeNonEsceDiLato() {
  const fc = nuovaTela(400, 400, false);
  const nome = aggiungi(fc, livello('name', 200, 200, 100, 30));
  nome.left = 600;                       // trascinato ben oltre il bordo destro
  nome.muovi();
  dentro(nome.riquadro(), 4, 4, 396, 396);
}

function testNomeNonEsceInAlto() {
  const fc = nuovaTela(400, 400, false);
  const nome = aggiungi(fc, livello('name', 200, 200, 100, 30));
  nome.top = -80;
  nome.muovi();
  dentro(nome.riquadro(), 4, 4, 396, 396);
}

function testValeAnchePerTestoFotoAdesivi() {
  // Il difetto non riguardava solo il nome: erano quattro tipi di livello a
  // non avere nessun limite.
  ['text', 'photo', 'sticker'].forEach(function (kind) {
    const fc = nuovaTela(400, 400, false);
    const o = aggiungi(fc, livello(kind, 200, 200, 60, 60));
    o.left = -300;
    o.top = 900;
    o.muovi();
    dentro(o.riquadro(), 4, 4, 396, 396);
  });
}

function testIlMarchioRestaAGlobalJs() {
  // global.js gli da' limiti piu' stretti (logoSafeBounds) e una scala minima
  // sua: due guardiani sullo stesso oggetto si contraddirebbero.
  const fc = nuovaTela(400, 400, false);
  const logo = aggiungi(fc, livello('logo', 200, 200, 60, 60));
  logo.left = 900;
  logo.muovi();
  assert.strictEqual(logo.left, 900, 'il marchio e\' stato spostato da qui');
}

function testUnaFotoPiuGrandeDellAreaLaCopreSempre() {
  // Regola diversa e voluta: se il livello non ci sta dentro, e' l'area a
  // dover stare dentro di lui, cosi' non resta mai un angolo bianco.
  const fc = nuovaTela(300, 300, false);
  const foto = aggiungi(fc, livello('photo', 150, 150, 400, 400));
  foto.left = 260;                       // spinta a destra: scoprirebbe sinistra
  foto.muovi();
  const r = foto.riquadro();
  assert.ok(r.left <= 4.001, 'la foto scopre il lato sinistro: ' + r.left);
  assert.ok(r.left + r.width >= 295.999, 'la foto scopre il lato destro');
}

function testMedagliettaUsaIlTondo() {
  // L'area e' un quadrato ma il prodotto e' un cerchio: il limite e' il
  // rettangolo inscritto, gli stessi numeri che global.js usa per il marchio.
  const fc = nuovaTela(300, 300, true);
  const nome = aggiungi(fc, livello('name', 150, 150, 40, 40));
  nome.left = 40;
  nome.muovi();
  const bordo = 150 - (300 * 0.92 / 2) / Math.SQRT2;   // ~52,4
  dentro(nome.riquadro(), bordo, bordo, 300 - bordo, 300 - bordo);
  assert.ok(bordo > 4, 'il limite tondo non e\' piu\' stretto del quadrato');
}

function testChiSttaGiaDentroNonSiMuove() {
  // Un guardiano che sposta di un pixel anche chi e' a posto si sentirebbe
  // come un editor che "non va dove lo metti": e' il difetto opposto.
  const fc = nuovaTela(400, 400, false);
  const nome = aggiungi(fc, livello('name', 210, 190, 100, 30));
  nome.muovi();
  assert.strictEqual(nome.left, 210);
  assert.strictEqual(nome.top, 190);
}

function testIlCollareNonSiMangiaMezzaTela() {
  // Il collare EU su un telefono e' alto 14 px. Con i 4 px fissi del marchio
  // sopra e sotto resterebbero 6 px di banda utile e il nome, alto 9, non ci
  // starebbe piu': il margine e' percentuale apposta.
  const fc = nuovaTela(330, 14, false);
  const nome = aggiungi(fc, livello('name', 165, 7, 40, 9));
  nome.top = 60;
  nome.muovi();
  const r = nome.riquadro();
  dentro(r, 1, 1, 329, 13);
  assert.ok(r.height <= 13 - 1, 'il nome non entra piu\' nella banda utile');
}

// ---- la risoluzione del file di stampa -----------------------------------

// Le aree di stampa vere, da scripts/perla-scala-stampa.py. Stanno qui come
// documentazione dell'intento: sono la misura che il file esportato dovrebbe
// avvicinare, ed e' rispetto a queste che "2000 px sul lato lungo" era il 3%.
const AREE = {
  'guinzaglio-eu': [12389, 219],
  'collare-eu': [7169, 315],
  'ciotola-eu': [6496, 803],
  'bandana-eu': [4125, 4125],
  'cuccia-usa': [15600, 12600],
};

// Quello che global.js calcola oggi in buildComposite(): 2000 px sul lato
// lungo, e il moltiplicatore per arrivarci dalla tela sullo schermo.
function comeGlobalJs(larghezzaTela, rapporto) {
  const exportW = rapporto >= 1 ? 2000 : Math.round(2000 * rapporto);
  return exportW / larghezzaTela;
}

function telaDaEsportare(larghezza, altezza, bytePerPixel) {
  const fabric = fintoFabric();
  caricaTema(fabric);
  const fc = new fabric.Canvas();
  fc.getWidth = () => larghezza;
  fc.getHeight = () => altezza;
  fc.getObjects = () => [];
  fc.requestRenderAll = () => {};
  fc.on = () => {};
  fc.lowerCanvasEl = { closest: () => null };
  if (bytePerPixel) fc.__bytePerPixel = bytePerPixel;
  return fc;
}

function testLAnteprimaNonSiTocca() {
  // updateMockupPreview chiama toDataURL SENZA moltiplicatore: quella e'
  // l'immagine che si vede a schermo e deve restare grande quanto la tela.
  const fc = telaDaEsportare(600, 400);
  fc.toDataURL({ format: 'png' });
  assert.deepStrictEqual(fc.__ultimo, { w: 600, h: 400, multiplier: 1 });
}

function testIlFileDiStampaQuadruplicaIPixel() {
  // Su un telefono la tela e' larga circa 330 px. Per ogni prodotto vero si
  // esporta come farebbe global.js e si verifica che i pixel consegnati siano
  // almeno quattro volte quelli di prima.
  Object.keys(AREE).forEach(function (tipo) {
    const rapporto = AREE[tipo][0] / AREE[tipo][1];
    const larghezza = 330;
    const altezza = Math.max(1, Math.round(larghezza / rapporto));
    const mult = comeGlobalJs(larghezza, rapporto);

    const prima = Math.round(larghezza * mult) * Math.round(altezza * mult);
    const fc = telaDaEsportare(larghezza, altezza);
    fc.toDataURL({ format: 'png', multiplier: mult });
    const dopo = fc.__ultimo.w * fc.__ultimo.h;

    assert.ok(dopo >= prima * 3.9,
      tipo + ': solo ' + (dopo / prima).toFixed(2) + ' volte i pixel di prima');
  });
}

function testNonSuperaILimitiDelTelefono() {
  // Oltre 4096 px di lato o 16 megapixel Safari su iPhone smette di disegnare
  // e toDataURL torna un'immagine vuota: meglio quattro volte i pixel ovunque
  // che sedici da nessuna parte.
  Object.keys(AREE).forEach(function (tipo) {
    const rapporto = AREE[tipo][0] / AREE[tipo][1];
    [330, 900, 1400].forEach(function (larghezza) {
      const altezza = Math.max(1, Math.round(larghezza / rapporto));
      const fc = telaDaEsportare(larghezza, altezza);
      fc.toDataURL({ format: 'png', multiplier: comeGlobalJs(larghezza, rapporto) });
      const u = fc.__ultimo;
      assert.ok(Math.max(u.w, u.h) <= 4096 + 1,
        tipo + ' a ' + larghezza + 'px: lato ' + Math.max(u.w, u.h));
      assert.ok(u.w * u.h <= 16e6 + 1000,
        tipo + ' a ' + larghezza + 'px: ' + (u.w * u.h / 1e6).toFixed(1) + ' megapixel');
    });
  });
}

function testNonRimpicciolisceMai() {
  // Su una tela gia' grande il moltiplicatore non deve MAI scendere: sarebbe
  // il difetto di partenza, al contrario.
  const fc = telaDaEsportare(3000, 3000);
  const mult = 1.2;
  fc.toDataURL({ format: 'png', multiplier: mult });
  assert.ok(fc.__ultimo.multiplier >= mult,
    'moltiplicatore sceso da ' + mult + ' a ' + fc.__ultimo.multiplier);
}

function testIlBudgetInByteFaScendere() {
  // perla-upload-endpoint.js rifiuta oltre MAX_UPLOAD_MB. Se il file alzato
  // sfora, deve scendere da solo invece di produrre un caricamento respinto.
  const fc = telaDaEsportare(330, 330, 0.9);   // finto: ~0,9 byte per pixel
  const mult = comeGlobalJs(330, 1);           // 6,06 -> alzato sarebbe 4000x4000
  const url = fc.toDataURL({ format: 'png', multiplier: mult });
  const byte = Math.round((url.length - url.indexOf(',') - 1) * 0.75);
  assert.ok(byte <= 8 * 1024 * 1024,
    'file da ' + (byte / 1e6).toFixed(1) + ' MB: oltre il budget');
  assert.ok(fc.__ultimo.multiplier >= mult,
    'sceso sotto quello che l\'editor produceva prima');
}

function testUnSoloPulsanteSchermoIntero() {
  // Il riquadro creava un secondo pulsante che non faceva altro che premere
  // quello gia' presente: sul telefono se ne vedevano due, con testi diversi
  // per la stessa azione. Qui si verifica che non torni.
  const testo = fs.readFileSync(SORGENTE, 'utf8');
  assert.ok(testo.indexOf('photo-studio__rotate-hint-btn') === -1,
    'il pulsante doppione e\' tornato nel sorgente');
  assert.ok(testo.indexOf('photo-studio__rotate-hint-text') !== -1,
    'la spiegazione e\' sparita: serve, dice perche\' conviene');
}

// ---- il nastro e la textarea: qui serve un pezzetto di DOM ---------------
//
// initNastro lavora su misure vere (offsetWidth del nastro, clientWidth della
// finestra) e su eventi veri, quindi non si puo' provare con la sola
// aritmetica. Il finto DOM qui sotto e' ridotto a quello che il file tocca:
// niente layout, niente rendering, solo le misure che gli si danno.

function nodo(opz) {
  const n = Object.assign({
    style: {}, attributi: {}, figli: {}, listener: [],
    offsetWidth: 0, offsetHeight: 0, clientWidth: 0, clientHeight: 0,
    scrollLeft: 0, scrollWidth: 0, hidden: false, className: '',
    classList: { add() {}, remove() {}, toggle() {} },
    querySelector(sel) { return this.figli[sel] || null; },
    querySelectorAll(sel) { return this.figli[sel] ? [this.figli[sel]] : []; },
    getAttribute(k) { return k in this.attributi ? this.attributi[k] : null; },
    setAttribute(k, v) { this.attributi[k] = v; },
    hasAttribute(k) { return k in this.attributi; },
    removeAttribute(k) { delete this.attributi[k]; },
    addEventListener(nome, fn, cattura) { this.listener.push({ nome, fn, cattura: !!cattura }); },
    removeEventListener() {},
    contains() { return true; },
    appendChild() {}, insertBefore() {}, remove() {},
    closest(sel) {
      // basta per l'uso che ne fa il file: "sono io uno di questi?"
      return sel.split(',').some((s) => this.hasAttribute(s.trim().replace(/[[\]]/g, '')))
        ? this : null;
    },
  }, opz);
  return n;
}

// Il collare EU su un telefono da 390: nastro 2208x97 in una finestra da 350.
function studioFinto(nastroW, nastroH, finestraW) {
  const wrap = nodo({ offsetWidth: nastroW, offsetHeight: nastroH });
  const viewport = nodo({ clientWidth: finestraW, scrollWidth: nastroW });
  viewport.parentNode = nodo({});
  const piu = nodo({ attributi: { 'data-view-zoom-in': '' } });
  const meno = nodo({ attributi: { 'data-view-zoom-out': '' } });
  const reset = nodo({ attributi: { 'data-view-zoom-reset': '' } });
  const cust = nodo({
    attributi: { 'data-print-ratio': String(nastroW / nastroH), 'data-photo-customizer': '' },
    figli: {
      '[data-fabric-wrap]': wrap,
      '[data-fabric-viewport]': viewport,
      '[data-view-zoom-in]': piu,
      '[data-view-zoom-out]': meno,
      '[data-view-zoom-reset]': reset,
    },
  });

  const doc = {
    readyState: 'complete',
    documentElement: { lang: 'it' },
    addEventListener: () => {},
    querySelector: () => null,
    querySelectorAll: (sel) => (sel === '[data-photo-customizer]' ? [cust] : []),
    createElement: () => nodo({}),
    fonts: null,
  };
  const fabric = fintoFabric();
  caricaTema(fabric, doc);
  return { cust, wrap, viewport, piu, meno, reset, fabric };
}

// Un clic come lo riceve il file: in cattura sul contenitore, dove passa prima
// che l'evento arrivi al pulsante.
function premi(s, bottone) {
  let fermato = false;
  const e = {
    target: bottone,
    preventDefault() {},
    stopPropagation() { fermato = true; },
  };
  s.cust.listener.filter((l) => l.nome === 'click' && l.cattura).forEach((l) => l.fn(e));
  return fermato;
}

function scalaDi(wrap) {
  const m = /scale\(([\d.]+)\)/.exec(wrap.style.transform || '');
  return m ? parseFloat(m[1]) : null;
}

function testIlNastroSiVedeTuttoAllApertura() {
  const s = studioFinto(2208, 97, 350);
  // 350 / 2208 = 0,1585: la striscia intera dentro la finestra, non un pezzo
  assert.strictEqual(s.cust.getAttribute('data-nastro-zoom'), 'tutta');
  const k = scalaDi(s.wrap);
  assert.ok(Math.abs(k - 350 / 2208) < 1e-3,
    'scala ' + k + ', attesa ' + (350 / 2208).toFixed(4));
  assert.strictEqual(s.wrap.style.transformOrigin, '0 0');
}

function testLoZoomMinimoEilTuttaNonUno() {
  // Il difetto di prima: lo zoom del tema partiva da 1 e non scendeva, quindi
  // l'insieme non si poteva vedere in nessun modo. Qui "-" all'apertura non
  // deve poter rimpicciolire sotto "tutta".
  const s = studioFinto(2208, 97, 350);
  const prima = scalaDi(s.wrap);
  premi(s, s.meno);
  assert.strictEqual(scalaDi(s.wrap), prima, 'e\' sceso sotto la vista intera');
  assert.strictEqual(s.cust.getAttribute('data-nastro-zoom'), 'tutta');
}

function testIlPiuIngrandisceEilResetTorna() {
  const s = studioFinto(2208, 97, 350);
  const tutta = scalaDi(s.wrap);
  premi(s, s.piu);
  assert.ok(scalaDi(s.wrap) > tutta, 'il "+" non ha ingrandito');
  assert.strictEqual(s.cust.getAttribute('data-nastro-zoom'), 'ingrandita');
  premi(s, s.reset);
  assert.ok(Math.abs(scalaDi(s.wrap) - tutta) < 1e-6, 'il Reset non e\' tornato a tutta');
  assert.strictEqual(s.cust.getAttribute('data-nastro-zoom'), 'tutta');
}

function testLoZoomDelTemaNonVieneChiamato() {
  // Registrarsi sui pulsanti non bastava: lo studio di global.js si avvia dopo
  // di noi, quindi i suoi ascoltatori parlavano per ultimi e restava il suo
  // scale(1.5). Ora l'evento si ferma in cattura, prima del pulsante.
  const s = studioFinto(2208, 97, 350);
  assert.ok(premi(s, s.piu), 'la propagazione non e\' stata fermata: global.js vince ancora');
  assert.ok(s.cust.listener.some((l) => l.nome === 'click' && l.cattura),
    'nessun ascoltatore in cattura sul contenitore');
}

function testFincheSiVedeTuttaIlRiquadroNonScorre() {
  // Sul guinzaglio il riquadro nasceva a scrollLeft 2088 -- meta' esatta -- e
  // la striscia finiva a -2068, fuori schermo a sinistra.
  const s = studioFinto(4526, 80, 350);
  s.viewport.scrollLeft = 2088;
  premi(s, s.reset);
  assert.strictEqual(s.viewport.style.overflowX, 'hidden');
  assert.strictEqual(s.viewport.scrollLeft, 0, 'la striscia resta spostata di lato');
  premi(s, s.piu);
  assert.strictEqual(s.viewport.style.overflowX, 'auto',
    'ingrandita deve poter scorrere dentro il riquadro');
}

function testSuiProdottiNormaliNonSiToccaNiente() {
  // Una bandana ci sta gia' dentro: nessuna scala, nessuno stato, niente.
  const s = studioFinto(320, 320, 350);
  assert.strictEqual(s.cust.getAttribute('data-nastro-zoom'), null);
  assert.ok(!s.wrap.style.transform, 'ha scalato un prodotto che ci stava gia\'');
}

function testLaTextareaNascostaNonAllargaLaPagina() {
  // Il difetto: fabric attacca la textarea al body in POSIZIONE ASSOLUTA alle
  // coordinate del cursore nel documento. Sul collare sono oltre i mille pixel,
  // e il corpo della pagina si allargava a ogni lettera -- misurato, da 390 a
  // 1084 px, che sul telefono e' la pagina che rimpicciolisce e scorre.
  const s = studioFinto(2208, 97, 350);
  const t = new s.fabric.IText();
  t.initHiddenTextarea();
  assert.strictEqual(t.hiddenTextarea.style.position, 'fixed',
    'la textarea e\' ancora assoluta: la pagina si allarga di nuovo');
  assert.strictEqual(t.hiddenTextarea.style.left, '0px');
  assert.strictEqual(t.hiddenTextarea.style.top, '0px');

  // e non basta alla nascita: fabric la rimette sotto il cursore a ogni tasto
  t.updateTextareaPosition();
  assert.strictEqual(t.hiddenTextarea.style.position, 'fixed');
  assert.strictEqual(t.hiddenTextarea.style.left, '0px',
    'dopo updateTextareaPosition e\' tornata dove non deve');
}

function testLaTextareaRestaA16px() {
  // Sotto i 16px Safari su iPhone ingrandisce la pagina da sola quando un campo
  // prende il fuoco: sarebbe lo stesso difetto per un'altra strada.
  const s = studioFinto(2208, 97, 350);
  const t = new s.fabric.IText();
  t.initHiddenTextarea();
  assert.strictEqual(t.hiddenTextarea.style.fontSize, '16px');
}

console.log('\nEditor: limiti dell\'area di stampa');
prova('il nome non esce di lato', testNomeNonEsceDiLato);
prova('il nome non esce in alto', testNomeNonEsceInAlto);
prova('vale anche per testo, foto e adesivi', testValeAnchePerTestoFotoAdesivi);
prova('il marchio resta a global.js, senza due guardiani', testIlMarchioRestaAGlobalJs);
prova('una foto piu\' grande dell\'area continua a coprirla', testUnaFotoPiuGrandeDellAreaLaCopreSempre);
prova('sulla medaglietta il limite e\' il tondo, non il quadrato', testMedagliettaUsaIlTondo);
prova('chi sta gia\' dentro non viene spostato di un pixel', testChiSttaGiaDentroNonSiMuove);
prova('sul collare il margine non si mangia mezza tela', testIlCollareNonSiMangiaMezzaTela);
prova('un solo pulsante "Schermo intero"', testUnSoloPulsanteSchermoIntero);

console.log('\nEditor: il nastro sul telefono');
prova('la striscia si vede tutta all\'apertura', testIlNastroSiVedeTuttoAllApertura);
prova('lo zoom minimo e\' "tutta", non 1', testLoZoomMinimoEilTuttaNonUno);
prova('il "+" ingrandisce e il Reset torna a tutta', testIlPiuIngrandisceEilResetTorna);
prova('lo zoom del tema non viene piu\' chiamato', testLoZoomDelTemaNonVieneChiamato);
prova('finche\' si vede tutta il riquadro non scorre di lato', testFincheSiVedeTuttaIlRiquadroNonScorre);
prova('sui prodotti normali non si tocca niente', testSuiProdottiNormaliNonSiToccaNiente);

console.log('\nEditor: scrivere il nome non allarga la pagina');
prova('la textarea nascosta non e\' mai assoluta', testLaTextareaNascostaNonAllargaLaPagina);
prova('la textarea nascosta resta a 16px', testLaTextareaRestaA16px);

console.log('\nEditor: risoluzione del file di stampa');
prova('l\'anteprima a schermo resta com\'era', testLAnteprimaNonSiTocca);
prova('il file di stampa quadruplica i pixel', testIlFileDiStampaQuadruplicaIPixel);
prova('non supera i limiti di tela del telefono', testNonSuperaILimitiDelTelefono);
prova('non rimpicciolisce mai quello che c\'era', testNonRimpicciolisceMai);
prova('se il file sfora il caricamento, scende da solo', testIlBudgetInByteFaScendere);

console.log('\n' + fatte + ' verifiche superate.' +
  (process.exitCode ? ' Alcune FALLITE.' : ''));
