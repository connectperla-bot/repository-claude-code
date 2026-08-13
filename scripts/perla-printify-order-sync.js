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
// ROUND 35 -- per scelta esplicita della titolare, il nuovo ordine resta in
// approvazione MANUALE "all'inizio": Printify va approvato da Printify >
// Orders > Send to production, Printful da Printful > Draft orders. Il
// codice per l'invio automatico (send_to_production / confirm:true) esiste
// gia' in providers/*-client.js, disattivato di default dietro due env var
// (PRINTIFY_AUTO_SEND_TO_PRODUCTION / PRINTFUL_AUTO_CONFIRM) -- va attivato
// solo quando la titolare decide di fidarsi del flusso senza controllo riga
// per riga. Indipendentemente da questo interruttore, ogni riga d'ordine e'
// isolata nel proprio try/catch: se una riga fallisce (variante non
// configurata, fornitore che rifiuta l'ordine, ecc.) resta solo loggata per
// un controllo manuale, senza bloccare ne' duplicare le altre righe dello
// stesso ordine (vedi isolamento errori qui sotto).
//
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
// Configurazione: copia config/printify.env.example in config/printify.local.env,
// inserisci le tue credenziali reali e caricale nell'ambiente prima di avviare.
// NON inserire mai le chiavi API in questo file o nel .bat.

const crypto = require('crypto');
const express = require('express');
const providerRouter = require('./provider-router');

const {
  SHOPIFY_WEBHOOK_SECRET,
  PRINTIFY_API_KEY,
  PRINTIFY_SHOP_ID,
  PORT = 3000,
} = process.env;

if (!SHOPIFY_WEBHOOK_SECRET || !PRINTIFY_API_KEY || !PRINTIFY_SHOP_ID) {
  console.error('Variabili di ambiente mancanti: vedi config/printify.env.example');
  process.exit(1);
}

// Mappatura tipo prodotto -> blueprint/print provider/variante, UNA per
// fornitore possibile (oggi solo Printify per tutti, + Printful per
// collare/bandana quando spediscono in EU — vedi provider-router.js).
// blueprint_id e print_provider_id di Printify sono gia' compilati con i
// valori reali del catalogo; VARIANT_ID va scelto da te in base alla
// taglia/colore che vendi davvero (vedi guida nel messaggio di errore).
const PRODUCT_TYPE_CONFIG = {
  printify: {
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
    // ROUND 18 — rete di sicurezza: se per errore un ordine non-EU (o senza
    // Printful configurato) arriva con product_type collare_eu/bandana_eu,
    // finisce comunque su Printify (stesso blueprint del collare/bandana
    // normale) invece di fallire silenziosamente - vedi handleCustomItem.
    collare_eu: {
      blueprintId: Number(process.env.COLLARE_BLUEPRINT_ID || 784),
      printProviderId: Number(process.env.COLLARE_PROVIDER_ID || 93),
      variantId: Number(process.env.COLLARE_VARIANT_ID || 0),
    },
    bandana_eu: {
      blueprintId: Number(process.env.BANDANA_BLUEPRINT_ID || 562),
      printProviderId: Number(process.env.BANDANA_PROVIDER_ID || 70),
      variantId: Number(process.env.BANDANA_VARIANT_ID || 0),
    },
    // ROUND 28 -- stessa rete di sicurezza di collare_eu/bandana_eu sopra,
    // per ciotola_eu/guinzaglio_eu.
    ciotola_eu: {
      blueprintId: Number(process.env.CIOTOLA_BLUEPRINT_ID || 570),
      printProviderId: Number(process.env.CIOTOLA_PROVIDER_ID || 70),
      variantId: Number(process.env.CIOTOLA_VARIANT_ID || 0),
    },
    guinzaglio_eu: {
      blueprintId: Number(process.env.GUINZAGLIO_BLUEPRINT_ID || 2791),
      printProviderId: Number(process.env.GUINZAGLIO_PROVIDER_ID || 80),
      variantId: Number(process.env.GUINZAGLIO_VARIANT_ID || 0),
    },
  },
  // ROUND 18 — collare_eu/bandana_eu (NON collare/bandana): Printful non ha
  // un prodotto equivalente al collare TPU o alla bandana rettangolare
  // venduti oggi (collare Printful e' in tessuto, bandana Printful e'
  // quadrata) - vedi provider-router.js. Sono quindi prodotti Shopify
  // NUOVI e distinti, cosi' l'attivazione di PRINTFUL_API_KEY non tocca
  // mai gli ordini dei prodotti collare/bandana esistenti.
  // storeId: l'account Printful ha un solo store nativo ("Personal
  // orders"), richiesto in ogni chiamata (header X-PF-Store-Id) - vedi
  // providers/printful-client.js.
  // options: alcuni prodotti Printful richiedono opzioni extra (verificato
  // con un ordine di prova reale, poi annullato): la bandana quadrata vuole
  // stitch_color, il collare no.
  printful: {
    collare_eu: {
      storeId: Number(process.env.PRINTFUL_STORE_ID || 0),
      variantId: Number(process.env.PRINTFUL_COLLARE_EU_VARIANT_ID || 0),
    },
    bandana_eu: {
      storeId: Number(process.env.PRINTFUL_STORE_ID || 0),
      variantId: Number(process.env.PRINTFUL_BANDANA_EU_VARIANT_ID || 0),
      options: [{ id: 'stitch_color', value: 'white' }],
    },
    // ROUND 28 -- ciotola_eu (Printful "Pet Bowl", id catalogo 678) e
    // guinzaglio_eu ("Pet Leash", id catalogo 745). Nessuna opzione extra
    // richiesta per questi due (verificato leggendo lo schema prodotto via
    // API, a differenza della bandana quadrata sopra che vuole
    // stitch_color) -- da confermare con un ordine di prova reale come gia'
    // fatto per collare_eu/bandana_eu, vedi commento in testa al file.
    ciotola_eu: {
      storeId: Number(process.env.PRINTFUL_STORE_ID || 0),
      variantId: Number(process.env.PRINTFUL_CIOTOLA_EU_VARIANT_ID || 0),
    },
    guinzaglio_eu: {
      storeId: Number(process.env.PRINTFUL_STORE_ID || 0),
      variantId: Number(process.env.PRINTFUL_GUINZAGLIO_EU_VARIANT_ID || 0),
    },
  },
  // ROUND 36 -- Contrado, linea premium a DESIGN FISSO (vedi
  // provider-router.js e providers/contrado-client.js). Qui serve solo lo
  // storeProductId del prodotto gia' creato nel negozio Contrado: la variante
  // arriva dalla SKU della variante Shopify, come per i prodotti Printify di
  // questo negozio.
  //
  // ATTENZIONE, questi tipi non passano di qui oggi. Questo handler evade
  // solo le righe con la proprieta' "_Personalizzazione" (vedi il filtro
  // customItems piu' sotto), e i prodotti Contrado non ce l'hanno mai:
  // l'API Contrado non trasporta file di stampa, quindi sono a design fisso
  // per forza. La configurazione e' pronta, ma perche' un ordine _lux arrivi
  // fin qui serve prima decidere COME si evadono i prodotti a design fisso:
  // con l'app Shopify di Contrado (che li sincronizza da sola, e allora
  // questo blocco resta inutilizzato), oppure allargando il filtro ai soli
  // tipi _lux. Il filtro NON va allargato a tutte le righe: i prodotti
  // Printify a design fisso sono gia' evasi dall'app Shopify di Printify, e
  // rievaderli qui creerebbe ordini doppi.
  contrado: {
    cuccia_lux: { productId: Number(process.env.CONTRADO_CUCCIA_LUX_PRODUCT_ID || 0) },
    guinzaglio_lux: { productId: Number(process.env.CONTRADO_GUINZAGLIO_LUX_PRODUCT_ID || 0) },
    bandana_lux: { productId: Number(process.env.CONTRADO_BANDANA_LUX_PRODUCT_ID || 0) },
    ciotola_lux: { productId: Number(process.env.CONTRADO_CIOTOLA_LUX_PRODUCT_ID || 0) },
    tappetino_lux: { productId: Number(process.env.CONTRADO_TAPPETINO_LUX_PRODUCT_ID || 0) },
    coperta_lux: { productId: Number(process.env.CONTRADO_COPERTA_LUX_PRODUCT_ID || 0) },
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
    // ROUND 17 — una riga e' personalizzata se ha il FRONTE o il RETRO valorizzato.
    // Sul doppio lato (medaglietta) il cliente puo' lasciare il fronte al solo
    // logo (che non genera composito, vedi hasContent in assets/global.js) e
    // riempire solo il retro: quella riga NON va persa.
    const customItems = (order.line_items || []).filter(function (item) {
      return (item.properties || []).some(function (p) {
        return (p.name === '_Personalizzazione' || p.name === '_Personalizzazione_Retro') && p.value;
      });
    });

    // ROUND 33 -- ogni riga viene elaborata nel proprio try/catch: prima, un
    // errore su UNA riga (es. variante non configurata) mandava in eccezione
    // l'intero handler, Express rispondeva 500, e Shopify ritenta lo stesso
    // webhook fino a ~48h -- rielaborando anche le righe GIA' andate a buon
    // fine, creando ordini duplicati su Printify/Printful (nessuna chiave di
    // idempotenza esiste qui). Isolando l'errore per riga, si risponde
    // sempre 200 dopo aver tentato tutte le righe: quelle riuscite non
    // vengono mai ripetute, quelle fallite restano loggate per un controllo
    // manuale invece di sparire o moltiplicarsi.
    const failures = [];
    for (const item of customItems) {
      let custom = null;
      const frontProp = item.properties.find(function (p) { return p.name === '_Personalizzazione' && p.value; });
      if (frontProp) {
        try { custom = JSON.parse(frontProp.value); }
        catch (e) { console.error('Personalizzazione (fronte) non leggibile:', frontProp.value); }
      }
      // Retro opzionale (medaglietta doppio lato): presente solo se il cliente
      // ha personalizzato ANCHE/SOLO il retro (input _Personalizzazione_Retro,
      // vedi sections/main-product.liquid).
      let customBack = null;
      const backProp = item.properties.find(function (p) { return p.name === '_Personalizzazione_Retro' && p.value; });
      if (backProp) {
        try { customBack = JSON.parse(backProp.value); }
        catch (e) { console.error('Personalizzazione (retro) non leggibile:', backProp.value); }
      }
      try {
        await handleCustomItem(order, item, custom, customBack);
      } catch (err) {
        console.error('Riga ordine ' + order.id + ' (' + (item.title || item.id) + ') NON evasa, richiede controllo manuale:', err.message);
        failures.push({ item: item.title || item.id, error: err.message });
      }
    }

    if (failures.length > 0) {
      console.error('Ordine ' + order.id + ': ' + failures.length + ' riga/righe su ' + customItems.length + ' richiedono controllo manuale.');
    }
    // Sempre 200: Shopify non deve ritentare (rielaborerebbe anche le righe
    // gia' riuscite). I fallimenti restano nei log di Render per un controllo
    // manuale -- non silenziosi, solo non piu' causa di duplicati.
    res.status(200).send('OK');
  } catch (err) {
    console.error('Errore elaborazione ordine (prima di iniziare le righe):', err);
    res.status(500).send('Errore interno');
  }
});

async function handleCustomItem(order, item, custom, customBack) {
  // ROUND 17 — un lato e' "valido" se porta un composito (printify_image_id).
  // Si procede se e' presente il FRONTE o il RETRO (o entrambi): cosi' il
  // caso "solo retro" (fronte al solo logo) non viene perso.
  const front = custom && custom.printify_image_id ? custom : null;
  const back = customBack && customBack.printify_image_id ? customBack : null;
  if (!front && !back) {
    console.error('Nessuna immagine associata alla riga ordine ' + order.id + ' (upload non riuscito o design vuoto).');
    return;
  }
  // product_type: da qualunque lato sia presente (entrambi lo riportano uguale).
  const productType = (front && front.product_type) || (back && back.product_type);

  // Instrada al fornitore giusto (Printify di default, Printful per
  // collare/bandana spediti in EU quando l'account e' configurato) — vedi
  // provider-router.js. Questo e' il SOLO punto che decide il fornitore:
  // il resto della funzione non sa nemmeno quale sia stato scelto.
  const providerName = providerRouter.chooseProviderName(productType, order, process.env);
  const config = (PRODUCT_TYPE_CONFIG[providerName] || {})[productType];
  if (!config) {
    console.error(
      'Tipo prodotto sconosciuto ("' + productType + '") per fornitore "' + providerName + '", ordine ' + order.id +
      ': aggiungi il tag tipo-* al prodotto in Shopify, o il tipo a PRODUCT_TYPE_CONFIG.' + providerName + '.'
    );
    return;
  }
  if (providerName === 'printify' && !config.variantId) {
    console.error(
      'Variante Printify non configurata per "' + productType + '". ' +
      'Imposta ' + String(productType).toUpperCase() + '_VARIANT_ID in config/printify.local.env ' +
      '(trovi gli id variante chiamando GET /v1/catalog/blueprints/' + config.blueprintId +
      '/print_providers/' + config.printProviderId + '/variants.json con la tua chiave Printify).'
    );
    return;
  }

  const client = providerRouter.chooseClient(productType, order, process.env);
  const result = await client.fulfillOrder({
    order, item, front, back, config,
    env: process.env,
  });
  // ROUND 35 -- approvazione manuale voluta dalla titolare "all'inizio":
  // sentToProduction e' false di default per entrambi i fornitori (vedi
  // providers/*-client.js, env PRINTIFY_AUTO_SEND_TO_PRODUCTION /
  // PRINTFUL_AUTO_CONFIRM) finche' non verranno attivati. Stato normale in
  // attesa, non un errore -- il log lo riflette cosi'.
  const statusLabel = result.sentToProduction ? 'inviato in produzione automaticamente' : 'creato, in attesa di approvazione manuale (pannello ' + result.provider + ')';
  console.log(
    'Ordine ' + result.provider + ' ' + statusLabel + ' per ordine Shopify ' + order.id +
    (result.orderId ? ' -> ' + result.provider + ' order ' + result.orderId : '')
  );
}

app.listen(PORT, function () {
  console.log('Sincronizzazione ordini Printify in ascolto sulla porta ' + PORT);
});
