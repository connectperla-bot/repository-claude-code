'use strict';

// Servizio di appoggio: riceve la foto caricata dal cliente sul prodotto e la
// carica direttamente su Printify (Uploads API). Restituisce l'id immagine
// Printify (serve per creare l'ordine) e un URL di anteprima ospitato da Printify.
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
// Configurazione: copia config/printify.env.example in config/printify.local.env,
// inserisci PRINTIFY_API_KEY e caricalo nell'ambiente prima di avviare.

const express = require('express');
const multer = require('multer');

const { PRINTIFY_API_KEY, PRINTIFY_SHOP_ID, PORT = 3001, MAX_UPLOAD_MB = 10, ALLOWED_ORIGIN = '*' } = process.env;

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

app.use(function (req, res, next) {
  res.header('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.post('/upload', upload.single('photo'), async function (req, res) {
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
    res.json({ id: data.id, url: data.preview_url });
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

app.get('/pattern-source', async function (req, res) {
  const productId = String(req.query.printify_product_id || '').trim();
  if (!productId) {
    return res.status(400).json({ error: 'printify_product_id mancante' });
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

app.post('/generate-mockup', express.json(), async function (req, res) {
  const body = req.body || {};
  const type = String(body.product_type || '').toUpperCase();
  const baseImageId = body.base_image_id;
  const compositeImageId = body.composite_image_id;

  if (!compositeImageId) {
    return res.status(400).json({ error: 'composite_image_id mancante' });
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

  const images = [];
  if (baseImageId) images.push({ id: baseImageId, x: 0.5, y: 0.5, scale: 1, angle: 0 });
  images.push({ id: compositeImageId, x: 0.5, y: 0.5, scale: 1, angle: 0 });

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
        print_areas: [{ variant_ids: [variantId], placeholders: [{ position: 'front', images: images }] }],
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

app.use(function (err, req, res, next) {
  console.error('Errore upload:', err.message);
  res.status(400).json({ error: err.message });
});

app.listen(PORT, function () {
  console.log('Servizio upload foto in ascolto sulla porta ' + PORT);
});
