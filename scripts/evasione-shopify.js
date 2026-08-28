'use strict';

// Chiude il cerchio: quando lo stampatore spedisce, il cliente lo viene a sapere.
//
// IL DIFETTO CHE QUESTO FILE CHIUDE
// Cercando `fulfillment` e `tracking` in perla-printify-order-sync.js e nei due
// client fornitore: zero occorrenze. Nessuno riportava la spedizione a Shopify.
// Quindi: il cliente paga, Printful o Printify producono e spediscono, e su
// Shopify l'ordine resta "non evaso" per sempre. Nessuna email "il tuo ordine
// e' partito", nessun numero da seguire. La pagina Spedizioni del negozio
// promette il contrario ("appena il pacco parte ricevi via email il link per
// seguirlo"): era una promessa che nessun pezzo di codice manteneva.
//
// PERCHE' LO SCRIVIAMO ANCHE SE LE APP POTREBBERO FARLO DA SOLE
// Printful e Printify sono installate come servizi di evasione su questo
// negozio, quindi in teoria potrebbero riportare loro la spedizione. Ma gli
// ordini non li creiamo attraverso le loro app: li creiamo via API contro lo
// store nativo ("Personal orders" per Printful, vedi il commento in
// providers/printful-client.js), che non e' lo store collegato a Shopify. Se
// e' cosi', loro non hanno nessun ordine Shopify a cui agganciare niente.
//
// Non serve saperlo in anticipo. `gia_evasa()` guarda lo stato PRIMA di
// scrivere: se l'app ha gia' evaso quella riga, questo codice non fa nulla e
// lo dice nei log. Funziona nei due mondi, e il primo ordine vero dira' quale
// dei due e'.
//
// COSA NON FA
// Non inventa una data, non stima, non "chiude" un ordine per farlo sembrare
// a posto. Se lo stampatore non manda il numero di tracciamento, si evade
// senza -- Shopify manda comunque l'email di spedizione, che e' meglio del
// silenzio -- e lo si scrive nei log.

const crypto = require('crypto');
const { leggiRiferimento } = require('./riferimento-ordine');

const API = '2025-01';

/* -------------------------------------------------------------------------
   1. LEGGERE IL WEBHOOK DELLO STAMPATORE

   I due fornitori mandano forme diverse. Qui diventano una cosa sola:
   { riferimento, corriere, codice, url }.
   ---------------------------------------------------------------------- */

// Printful, evento "package_shipped".
// data.order.external_id e' il nostro riferimento; data.shipment porta corriere
// e tracciamento. Un ordine puo' partire in piu' colli (shipment separati): ogni
// collo arriva come un webhook a se', ed e' giusto cosi'.
function daPrintful(payload) {
  const dati = (payload && payload.data) || {};
  const spedizione = dati.shipment || {};
  const ordine = dati.order || {};
  if (!ordine.external_id) return null;
  return {
    fornitore: 'printful',
    riferimento: String(ordine.external_id),
    corriere: spedizione.carrier || null,
    codice: spedizione.tracking_number || null,
    url: spedizione.tracking_url || null,
  };
}

// Printify, evento "order:shipment:created".
//
// ATTENZIONE alla differenza che conta: Printify NON mette l'external_id nel
// corpo del webhook, mette solo il proprio id d'ordine. Il riferimento va
// quindi richiesto a loro con una seconda chiamata (vedi riferimentoPrintify).
// Se un giorno lo aggiungessero, il campo qui sotto lo prende senza modifiche.
function daPrintify(payload) {
  const risorsa = (payload && payload.resource) || {};
  const dati = risorsa.data || {};
  const corriere = dati.carrier || {};
  const rif = dati.external_id || risorsa.external_id || null;
  return {
    fornitore: 'printify',
    riferimento: rif ? String(rif) : null,
    idFornitore: risorsa.id ? String(risorsa.id) : null,
    corriere: corriere.name || corriere.code || null,
    codice: dati.tracking_number || null,
    url: dati.tracking_url || null,
  };
}

// La seconda chiamata di cui sopra: dall'id ordine Printify al nostro
// riferimento. Si fa solo quando serve davvero, cioe' quando il webhook non lo
// portava gia'.
async function riferimentoPrintify(idOrdine, env, fetchImpl) {
  const f = fetchImpl || fetch;
  const res = await f('https://api.printify.com/v1/shops/' + env.PRINTIFY_SHOP_ID +
    '/orders/' + idOrdine + '.json', {
    headers: { Authorization: 'Bearer ' + env.PRINTIFY_API_KEY },
  });
  if (!res.ok) {
    throw new Error('Printify non ha voluto dire a quale ordine appartiene la ' +
      'spedizione ' + idOrdine + ' (' + res.status + ').');
  }
  const dati = await res.json();
  return dati && dati.external_id ? String(dati.external_id) : null;
}

/* -------------------------------------------------------------------------
   2. LE FIRME

   Printify firma con X-Pfy-Signature: sha256=<hex>, HMAC sul corpo grezzo --
   stessa forma della firma Shopify che questo servizio gia' verifica.
   Printful non firma niente: la loro documentazione dice di usare una URL
   segreta. Quindi il segreto sta nel percorso, e va trattato come una
   password -- non finisce nei log.
   ---------------------------------------------------------------------- */

function firmaPrintifyValida(corpoGrezzo, intestazione, segreto) {
  if (!segreto) return false;
  const arrivata = String(intestazione || '').replace(/^sha256=/, '');
  if (!arrivata) return false;
  const attesa = crypto.createHmac('sha256', segreto).update(corpoGrezzo).digest('hex');
  const a = Buffer.from(arrivata, 'utf8');
  const b = Buffer.from(attesa, 'utf8');
  // timingSafeEqual pretende la stessa lunghezza, e sollevare qui direbbe a chi
  // prova quanto e' lunga la firma giusta.
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function segretoUrlValido(ricevuto, atteso) {
  if (!atteso || !ricevuto) return false;
  const a = Buffer.from(String(ricevuto), 'utf8');
  const b = Buffer.from(String(atteso), 'utf8');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

/* -------------------------------------------------------------------------
   3. PARLARE A SHOPIFY
   ---------------------------------------------------------------------- */

async function chiediAShopify(query, variables, env, fetchImpl) {
  const f = fetchImpl || fetch;
  const res = await f('https://' + env.SHOPIFY_SHOP_DOMAIN + '/admin/api/' + API + '/graphql.json', {
    method: 'POST',
    headers: {
      'X-Shopify-Access-Token': env.SHOPIFY_ADMIN_TOKEN,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, variables }),
  });
  if (!res.ok) {
    throw new Error('Shopify ha risposto ' + res.status + ' alla richiesta di evasione.');
  }
  const dati = await res.json();
  if (dati.errors && dati.errors.length) {
    throw new Error('Shopify: ' + dati.errors.map(function (e) { return e.message; }).join('; '));
  }
  return dati.data;
}

const QUERY_ORDINE = `
query righeDaEvadere($id: ID!) {
  order(id: $id) {
    id
    name
    fulfillmentOrders(first: 20, query: "status:open OR status:in_progress") {
      nodes {
        id
        status
        lineItems(first: 50) {
          nodes { id remainingQuantity lineItem { id } }
        }
      }
    }
  }
}`;

// fulfillmentCreate, non fulfillmentCreateV2: quest'ultima e' deprecata
// nell'API 2025-01 (verificato validando la mutazione contro lo schema vero,
// che risponde "Use `fulfillmentCreate` instead").
const MUTAZIONE_EVADI = `
mutation evadi($f: FulfillmentInput!) {
  fulfillmentCreate(fulfillment: $f) {
    fulfillment { id status trackingInfo { number url company } }
    userErrors { field message }
  }
}`;

/* -------------------------------------------------------------------------
   4. IL LAVORO

   Una riga alla volta: si evade SOLO la riga che e' partita davvero. Un ordine
   con un collare (Printful, Spagna) e una medaglietta (Printify, Stati Uniti)
   parte in due momenti da due continenti, e chiuderlo tutto al primo collo
   direbbe al cliente una cosa falsa sulla meta' che sta ancora arrivando.
   ---------------------------------------------------------------------- */

async function evadiRiga(spedizione, env, fetchImpl) {
  const rif = leggiRiferimento(spedizione.riferimento);
  if (!rif) {
    return { esito: 'ignorato', motivo: 'riferimento non nostro: ' + spedizione.riferimento };
  }
  if (!env.SHOPIFY_ADMIN_TOKEN || !env.SHOPIFY_SHOP_DOMAIN) {
    // Non e' un dettaglio: senza token questo file non puo' fare NIENTE, e il
    // cliente resta senza email. Va detto forte, non nascosto in un ramo muto.
    return {
      esito: 'impossibile',
      motivo: 'SHOPIFY_ADMIN_TOKEN / SHOPIFY_SHOP_DOMAIN non impostati su Render: ' +
        'la spedizione e\' arrivata ma non puo\' essere scritta su Shopify.',
    };
  }

  const dati = await chiediAShopify(QUERY_ORDINE,
    { id: 'gid://shopify/Order/' + rif.ordine }, env, fetchImpl);
  const ordine = dati && dati.order;
  if (!ordine) {
    return { esito: 'ignorato', motivo: 'ordine Shopify ' + rif.ordine + ' non trovato' };
  }

  const rigaGid = 'gid://shopify/LineItem/' + rif.riga;
  for (const fo of (ordine.fulfillmentOrders && ordine.fulfillmentOrders.nodes) || []) {
    const righe = (fo.lineItems && fo.lineItems.nodes) || [];
    const mia = righe.filter(function (r) {
      return r.lineItem && r.lineItem.id === rigaGid && r.remainingQuantity > 0;
    });
    if (!mia.length) continue;

    const tracking = {};
    if (spedizione.codice) tracking.number = spedizione.codice;
    if (spedizione.url) tracking.url = spedizione.url;
    if (spedizione.corriere) tracking.company = spedizione.corriere;

    const esito = await chiediAShopify(MUTAZIONE_EVADI, {
      f: {
        lineItemsByFulfillmentOrder: [{
          fulfillmentOrderId: fo.id,
          fulfillmentOrderLineItems: mia.map(function (r) {
            return { id: r.id, quantity: r.remainingQuantity };
          }),
        }],
        // Questa e' la riga che manda l'email al cliente. E' il motivo per cui
        // esiste tutto il file.
        notifyCustomer: true,
        ...(Object.keys(tracking).length ? { trackingInfo: tracking } : {}),
      },
    }, env, fetchImpl);

    const errori = ((esito.fulfillmentCreate || {}).userErrors) || [];
    if (errori.length) {
      throw new Error('Shopify ha rifiutato l\'evasione: ' +
        errori.map(function (e) { return e.message; }).join('; '));
    }
    return {
      esito: 'evasa',
      ordine: ordine.name,
      conTracciamento: !!spedizione.codice,
      fulfillment: ((esito.fulfillmentCreate || {}).fulfillment || {}).id || null,
    };
  }

  // Nessuna riga aperta: o l'ha gia' evasa l'app dello stampatore, o e' il
  // secondo arrivo dello stesso webhook. Le due cose si trattano uguale --
  // non si scrive niente -- ed e' esattamente cio' che rende sicuro far
  // girare questo codice insieme alle app installate.
  return { esito: 'gia_evasa', ordine: ordine.name };
}

/* ---------------------------------------------------------------------------
   LA SPEDIZIONE TORNA AL CLIENTE

   Le due rotte qui sotto sono l'altra meta' del servizio: /webhooks/orders-create
   manda l'ordine allo stampatore, queste riportano indietro la spedizione. La
   logica vera sta in evasione-shopify.js -- qui restano solo la firma e i log,
   perche' questo file e' gia' lungo.

   DA CONFIGURARE DALLO STAMPATORE (una volta sola, nei loro pannelli):
     Printful  -> Impostazioni > Webhook > "Package shipped", indirizzo
                  https://<servizio>.onrender.com/webhooks/printful/<SEGRETO>
                  dove <SEGRETO> e' PRINTFUL_WEBHOOK_PATH su Render. Printful
                  non firma le chiamate: la loro documentazione dice di usare
                  una URL segreta, ed e' quello che facciamo.
     Printify  -> Webhook "order:shipment:created" su
                  https://<servizio>.onrender.com/webhooks/printify/shipment
                  Printify firma davvero: PRINTIFY_WEBHOOK_SECRET su Render.

   Senza SHOPIFY_ADMIN_TOKEN e SHOPIFY_SHOP_DOMAIN su Render queste rotte
   ricevono e non possono scrivere: lo dicono nei log a voce alta invece di
   fallire in silenzio.
   ------------------------------------------------------------------------ */

function registraRotte(app) {
  async function concludi(res, spedizione, dove) {
    try {
      const esito = await evadiRiga(spedizione, process.env);
      if (esito.esito === 'evasa') {
        console.log(dove + ': ordine ' + esito.ordine + ' evaso su Shopify' +
          (esito.conTracciamento ? ' col numero di tracciamento.' :
            ' SENZA numero di tracciamento (lo stampatore non l\'ha mandato).') +
          ' Email di spedizione inviata al cliente.');
      } else if (esito.esito === 'gia_evasa') {
        console.log(dove + ': ordine ' + esito.ordine + ' era gia\' evaso, non tocco niente.');
      } else {
        console.error(dove + ': NON evaso — ' + esito.motivo);
      }
    } catch (err) {
      // 200 comunque: uno stampatore che ritenta all'infinito non aiuta nessuno,
      // e la spedizione e' un fatto gia' avvenuto. Resta nei log da sistemare.
      console.error(dove + ': errore durante l\'evasione, da controllare a mano:', err.message);
    }
    res.status(200).send('OK');
  }

  app.post('/webhooks/printful/:segreto', async function (req, res) {
    if (!segretoUrlValido(req.params.segreto, process.env.PRINTFUL_WEBHOOK_PATH)) {
      // Nessun dettaglio a chi bussa, e nessun segreto nei log.
      console.error('Webhook Printful rifiutato: segreto nell\'indirizzo non valido.');
      return res.status(404).send('Non trovato');
    }
    let payload;
    try {
      payload = JSON.parse(req.body.toString('utf8'));
    } catch (e) {
      return res.status(400).send('Corpo non leggibile');
    }
    if (payload.type && payload.type !== 'package_shipped') {
      console.log('Webhook Printful "' + payload.type + '" ignorato: non e\' una spedizione.');
      return res.status(200).send('OK');
    }
    const spedizione = daPrintful(payload);
    if (!spedizione) {
      console.error('Webhook Printful senza external_id: impossibile capire di quale riga si tratti.');
      return res.status(200).send('OK');
    }
    await concludi(res, spedizione, 'Printful');
  });

  app.post('/webhooks/printify/shipment', async function (req, res) {
    if (!firmaPrintifyValida(req.body, req.get('X-Pfy-Signature'),
      process.env.PRINTIFY_WEBHOOK_SECRET)) {
      console.error('Webhook Printify rifiutato: firma non valida, oppure ' +
        'PRINTIFY_WEBHOOK_SECRET su Render non corrisponde a quello del webhook.');
      return res.status(401).send('Firma non valida');
    }
    let payload;
    try {
      payload = JSON.parse(req.body.toString('utf8'));
    } catch (e) {
      return res.status(400).send('Corpo non leggibile');
    }
    const spedizione = daPrintify(payload);
    if (!spedizione.riferimento) {
      // Printify manda solo il proprio id d'ordine: il riferimento glielo si
      // chiede indietro. Vedi il commento in evasione-shopify.js.
      try {
        spedizione.riferimento = await riferimentoPrintify(
          spedizione.idFornitore, process.env);
      } catch (err) {
        console.error('Printify:', err.message);
        return res.status(200).send('OK');
      }
    }
    await concludi(res, spedizione, 'Printify');
  });
}

module.exports = {
  daPrintful,
  daPrintify,
  riferimentoPrintify,
  firmaPrintifyValida,
  segretoUrlValido,
  evadiRiga,
  registraRotte,
};
