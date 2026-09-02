'use strict';

// Il filo che lega una RIGA d'ordine Shopify all'ordine creato dallo stampatore.
//
// PERCHE' ESISTE
// Fino a oggi tutti e due i client mandavano `external_id: String(order.id)`,
// cioe' l'id dell'ORDINE Shopify. Ma perla-printify-order-sync.js crea un
// ordine dallo stampatore per ogni RIGA personalizzata (il ciclo
// `for (const item of customItems)`), quindi due righe nello stesso ordine
// mandavano due volte lo stesso external_id.
//
// Due guasti, non uno:
//
// 1. Printful e Printify pretendono che external_id sia unico. La SECONDA riga
//    di un ordine con due articoli personalizzati veniva rifiutata. Chi compra
//    un collare e un guinzaglio insieme -- cioe' esattamente l'ordine che
//    vogliamo -- riceveva solo il collare.
//
// 2. Quando arriva il webhook della spedizione, l'unica cosa che lo stampatore
//    ci ridice e' l'external_id. Con l'id dell'ordine non si sa QUALE riga e'
//    partita, e non si puo' evadere quella e solo quella su Shopify.
//
// Nessun ordine e' mai passato per questo servizio (zero ordini sul negozio),
// quindi non c'e' niente di vecchio da convertire: il formato nuovo vale da
// subito e non ha bisogno di un periodo di transizione.
//
// IL FORMATO
//     <id ordine Shopify>-<id riga Shopify>      es. "5432167890-9876543210"
//
// Un trattino, due numeri. Non JSON, non base64: questo valore compare nel
// pannello dello stampatore, e chi lo guarda a mano deve poterci leggere
// l'ordine senza decodificare niente.

/**
 * @param {object} order  l'ordine Shopify (dal webhook orders/create)
 * @param {object} item   la riga d'ordine
 * @returns {string} il riferimento da mandare allo stampatore come external_id
 */
function riferimento(order, item) {
  const ordine = order && order.id;
  const riga = item && item.id;
  if (ordine == null || riga == null) {
    // Meglio fermarsi che mandare "undefined-undefined": quel valore
    // passerebbe la validazione dello stampatore e tornerebbe indietro col
    // webhook della spedizione senza dire niente a nessuno.
    throw new Error('Riferimento non costruibile: manca ' +
      (ordine == null ? "l'id dell'ordine" : "l'id della riga") + '.');
  }
  return String(ordine) + '-' + String(riga);
}

/**
 * Il verso opposto, usato quando torna il webhook della spedizione.
 * @param {string} testo l'external_id ricevuto dallo stampatore
 * @returns {{ordine: string, riga: string}|null} null se non e' dei nostri
 */
function leggiRiferimento(testo) {
  const m = /^(\d+)-(\d+)$/.exec(String(testo == null ? '' : testo).trim());
  if (!m) return null;
  return { ordine: m[1], riga: m[2] };
}

module.exports = { riferimento, leggiRiferimento };
