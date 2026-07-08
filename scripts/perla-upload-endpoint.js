'use strict';

// Servizio di appoggio: riceve la foto caricata dal cliente sul prodotto e la
// carica direttamente su Printify (Uploads API). Restituisce l'id immagine
// Printify (serve per creare l'ordine) e un URL di anteprima ospitato da Printify.
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
// Configurazione: copia config/printify.env.example in config/printify.local.env,
// inserisci PRINTIFY_API_KEY e caricalo nell'ambiente prima di avviare.

const express = require('express');
const multer = require('multer');

const { PRINTIFY_API_KEY, PORT = 3001, MAX_UPLOAD_MB = 10, ALLOWED_ORIGIN = '*' } = process.env;

if (!PRINTIFY_API_KEY) {
  console.error('Variabile PRINTIFY_API_KEY mancante: vedi config/printify.env.example');
  process.exit(1);
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

app.use(function (err, req, res, next) {
  console.error('Errore upload:', err.message);
  res.status(400).json({ error: err.message });
});

app.listen(PORT, function () {
  console.log('Servizio upload foto in ascolto sulla porta ' + PORT);
});
