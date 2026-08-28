'use strict';

// La spedizione che torna al cliente, e il riferimento che la rende possibile.
//
// COSA CHIUDONO QUESTE PROVE
// Due difetti trovati insieme, che erano lo stesso difetto visto da due lati.
//
// 1. Tutti e due i client mandavano `external_id: String(order.id)` -- l'id
//    dell'ORDINE -- mentre creano un ordine dallo stampatore per ogni RIGA.
//    Chi comprava un collare e un guinzaglio insieme mandava due volte lo
//    stesso external_id: Printful e Printify lo pretendono unico, quindi la
//    seconda riga veniva rifiutata e quel cliente riceveva mezzo ordine.
//
// 2. Al ritorno, l'unica cosa che lo stampatore ridice e' l'external_id. Con
//    l'id del solo ordine non si sa QUALE riga e' partita, e non si puo'
//    evadere quella e solo quella.
//
// COME SI PROVA
// Niente rete: `fetch` e' un parametro, non un globale, quindi le risposte di
// Shopify e di Printify si scrivono qui a mano. Le firme invece sono vere --
// HMAC di crypto, non finte -- perche' e' il punto dove un errore lascia
// entrare chiunque.

const assert = require('assert');
const crypto = require('crypto');
const path = require('path');

const rif = require(path.join(__dirname, '..', 'scripts', 'riferimento-ordine'));
const ev = require(path.join(__dirname, '..', 'scripts', 'evasione-shopify'));

let fatte = 0;
function prova(nome, fn) {
  try {
    const r = fn();
    if (r && typeof r.then === 'function') {
      throw new Error('prova asincrona passata a prova(): usa provaAsync');
    }
    console.log('  ok   ' + nome);
    fatte++;
  } catch (err) {
    console.log('  FALLITO   ' + nome + '\n        ' + err.message);
    process.exitCode = 1;
  }
}

const inCoda = [];
function provaAsync(nome, fn) { inCoda.push([nome, fn]); }

// ---- finto Shopify --------------------------------------------------------

// Un ordine con DUE righe personalizzate: un collare (Printful, parte dalla
// Spagna) e una medaglietta (Printify, parte dagli Stati Uniti). E' il caso
// che rompeva tutto, ed e' anche l'ordine che vogliamo di piu'.
const RIGA_COLLARE = '111';
const RIGA_MEDAGLIETTA = '222';

function fintoShopify(opz) {
  const stato = { evasioni: [], chiamate: 0 };
  const rimaste = Object.assign(
    { [RIGA_COLLARE]: 1, [RIGA_MEDAGLIETTA]: 1 },
    (opz && opz.rimaste) || {}
  );

  async function finto(url, init) {
    stato.chiamate++;
    const corpo = JSON.parse(init.body);
    if (/righeDaEvadere/.test(corpo.query)) {
      const nodi = Object.keys(rimaste)
        .filter(function (r) { return rimaste[r] > 0; })
        .map(function (r) {
          return {
            id: 'gid://shopify/FulfillmentOrder/fo-' + r,
            status: 'OPEN',
            lineItems: { nodes: [{
              id: 'gid://shopify/FulfillmentOrderLineItem/foli-' + r,
              remainingQuantity: rimaste[r],
              lineItem: { id: 'gid://shopify/LineItem/' + r },
            }] },
          };
        });
      return {
        ok: true,
        json: async function () {
          return { data: { order: { id: corpo.variables.id, name: '#1001',
            fulfillmentOrders: { nodes: nodi } } } };
        },
      };
    }
    // la mutazione
    const f = corpo.variables.f;
    stato.evasioni.push(f);
    // quello che Shopify fa davvero: la riga evasa non e' piu' da evadere
    f.lineItemsByFulfillmentOrder.forEach(function (g) {
      g.fulfillmentOrderLineItems.forEach(function (l) {
        const n = String(l.id).replace('gid://shopify/FulfillmentOrderLineItem/foli-', '');
        rimaste[n] = 0;
      });
    });
    return {
      ok: true,
      json: async function () {
        return { data: { fulfillmentCreate: {
          fulfillment: { id: 'gid://shopify/Fulfillment/f1', status: 'SUCCESS',
            trackingInfo: [] },
          userErrors: [],
        } } };
      },
    };
  }
  return { finto, stato };
}

const AMBIENTE = {
  SHOPIFY_ADMIN_TOKEN: 'token-finto',
  SHOPIFY_SHOP_DOMAIN: 'negozio.myshopify.com',
};

// ---- il riferimento -------------------------------------------------------

function testRiferimentoDiversoPerOgniRiga() {
  const ordine = { id: 5432167890 };
  const a = rif.riferimento(ordine, { id: 111 });
  const b = rif.riferimento(ordine, { id: 222 });
  assert.notStrictEqual(a, b,
    'due righe dello stesso ordine hanno lo stesso riferimento: lo stampatore ' +
    'rifiuta la seconda');
  assert.strictEqual(a, '5432167890-111');
}

function testRiferimentoSiRilegge() {
  const letto = rif.leggiRiferimento('5432167890-111');
  assert.deepStrictEqual(letto, { ordine: '5432167890', riga: '111' });
}

function testRiferimentoAltruiVieneIgnorato() {
  // Uno stampatore puo' avere ordini che non vengono da noi: non vanno letti
  // come nostri, e nemmeno fatti esplodere.
  assert.strictEqual(rif.leggiRiferimento('ORD-2024-ACME'), null);
  assert.strictEqual(rif.leggiRiferimento(''), null);
  assert.strictEqual(rif.leggiRiferimento(null), null);
  assert.strictEqual(rif.leggiRiferimento('undefined-undefined'), null);
}

function testRiferimentoSenzaIdSiFerma() {
  // "undefined-undefined" passerebbe la validazione dello stampatore e
  // tornerebbe indietro col webhook senza dire niente a nessuno.
  assert.throws(function () { rif.riferimento({ id: 5 }, {}); }, /riga/);
  assert.throws(function () { rif.riferimento({}, { id: 5 }); }, /ordine/);
}

function testIClientNonMandanoPiuLIdDelSoloOrdine() {
  // La prova che guarda il difetto dove viveva. `riferimento()` puo' essere
  // giusta quanto si vuole: se i client continuano a mandare String(order.id)
  // non serve a niente, e le prove sopra passerebbero tutte lo stesso.
  const fs = require('fs');
  for (const nome of ['printify-client.js', 'printful-client.js']) {
    const testo = fs.readFileSync(
      path.join(__dirname, '..', 'scripts', 'providers', nome), 'utf8');
    assert.ok(testo.indexOf('external_id: String(order.id)') === -1,
      nome + ' manda ancora l\'id del solo ordine: la seconda riga di un ' +
      'ordine con due articoli personalizzati verra\' rifiutata');
    assert.ok(/external_id:\s*riferimento\(order, item\)/.test(testo),
      nome + ' non usa riferimento(order, item)');
  }
}

// ---- leggere i due webhook ------------------------------------------------

function testLeggeLaSpedizionePrintful() {
  const s = ev.daPrintful({
    type: 'package_shipped',
    data: {
      order: { id: 99, external_id: '5432167890-111' },
      shipment: { carrier: 'DHL', tracking_number: 'JD0002', tracking_url: 'https://dhl/JD0002' },
    },
  });
  assert.strictEqual(s.riferimento, '5432167890-111');
  assert.strictEqual(s.corriere, 'DHL');
  assert.strictEqual(s.codice, 'JD0002');
}

function testPrintfulSenzaRiferimentoNonInventaNiente() {
  assert.strictEqual(ev.daPrintful({ type: 'package_shipped', data: { shipment: {} } }), null);
}

function testLeggeLaSpedizionePrintify() {
  // Printify NON manda l'external_id: manda il proprio id d'ordine. Questa
  // prova fissa quella differenza, perche' e' il motivo per cui esiste la
  // seconda chiamata.
  const s = ev.daPrintify({
    type: 'order:shipment:created',
    resource: {
      id: 'printify-abc',
      data: { carrier: { code: 'usps', name: 'USPS' },
        tracking_number: '9400', tracking_url: 'https://usps/9400' },
    },
  });
  assert.strictEqual(s.riferimento, null, 'Printify non lo manda: non va inventato');
  assert.strictEqual(s.idFornitore, 'printify-abc');
  assert.strictEqual(s.corriere, 'USPS');
  assert.strictEqual(s.codice, '9400');
}

// ---- le firme -------------------------------------------------------------

function testFirmaPrintifyVera() {
  const corpo = Buffer.from('{"type":"order:shipment:created"}', 'utf8');
  const giusta = crypto.createHmac('sha256', 'segreto').update(corpo).digest('hex');
  assert.ok(ev.firmaPrintifyValida(corpo, 'sha256=' + giusta, 'segreto'));
  assert.ok(ev.firmaPrintifyValida(corpo, giusta, 'segreto'), 'senza il prefisso sha256=');
}

function testFirmaPrintifyFalsaRifiutata() {
  const corpo = Buffer.from('{"type":"order:shipment:created"}', 'utf8');
  const altra = crypto.createHmac('sha256', 'altro-segreto').update(corpo).digest('hex');
  assert.ok(!ev.firmaPrintifyValida(corpo, 'sha256=' + altra, 'segreto'));
  assert.ok(!ev.firmaPrintifyValida(corpo, '', 'segreto'));
  assert.ok(!ev.firmaPrintifyValida(corpo, 'sha256=corta', 'segreto'),
    'una firma di lunghezza diversa non deve far sollevare timingSafeEqual');
}

function testSenzaSegretoNienteEntra() {
  // Se PRINTIFY_WEBHOOK_SECRET non e' impostato su Render, la porta deve
  // restare chiusa -- non aprirsi a tutti.
  const corpo = Buffer.from('{}', 'utf8');
  assert.ok(!ev.firmaPrintifyValida(corpo, 'sha256=qualunque', undefined));
  assert.ok(!ev.segretoUrlValido('qualunque', undefined));
  assert.ok(!ev.segretoUrlValido('qualunque', ''));
}

function testSegretoNellaUrl() {
  assert.ok(ev.segretoUrlValido('abc123', 'abc123'));
  assert.ok(!ev.segretoUrlValido('abc124', 'abc123'));
  assert.ok(!ev.segretoUrlValido('abc', 'abc123'));
}

// ---- evadere --------------------------------------------------------------

provaAsync('evade la riga giusta, e manda l\'email al cliente', async function () {
  const { finto, stato } = fintoShopify();
  const esito = await ev.evadiRiga(
    { riferimento: '5432167890-' + RIGA_COLLARE, corriere: 'DHL',
      codice: 'JD0002', url: 'https://dhl/JD0002' },
    AMBIENTE, finto);

  assert.strictEqual(esito.esito, 'evasa');
  assert.strictEqual(stato.evasioni.length, 1);
  const f = stato.evasioni[0];
  assert.strictEqual(f.notifyCustomer, true,
    'notifyCustomer false: il cliente non riceve l\'email, ed e\' tutto il punto');
  assert.deepStrictEqual(f.trackingInfo,
    { number: 'JD0002', url: 'https://dhl/JD0002', company: 'DHL' });
  assert.strictEqual(f.lineItemsByFulfillmentOrder.length, 1);
});

provaAsync('non chiude l\'altra meta\' dell\'ordine', async function () {
  // Il collare parte dalla Spagna e la medaglietta dagli Stati Uniti, in due
  // momenti diversi. Chiudere tutto al primo collo direbbe al cliente una cosa
  // falsa sulla meta' che sta ancora arrivando.
  const { finto, stato } = fintoShopify();
  await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE, codice: 'JD0002' },
    AMBIENTE, finto);
  const righeToccate = stato.evasioni[0].lineItemsByFulfillmentOrder[0]
    .fulfillmentOrderLineItems.map(function (l) { return l.id; });
  assert.ok(righeToccate.every(function (id) { return id.indexOf(RIGA_COLLARE) !== -1; }),
    'ha evaso anche la riga che non e\' partita: ' + righeToccate.join(', '));
});

provaAsync('lo stesso webhook due volte non evade due volte', async function () {
  // Gli stampatori ritentano. Due email di spedizione per un pacco solo fanno
  // pensare al cliente di aver comprato due volte.
  const { finto, stato } = fintoShopify();
  const uno = await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE, codice: 'X' },
    AMBIENTE, finto);
  const due = await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE, codice: 'X' },
    AMBIENTE, finto);
  assert.strictEqual(uno.esito, 'evasa');
  assert.strictEqual(due.esito, 'gia_evasa');
  assert.strictEqual(stato.evasioni.length, 1, 'ha evaso due volte');
});

provaAsync('se l\'app dello stampatore ha gia\' evaso, non tocca niente', async function () {
  // E' cio' che rende sicuro far girare questo codice insieme alle app
  // Printful/Printify installate sul negozio: se fanno gia' loro il lavoro,
  // qui non succede nulla invece di raddoppiare.
  const { finto, stato } = fintoShopify({ rimaste: { [RIGA_COLLARE]: 0 } });
  const esito = await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE },
    AMBIENTE, finto);
  assert.strictEqual(esito.esito, 'gia_evasa');
  assert.strictEqual(stato.evasioni.length, 0);
});

provaAsync('senza numero di tracciamento evade lo stesso', async function () {
  // Meglio "e' partito" senza numero che il silenzio.
  const { finto, stato } = fintoShopify();
  const esito = await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE },
    AMBIENTE, finto);
  assert.strictEqual(esito.esito, 'evasa');
  assert.strictEqual(esito.conTracciamento, false);
  assert.strictEqual(stato.evasioni[0].trackingInfo, undefined,
    'un trackingInfo vuoto e\' peggio di nessun trackingInfo');
  assert.strictEqual(stato.evasioni[0].notifyCustomer, true);
});

provaAsync('un riferimento non nostro viene lasciato stare', async function () {
  const { finto, stato } = fintoShopify();
  const esito = await ev.evadiRiga({ riferimento: 'ORD-2024-ACME' }, AMBIENTE, finto);
  assert.strictEqual(esito.esito, 'ignorato');
  assert.strictEqual(stato.chiamate, 0, 'ha chiamato Shopify per un ordine non suo');
});

provaAsync('senza token lo dice, invece di fallire in silenzio', async function () {
  const { finto } = fintoShopify();
  const esito = await ev.evadiRiga({ riferimento: '5432167890-' + RIGA_COLLARE },
    { SHOPIFY_SHOP_DOMAIN: 'negozio.myshopify.com' }, finto);
  assert.strictEqual(esito.esito, 'impossibile');
  assert.ok(/SHOPIFY_ADMIN_TOKEN/.test(esito.motivo));
});

provaAsync('il riferimento Printify si chiede indietro a loro', async function () {
  let chiesto = null;
  async function finto(url) {
    chiesto = url;
    return { ok: true, json: async function () { return { external_id: '5432167890-111' }; } };
  }
  const r = await ev.riferimentoPrintify('printify-abc',
    { PRINTIFY_SHOP_ID: '77', PRINTIFY_API_KEY: 'k' }, finto);
  assert.strictEqual(r, '5432167890-111');
  assert.ok(/\/shops\/77\/orders\/printify-abc\.json$/.test(chiesto), chiesto);
});

// ---- esecuzione -----------------------------------------------------------

console.log('\nRiferimento fra riga d\'ordine e stampatore');
prova('un riferimento diverso per ogni riga', testRiferimentoDiversoPerOgniRiga);
prova('il riferimento si rilegge al ritorno', testRiferimentoSiRilegge);
prova('un ordine non nostro viene ignorato', testRiferimentoAltruiVieneIgnorato);
prova('senza id non si costruisce un riferimento finto', testRiferimentoSenzaIdSiFerma);
prova('i client non mandano piu\' l\'id del solo ordine', testIClientNonMandanoPiuLIdDelSoloOrdine);

console.log('\nI webhook dei due stampatori');
prova('legge la spedizione Printful', testLeggeLaSpedizionePrintful);
prova('Printful senza riferimento non inventa niente', testPrintfulSenzaRiferimentoNonInventaNiente);
prova('legge la spedizione Printify', testLeggeLaSpedizionePrintify);

console.log('\nLe firme');
prova('la firma Printify vera passa', testFirmaPrintifyVera);
prova('la firma Printify falsa non passa', testFirmaPrintifyFalsaRifiutata);
prova('senza segreto configurato non entra nessuno', testSenzaSegretoNienteEntra);
prova('il segreto nella URL di Printful', testSegretoNellaUrl);

(async function () {
  console.log('\nL\'evasione su Shopify');
  for (const [nome, fn] of inCoda) {
    try {
      await fn();
      console.log('  ok   ' + nome);
      fatte++;
    } catch (err) {
      console.log('  FALLITO   ' + nome + '\n        ' + err.message);
      process.exitCode = 1;
    }
  }
  console.log('\n' + fatte + ' verifiche superate.' +
    (process.exitCode ? ' Alcune FALLITE.' : ''));
})();
