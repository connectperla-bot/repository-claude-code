'use strict';

// Riceve il webhook Shopify "orders/create", verifica la firma HMAC reale di
// Shopify e, per ogni riga d'ordine con una personalizzazione (proprieta'
// "_Personalizzazione"), crea su Printify un prodotto con la foto posizionata
// esattamente come l'ha impostata il cliente (stessi valori x/y/scale/angle
// scelti nello studio sul sito), poi crea l'ordine collegato a quel prodotto.
//
// SHOPIFY_WEBHOOK_SECRET = il "signing secret" mostrato in Shopify Admin ->
// Impostazioni -> Notifiche -> sezione Webhook, quando crei li' il webhook
// "Order creation" verso questo servizio. Quel secret firma DAVVERO le
// richieste in arrivo, quindi la verifica HMAC qui sotto e' autentica.
//
// IMPORTANTE: per sicurezza, il nuovo ordine NON viene inviato automaticamente
// in produzione. Resta in sospeso nel pannello Printify finche' non lo approvi
// tu manualmente (Printify > Ordini > Invia in produzione). Quando sarai
// sicuro del flusso potrai automatizzare anche quel passo.
//
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
// Configurazione: copia config/printify.env.example in config/printify.local.env,
// inserisci le tue credenziali reali e caricale nell'ambiente prima di avviare.
// NON inserire mai le chiavi API in questo file o nel .bat.

const crypto = require('crypto');
const express = require('express');

const {
  SHOPIFY_WEBHOOK_SECRET,
  PRINTIFY_API_KEY,
  PRINTIFY_SHOP_ID,
  PERLA_LOGO_IMAGE_ID,
  PORT = 3000,
} = process.env;

if (!SHOPIFY_WEBHOOK_SECRET || !PRINTIFY_API_KEY || !PRINTIFY_SHOP_ID) {
  console.error('Variabili di ambiente mancanti: vedi config/printify.env.example');
  process.exit(1);
}

// Mappatura tipo prodotto -> blueprint/print provider/variante Printify.
// blueprint_id e print_provider_id sono gia' compilati con i valori reali del
// catalogo Printify per questi prodotti; VARIANT_ID va scelto da te in base
// alla taglia/colore che vendi davvero (vedi guida nel messaggio di errore).
const PRODUCT_TYPE_CONFIG = {
  collare: {
    blueprintId: Number(process.env.COLLARE_BLUEPRINT_ID || 784),
    printProviderId: Number(process.env.COLLARE_PROVIDER_ID || 93),
    variantId: Number(process.env.COLLARE_VARIANT_ID || 0),
  },
  bandana: {
    blueprintId: Number(process.env.BANDANA_BLUEPRINT_ID || 562),
    printProviderId: Number(process.env.BANDANA_PROVIDER_ID || 70),
    variantId: Number(process.env.BANDANA_VARIANT_ID || 0),
  },
  medaglietta: {
    blueprintId: Number(process.env.MEDAGLIETTA_BLUEPRINT_ID || 566),
    printProviderId: Number(process.env.MEDAGLIETTA_PROVIDER_ID || 70),
    variantId: Number(process.env.MEDAGLIETTA_VARIANT_ID || 0),
  },
  ciotola: {
    blueprintId: Number(process.env.CIOTOLA_BLUEPRINT_ID || 570),
    printProviderId: Number(process.env.CIOTOLA_PROVIDER_ID || 70),
    variantId: Number(process.env.CIOTOLA_VARIANT_ID || 0),
  },
  cuccia: {
    blueprintId: Number(process.env.CUCCIA_BLUEPRINT_ID || 419),
    printProviderId: Number(process.env.CUCCIA_PROVIDER_ID || 10),
    variantId: Number(process.env.CUCCIA_VARIANT_ID || 0),
  },
  tappetino: {
    blueprintId: Number(process.env.TAPPETINO_BLUEPRINT_ID || 855),
    printProviderId: Number(process.env.TAPPETINO_PROVIDER_ID || 70),
    variantId: Number(process.env.TAPPETINO_VARIANT_ID || 0),
  },
  guinzaglio: {
    blueprintId: Number(process.env.GUINZAGLIO_BLUEPRINT_ID || 2791),
    printProviderId: Number(process.env.GUINZAGLIO_PROVIDER_ID || 80),
    variantId: Number(process.env.GUINZAGLIO_VARIANT_ID || 0),
  },
};

const app = express();
app.use(express.raw({ type: 'application/json' }));

function verifyShopifyWebhook(req) {
  const hmacHeader = req.get('X-Shopify-Hmac-Sha256') || '';
  const digest = crypto
    .createHmac('sha256', SHOPIFY_WEBHOOK_SECRET)
    .update(req.body)
    .digest('base64');
  try {
    return crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(hmacHeader));
  } catch (err) {
    return false;
  }
}

app.post('/webhooks/orders-create', async function (req, res) {
  try {
    if (!verifyShopifyWebhook(req)) {
      return res.status(401).send('Firma non valida');
    }

    const order = JSON.parse(req.body.toString('utf8'));
    const customItems = (order.line_items || []).filter(function (item) {
      return (item.properties || []).some(function (p) { return p.name === '_Personalizzazione' && p.value; });
    });

    for (const item of customItems) {
      const raw = item.properties.find(function (p) { return p.name === '_Personalizzazione'; }).value;
      let custom;
      try { custom = JSON.parse(raw); } catch (e) { console.error('Personalizzazione non leggibile:', raw); continue; }
      await handleCustomItem(order, item, custom);
    }

    res.status(200).send('OK');
  } catch (err) {
    console.error('Errore elaborazione ordine:', err);
    res.status(500).send('Errore interno');
  }
});

async function handleCustomItem(order, item, custom) {
  const config = PRODUCT_TYPE_CONFIG[custom.product_type];
  if (!config) {
    console.error('Tipo prodotto sconosciuto ("' + custom.product_type + '") per ordine ' + order.id + ': aggiungi il tag tipo-* al prodotto in Shopify.');
    return;
  }
  if (!config.variantId) {
    console.error(
      'Variante Printify non configurata per "' + custom.product_type + '". ' +
      'Imposta ' + custom.product_type.toUpperCase() + '_VARIANT_ID in config/printify.local.env ' +
      '(trovi gli id variante chiamando GET /v1/catalog/blueprints/' + config.blueprintId +
      '/print_providers/' + config.printProviderId + '/variants.json con la tua chiave Printify).'
    );
    return;
  }
  if (!custom.printify_image_id) {
    console.error('Nessuna immagine Printify associata alla riga ordine ' + order.id + ' (upload non riuscito o endpoint non configurato).');
    return;
  }

  const product = await createPrintifyProduct(order, item, custom, config);
  await createPrintifyOrder(order, product.id, config.variantId, item.quantity);
  console.log('Ordine Printify creato (in sospeso, da approvare manualmente) per ordine Shopify ' + order.id);
}

async function createPrintifyProduct(order, item, custom, config) {
  const response = await fetch('https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/products.json', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: (item.title || 'Personalizzato') + ' - Ordine #' + order.order_number,
      description: 'Your best friend deserves the best. This custom personalized pet accessory is inspired by Italian elegance — clean lines and premium materials. As loved by real pets Aron & Mia.\n\n- Premium materials: soft, durable, easy to clean\n- Secure construction for daily use\n- Personalized with your pet\'s name or photo\n\nShips within the USA in 3-8 business days. FREE shipping over $59.\n\nCountry of Origin: varies by provider (often USA or imported). Complies with applicable U.S. consumer product safety regulations (CPSIA where applicable). Always supervise your pet. Personalized items are final sale. Tested on Aron & Mia.',
      blueprint_id: config.blueprintId,
      print_provider_id: config.printProviderId,
      variants: [{ id: config.variantId, price: 0, is_enabled: true }],
      print_areas: [
        {
          variant_ids: [config.variantId],
          placeholders: [
            {
              position: custom.position || 'front',
              images: [
                // Design di base (pattern tipo 2, o solo-logo tipo 3), sotto a
                // tutto il resto. Identita' perche' e' gia' a piena area (vedi
                // GET /pattern-source in perla-upload-endpoint.js). Assente per
                // i prodotti tipo 1-con-foto di oggi: nessun cambiamento li'.
                ...(custom.base_image_id ? [{
                  id: custom.base_image_id,
                  x: 0.5,
                  y: 0.5,
                  scale: 1,
                  angle: 0,
                }] : []),
                {
                  id: custom.printify_image_id,
                  x: custom.x,
                  y: custom.y,
                  scale: custom.scale,
                  angle: custom.angle,
                },
                // Fixed Perla logo layer - always visible, small in corner
                ...(PERLA_LOGO_IMAGE_ID ? [{
                  id: PERLA_LOGO_IMAGE_ID,
                  x: 0.82,
                  y: 0.82,
                  scale: 0.12,
                  angle: 0,
                }] : []),
              ],
            },
          ],
        },
      ],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error('Errore creazione prodotto Printify (' + response.status + '): ' + text);
  }
  return response.json();
}

async function createPrintifyOrder(order, productId, variantId, quantity) {
  const response = await fetch('https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/orders.json', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY, 'Content-Type': 'application/json' },
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

app.listen(PORT, function () {
  console.log('Sincronizzazione ordini Printify in ascolto sulla porta ' + PORT);
});
