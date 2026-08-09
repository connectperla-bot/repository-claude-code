'use strict';

// Client Printify — logica identica a quella gia' in produzione in
// perla-printify-order-sync.js, solo estratta in un modulo separato cosi'
// il file principale puo' scegliere il fornitore giusto per ogni ordine
// (vedi scripts/provider-router.js) invece di parlare SOLO con Printify.
// Nessun comportamento cambiato per gli ordini che restano su Printify.

// Costruisce un placeholder Printify (un lato di stampa) dai valori salvati
// dall'editor: base_image_id opzionale (design di base, sotto) + il composito
// del cliente (printify_image_id) con la sua trasformazione.
function buildPlaceholder(data, fallbackPosition) {
  return {
    position: data.position || fallbackPosition,
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
  if (front && front.printify_image_id) placeholders.push(buildPlaceholder(front, 'front'));
  if (back && back.printify_image_id) placeholders.push(buildPlaceholder(back, 'back'));

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

async function createOrderOnPrintify(order, productId, variantId, quantity, apiKey, shopId) {
  const response = await fetch('https://api.printify.com/v1/shops/' + shopId + '/orders.json', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      external_id: String(order.id),
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
  const printifyOrder = await createOrderOnPrintify(order, product.id, config.variantId, item.quantity, env.PRINTIFY_API_KEY, env.PRINTIFY_SHOP_ID);

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

module.exports = { fulfillOrder };
