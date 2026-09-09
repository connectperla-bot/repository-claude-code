'use strict';

const { riferimento } = require('../riferimento-ordine');

// Client Printify — logica identica a quella gia' in produzione in
// perla-printify-order-sync.js, solo estratta in un modulo separato cosi'
// il file principale puo' scegliere il fornitore giusto per ogni ordine
// (vedi scripts/provider-router.js) invece di parlare SOLO con Printify.
// Nessun comportamento cambiato per gli ordini che restano su Printify.

// CHI DECIDE LA POSIZIONE DI STAMPA, E PERCHE' NON PUO' DECIDERLA IL TEMA
//
// L'editor scrive nell'ordine un campo `position` che vale sempre "front" sul
// lato davanti e "back" sul retro: e' il LATO DELL'EDITOR, non il nome
// dell'area di stampa del fornitore. Sono due cose diverse e su un prodotto
// si vede: il giacchetto parka (blueprint 10740) il fronte NON ce l'ha,
// l'unica area che Printify conosce si chiama 'back_dtf'. Un ordine spedito
// con "front" verrebbe rifiutato o, peggio, stampato senza il disegno pagato.
//
// Quindi quando la configurazione del tipo dichiara una posizione, quella
// vince. Dove non la dichiara -- cioe' su tutti i tipi storici -- decide come
// prima il campo dell'editor, e il retro della medaglietta continua a
// stampare sul retro.
//
// LA PRIMA STESURA DI QUESTA CORREZIONE NON FUNZIONAVA: passava la
// configurazione come RIPIEGO (`data.position || fallback`), e siccome
// l'editor scrive sempre "front", il ripiego non entrava mai in gioco. Se ne
// e' accorto solo chi e' andato a leggere cosa scrive davvero il tema.
function posizioneFronte(front, config) {
  return (config && config.position) || (front && front.position) || 'front';
}

function posizioneRetro(back) {
  return (back && back.position) || 'back';
}

// Costruisce un placeholder Printify (un lato di stampa) dai valori salvati
// dall'editor: base_image_id opzionale (design di base, sotto) + il composito
// del cliente (printify_image_id) con la sua trasformazione.
function buildPlaceholder(data, posizione) {
  return {
    position: posizione,
    images: [
      ...(data.base_image_id ? [{ id: data.base_image_id, x: 0.5, y: 0.5, scale: 1, angle: 0 }] : []),
      {
        id: data.printify_image_id,
        x: data.x != null ? data.x : 0.5,
        y: data.y != null ? data.y : 0.5,
        scale: data.scale != null ? data.scale : 1,
        angle: data.angle != null ? data.angle : 0,
      },
    ],
  };
}

async function createProduct(order, item, front, back, config, apiKey, shopId) {
  const placeholders = [];
  if (front && front.printify_image_id) placeholders.push(buildPlaceholder(front, posizioneFronte(front, config)));
  if (back && back.printify_image_id) placeholders.push(buildPlaceholder(back, posizioneRetro(back)));

  const response = await fetch('https://api.printify.com/v1/shops/' + shopId + '/products.json', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: (item.title || 'Personalizzato') + ' - Ordine #' + order.order_number,
      description: (item.title || 'Prodotto personalizzato') + ' — personalizzato dal cliente su ordine Shopify.',
      blueprint_id: config.blueprintId,
      print_provider_id: config.printProviderId,
      variants: [{ id: config.variantId, price: 0, is_enabled: true }],
      print_areas: [{ variant_ids: [config.variantId], placeholders: placeholders }],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error('Errore creazione prodotto Printify (' + response.status + '): ' + text);
  }
  return response.json();
}

async function createOrderOnPrintify(order, item, productId, variantId, quantity, apiKey, shopId) {
  const response = await fetch('https://api.printify.com/v1/shops/' + shopId + '/orders.json', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      // Un riferimento per RIGA, non per ordine: vedi riferimento-ordine.js.
      external_id: riferimento(order, item),
      line_items: [{ product_id: productId, variant_id: variantId, quantity: quantity }],
      shipping_method: 1,
      send_shipping_notification: false,
      address_to: {
        first_name: order.shipping_address && order.shipping_address.first_name,
        last_name: order.shipping_address && order.shipping_address.last_name,
        email: order.email,
        address1: order.shipping_address && order.shipping_address.address1,
        city: order.shipping_address && order.shipping_address.city,
        zip: order.shipping_address && order.shipping_address.zip,
        country: order.shipping_address && order.shipping_address.country_code,
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error('Errore creazione ordine Printify (' + response.status + '): ' + text);
  }
  return response.json();
}

// ROUND 33 -- creare l'ordine su Printify lo lascia in stato "pending", NON
// in produzione: senza questa seconda chiamata resta in sospeso nel pannello
// Printify (Orders) finche' qualcuno non lo approva a mano, premendo "Send to
// production" li'. ROUND 35 -- la titolare vuole approvare lei gli ordini
// "all'inizio", quindi fulfillOrder() sotto NON chiama piu' questa funzione
// di default: resta qui pronta (non cancellata) per quando vorra' passare
// all'invio automatico, dietro l'env var PRINTIFY_AUTO_SEND_TO_PRODUCTION.
async function sendToProduction(orderId, apiKey, shopId) {
  const response = await fetch(
    'https://api.printify.com/v1/shops/' + shopId + '/orders/' + orderId + '/send_to_production.json',
    { method: 'POST', headers: { Authorization: 'Bearer ' + apiKey } }
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error('Errore invio in produzione Printify ordine ' + orderId + ' (' + response.status + '): ' + text);
  }
  return response.json();
}

// Interfaccia comune usata da provider-router.js: fulfillOrder(ctx) dove ctx
// contiene { order, item, front, back, config, env }. env porta le chiavi
// API/shopId invece di leggerle da process.env qui dentro, cosi' il modulo
// resta testabile senza dover impostare variabili globali.
async function fulfillOrder(ctx) {
  const { order, item, front, back, config, env } = ctx;
  const product = await createProduct(order, item, front, back, config, env.PRINTIFY_API_KEY, env.PRINTIFY_SHOP_ID);
  const printifyOrder = await createOrderOnPrintify(order, item, product.id, config.variantId, item.quantity, env.PRINTIFY_API_KEY, env.PRINTIFY_SHOP_ID);

  let sentToProduction = false;
  if (env.PRINTIFY_AUTO_SEND_TO_PRODUCTION === 'true') {
    try {
      await sendToProduction(printifyOrder.id, env.PRINTIFY_API_KEY, env.PRINTIFY_SHOP_ID);
      sentToProduction = true;
    } catch (err) {
      // Ordine creato ma non confermato in automatico: resta pending su
      // Printify, va inviato a mano da li'.
      console.error('Ordine Printify ' + printifyOrder.id + ' creato ma NON inviato in produzione automaticamente:', err.message);
    }
  }
  // Approvazione manuale (default): l'ordine resta "pending" nel pannello
  // Printify -> Orders finche' la titolare non preme "Send to production".

  return { provider: 'printify', productId: product.id, orderId: printifyOrder.id, sentToProduction };
}

// posizioneFronte/posizioneRetro escono di qui perche' sono la regola che
// decide DOVE si stampa, ed e' l'unica di questo file che si puo' provare
// senza parlare con Printify: vedi tests/posizione-di-stampa.test.js.
module.exports = { fulfillOrder, posizioneFronte, posizioneRetro };
