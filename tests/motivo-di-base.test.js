'use strict';

// Verifica che il motivo del prodotto finisca davvero nel file di stampa.
//
// IL DIFETTO CHE QUESTO TEST COGLIE
// L'editor esporta solo la tela: nome e foto su fondo trasparente. Sui
// prodotti EU (Printful) il motivo non arriva da nessun'altra parte, quindi
// senza questa unione il cliente vedeva -- e avrebbe ricevuto -- una bandana
// BIANCA con sopra soltanto il suo nome. Segnalato dalla titolare: "quando
// inserisco il nome e premo genera anteprima appare solo la scritta su una
// bandana bianca invece di riprendere il design".
//
// Uso:  node tests/motivo-di-base.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const motivo = require('../scripts/motivo-di-base');

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

const CLIENTE = 'https://res.cloudinary.com/qarb7ouo/image/upload/v1786899999/nomecliente.png';
const MOTIVO  = 'https://res.cloudinary.com/qarb7ouo/image/upload/v1786893556/zw9ly6pw92d5o0c39fcl.jpg';

console.log('\nIl motivo entra nel file di stampa');

prova('l\'immagine unita contiene sia il motivo che il livello del cliente', function () {
  const u = motivo.componiConMotivo(CLIENTE, MOTIVO);
  assert.notStrictEqual(u, CLIENTE,
    'ha restituito il solo livello cliente: e\' esattamente la bandana bianca');
  assert.ok(u.indexOf('zw9ly6pw92d5o0c39fcl') !== -1, 'manca il motivo: ' + u);
  assert.ok(u.indexOf('l_nomecliente') !== -1, 'manca il livello del cliente: ' + u);
});

prova('il motivo sta sotto e il cliente sopra, non il contrario', function () {
  const u = motivo.componiConMotivo(CLIENTE, MOTIVO);
  // Su Cloudinary la base e' l'ultimo segmento; l'overlay e' l_<id> ... fl_layer_apply
  assert.ok(/\/l_nomecliente,[^/]*\/fl_layer_apply\/zw9ly6pw92d5o0c39fcl\.jpg$/.test(u),
    'ordine dei livelli inatteso: ' + u);
});

prova('il livello del cliente non viene deformato', function () {
  const u = motivo.componiConMotivo(CLIENTE, MOTIVO);
  assert.ok(u.indexOf('c_fit') !== -1, 'senza c_fit un nome lungo verrebbe schiacciato');
  assert.ok(u.indexOf('fl_relative') !== -1, 'senza fl_relative le misure non seguono il motivo');
});

prova('l\'immagine unita resta una URL Cloudinary valida per il server', function () {
  // urlCompositoValida() in perla-upload-endpoint.js accetta solo questo host:
  // se la formula cambiasse forma, il composito verrebbe rifiutato in silenzio.
  const u = motivo.componiConMotivo(CLIENTE, MOTIVO);
  assert.ok(/^https:\/\/res\.cloudinary\.com\/[A-Za-z0-9_-]+\/image\/upload\//.test(u), u);
  assert.ok(u.length < 2048);
});

console.log('\nQuando NON si deve unire niente');

prova('un prodotto senza motivo lascia passare il livello cliente intatto', function () {
  assert.strictEqual(motivo.componiConMotivo(CLIENTE, null), CLIENTE);
  assert.strictEqual(motivo.componiConMotivo(CLIENTE, ''), CLIENTE);
});

prova('una URL fuori da Cloudinary non viene toccata', function () {
  const altrove = 'https://images-api.printify.com/mockup/abc.png';
  assert.strictEqual(motivo.componiConMotivo(altrove, MOTIVO), altrove);
});

console.log('\nRiconoscere i prodotti EU dall\'id');

const manifest = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'scripts', 'perla-eu-prodotti.json'), 'utf8'));

prova('ogni prodotto EU del manifest trova il suo motivo', function () {
  let n = 0;
  for (const p of manifest) {
    const cifre = String(p.id).split('/').pop();
    const trovato = motivo.motivoPerProdotto(cifre);
    assert.strictEqual(trovato, p.pattern, p.handle + ': motivo sbagliato o mancante');
    n++;
  }
  assert.ok(n >= 60, 'il manifest sembra incompleto: solo ' + n + ' prodotti');
});

prova('un prodotto Printify non viene riconosciuto come EU', function () {
  // Sui prodotti Printify il motivo lo sovrappone gia' il fornitore: unirlo
  // anche qui lo stamperebbe due volte.
  assert.strictEqual(motivo.motivoPerProdotto('99999999999'), null);
});

prova('un id malformato non diventa una chiamata a caso', function () {
  for (const cattivo of ['../../uploads', '', null, undefined, 'abc', '12; DROP']) {
    assert.strictEqual(motivo.motivoPerProdotto(cattivo), null, 'accettato: ' + cattivo);
  }
});

console.log('\nIl caso reale della segnalazione');

prova('bandana "Barocco": il file di stampa porta il damascato, non il bianco', function () {
  const bandana = manifest.find(function (p) {
    return p.handle === 'bandana-eu-barocco-navy-oro-fornitore-europeo';
  });
  assert.ok(bandana, 'la bandana Barocco non e\' nel manifest');
  const m = motivo.motivoPerProdotto(String(bandana.id).split('/').pop());
  assert.ok(m, 'nessun motivo trovato per la bandana Barocco');
  const u = motivo.componiConMotivo(CLIENTE, m);
  assert.notStrictEqual(u, CLIENTE,
    'il file di stampa sarebbe il solo nome su fondo bianco -- il difetto segnalato');
  assert.ok(u.indexOf(motivo.idPubblicoCloudinary(m)) !== -1, 'il motivo non e\' nell\'unione');
});

console.log('\nRitrovare il file di stampa partendo dal solo id');

prova('la URL del composito si ricostruisce dall\'id, senza tenere stato', function () {
  // Il tema salva SOLO printify_image_id. Chi evade l'ordine deve poter
  // risalire al file a piena risoluzione con quello e basta.
  const u = motivo.urlCompositoDaId('68f0a1b2c3d4e5f60718293a', 'qarb7ouo');
  assert.strictEqual(u,
    'https://res.cloudinary.com/qarb7ouo/image/upload/perla-composito-68f0a1b2c3d4e5f60718293a.jpg');
});

prova('le due meta\' della convenzione combaciano', function () {
  const id = 'abc123';
  const nome = motivo.nomeCompositoCloudinary(id);
  const url = motivo.urlCompositoDaId(id, 'qarb7ouo');
  assert.ok(url.indexOf('/' + nome + '.jpg') !== -1,
    'il nome usato in caricamento non e\' quello ricostruito in lettura: ' + nome + ' vs ' + url);
});

prova('la URL ricostruita non tronca la risoluzione', function () {
  // Il ripiego sarebbe la preview_url di Printify, che porta il lato lungo a
  // 1200px: su un collare da 7169px sono sei pixel su sette buttati.
  const u = motivo.urlCompositoDaId('abc123', 'qarb7ouo');
  assert.ok(!/w_\d+|c_(scale|limit|fill)/.test(u),
    'la URL contiene una trasformazione che ridimensiona: ' + u);
});

prova('un id o un cloud name malformati non producono una URL', function () {
  assert.strictEqual(motivo.urlCompositoDaId('../altro', 'qarb7ouo'), null);
  assert.strictEqual(motivo.urlCompositoDaId('abc', 'cloud/../x'), null);
  assert.strictEqual(motivo.urlCompositoDaId('abc', ''), null);
  assert.strictEqual(motivo.urlCompositoDaId('', 'qarb7ouo'), null);
  assert.strictEqual(motivo.nomeCompositoCloudinary('a b'), null);
});

console.log('\n' + passati + ' verifiche superate.' +
  (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
