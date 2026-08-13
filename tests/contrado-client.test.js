'use strict';

// Verifica le protezioni del client Contrado PRIMA che parta una chiamata di
// rete. Sono i due casi in cui un ordine sbagliato arriverebbe al cliente
// senza che nessuno se ne accorga, quindi vanno provati davvero.
//
// Uso:  node tests/contrado-client.test.js

const assert = require('assert');
const client = require('../scripts/providers/contrado-client');

const ordine = {
  id: 123456,
  currency: 'EUR',
  email: 'cliente@esempio.it',
  shipping_address: {
    first_name: 'Giulia', last_name: 'Rossi',
    address1: 'Via Roma 1', city: 'Milano',
    province_code: 'MI', province: 'Milano',
    country_code: 'IT', country: 'Italy',
    zip: '20121', phone: '+390000000',
  },
};

const riga = { id: 99, title: 'Cuccia "Damasco"', quantity: 1, price: '129.00', sku: 'VAR-ABC' };
const config = { productId: 591879 };

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

// Raccoglie il messaggio d'errore di una fulfillOrder che DEVE fallire.
async function messaggioErrore(ctx) {
  try {
    await client.fulfillOrder(ctx);
  } catch (err) {
    return err.message;
  }
  throw new Error('la chiamata doveva fallire e invece e\' andata a buon fine');
}

async function main() {
  console.log('\nProtezioni del client Contrado');

  await prova('senza CONTRADO_API_KEY la riga non parte', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null, back: null, config,
      env: { CONTRADO_INVIO_AUTOMATICO: 'true' },
    });
    assert.ok(/CONTRADO_API_KEY/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  await prova('senza storeProductId configurato la riga non parte', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null, back: null, config: { productId: 0 },
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'true' },
    });
    assert.ok(/PRODUCT_ID/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  // Il caso peggiore: il cliente paga una personalizzazione, Contrado non
  // puo' riceverla, e senza questo controllo gli arriverebbe il design fisso.
  await prova('una riga personalizzata viene rifiutata invece di perdere il design', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga,
      front: { printify_image_id: 'abc', printify_image_url: 'https://esempio/x.jpg' },
      back: null, config,
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'true' },
    });
    assert.ok(/personalizzazione/i.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  await prova('vale anche se personalizzato solo il retro', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null,
      back: { printify_image_id: 'abc' }, config,
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'true' },
    });
    assert.ok(/personalizzazione/i.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  // Contrado non ha lo stato di bozza: se l'interruttore e' spento, la riga
  // non deve partire da sola.
  await prova('con invio automatico spento la riga non parte', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null, back: null, config,
      env: { CONTRADO_API_KEY: 'x' },
    });
    assert.ok(/CONTRADO_INVIO_AUTOMATICO/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  await prova('un valore diverso da "true" non accende l\'invio', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null, back: null, config,
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'si' },
    });
    assert.ok(/CONTRADO_INVIO_AUTOMATICO/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  await prova('codice cultura non valido viene fermato prima della chiamata', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: riga, front: null, back: null, config,
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'true', CONTRADO_CULTURE_CODE: 'it-XX' },
    });
    assert.ok(/CONTRADO_CULTURE_CODE/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  await prova('senza SKU e senza variantId di riserva la riga non parte', async function () {
    const msg = await messaggioErrore({
      order: ordine, item: { id: 99, title: 'Cuccia', quantity: 1, price: '129.00' },
      front: null, back: null, config,
      env: { CONTRADO_API_KEY: 'x', CONTRADO_INVIO_AUTOMATICO: 'true' },
    });
    assert.ok(/[Vv]ariante Contrado non determinabile/.test(msg), 'messaggio poco chiaro: ' + msg);
  });

  console.log('\n' + passati + ' verifiche superate.' + (process.exitCode ? ' CI SONO FALLIMENTI.' : ''));
}

main();
