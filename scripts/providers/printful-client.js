'use strict';

// Client Printful — NON ANCORA UTILIZZABILE IN PRODUZIONE: serve un account
// Printful reale (PRINTFUL_API_KEY) e gli ID variante del loro catalogo per
// collare/bandana (PRINTFUL_COLLARE_VARIANT_ID / PRINTFUL_BANDANA_VARIANT_ID),
// nessuno dei due esiste ancora. Scritto seguendo la documentazione ufficiale
// dell'API Printful (POST /orders) cosi' e' pronto appena l'account esiste;
// provider-router.js non lo sceglie mai se PRINTFUL_API_KEY manca (torna
// automaticamente su Printify, vedi quel file).
//
// Differenza chiave rispetto a Printify: Printful vuole una URL pubblica
// dell'immagine (files[].url), non un id di un'immagine gia' caricata sui
// loro server. Per questo assets/global.js ora salva anche
// printify_image_url (oltre a printify_image_id) nella proprieta'
// _Personalizzazione — vedi quel file, funzione writePropData.

async function createOrderOnPrintful(order, item, front, back, config, apiKey) {
  const files = [];
  if (front && front.printify_image_url) files.push({ type: 'default', url: front.printify_image_url });
  if (back && back.printify_image_url) files.push({ type: 'back', url: back.printify_image_url });
  if (!files.length) {
    throw new Error('Nessuna URL immagine disponibile per Printful (printify_image_url mancante — il cliente ha personalizzato prima di questo aggiornamento del sito?).');
  }

  const response = await fetch('https://api.printful.com/orders', {
    method: 'POST',
    headers: {
      Authorization: 'Bearer ' + apiKey,
      'Content-Type': 'application/json',
      // richiesto da Printful da quando l'account ha un solo store nativo
      // ("Personal orders") invece di uno store sync collegato a un canale
      // di vendita - senza questo header ogni chiamata fallisce con
      // "This endpoint requires `store_id`!" (verificato con un ordine di
      // prova reale, poi annullato).
      'X-PF-Store-Id': String(config.storeId),
    },
    body: JSON.stringify({
      external_id: String(order.id),
      // confirm:false -> l'ordine resta in bozza su Printful finche' non lo
      // approvi manualmente da li', stessa cautela gia' in uso per Printify
      // (vedi commento in testa a perla-printify-order-sync.js).
      confirm: false,
      recipient: {
        name: [order.shipping_address && order.shipping_address.first_name, order.shipping_address && order.shipping_address.last_name].filter(Boolean).join(' '),
        address1: order.shipping_address && order.shipping_address.address1,
        city: order.shipping_address && order.shipping_address.city,
        zip: order.shipping_address && order.shipping_address.zip,
        country_code: order.shipping_address && order.shipping_address.country_code,
        email: order.email,
      },
      items: [{
        variant_id: config.variantId,
        quantity: item.quantity,
        files: files,
        // alcuni prodotti Printful richiedono opzioni specifiche (es. la
        // bandana quadrata vuole stitch_color: senza, l'ordine e' rifiutato
        // con 400 "option missing or has an invalid value") - config-driven
        // cosi' ogni tipo prodotto porta le sue, verificato con un ordine
        // di prova reale per bandana (630, richiede stitch_color) e collare
        // (749, nessuna opzione richiesta).
        ...(config.options ? { options: config.options } : {}),
      }],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error('Errore creazione ordine Printful (' + response.status + '): ' + text);
  }
  return response.json();
}

// Stessa interfaccia di printify-client.js: fulfillOrder(ctx).
async function fulfillOrder(ctx) {
  const { order, item, front, back, config, env } = ctx;
  if (!config.variantId) {
    throw new Error(
      'Variante Printful non configurata per questo tipo di prodotto. ' +
      'Imposta PRINTFUL_COLLARE_VARIANT_ID / PRINTFUL_BANDANA_VARIANT_ID in config/printify.local.env ' +
      'una volta che l\'account Printful esiste (li trovi nel loro catalogo API).'
    );
  }
  const printfulOrder = await createOrderOnPrintful(order, item, front, back, config, env.PRINTFUL_API_KEY);
  return { provider: 'printful', orderId: printfulOrder.result && printfulOrder.result.id };
}

module.exports = { fulfillOrder };
