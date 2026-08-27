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
  return { Canvas: Canvas, StaticCanvas: StaticCanvas };
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

function caricaTema(fabric) {
  const ascoltatori = {};
  global.window = {
    fabric: fabric,
    addEventListener: () => {},
    matchMedia: () => ({ matches: false }),
  };
  global.document = {
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

console.log('\nEditor: risoluzione del file di stampa');
prova('l\'anteprima a schermo resta com\'era', testLAnteprimaNonSiTocca);
prova('il file di stampa quadruplica i pixel', testIlFileDiStampaQuadruplicaIPixel);
prova('non supera i limiti di tela del telefono', testNonSuperaILimitiDelTelefono);
prova('non rimpicciolisce mai quello che c\'era', testNonRimpicciolisceMai);
prova('se il file sfora il caricamento, scende da solo', testIlBudgetInByteFaScendere);

console.log('\n' + fatte + ' verifiche superate.' +
  (process.exitCode ? ' Alcune FALLITE.' : ''));
