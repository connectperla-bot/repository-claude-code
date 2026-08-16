'use strict';

// Client Printful — account reale collegato dal 2026-07-29 (store "Personal
// orders"), variantId per ogni tipo EU in config/printify.local.env. Scritto
// seguendo la documentazione ufficiale dell'API Printful (POST /orders).
// provider-router.js non lo sceglie mai se PRINTFUL_API_KEY manca sul
// servizio Render specifico (torna automaticamente su Printify, vedi quel
// file) -- verifica quella variabile su Render se un ordine EU non evade.
//
// Differenza chiave rispetto a Printify: Printful vuole una URL pubblica
// dell'immagine (files[].url), non un id di un'immagine gia' caricata sui
// loro server. Per questo assets/global.js ora salva anche
// printify_image_url (oltre a printify_image_id) nella proprieta'
// _Personalizzazione — vedi quel file, funzione writePropData.

// ROUND 22/44 -- il motivo non finiva nel file di stampa.
//
// buildComposite() nel tema esporta SOLO il canvas Fabric: il nome del cliente
// su fondo trasparente, niente motivo. Sui prodotti Printify il motivo arriva
// a parte, come base_image_id preso da /pattern-source; ma /pattern-source
// lavora sul printify_product_id, che i prodotti Printful non hanno.
//
// ROUND 22 aveva provato a unire i due livelli QUI, leggendo front.pattern_url
// e front.printify_image_url dalla proprieta' _Personalizzazione. Quella
// correzione non ha mai funzionato: il tema pubblicato e' fermo al Round 17 e
// quei due campi non li scrive nessuno. Il risultato non era nemmeno una
// stampa bianca -- era un'eccezione qui sotto, e l'ordine EU non partiva
// affatto.
//
// ROUND 44 sposta l'unione dove i dati ci sono davvero: in /upload
// (perla-upload-endpoint.js), prima del caricamento su Printify. Quindi
// l'immagine dietro printify_image_id e' GIA' completa, e qui non c'e' piu'
// niente da sovrapporre -- rifarlo stamperebbe il motivo due volte.
//
// Resta un problema di sola URL: Printful vuole un indirizzo pubblico, il tema
// manda solo un id, e la preview_url di Printify tronca il lato lungo a
// 1200px. Per questo /upload ripubblica il composito su Cloudinary con un nome
// derivato dall'id, e qui lo si ricostruisce (vedi motivo-di-base.js).
const motivoDiBase = require('../motivo-di-base');

async function urlDelComposito(lato, env) {
  if (!lato) return null;
  // Se un tema futuro tornera' a mandare la URL, quella ha la precedenza.
  if (lato.printify_image_url) return lato.printify_image_url;

  const ricostruita = motivoDiBase.urlCompositoDaId(
    lato.printify_image_id, env && env.CLOUDINARY_CLOUD_NAME);
  if (ricostruita) {
    // Se il composito non fosse mai stato ripubblicato con quel nome
    // (upload precedenti a ROUND 44) Cloudinary risponde 404: meglio
    // accorgersene qui che far rifiutare l'ordine da Printful.
    try {
      const res = await fetch(ricostruita, { method: 'HEAD' });
      if (res.ok) return ricostruita;
      console.error('Composito a piena risoluzione non trovato (' + res.status +
        ') per ' + lato.printify_image_id + ': si ripiega sulla copia Printify a 1200px.');
    } catch (err) {
      console.error('Composito a piena risoluzione non raggiungibile:', err.message);
    }
  }

  // Ripiego: la copia su Printify. Perde risoluzione ma l'ordine parte.
  if (!lato.printify_image_id || !env || !env.PRINTIFY_API_KEY) return null;
  const res = await fetch('https://api.printify.com/v1/uploads/' + lato.printify_image_id + '.json', {
    headers: { Authorization: 'Bearer ' + env.PRINTIFY_API_KEY },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.preview_url || null;
}

async function createOrderOnPrintful(order, item, front, back, config, apiKey, autoConfirm, env) {
  const files = [];
  const urlFronte = await urlDelComposito(front, env);
  if (urlFronte) files.push({ type: 'default', url: urlFronte });
  const urlRetro = await urlDelComposito(back, env);
  if (urlRetro) files.push({ type: 'back', url: urlRetro });
  if (!files.length) {
    throw new Error('Nessuna URL immagine disponibile per Printful: ne\' printify_image_url, ne\' il composito su Cloudinary, ne\' la copia su Printify.');
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
      // ROUND 35 -- confirm:false (default): l'ordine arriva su Printful
      // come bozza in "Draft orders", in attesa che la titolare lo confermi
      // da li' (approvazione manuale voluta "all'inizio"). Diventa
      // confirm:true solo con PRINTFUL_AUTO_CONFIRM=true su Render, stesso
      // interruttore di PRINTIFY_AUTO_SEND_TO_PRODUCTION in
      // providers/printify-client.js -- un solo env var da cambiare quando
      // si vorra' passare all'invio automatico, nessun redeploy di codice.
      confirm: !!autoConfirm,
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
  const autoConfirm = env.PRINTFUL_AUTO_CONFIRM === 'true';
  const printfulOrder = await createOrderOnPrintful(order, item, front, back, config, env.PRINTFUL_API_KEY, autoConfirm, env);
  return { provider: 'printful', orderId: printfulOrder.result && printfulOrder.result.id, sentToProduction: autoConfirm };
}

module.exports = { fulfillOrder };
