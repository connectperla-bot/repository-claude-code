'use strict';

// ROUND 45 -- gli id e le URL che arrivano da fuori.
//
// Due strade portano input non fidato dentro chiamate autenticate ai fornitori:
//
//   1. il corpo JSON di /generate-mockup, che e' una rotta pubblica;
//   2. le proprieta' _Personalizzazione della riga d'ordine, che sono
//      compilate dal FORM DEL CARRELLO, cioe' dal browser del cliente. La
//      firma HMAC del webhook prova che il messaggio viene da Shopify, non
//      che il contenuto sia onesto.
//
// Prima di questo giro, in entrambi i casi il valore finiva dritto dentro una
// URL chiamata con la chiave API della titolare, oppure dentro il file di
// stampa. Qui si verifica che non succeda piu'.

const assert = require('assert');
const printful = require('../scripts/providers/printful-client.js');

let fatte = 0;
function prova(nome, fn) {
  try {
    fn();
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}
async function provaAsync(nome, fn) {
  try {
    await fn();
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

const CLOUD = 'qarb7ouo';
const NOSTRA = 'https://res.cloudinary.com/' + CLOUD + '/image/upload/v1/perla-composito-abc123.jpg';

console.log('\nIl file di stampa non lo sceglie il cliente');

async function main() {
  // Rete di sicurezza: nessuna chiamata di rete deve partire da questi casi.
  const fetchVero = global.fetch;
  let chiamate = [];
  global.fetch = async function (url, opts) {
    chiamate.push(String(url));
    return { ok: true, status: 200, json: async function () { return {}; } };
  };

  await provaAsync('una URL su un Cloudinary altrui non diventa il file di stampa', async function () {
    chiamate = [];
    const lato = {
      printify_image_url: 'https://res.cloudinary.com/account-attaccante/image/upload/v1/x.png',
      printify_image_id: 'abc123',
    };
    const url = await printful.__test.urlDelComposito(lato, { CLOUDINARY_CLOUD_NAME: CLOUD });
    assert.notStrictEqual(url, lato.printify_image_url,
      'la URL di un account estraneo non deve mai essere restituita');
  });

  await provaAsync('un host che finge di essere Cloudinary viene rifiutato', async function () {
    for (const cattiva of [
      'https://res.cloudinary.com.attaccante.it/' + CLOUD + '/image/upload/v1/x.png',
      'https://res.cloudinary.com@evil.com/' + CLOUD + '/image/upload/v1/x.png',
      'http://res.cloudinary.com/' + CLOUD + '/image/upload/v1/x.png',
      'https://res.cloudinary.com/' + CLOUD + '/image/fetch/https://evil.com/x.png',
      'https://res.cloudinary.com/' + CLOUD + '/image/upload/l_fetch:aHR0cHM6Ly9ldmlsLmNvbQ==/x.png',
    ]) {
      const url = await printful.__test.urlDelComposito(
        { printify_image_url: cattiva }, { CLOUDINARY_CLOUD_NAME: CLOUD });
      assert.notStrictEqual(url, cattiva, 'accettata una URL che non doveva passare: ' + cattiva);
    }
  });

  await provaAsync('la nostra URL invece passa', async function () {
    const url = await printful.__test.urlDelComposito(
      { printify_image_url: NOSTRA }, { CLOUDINARY_CLOUD_NAME: CLOUD });
    assert.strictEqual(url, NOSTRA, 'la URL sul nostro account deve essere usata');
  });

  console.log('\nGli id non possono cambiare endpoint');

  await provaAsync('un id con ../ non fa partire nessuna chiamata a Printify', async function () {
    chiamate = [];
    const url = await printful.__test.urlDelComposito(
      { printify_image_id: '../shops/27790439/orders' },
      { PRINTIFY_API_KEY: 'chiave-finta' });
    assert.strictEqual(url, null, 'non deve risolvere niente');
    assert.deepStrictEqual(chiamate, [],
      'nessuna chiamata doveva partire, invece: ' + chiamate.join(', '));
  });

  global.fetch = fetchVero;
}

main().then(function () {
  prova('la funzione di validazione e\' esportata per i test', function () {
    assert.strictEqual(typeof printful.__test.urlDelComposito, 'function');
  });
  console.log('\n' + fatte + ' verifiche superate.' +
    (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
});
