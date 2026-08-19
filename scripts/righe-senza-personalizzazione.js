'use strict';

// Rende visibili le righe d'ordine arrivate SENZA personalizzazione da un
// canale dove lo studio di personalizzazione non puo' girare.
//
// PERCHE' ESISTE
// Lo studio (la tela dove il cliente sistema la foto) vive sulla scheda
// prodotto del sito: e' li' che si compila la proprieta' _Personalizzazione.
// Da quando i prodotti sono pubblicati anche su Facebook, Instagram e Shop,
// un cliente puo' comprare senza mai passare di li'. La riga arriva al
// webhook senza personalizzazione, il filtro in perla-printify-order-sync.js
// la scarta, e sparisce in silenzio: nessun errore, nessun log, nessuna
// traccia. La titolare scoprirebbe il problema dal cliente che scrive.
//
// COSA FA E COSA NON FA
// Non prova a evadere la riga: senza disegno non c'e' niente da stampare, e
// un ripiego qualunque significherebbe spedire una cosa che il cliente non
// ha scelto. La rende visibile nei log, che e' l'unica cosa onesta da fare.
//
// La correzione vera non sta nel codice: sta nel pannello del canale
// Facebook & Instagram, mettendo il checkout su "negozio online" invece che
// dentro Meta. Questo e' il paracadute per quando quella impostazione manca,
// cambia, o un canale nuovo si aggiunge senza che nessuno ci pensi.

// Canali da cui il cliente PASSA dalla scheda prodotto del sito, e quindi ha
// potuto personalizzare. Si elencano quelli sicuri invece dei sospetti: un
// canale nuovo che comparisse domani verrebbe segnalato invece che ignorato,
// che e' il verso giusto in cui sbagliare.
//
// 'web'                 -> negozio online
// 'shopify_draft_order' -> ordine compilato a mano dalla titolare
// 'pos'                 -> vendita di persona, la personalizzazione si
//                          concorda col cliente davanti
const CANALI_CON_STUDIO = ['web', 'shopify_draft_order', 'pos'];

// Perche' TUTTE le righe senza personalizzazione e non solo quelle dei
// prodotti personalizzabili: il payload del webhook non porta i tag del
// prodotto (ne' il tipo-*), quindi da qui non si puo' sapere se quella riga
// fosse personalizzabile. Saperlo richiederebbe una chiamata all'API per
// ogni riga di ogni ordine non-web. Dato che il catalogo Perla e' tutto
// personalizzabile, la distinzione oggi non esiste; se un giorno entrasse a
// catalogo un prodotto non personalizzabile, questo e' il punto da
// rivedere -- costo: una segnalazione di troppo, non un ordine perso.
function trovaRigheOrfane(order, righePersonalizzate) {
  const personalizzate = new Set(
    (righePersonalizzate || []).map(function (r) { return r.id; })
  );
  return (order.line_items || []).filter(function (item) {
    return !personalizzate.has(item.id);
  });
}

function descriviRiga(item) {
  return item.title + (item.variant_title ? ' (' + item.variant_title + ')' : '');
}

/**
 * @param {object} order              l'ordine Shopify dal webhook
 * @param {Array}  righePersonalizzate le righe che HANNO la personalizzazione
 * @param {function} [log]            dove scrivere (console.error di default)
 * @returns {Array} le righe segnalate, vuoto se non c'e' niente da segnalare
 */
function segnalaRigheSenzaPersonalizzazione(order, righePersonalizzate, log) {
  const scrivi = log || console.error;
  const canale = order.source_name || 'sconosciuto';
  if (CANALI_CON_STUDIO.indexOf(canale) !== -1) return [];

  const orfane = trovaRigheOrfane(order, righePersonalizzate);
  if (!orfane.length) return [];

  scrivi(
    'Ordine ' + order.id + ' dal canale "' + canale + '": ' + orfane.length +
    ' riga/righe senza personalizzazione. Lo studio di personalizzazione vive ' +
    'sulla scheda prodotto del sito, quindi da questo canale il cliente non ci ' +
    'e\' passato. NON sono state inviate in stampa -- senza disegno non c\'e\' ' +
    'niente da stampare. Vanno gestite a mano: ' +
    orfane.map(descriviRiga).join(', ') +
    '. Per evitarlo: nel pannello del canale, metti il checkout sul negozio online.'
  );
  return orfane;
}

module.exports = {
  segnalaRigheSenzaPersonalizzazione,
  trovaRigheOrfane,
  CANALI_CON_STUDIO,
};
