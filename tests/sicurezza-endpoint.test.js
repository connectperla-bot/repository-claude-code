'use strict';

// Verifica le protezioni di scripts/perla-upload-endpoint.js avviandolo
// davvero e interrogandolo via HTTP.
//
// PERCHE' COSI' E NON A UNITA'
// Le protezioni sono middleware Express: contano solo se sono montate sulle
// rotte giuste, nell'ordine giusto. Un test che chiama la funzione da sola
// direbbe che il codice funziona anche se qualcuno domani si dimentica di
// applicarlo a /upload. Qui si parla al servizio come ci parlerebbe un
// estraneo.
//
// Nessuna chiamata esce verso Printify o Cloudinary: le credenziali sono
// finte e ogni caso provato viene rifiutato PRIMA della chiamata esterna.
//
// Uso:  node tests/sicurezza-endpoint.test.js

const assert = require('assert');
const { spawn } = require('child_process');
const path = require('path');

const PORTA = 3399;
const BASE = 'http://127.0.0.1:' + PORTA;
const SCRIPT = path.join(__dirname, '..', 'scripts', 'perla-upload-endpoint.js');

let passati = 0;
async function prova(descrizione, fn) {
  try {
    await fn();
    passati++;
    console.log('  ok   ' + descrizione);
  } catch (err) {
    console.error('  FALLITO   ' + descrizione);
    console.error('        ' + err.message);
    process.exitCode = 1;
  }
}

function attendi(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

async function aspettaAvvio(tentativi) {
  for (let i = 0; i < tentativi; i++) {
    try {
      await fetch(BASE + '/pattern-source');
      return true;
    } catch (e) {
      await attendi(250);
    }
  }
  return false;
}

async function main() {
  const servizio = spawn(process.execPath, [SCRIPT], {
    env: Object.assign({}, process.env, {
      // credenziali finte: nessun caso provato arriva a usarle
      PRINTIFY_API_KEY: 'finta-per-il-test',
      PRINTIFY_SHOP_ID: '1',
      PORT: String(PORTA),
      RATE_MAX_AL_MINUTO: '5',
      ALLOWED_ORIGIN: 'https://perlaitaly.com',
      // niente Cloudinary/Printful: il servizio avvisa e prosegue
      CLOUDINARY_CLOUD_NAME: '', CLOUDINARY_API_KEY: '', CLOUDINARY_API_SECRET: '',
      PRINTFUL_API_KEY: '', PRINTFUL_STORE_ID: '',
    }),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  servizio.stdout.on('data', function () {});
  servizio.stderr.on('data', function () {});

  try {
    const su = await aspettaAvvio(40);
    assert.ok(su, 'il servizio non si e\' avviato sulla porta ' + PORTA);

    console.log('\nValidazione di printify_product_id');

    // Il caso che prima leggeva dati dell'account Printify: l'id finiva dentro
    // l'URL chiamato con la nostra chiave, e "../../../uploads" lo dirottava
    // su un endpoint diverso.
    await prova('un id con ../ viene rifiutato', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=' + encodeURIComponent('../../../uploads'));
      assert.strictEqual(r.status, 400);
      const j = await r.json();
      assert.ok(/non valido/i.test(j.error), 'messaggio inatteso: ' + j.error);
    });

    await prova('un id con lettere viene rifiutato', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=abc123');
      assert.strictEqual(r.status, 400);
    });

    await prova('un id vuoto viene rifiutato', async function () {
      const r = await fetch(BASE + '/pattern-source');
      assert.strictEqual(r.status, 400);
    });

    // Un id numerico deve SUPERARE la validazione: fallira' dopo, sulla
    // chiamata a Printify con la chiave finta, ed e' esattamente cio' che
    // deve succedere. Se tornasse 400 avremmo rotto il caso buono.
    await prova('un id numerico supera la validazione', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=123456');
      assert.notStrictEqual(r.status, 400, 'un id valido non deve essere rifiutato');
    });

    console.log('\nRotte OAuth temporanee rimosse');

    await prova('/session-exchange non esiste piu\'', async function () {
      const r = await fetch(BASE + '/session-exchange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: 'qualsiasi' }),
      });
      assert.strictEqual(r.status, 404);
    });

    await prova('/embedded non esiste piu\'', async function () {
      const r = await fetch(BASE + '/embedded');
      assert.strictEqual(r.status, 404);
    });

    console.log('\nCORS');

    await prova('l\'origine ammessa e\' il negozio, non "*"', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=1');
      assert.strictEqual(r.headers.get('access-control-allow-origin'), 'https://perlaitaly.com');
    });

    console.log('\nIntestazioni di sicurezza');

    // Si guardano le intestazioni della risposta VERA, non il codice: e' l'unico
    // modo di accorgersi se un middleware smette di essere applicato.
    await prova('nosniff, DENY e no-referrer sono presenti', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=1');
      assert.strictEqual(r.headers.get('x-content-type-options'), 'nosniff');
      assert.strictEqual(r.headers.get('x-frame-options'), 'DENY');
      assert.strictEqual(r.headers.get('referrer-policy'), 'no-referrer');
    });

    await prova('il servizio non annuncia piu\' Express', async function () {
      const r = await fetch(BASE + '/pattern-source?printify_product_id=1');
      assert.strictEqual(r.headers.get('x-powered-by'), null,
        'X-Powered-By c\'e\' ancora: app.disable non e\' stato applicato');
    });

    console.log('\nLimite di richieste');

    // RATE_MAX_AL_MINUTO=5 in questo test: la sesta deve essere respinta.
    await prova('oltre il limite si riceve 429 con Retry-After', async function () {
      let ultimo = null;
      for (let i = 0; i < 12; i++) {
        ultimo = await fetch(BASE + '/pattern-source?printify_product_id=' + (900000 + i));
        if (ultimo.status === 429) break;
      }
      assert.strictEqual(ultimo.status, 429, 'il limite non ha mai bloccato');
      assert.ok(ultimo.headers.get('retry-after'), 'manca l\'intestazione Retry-After');
    });

    console.log('\n' + passati + ' verifiche superate.' + (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
  } finally {
    servizio.kill();
  }
}

main().catch(function (err) {
  console.error('Errore nel test:', err.message);
  process.exit(1);
});
