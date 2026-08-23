'use strict';

// Quando il cliente chiede una persona, l'assistente deve passare la mano.
//
// PERCHE' COSI' E NON A UNITA'
// Come tests/sicurezza-endpoint.test.js: il servizio viene avviato davvero e
// interrogato via HTTP. Quello che conta non e' che una funzione riconosca una
// frase, ma che la RISPOSTA che arriva al tema porti apri_chat, perche' e'
// quel campo che apre la chat con gli admin.
//
// La chiave Gemini qui e' finta di proposito, e non e' una limitazione: e'
// esattamente il caso peggiore. Se il modello non risponde e il cliente ha
// chiesto una persona, deve comunque essere passato a una persona -- dirgli
// "servizio non disponibile" in quel momento e' il modo migliore per perderlo.
// Con la chiave finta ogni chiamata al modello fallisce, quindi ogni prova
// qui dentro esercita proprio quel ramo.
//
// Uso:  node tests/passaggio-a-persona.test.js

const assert = require('assert');
const { spawn } = require('child_process');
const path = require('path');

const PORTA = 3401;
const BASE = 'http://127.0.0.1:' + PORTA;
const SCRIPT = path.join(__dirname, '..', 'scripts', 'perla-assistant-bot.js');

let passati = 0;
async function prova(descrizione, fn) {
  try {
    await fn();
    passati++;
    console.log('  ok   ' + descrizione);
  } catch (err) {
    console.error('  FALLITO   ' + descrizione + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

function attendi(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

async function chiedi(messaggio) {
  const r = await fetch(BASE + '/assistant/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: messaggio }),
  });
  return { stato: r.status, corpo: await r.json().catch(function () { return {}; }) };
}

async function aspettaAvvio(tentativi) {
  for (let i = 0; i < tentativi; i++) {
    try {
      await fetch(BASE + '/assistant/ask', { method: 'POST' });
      return true;
    } catch (e) {
      await attendi(250);
    }
  }
  return false;
}

(async function () {
  console.log('\nPassaggio a una persona');

  const servizio = spawn(process.execPath, [SCRIPT], {
    env: Object.assign({}, process.env, {
      PORT: String(PORTA),
      GEMINI_API_KEY: 'chiave-finta-per-il-test',
      RATE_MAX_AL_MINUTO: '200',
    }),
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  let errori = '';
  servizio.stderr.on('data', function (b) { errori += b.toString(); });

  try {
    if (!await aspettaAvvio(40)) throw new Error('il servizio non si e\' avviato\n' + errori);

    await prova('"voglio parlare con una persona" apre la chat', async function () {
      const r = await chiedi('voglio parlare con una persona');
      assert.strictEqual(r.stato, 200, 'stato ' + r.stato);
      assert.strictEqual(r.corpo.apri_chat, true);
      assert.ok(r.corpo.reply && r.corpo.reply.length > 10, 'serve una frase, non un campo vuoto');
    });

    await prova('funziona anche con l\'accento: "c\'è qualcuno?"', async function () {
      const r = await chiedi('ciao, cè qualcuno?');
      assert.strictEqual(r.corpo.apri_chat, true);
    });

    await prova('e in inglese', async function () {
      const r = await chiedi('can I talk to someone please');
      assert.strictEqual(r.corpo.apri_chat, true);
    });

    // ROUND 47 -- questa prova diceva l'opposto, e il 23 agosto la produzione
    // ha spiegato perche' era sbagliata: sette domande su dieci tornavano
    // "Servizio AI non disponibile" per un 503 di Google, e il tema mostrava
    // "Scrivici via email" -- un vicolo cieco. Il ripiego giusto quando il
    // modello tace non e' l'errore: e' la persona.
    //
    // Con la chiave finta il modello non risponde mai, quindi qui si esercita
    // sempre quel ramo. Cio' che resta distinguibile, e che conta, e' che le
    // due strade dicano cose diverse: chi ha chiesto una persona non deve
    // sentirsi rispondere che l'assistente e' guasto.
    await prova('se il modello tace, anche una domanda normale passa a una persona', async function () {
      const r = await chiedi('quanto costa la spedizione in Italia?');
      assert.strictEqual(r.stato, 200, 'un errore secco lascia il cliente a un vicolo cieco');
      assert.strictEqual(r.corpo.apri_chat, true);
      assert.ok(/non riesco a rispondere/i.test(r.corpo.reply || ''),
        'risposta inattesa: ' + r.corpo.reply);
    });

    await prova('chi chiede una persona non sente parlare di guasti', async function () {
      const r = await chiedi('voglio parlare con una persona');
      assert.ok(/apro subito la chat/i.test(r.corpo.reply || ''),
        'risposta inattesa: ' + r.corpo.reply);
      assert.ok(!/non riesco a rispondere/i.test(r.corpo.reply || ''),
        'a chi chiede aiuto non si racconta che il bot e\' rotto');
    });

    // I nuovi tentativi servono per il 503 ("alta domanda"), che passa da solo.
    // Una chiave sbagliata e' un 400 e non guarisce insistendo: se finisse
    // nella scaletta dei tentativi il cliente aspetterebbe otto secondi per
    // ricevere comunque niente. Qui la chiave e' finta, quindi il tempo di
    // risposta e' la misura diretta che il 400 non viene ripetuto.
    await prova('una chiave sbagliata non fa aspettare il cliente', async function () {
      const inizio = Date.now();
      await chiedi('quanto costa la spedizione in Italia?');
      const durata = Date.now() - inizio;
      assert.ok(durata < 3000, 'ha impiegato ' + durata + ' ms: sta riprovando un errore che non passa');
    });

    await prova('nessun segnale [PERSONA] finisce sotto gli occhi del cliente', async function () {
      const r = await chiedi('mi passi un operatore');
      assert.ok(!/\[PERSONA\]/i.test(r.corpo.reply || ''), 'segnale visibile: ' + r.corpo.reply);
    });

    await prova('messaggio vuoto resta un errore di richiesta', async function () {
      const r = await chiedi('   ');
      assert.strictEqual(r.stato, 400);
    });
  } finally {
    servizio.kill();
  }

  console.log('\n' + passati + ' verifiche superate.\n');
})();
