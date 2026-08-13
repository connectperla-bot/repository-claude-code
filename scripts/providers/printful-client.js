'use strict';

const rete = require('../perla-rete');

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

// ROUND 22 -- il motivo non finiva nel file di stampa.
//
// buildComposite() in assets/global.js esporta SOLO il canvas Fabric: il nome
// del cliente su fondo trasparente, niente motivo (in global.js non esiste
// nessun setBackgroundImage). Sui prodotti Printify il motivo arriva a parte,
// come base_image_id preso da /pattern-source; ma /pattern-source lavora sul
// printify_product_id, che i prodotti Printful non hanno. Risultato: un ordine
// EU stampava il nome su un accessorio BIANCO, non sul damascato della foto.
//
// Qui i due livelli vengono uniti prima di mandarli a Printful, con una
// sovrapposizione Cloudinary: motivo sotto (a piena risoluzione nativa, la
// stessa dell'area di stampa), livello cliente sopra. Il risultato esce
// automaticamente alla misura del motivo, quindi non serve nessuna tabella di
// misure da tenere allineata: e' la stessa formula per collare, bandana,
// ciotola e guinzaglio (verificato su tutti e quattro).
//
// Non si tocca il percorso Printify: la' il motivo c'e' gia', e sovrapporlo
// una seconda volta lo stamperebbe doppio.
function idPubblicoCloudinary(url) {
  // https://res.cloudinary.com/<cloud>/image/upload/v123/<id>.<est>
  const m = String(url || '').match(/\/image\/upload\/(?:[^/]+\/)*?([^/.]+)\.[a-z0-9]+$/i);
  return m ? m[1] : null;
}

function componiConMotivo(urlCliente, urlMotivo) {
  const idCliente = idPubblicoCloudinary(urlCliente);
  const idMotivo = idPubblicoCloudinary(urlMotivo);
  // Se uno dei due non e' su Cloudinary si torna al file del cliente da solo:
  // meglio quello che un file di stampa costruito male.
  //
  // MA VA DETTO AD ALTA VOCE, e questa e' una correzione. Prima ripiegava in
  // silenzio, e c'e' un caso in cui il silenzio costa: se il MOTIVO non e'
  // Cloudinary (per esempio perche' e' stato ospitato su Shopify Files, cosa
  // che stiamo iniziando a fare) il cliente riceve il suo nome stampato su
  // fondo vuoto, senza il damasco sotto, e nessuno se ne accorge finche' non
  // arriva il pacco. Casi legittimi: i prodotti neutri, che un motivo non ce
  // l'hanno proprio. Quelli si riconoscono perche' urlMotivo e' vuoto.
  if (!idCliente || !idMotivo) {
    if (urlMotivo && !idMotivo) {
      console.error(
        'MOTIVO NON COMPOSTO: il file di stampa uscira' + "'" + ' SENZA il motivo sotto. ' +
        'componiConMotivo() sa comporre solo da Cloudinary, e questo motivo sta altrove: ' +
        String(urlMotivo).slice(0, 120)
      );
    }
    if (!idCliente && urlCliente) {
      console.error('Design del cliente non su Cloudinary, composizione saltata: ' +
                    String(urlCliente).slice(0, 120));
    }
    return urlCliente;
  }
  const base = String(urlMotivo).split('/image/upload/')[0] + '/image/upload';
  // w_1.0/h_1.0 + fl_relative = "grande quanto il motivo", c_fit non deforma.
  return base + '/l_' + idCliente + ',w_1.0,h_1.0,c_fit,fl_relative/fl_layer_apply/' + idMotivo + '.jpg';
}

async function createOrderOnPrintful(order, item, front, back, config, apiKey, autoConfirm) {
  const files = [];
  if (front && front.printify_image_url) {
    files.push({ type: 'default', url: componiConMotivo(front.printify_image_url, front.pattern_url) });
  }
  if (back && back.printify_image_url) {
    files.push({ type: 'back', url: componiConMotivo(back.printify_image_url, back.pattern_url) });
  }
  if (!files.length) {
    throw new Error('Nessuna URL immagine disponibile per Printful (printify_image_url mancante — il cliente ha personalizzato prima di questo aggiornamento del sito?).');
  }

  const response = await rete.scrivi('https://api.printful.com/orders', {
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
  const printfulOrder = await createOrderOnPrintful(order, item, front, back, config, env.PRINTFUL_API_KEY, autoConfirm);
  return { provider: 'printful', orderId: printfulOrder.result && printfulOrder.result.id, sentToProduction: autoConfirm };
}

module.exports = { fulfillOrder };
