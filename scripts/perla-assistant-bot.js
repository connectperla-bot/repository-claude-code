'use strict';

// Servizio di risposta reale per l'assistente del sito (bolla in basso a destra).
// Riceve la domanda del cliente e risponde usando un modello linguistico gratuito
// (Google Gemini - gemini-flash-latest, piano gratuito senza carta di credito:
// https://aistudio.google.com/apikey).
// Va avviato ed ospitato separatamente (non viene eseguito dal file .bat).
//
// Configurazione: copia config/printify.env.example (o crea config/assistant.local.env)
// e imposta GEMINI_API_KEY, poi caricalo nell'ambiente prima di avviare.

const express = require('express');

const { GEMINI_API_KEY, PORT = 3002, ALLOWED_ORIGIN = '*' } = process.env;

if (!GEMINI_API_KEY) {
  console.error('Variabile GEMINI_API_KEY mancante. Ottieni una chiave gratuita su https://aistudio.google.com/apikey');
  process.exit(1);
}

// Conoscenza di base del negozio: tienila aggiornata se cambiano politiche reali.
const SYSTEM_PROMPT = `Sei l'assistente virtuale del negozio "Perla Italia", che vende accessori per cani
(collari, bandane, medagliette, ciotole), anche personalizzabili con nome del pet e foto del cliente.
Rispondi SEMPRE in italiano, in modo breve, cordiale e concreto.
Regole:
- Spedizioni: Italia 4-8 giorni, Europa e USA 5-12 giorni. Tracciamento sempre incluso via email.
- Resi: 30 giorni dalla consegna.
- Pagamenti: carte (Visa, Mastercard, Amex), PayPal, Apple Pay, Google Pay. Anche a rate con Scalapay/Klarna.
- Prodotti personalizzabili: nome del pet ricamato/stampato, e in alcuni prodotti foto caricata dal cliente.
- Se non conosci la risposta, o riguarda un ordine specifico (numero d'ordine, stato spedizione reale),
  invita gentilmente il cliente a scrivere via email invece di inventare informazioni. Non menzionare
  mai WhatsApp: il canale di contatto per le richieste che non sai gestire e' solo l'email.
- Non inventare mai policy, prezzi o tempi diversi da quelli sopra.
- Rispondi in massimo 3 frasi.`;

const app = express();
app.use(express.json({ limit: '10kb' }));

app.use(function (req, res, next) {
  res.header('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.post('/assistant/ask', async function (req, res) {
  const message = (req.body && req.body.message || '').toString().trim().slice(0, 500);
  if (!message) {
    return res.status(400).json({ error: 'Messaggio mancante' });
  }

  try {
    const reply = await askGemini(message);
    res.json({ reply: reply });
  } catch (err) {
    console.error('Errore assistente AI:', err.message);
    res.status(502).json({ error: 'Servizio AI non disponibile' });
  }
});

async function askGemini(message) {
  const url =
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=' +
    GEMINI_API_KEY;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents: [{ role: 'user', parts: [{ text: message }] }],
      generationConfig: {
        maxOutputTokens: 300,
        temperature: 0.4,
        thinkingConfig: { thinkingBudget: 0 },
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error('Gemini API error (' + response.status + '): ' + text);
  }

  const data = await response.json();
  const reply = data.candidates && data.candidates[0] && data.candidates[0].content
    && data.candidates[0].content.parts && data.candidates[0].content.parts[0]
    && data.candidates[0].content.parts[0].text;

  if (!reply) throw new Error('Risposta vuota dal modello');
  return reply.trim();
}

app.listen(PORT, function () {
  console.log('Assistente AI in ascolto sulla porta ' + PORT);
});
