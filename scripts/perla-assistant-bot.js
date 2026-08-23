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

const { GEMINI_API_KEY, PORT = 3002, ALLOWED_ORIGIN = 'https://perlaitaly.com' } = process.env;

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
- Dietro questa chat ci sono persone vere (Emanuele e Nicola). Se il cliente chiede di parlare con
  qualcuno, oppure se la domanda riguarda un ordine specifico (numero d'ordine, stato reale della
  spedizione, un problema con un pezzo ricevuto), NON inventare: digli in una frase che apri la
  chat con il team e che gli rispondono da li'. In quel caso, e solo in quel caso, chiudi il
  messaggio con il segnale [PERSONA] su una riga a parte.
- Se non conosci la risposta ma non serve una persona, dillo semplicemente invece di inventare.
- Non inventare mai policy, prezzi o tempi diversi da quelli sopra.
- Rispondi in massimo 3 frasi.`;

// ROUND 46 -- PASSAGGIO A UNA PERSONA
//
// Chi scrive "voglio parlare con qualcuno" ha gia' deciso che il robot non gli
// basta: rispondergli con un altro paragrafo di robot lo fa andare via. Prima
// qui c'era solo un invito a mandare un'email, cioe' una risposta domani a una
// domanda di adesso.
//
// Il riconoscimento e' doppio di proposito, e i due strati coprono buchi
// diversi. Il modello capisce le richieste storte ("c'e' nessuno li?", "mi
// passi un umano"), ma e' un modello: ogni tanto si dimentica il segnale.
// L'elenco di parole non si dimentica niente, ma non capisce le frasi che non
// ha previsto. Insieme sbagliano molto meno di ognuno dei due.
//
// Se sbagliano lo stesso, sbagliano dalla parte giusta: aprire la chat con una
// persona quando non serviva costa un clic al cliente, non aprirla quando
// serviva costa l'ordine.
const CHIEDE_UNA_PERSONA = new RegExp([
  'parlare con (un|una|qualcun|il|la)', 'con un operator', 'operatore',
  'assistenza client', 'servizio client', 'un umano', 'una persona (vera|reale)',
  'persona vera', 'essere umano',
  // "c'e' qualcuno?" si scrive in almeno quattro modi -- c'e, c'e', ce, c'e' --
  // piu' le versioni con l'accento al posto dell'apostrofo. La prima stesura
  // ne copriva due, ed erano le due che scrive chi ha la tastiera inglese.
  "c\\s*['’`]?\\s*(e|è)\\s*['’`]?\\s*(qualcuno|nessuno)",
  '(voglio|vorrei|posso|potrei) parlare', 'mi passi',
  'speak (to|with) (a|an|someone)', 'talk to (a|an|someone|somebody)',
  'real person', 'human (being|agent|support)?', 'customer (service|support)',
  'live (chat|agent)', 'is anyone there',
].join('|'), 'i');

const SEGNALE = /\s*\[PERSONA\]\s*/i;

// Usata solo quando il modello non risponde: e' la frase che il modello
// direbbe, scritta a mano una volta sola.
const RISPOSTA_PERSONA = 'Ti apro subito la chat con noi: scrivi pure li\', ' +
  'ti risponde una persona del team.';

// ROUND 47 -- cosa si dice quando il modello non risponde affatto.
//
// Misurato in produzione il 23 agosto: 7 domande su 10 tornavano
// "Servizio AI non disponibile" per un 503 UNAVAILABLE di Google ("this model
// is currently experiencing high demand"). Il tema, davanti a quell'errore,
// mostra "Non riesco a risponderti proprio ora. Scrivici via email.": un
// vicolo cieco proprio mentre il cliente sta chiedendo qualcosa. Quel
// messaggio non porta da nessuna parte, e l'email e' il canale piu' lento che
// abbiamo.
//
// Adesso il fallimento del modello degrada verso la persona invece che verso
// il nulla: si risponde 200 con un testo utile e apri_chat, e il tema apre la
// chat come per una richiesta esplicita. Il guasto resta visibile dove serve
// -- nei log di Render -- non davanti al cliente.
const RISPOSTA_AI_GIU = 'In questo momento non riesco a rispondere da solo. ' +
  'Ti apro la chat con noi: scrivi pure li\', ti risponde una persona del team.';

const app = express();
app.use(express.json({ limit: '10kb' }));

// Render sta dietro un proxy: senza questo req.ip e' l'indirizzo del proxy e
// il limitatore conterebbe tutti i visitatori come uno solo.
app.set('trust proxy', 1);

// Express annuncia se stesso in ogni risposta con X-Powered-By: informazione
// gratis per chi cerca bersagli con una certa versione.
app.disable('x-powered-by');

app.use(function (req, res, next) {
  res.header('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  // ROUND 40 -- vedi il commento esteso in perla-upload-endpoint.js
  res.header('X-Content-Type-Options', 'nosniff');
  res.header('X-Frame-Options', 'DENY');
  res.header('Referrer-Policy', 'no-referrer');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ROUND 39 -- LIMITE DI RICHIESTE PER INDIRIZZO.
//
// Questa rotta inoltra a Gemini: ogni chiamata consuma quota dell'account.
// Era pubblica, con CORS aperto a chiunque e nessun limite -- un ciclo da
// qualsiasi sito bastava a esaurirla, e l'assistente sul negozio smetteva di
// rispondere ai clienti veri. Dieci domande al minuto sono piu' di quante ne
// faccia una persona; chi ne fa di piu' non e' una persona.
const RATE_FINESTRA_MS = 60 * 1000;
const RATE_MAX = Number(process.env.RATE_MAX_AL_MINUTO || 10);
const rateVisite = new Map();

function limitePerIp(req, res, next) {
  const ora = Date.now();
  const ip = req.ip || 'sconosciuto';
  const recenti = (rateVisite.get(ip) || []).filter(function (t) { return ora - t < RATE_FINESTRA_MS; });
  if (recenti.length >= RATE_MAX) {
    res.set('Retry-After', String(Math.ceil(RATE_FINESTRA_MS / 1000)));
    return res.status(429).json({ error: 'Troppe domande di fila, riprova fra un minuto' });
  }
  recenti.push(ora);
  rateVisite.set(ip, recenti);
  if (rateVisite.size > 5000) {
    for (const [chiave, tempi] of rateVisite) {
      if (!tempi.length || ora - tempi[tempi.length - 1] > RATE_FINESTRA_MS) rateVisite.delete(chiave);
    }
  }
  next();
}

app.post('/assistant/ask', limitePerIp, async function (req, res) {
  const message = (req.body && req.body.message || '').toString().trim().slice(0, 500);
  if (!message) {
    return res.status(400).json({ error: 'Messaggio mancante' });
  }

  // Le parole si guardano PRIMA di chiamare il modello, e non per fretta: chi
  // ha chiesto una persona deve poterla raggiungere anche quando l'AI e' giu'.
  // Rispondere "servizio non disponibile" a "voglio parlare con qualcuno" e'
  // il momento peggiore in cui si possa lasciare solo un cliente.
  const chiedePersona = CHIEDE_UNA_PERSONA.test(message);

  try {
    const grezza = await askGemini(message);
    // Il segnale non deve MAI arrivare al cliente: si toglie dal testo e
    // diventa un campo a parte, che il tema usa per aprire la chat.
    const apriChat = chiedePersona || SEGNALE.test(grezza);
    const reply = grezza.replace(SEGNALE, ' ').trim();
    res.json({ reply: reply, apri_chat: apriChat });
  } catch (err) {
    console.error('Errore assistente AI:', err.message);
    if (chiedePersona) {
      return res.json({ reply: RISPOSTA_PERSONA, apri_chat: true });
    }
    res.json({ reply: RISPOSTA_AI_GIU, apri_chat: true });
  }
});

// ROUND 47 -- il 503 di Google si riprova, non si subisce.
//
// "This model is currently experiencing high demand" e' per definizione
// temporaneo, e infatti su dieci domande identiche tre passavano e sette no.
// Una singola chiamata secca trasformava un intoppo di un secondo nel
// fallimento della conversazione.
//
// Due leve, in quest'ordine:
//   1. si riprova lo stesso modello dopo una pausa breve;
//   2. si passa a un modello diverso, che ha capacita' sua e quasi mai e'
//      sovraccarico nello stesso istante.
//
// I tempi sono tarati su una chat, non su un lavoro in coda: il cliente sta
// guardando il puntino che lampeggia. Con questa scaletta il caso peggiore
// resta sotto gli 8 secondi, e chi non riceve risposta viene comunque passato
// a una persona (vedi RISPOSTA_AI_GIU) invece di leggere un errore.
const TENTATIVI = [
  { modello: 'gemini-flash-latest', attesaPrima: 0 },
  { modello: 'gemini-flash-latest', attesaPrima: 350 },
  { modello: 'gemini-flash-lite-latest', attesaPrima: 0 },
  { modello: 'gemini-flash-lite-latest', attesaPrima: 900 },
];
const BUDGET_MS = 8000;

// 429 = troppe richieste, 5xx = problema loro: tutti passeggeri, si riprova.
// 400/401/403 no: chiave sbagliata o richiesta malformata non guariscono
// insistendo, e insistere ruberebbe secondi al cliente per niente.
// 404 e' il caso di mezzo -- modello ritirato: inutile ripetere lo stesso
// nome, ha senso solo passare al successivo.
function transitorio(stato) {
  return stato === 429 || stato >= 500;
}

function pausa(ms) {
  return new Promise(function (r) { setTimeout(r, ms); });
}

async function askGemini(message) {
  const scadenza = Date.now() + BUDGET_MS;
  let ultimoErrore = null;
  let modelloMorto = null;

  for (const tentativo of TENTATIVI) {
    if (tentativo.modello === modelloMorto) continue;
    if (tentativo.attesaPrima) {
      if (Date.now() + tentativo.attesaPrima >= scadenza) break;
      await pausa(tentativo.attesaPrima);
    }
    if (Date.now() >= scadenza) break;

    try {
      return await unaChiamata(tentativo.modello, message);
    } catch (err) {
      ultimoErrore = err;
      if (err.stato === 404) { modelloMorto = tentativo.modello; continue; }
      if (err.stato && !transitorio(err.stato)) throw err;
    }
  }

  throw ultimoErrore || new Error('Gemini non raggiungibile entro il tempo utile');
}

async function unaChiamata(modello, message) {
  const url =
    'https://generativelanguage.googleapis.com/v1beta/models/' + modello +
    ':generateContent?key=' + GEMINI_API_KEY;

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
    const err = new Error('Gemini API error (' + response.status + ') su ' +
      modello + ': ' + text);
    err.stato = response.status;   // askGemini decide se vale la pena riprovare
    throw err;
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
