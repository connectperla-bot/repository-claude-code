'use strict';

// Servizio di appoggio: riceve la foto caricata dal cliente sul prodotto e la
// carica direttamente su Printify (Uploads API). Restituisce l'id immagine
// Printify (serve per creare l'ordine) e un URL di anteprima ospitato da Printify.
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
// Configurazione: copia config/printify.env.example in config/printify.local.env,
// inserisci PRINTIFY_API_KEY e caricalo nell'ambiente prima di avviare.

const express = require('express');
const multer = require('multer');
const crypto = require('crypto');

const {
  PRINTIFY_API_KEY, PRINTIFY_SHOP_ID, PRINTFUL_API_KEY, PRINTFUL_STORE_ID,
  CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
  PORT = 3001, MAX_UPLOAD_MB = 10, ALLOWED_ORIGIN = 'https://perlaitaly.com',
} = process.env;

if (!PRINTIFY_API_KEY) {
  console.error('Variabile PRINTIFY_API_KEY mancante: vedi config/printify.env.example');
  process.exit(1);
}
// PRINTIFY_SHOP_ID serve solo per /pattern-source (design di base dei prodotti
// tipo 2/3). Non blocca l'avvio: /upload continua a funzionare senza, cosi'
// il deploy non si rompe finche' non si aggiunge la variabile su Render.
if (!PRINTIFY_SHOP_ID) {
  console.warn('Variabile PRINTIFY_SHOP_ID mancante: /pattern-source restituira errore finche\' non la imposti.');
}
// PRINTFUL_API_KEY/PRINTFUL_STORE_ID servono solo per /generate-mockup sui
// tipi EU (collare_eu/bandana_eu/ciotola_eu/guinzaglio_eu, fornitore
// Printful) — vedi PRINTFUL_MOCKUP_CONFIG piu' sotto. Non bloccano l'avvio,
// stesso trattamento di PRINTIFY_SHOP_ID sopra.
if (!PRINTFUL_API_KEY || !PRINTFUL_STORE_ID) {
  console.warn('Variabili PRINTFUL_API_KEY/PRINTFUL_STORE_ID mancanti: /generate-mockup sui tipi _eu restituira errore finche\' non le imposti.');
}
// CLOUDINARY_* servono per ospitare il composito a piena risoluzione (Printify
// preview_url tronca a 1200px sul lato lungo, che diventa anche il file usato
// per la stampa reale su Printful — vedi perla-shopify-app-scope-gotcha).
// Se mancano, /upload ricade sul preview_url Printify come prima: nessun
// deploy si rompe.
if (!CLOUDINARY_CLOUD_NAME || !CLOUDINARY_API_KEY || !CLOUDINARY_API_SECRET) {
  console.warn('Variabili CLOUDINARY_* mancanti: /upload restituira\' l\'URL Printify (1200px) invece della piena risoluzione.');
}

async function uploadToCloudinary(buffer, fileName) {
  const timestamp = Math.round(Date.now() / 1000);
  const signature = crypto
    .createHash('sha1')
    .update('timestamp=' + timestamp + CLOUDINARY_API_SECRET)
    .digest('hex');
  const form = new FormData();
  form.append('file', new Blob([buffer]), fileName);
  form.append('api_key', CLOUDINARY_API_KEY);
  form.append('timestamp', String(timestamp));
  form.append('signature', signature);
  const res = await fetch('https://api.cloudinary.com/v1_1/' + CLOUDINARY_CLOUD_NAME + '/image/upload', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error('Cloudinary upload error (' + res.status + '): ' + text);
  }
  const data = await res.json();
  return data.secure_url;
}

const ALLOWED_MIME = new Set(['image/png', 'image/jpeg', 'image/webp']);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: Number(MAX_UPLOAD_MB) * 1024 * 1024 },
  fileFilter: function (req, file, cb) {
    if (!ALLOWED_MIME.has(file.mimetype)) {
      return cb(new Error('Formato non supportato'));
    }
    cb(null, true);
  },
});

const app = express();

// Render sta dietro un proxy: senza questo req.ip e' sempre l'indirizzo del
// proxy, e il limitatore qui sotto conterebbe tutti i visitatori come uno
// solo -- bloccando il negozio intero al primo che supera la soglia.
app.set('trust proxy', 1);

// Express annuncia se stesso in ogni risposta con X-Powered-By. Non e' una
// falla, ma e' informazione gratis per chi cerca bersagli con una certa
// versione: si toglie e basta.
app.disable('x-powered-by');

app.use(function (req, res, next) {
  res.header('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  // ROUND 40 -- intestazioni di sicurezza.
  //   nosniff      il browser non prova a indovinare il tipo di un file: senza,
  //                una risposta manipolata puo' essere eseguita come script
  //   DENY         questo servizio non va mai dentro un iframe. Impedisce che
  //                qualcuno lo incornici per far cliccare un cliente su
  //                qualcosa che non vede (clickjacking)
  //   no-referrer  gli indirizzi delle nostre rotte, con i loro parametri, non
  //                finiscono nei log dei siti verso cui si esce
  res.header('X-Content-Type-Options', 'nosniff');
  res.header('X-Frame-Options', 'DENY');
  res.header('Referrer-Policy', 'no-referrer');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ROUND 39 -- LIMITE DI RICHIESTE PER INDIRIZZO.
//
// Le rotte di questo servizio spendono soldi veri a ogni chiamata: /upload
// carica su Cloudinary, /generate-mockup CREA UN PRODOTTO su Printify. Erano
// pubbliche, senza autenticazione e senza limite: bastava un ciclo da
// qualunque sito per riempire l'account Printify di spazzatura e consumare la
// quota Cloudinary.
//
// Finestra scorrevole in memoria, senza dipendenze nuove: il servizio gira in
// un solo processo e un limitatore con Redis sarebbe piu' infrastruttura di
// quanta ne serva. Se un domani i processi diventano due, questo conta per
// processo -- va saputo, ma il doppio del limite e' comunque un limite.
const RATE_FINESTRA_MS = 60 * 1000;
const RATE_MAX = Number(process.env.RATE_MAX_AL_MINUTO || 20);
const rateVisite = new Map();

function limitePerIp(req, res, next) {
  const ora = Date.now();
  const ip = req.ip || 'sconosciuto';
  const recenti = (rateVisite.get(ip) || []).filter(function (t) { return ora - t < RATE_FINESTRA_MS; });
  if (recenti.length >= RATE_MAX) {
    res.set('Retry-After', String(Math.ceil(RATE_FINESTRA_MS / 1000)));
    return res.status(429).json({ error: 'Troppe richieste, riprova fra un minuto' });
  }
  recenti.push(ora);
  rateVisite.set(ip, recenti);
  // La mappa non deve crescere all'infinito: ogni tanto si buttano via gli
  // indirizzi fermi da piu' di una finestra.
  if (rateVisite.size > 5000) {
    for (const [chiave, tempi] of rateVisite) {
      if (!tempi.length || ora - tempi[tempi.length - 1] > RATE_FINESTRA_MS) rateVisite.delete(chiave);
    }
  }
  next();
}

app.post('/upload', limitePerIp, upload.single('photo'), async function (req, res) {
  if (!req.file) {
    return res.status(400).json({ error: 'Nessun file ricevuto' });
  }
  try {
    const response = await fetch('https://api.printify.com/v1/uploads/images.json', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + PRINTIFY_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_name: req.file.originalname,
        contents: req.file.buffer.toString('base64'),
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error('Printify upload error (' + response.status + '): ' + text);
    }

    const data = await response.json();
    var previewUrl = data.preview_url;
    if (CLOUDINARY_CLOUD_NAME && CLOUDINARY_API_KEY && CLOUDINARY_API_SECRET) {
      try {
        previewUrl = await uploadToCloudinary(req.file.buffer, req.file.originalname);
      } catch (cloudErr) {
        console.error('Errore upload Cloudinary (uso preview Printify come fallback):', cloudErr.message);
      }
    }
    res.json({ id: data.id, url: previewUrl });
  } catch (err) {
    console.error('Errore upload Printify:', err.message);
    res.status(502).json({ error: 'Caricamento su Printify non riuscito' });
  }
});

// Design di base di un prodotto tipo 2/3 (pattern esistente o solo-logo su cui
// il cliente aggiunge foto/nome/testo). Il frontend lo chiama una volta con il
// printify_product_id salvato nel metafield printify_custom.printify_product_id
// (vedi sections/main-product.liquid) per mostrare quel design come sfondo
// dell'area di stampa e per mandarlo a scripts/perla-printify-order-sync.js
// come base_image_id, cosi' l'ordine finale include design + aggiunte del
// cliente invece di sostituire il design con la sola foto.
const patternSourceCache = new Map(); // productId -> { data, expires }
const PATTERN_SOURCE_TTL_MS = 10 * 60 * 1000;

app.get('/pattern-source', limitePerIp, async function (req, res) {
  const productId = String(req.query.printify_product_id || '').trim();
  if (!productId) {
    return res.status(400).json({ error: 'printify_product_id mancante' });
  }
  // ROUND 39 -- solo cifre, e il controllo non e' formale.
  //
  // Questo valore finiva dritto dentro l'URL chiamato a Printify:
  //   .../v1/shops/<SHOP_ID>/products/<productId>.json
  // Un id come "../../../uploads" si normalizza in un endpoint Printify
  // completamente diverso, chiamato con la NOSTRA chiave API. Bastava la
  // barra degli indirizzi per farsi restituire dati dell'account.
  // Gli id Printify sono numerici: tutto il resto si rifiuta e basta.
  if (!/^[0-9]+$/.test(productId)) {
    return res.status(400).json({ error: 'printify_product_id non valido' });
  }
  if (!PRINTIFY_SHOP_ID) {
    return res.status(500).json({ error: 'PRINTIFY_SHOP_ID non configurato sul server' });
  }

  const cached = patternSourceCache.get(productId);
  if (cached && cached.expires > Date.now()) {
    return res.json(cached.data);
  }

  try {
    const productRes = await fetch(
      'https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/products/' + productId + '.json',
      { headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY } }
    );
    if (!productRes.ok) {
      const text = await productRes.text();
      throw new Error('Printify product error (' + productRes.status + '): ' + text);
    }
    const product = await productRes.json();
    const baseImageId = product.print_areas &&
      product.print_areas[0] &&
      product.print_areas[0].placeholders &&
      product.print_areas[0].placeholders[0] &&
      product.print_areas[0].placeholders[0].images &&
      product.print_areas[0].placeholders[0].images[0] &&
      product.print_areas[0].placeholders[0].images[0].id;
    if (!baseImageId) {
      return res.status(404).json({ error: 'Nessun design di base trovato su questo prodotto Printify' });
    }

    const uploadRes = await fetch('https://api.printify.com/v1/uploads/' + baseImageId + '.json', {
      headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY },
    });
    if (!uploadRes.ok) {
      const text = await uploadRes.text();
      throw new Error('Printify upload lookup error (' + uploadRes.status + '): ' + text);
    }
    const uploadData = await uploadRes.json();

    const data = { id: uploadData.id, preview_url: uploadData.preview_url };
    patternSourceCache.set(productId, { data: data, expires: Date.now() + PATTERN_SOURCE_TTL_MS });
    res.json(data);
  } catch (err) {
    console.error('Errore pattern-source:', err.message);
    res.status(502).json({ error: 'Impossibile recuperare il design di base da Printify' });
  }
});

// "Salva anteprima" - genera un mockup REALE (fotorealistico, generato dai
// server di Printify) del design del cliente. Regole di sicurezza:
// 1. Non tocca MAI il prodotto vero collegato al catalogo: se aggiornassimo
//    quello, la vetrina cambierebbe per TUTTI i clienti che lo guardano in
//    quel momento, non solo per chi ha chiesto l'anteprima.
// 2. Crea un prodotto TEMPORANEO isolato per QUESTA richiesta soltanto e lo
//    cancella subito dopo aver preso le immagini (blocco finally qui sotto):
//    mai un prodotto "di scorta" riusato tra piu' richieste, perche' la foto
//    personale di un cliente potrebbe comparire per sbaglio nell'anteprima
//    generata nello stesso momento per un altro cliente.
const MOCKUP_PRODUCT_TYPES = ['COLLARE', 'BANDANA', 'MEDAGLIETTA', 'CIOTOLA', 'CUCCIA', 'TAPPETINO', 'GUINZAGLIO'];
const MOCKUP_POLL_ATTEMPTS = 6;
const MOCKUP_POLL_DELAY_MS = 1500;

// Prodotti EU (fornitore Printful, non Printify): niente prodotto temporaneo
// da creare/cancellare come sotto -- il Mockup Generator di Printful e'
// gia' un task effimero lato loro (create-task + poll, nessuna scoria da
// pulire). catalogId/placement/area presi dalle risposte REALI di
// GET /mockup-generator/printfiles/<catalogId> (verificato con l'account
// Printful vero, stessi dati gia' usati in snippets/perla-print-areas.liquid
// per i ratio ROUND 18/28) -- non inventati. variantEnv punta alla variante
// Shopify/Printful gia' in uso per quel tipo (vedi config/printify.local.env).
//
// placement e' il files[].TYPE di
// GET https://api.printful.com/products/<catalogId> (endpoint pubblico, non
// serve la chiave) -- non il files[].id.
//
// Il commento che stava qui diceva l'esatto contrario, ed era sbagliato: il
// guinzaglio, messo su 'default' (il suo id) per quel motivo, ha continuato a
// fallire. Adesso che generatePrintfulMockup riporta il messaggio di Printful
// nel campo "detail" si legge in chiaro:
//
//   Printful create-task error (400): "File type default is not allowed for
//   this product"
//
// Sui quattro cataloghi l'id e' sempre "default"; il type e' "front" su
// collare, bandana e guinzaglio, "default" sulla ciotola. Usare il type spiega
// tutto quello che si e' visto: collare e bandana hanno sempre funzionato con
// 'front', la ciotola con 'default', e il guinzaglio ora torna in riga.
const PRINTFUL_MOCKUP_CONFIG = {
  COLLARE_EU: { catalogId: 749, variantEnv: 'PRINTFUL_COLLARE_EU_VARIANT_ID', placement: 'front', width: 7169, height: 315 },
  BANDANA_EU: { catalogId: 630, variantEnv: 'PRINTFUL_BANDANA_EU_VARIANT_ID', placement: 'front', width: 4125, height: 4125 },
  CIOTOLA_EU: { catalogId: 678, variantEnv: 'PRINTFUL_CIOTOLA_EU_VARIANT_ID', placement: 'default', width: 6496, height: 803 },
  GUINZAGLIO_EU: { catalogId: 745, variantEnv: 'PRINTFUL_GUINZAGLIO_EU_VARIANT_ID', placement: 'front', width: 12389, height: 219 },
};
const PRINTFUL_POLL_ATTEMPTS = 8;
const PRINTFUL_POLL_DELAY_MS = 1500;

// ROUND 23 -- le anteprime EU uscivano impastate, a qualunque risoluzione.
//
// Misurato: dando in pasto a questa rotta lo stesso motivo a 7169x315 (nativo),
// 2400x105 e 1200x53 il mockup che torna indietro e' sempre lo stesso impasto,
// con le stesse identiche metriche. Cioe' la risoluzione di partenza non conta:
// a Printful arriva comunque una copia a 1200px, perche' resolvePrintifyImageUrl
// qui sotto restituisce il preview_url di Printify, che tronca il lato lungo a
// 1200px (e' scritto anche nel commento delle variabili CLOUDINARY_* in cima).
// Su un collare 7169px significa buttare via 6 pixel su 7: le volute dorate del
// damascato diventano una macchia. Non si vedeva prima perche' i vecchi file di
// stampa erano gia' larghi ~1200px, con il motivo molto piu' rado.
//
// Il file a piena risoluzione pero' esiste gia': /upload lo mette su Cloudinary
// e ne restituisce la URL insieme all'id Printify. Quindi se il client la
// rimanda (composite_image_url) si usa quella; se non c'e' -- client vecchi,
// chiamate fatte a mano -- si ricade sul preview_url di prima.
//
// Solo Cloudinary, e solo https: e' l'unico host su cui scriviamo noi, e questa
// URL finisce dentro una richiesta autenticata al nostro account Printful.
const CLOUDINARY_HOST_RE = /^https:\/\/res\.cloudinary\.com\/[A-Za-z0-9_-]+\/image\/upload\//;

function urlCompositoValida(url) {
  return typeof url === 'string' && url.length < 2048 && CLOUDINARY_HOST_RE.test(url);
}

// Il client manda sempre un id di un'immagine gia' caricata su Printify
// (vedi /upload sopra, riusato come semplice hosting pubblico anche per i
// compositi destinati a Printful) -- qui si risolve quell'id nella sua URL
// pubblica (stesso identico lookup di /pattern-source sopra), perche' il
// Mockup Generator di Printful vuole una URL fetchabile, non un id Printify.
async function resolvePrintifyImageUrl(imageId) {
  const res = await fetch('https://api.printify.com/v1/uploads/' + imageId + '.json', {
    headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error('Printify upload lookup error (' + res.status + '): ' + text);
  }
  const data = await res.json();
  if (!data.preview_url) throw new Error('Nessuna preview_url per questo upload Printify');
  return data.preview_url;
}

async function generatePrintfulMockup(config, compositeImageId, res, compositeImageUrl) {
  if (!PRINTFUL_API_KEY || !PRINTFUL_STORE_ID) {
    return res.status(500).json({ error: 'PRINTFUL_API_KEY/PRINTFUL_STORE_ID non configurati sul server' });
  }
  const variantId = Number(process.env[config.variantEnv]);
  if (!variantId) {
    return res.status(500).json({ error: 'Variante Printful non configurata sul server per questo tipo' });
  }
  try {
    const imageUrl = urlCompositoValida(compositeImageUrl)
      ? compositeImageUrl
      : await resolvePrintifyImageUrl(compositeImageId);
    const createRes = await fetch('https://api.printful.com/mockup-generator/create-task/' + config.catalogId, {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + PRINTFUL_API_KEY, 'X-PF-Store-Id': String(PRINTFUL_STORE_ID), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        variant_ids: [variantId],
        files: [{
          placement: config.placement,
          image_url: imageUrl,
          // Il composito ha gia' tutti i livelli posizionati (stesso principio
          // della trasformazione IDENTITA' usata per Printify, vedi
          // writePropData in assets/global.js): riempie l'intera area di stampa.
          position: { area_width: config.width, area_height: config.height, width: config.width, height: config.height, top: 0, left: 0 },
        }],
        // PNG e non JPG: stessa dimensione in pixel (1000x1000, e non si puo'
        // alzare -- create-task non ha nessun parametro di larghezza, i
        // parametri accettati sono solo variant_ids, files, format, options,
        // option_groups e product_options), ma senza gli aloni della
        // compressione attorno alle volute dorate, che e' dove si notano.
        format: 'png',
      }),
    });
    if (!createRes.ok) {
      const text = await createRes.text();
      throw new Error('Printful create-task error (' + createRes.status + '): ' + text);
    }
    const created = await createRes.json();
    const taskKey = created.result && created.result.task_key;
    if (!taskKey) throw new Error('Nessun task_key restituito da Printful');

    let mockups = [];
    for (let attempt = 0; attempt < PRINTFUL_POLL_ATTEMPTS && mockups.length === 0; attempt++) {
      await new Promise(function (r) { setTimeout(r, PRINTFUL_POLL_DELAY_MS); });
      const pollRes = await fetch('https://api.printful.com/mockup-generator/task?task_key=' + taskKey, {
        headers: { Authorization: 'Bearer ' + PRINTFUL_API_KEY, 'X-PF-Store-Id': String(PRINTFUL_STORE_ID) },
      });
      if (!pollRes.ok) continue;
      const polled = await pollRes.json();
      const status = polled.result && polled.result.status;
      if (status === 'completed') {
        // Ogni voce di "mockups" ha l'inquadratura principale in mockup_url e
        // le altre in extra[] (piegato, indossato, di lato -- dipende dal
        // catalogo). Prima tenevamo solo la prima e i prodotti EU restavano con
        // una foto sola, contro le otto dei Printify. Ora si prendono tutte, in
        // ordine: prima le principali, poi le aggiuntive.
        var principali = [], aggiuntive = [];
        (polled.result.mockups || []).forEach(function (m) {
          if (m.mockup_url) principali.push(m.mockup_url);
          (m.extra || []).forEach(function (e) { if (e && e.url) aggiuntive.push(e.url); });
        });
        mockups = principali.concat(aggiuntive);
      } else if (status === 'failed') {
        throw new Error('Printful mockup task failed: ' + (polled.result.error || 'nessun motivo indicato'));
      }
    }
    if (mockups.length === 0) {
      return res.status(504).json({ error: 'Anteprima non pronta, riprova tra qualche secondo' });
    }
    res.json({ images: mockups.slice(0, 4) });
  } catch (err) {
    // Il messaggio per il cliente resta quello, generico e in italiano: e'
    // quello che il tema mostra. "detail" e' in piu', per chi guarda la
    // risposta con gli strumenti da sviluppatore -- prima il motivo vero
    // esisteva solo nei log di Render, e per capire perche' il guinzaglio non
    // generava mockup e' servito ricostruirlo dal catalogo pubblico. Sono
    // messaggi di Printful tipo "Placement 'front' is not valid": nessun
    // segreto, nessuna chiave, tagliati a 300 caratteri.
    console.error('Errore generate-mockup (Printful):', err.message);
    res.status(502).json({
      error: 'Impossibile generare l\'anteprima da Printful',
      detail: String(err.message || '').slice(0, 300),
    });
  }
}

app.post('/generate-mockup', limitePerIp, express.json(), async function (req, res) {
  const body = req.body || {};
  const type = String(body.product_type || '').toUpperCase();
  const baseImageId = body.base_image_id;
  const compositeImageId = body.composite_image_id;
  // URL a piena risoluzione dello stesso composito (vedi urlCompositoValida):
  // opzionale, serve solo ai tipi EU. Il percorso Printify qui sotto non la
  // usa -- la' il composito viaggia gia' per id, dentro il loro sistema.
  const compositeImageUrl = body.composite_image_url;
  // ROUND 17 — retro opzionale (medaglietta doppio lato): se presente, il
  // prodotto temporaneo per il mockup include anche il placeholder "back",
  // cosi' l'anteprima reale mostra entrambi i lati. Assente per tutti gli altri
  // prodotti/lati singoli: comportamento di oggi invariato.
  const backBaseImageId = body.back_base_image_id;
  const backCompositeImageId = body.back_composite_image_id;

  if (!compositeImageId) {
    return res.status(400).json({ error: 'composite_image_id mancante' });
  }
  // Tipi EU (fornitore Printful): stesso payload del client, ma un flusso di
  // generazione mockup completamente diverso (vedi PRINTFUL_MOCKUP_CONFIG
  // sopra) -- nessuna delle regole/pulizia del prodotto temporaneo Printify
  // qui sotto si applica a questi tipi.
  if (PRINTFUL_MOCKUP_CONFIG[type]) {
    return generatePrintfulMockup(PRINTFUL_MOCKUP_CONFIG[type], compositeImageId, res, compositeImageUrl);
  }
  if (!PRINTIFY_SHOP_ID) {
    return res.status(500).json({ error: 'PRINTIFY_SHOP_ID non configurato sul server' });
  }
  if (MOCKUP_PRODUCT_TYPES.indexOf(type) === -1) {
    return res.status(400).json({ error: 'Tipo prodotto non riconosciuto' });
  }
  const blueprintId = Number(process.env[type + '_BLUEPRINT_ID']);
  const providerId = Number(process.env[type + '_PROVIDER_ID']);
  const variantId = Number(process.env[type + '_VARIANT_ID']);
  if (!blueprintId || !providerId || !variantId) {
    return res.status(500).json({ error: 'Configurazione blueprint/provider/variante mancante sul server per questo tipo' });
  }

  function buildMockupImages(baseId, compositeId) {
    const imgs = [];
    if (baseId) imgs.push({ id: baseId, x: 0.5, y: 0.5, scale: 1, angle: 0 });
    imgs.push({ id: compositeId, x: 0.5, y: 0.5, scale: 1, angle: 0 });
    return imgs;
  }
  const placeholders = [{ position: 'front', images: buildMockupImages(baseImageId, compositeImageId) }];
  if (backCompositeImageId) {
    placeholders.push({ position: 'back', images: buildMockupImages(backBaseImageId, backCompositeImageId) });
  }

  let tempProductId = null;
  try {
    const createRes = await fetch('https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/products.json', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: 'Perla - Anteprima temporanea',
        description: 'Prodotto generato automaticamente solo per mostrare un\'anteprima al cliente. Viene cancellato in automatico subito dopo.',
        blueprint_id: blueprintId,
        print_provider_id: providerId,
        variants: [{ id: variantId, price: 100, is_enabled: true }],
        print_areas: [{ variant_ids: [variantId], placeholders: placeholders }],
        tags: ['perla-preview-temp'],
      }),
    });
    if (!createRes.ok) {
      const text = await createRes.text();
      throw new Error('Printify create error (' + createRes.status + '): ' + text);
    }
    const created = await createRes.json();
    tempProductId = created.id;

    // Il mockup viene generato lato Printify in modo asincrono: si interroga
    // il prodotto finche' le immagini non sono pronte o si arriva al limite
    // di tentativi (~9 secondi totali).
    let mockupImages = (created.images || []).map(function (img) { return img.src; }).filter(Boolean);
    for (let attempt = 0; attempt < MOCKUP_POLL_ATTEMPTS && mockupImages.length === 0; attempt++) {
      await new Promise(function (r) { setTimeout(r, MOCKUP_POLL_DELAY_MS); });
      const checkRes = await fetch('https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/products/' + tempProductId + '.json', {
        headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY },
      });
      if (checkRes.ok) {
        const checked = await checkRes.json();
        mockupImages = (checked.images || []).map(function (img) { return img.src; }).filter(Boolean);
      }
    }

    if (mockupImages.length === 0) {
      return res.status(504).json({ error: 'Anteprima non pronta, riprova tra qualche secondo' });
    }
    res.json({ images: mockupImages.slice(0, 4) });
  } catch (err) {
    console.error('Errore generate-mockup:', err.message);
    res.status(502).json({ error: 'Impossibile generare l\'anteprima da Printify' });
  } finally {
    // FIX "schermo blu, l'anteprima non si apre": cancellare il prodotto
    // temporaneo SUBITO dopo aver risposto rompeva gli URL delle immagini
    // mockup nel giro di pochi secondi (sono servite da Printify legate
    // all'esistenza del prodotto) - la miniatura faceva in tempo a caricarsi
    // una volta, ma cliccandola per ingrandirla il link era gia' morto.
    // Il prodotto resta comunque dedicato a QUESTA sola richiesta (creato
    // sopra, mai riusato tra clienti diversi: l'unico motivo per cui va
    // cancellato e' non lasciare scorie nel catalogo Printify, non la
    // privacy tra clienti) quindi possiamo ritardare la cancellazione senza
    // reintrodurre il rischio che due clienti vedano la foto l'uno dell'altro.
    if (tempProductId) {
      const idToDelete = tempProductId;
      setTimeout(function () {
        fetch('https://api.printify.com/v1/shops/' + PRINTIFY_SHOP_ID + '/products/' + idToDelete + '.json', {
          method: 'DELETE',
          headers: { Authorization: 'Bearer ' + PRINTIFY_API_KEY },
        }).catch(function (cleanupErr) {
          console.error('Errore cancellazione prodotto temporaneo:', cleanupErr.message);
        });
      }, 10 * 60 * 1000);
    }
  }
});

// ROUND 39 -- RIMOSSO il blocco OAuth temporaneo (/embedded e
// /session-exchange, piu' le costanti OAUTH_CLIENT_ID/OAUTH_CLIENT_SECRET).
//
// Serviva a ottenere UNA VOLTA, il 2026-08-03, un token Admin API con scope di
// scrittura. Il commento originale diceva "Rimuovere a token ottenuto": dieci
// giorni dopo era ancora online, e faceva due cose gravi.
//
//   console.log('TOKEN EXCHANGE RESULT', JSON.stringify(data));
//   res.json(data);
//
// Il token Admin -- che per ammissione dello stesso commento NON SCADE --
// finiva scritto nei log di Render e restituito nella risposta HTTP. Chiunque
// avesse accesso ai log lo leggeva, per sempre.
//
// Se un domani serve rifare il giro, si fa in locale e una volta sola, non da
// una rotta pubblica lasciata accesa. E il token passato di qui va considerato
// bruciato: va rigenerato dal pannello Shopify.

app.use(function (err, req, res, next) {
  console.error('Errore upload:', err.message);
  // ROUND 39 -- il dettaglio resta nei log, al cliente va un messaggio
  // generico. Prima usciva err.message grezzo, che nei casi peggiori conteneva
  // nomi di variabili d'ambiente e risposte intere dei fornitori.
  //
  // Due eccezioni: sono errori che il cliente PUO' correggere da solo, e
  // nasconderli lo lascerebbe a fissare un fallimento senza spiegazione.
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(400).json({ error: 'Immagine troppo grande (massimo ' + MAX_UPLOAD_MB + ' MB)' });
  }
  if (err.message === 'Formato non supportato') {
    return res.status(400).json({ error: 'Formato non supportato: usa JPG, PNG o WebP' });
  }
  res.status(400).json({ error: 'Richiesta non valida' });
});

app.listen(PORT, function () {
  console.log('Servizio upload foto in ascolto sulla porta ' + PORT);
});
