'use strict';

// Unisce il motivo del prodotto al livello disegnato dal cliente.
//
// PERCHE' ESISTE
// L'editor sul sito esporta SOLO la tela: il nome e la foto del cliente su
// fondo trasparente. Il motivo del prodotto -- il damascato, la toile, il
// tartan -- non entra mai in quella esportazione, perche' nell'editor e' lo
// sfondo dell'area di stampa, non un livello.
//
// Sui prodotti Printify il motivo viaggia a parte: il tema chiede
// /pattern-source, ottiene un base_image_id, e Printify sovrappone i due
// livelli al momento della stampa. Sui prodotti Printful -- cioe' tutta la
// linea EU -- quella strada non esiste: /pattern-source cerca per
// printify_product_id, che un prodotto Printful non ha.
//
// Risultato, prima di questo file: l'anteprima mostrava il nome su una
// bandana BIANCA, e in stampa sarebbe finita la stessa cosa. Non era un
// difetto dell'anteprima: l'anteprima diceva la verita'.
//
// COME
// Sovrapposizione lato Cloudinary: motivo sotto a piena risoluzione nativa,
// livello cliente sopra ridimensionato per starci dentro senza deformarsi. Il
// risultato esce automaticamente alla misura del motivo, quindi non serve
// nessuna tabella di misure da mantenere: stessa formula per collare,
// bandana, ciotola e guinzaglio.
//
// DOVE VA APPLICATA
// In /upload (perla-upload-endpoint.js), PRIMA di caricare su Printify. Cosi'
// l'id restituito al tema punta gia' all'immagine unita, e da li' in poi tutto
// il resto -- anteprima e ordine -- usa quella senza sapere niente di questa
// logica. E' l'unico punto in cui si puo' intervenire senza ripubblicare il
// tema, che e' fermo al Round 17 e non manda ne' printify_image_url ne'
// pattern_url.
//
// MAI SUI PRODOTTI PRINTIFY
// La', il motivo lo sovrappone gia' il fornitore. Farlo anche qui lo
// stamperebbe due volte. Il riconoscimento e' per esclusione e non per tipo:
// perla-eu-prodotti.json contiene i 66 prodotti EU e nient'altro, quindi un id
// che non e' li' dentro non viene toccato.

const fs = require('fs');
const path = require('path');

function idPubblicoCloudinary(url) {
  // https://res.cloudinary.com/<cloud>/image/upload/v123/<id>.<est>
  const m = String(url || '').match(/\/image\/upload\/(?:[^/]+\/)*?([^/.]+)\.[a-z0-9]+$/i);
  return m ? m[1] : null;
}

/**
 * @param {string} urlCliente URL Cloudinary del livello disegnato dal cliente
 * @param {string} urlMotivo  URL Cloudinary del motivo del prodotto
 * @returns {string} la URL dell'immagine unita, o urlCliente se non si puo'
 */
function componiConMotivo(urlCliente, urlMotivo) {
  const idCliente = idPubblicoCloudinary(urlCliente);
  const idMotivo = idPubblicoCloudinary(urlMotivo);
  // Se uno dei due non e' su Cloudinary (prodotti neutri senza motivo, ordini
  // vecchi) si torna al livello cliente da solo: meglio un file di stampa
  // incompleto che nessun file.
  if (!idCliente || !idMotivo) return urlCliente;
  const base = String(urlMotivo).split('/image/upload/')[0] + '/image/upload';
  // w_1.0/h_1.0 + fl_relative = "grande quanto il motivo", c_fit non deforma.
  return base + '/l_' + idCliente + ',w_1.0,h_1.0,c_fit,fl_relative/fl_layer_apply/' + idMotivo + '.jpg';
}

// id Shopify -> URL del motivo. Il manifest porta l'id come gid
// ("gid://shopify/Product/15902507106648"), il tema manda solo le cifre.
let indice = null;

function caricaIndice() {
  if (indice) return indice;
  indice = new Map();
  const percorso = path.join(__dirname, 'perla-eu-prodotti.json');
  let prodotti;
  try {
    prodotti = JSON.parse(fs.readFileSync(percorso, 'utf8'));
  } catch (err) {
    // Il servizio deve restare in piedi anche senza manifest: senza motivo si
    // stampa il solo livello cliente, che e' il comportamento di prima.
    console.error('perla-eu-prodotti.json non leggibile, i motivi EU non verranno uniti:', err.message);
    return indice;
  }
  for (const p of prodotti) {
    const cifre = String(p.id || '').split('/').pop();
    if (cifre && p.pattern) indice.set(cifre, p.pattern);
  }
  return indice;
}

/**
 * @param {string|number} productId l'id numerico Shopify del prodotto
 * @returns {string|null} la URL del motivo, o null se non e' un prodotto EU
 */
function motivoPerProdotto(productId) {
  const chiave = String(productId == null ? '' : productId).trim();
  if (!/^[0-9]+$/.test(chiave)) return null;
  return caricaIndice().get(chiave) || null;
}

// Per i test: rilegge il manifest dal disco.
function scordaIndice() { indice = null; }

// COME L'ORDINE RITROVA IL FILE DI STAMPA
//
// Il tema pubblicato salva nella proprieta' _Personalizzazione soltanto
// printify_image_id: non printify_image_url, non pattern_url. Chi evade
// l'ordine (providers/printful-client.js) ha pero' bisogno di una URL
// pubblica, e non puo' usare la preview_url di Printify perche' quella
// tronca il lato lungo a 1200px -- su un collare da 7169px vuol dire buttare
// via sei pixel su sette.
//
// Per questo /upload, dopo aver caricato l'immagine unita su Printify, la
// rimette anche su Cloudinary con un nome DERIVATO dall'id Printify. Cosi'
// chiunque abbia l'id puo' ricostruire la URL a piena risoluzione senza
// tenere nessuno stato e senza che il tema debba mandare niente di nuovo.
//
// Le due funzioni qui sotto sono le due meta' della stessa convenzione: se
// cambia una, deve cambiare l'altra.
const PREFISSO_COMPOSITO = 'perla-composito-';

function nomeCompositoCloudinary(printifyImageId) {
  const id = String(printifyImageId == null ? '' : printifyImageId).trim();
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;
  return PREFISSO_COMPOSITO + id;
}

function urlCompositoDaId(printifyImageId, cloudName) {
  const nome = nomeCompositoCloudinary(printifyImageId);
  if (!nome || !cloudName || !/^[A-Za-z0-9_-]+$/.test(String(cloudName))) return null;
  return 'https://res.cloudinary.com/' + cloudName + '/image/upload/' + nome + '.jpg';
}

module.exports = {
  componiConMotivo,
  idPubblicoCloudinary,
  motivoPerProdotto,
  nomeCompositoCloudinary,
  urlCompositoDaId,
  scordaIndice,
};
