'use strict';

// ANNULLARE O CAMBIARE UN ORDINE, FINCHE' LA STAMPA NON E' PARTITA.
//
// Regola decisa dalla titolare: si puo' annullare o cambiare solo se la stampa
// non e' ancora partita. Qui quella regola diventa una domanda sola -- lo stato
// dell'ordine dal fornitore -- e la risposta non e' un'opinione: e' quello che
// dice Printify o Printful in quel momento.
//
// PERCHE' STA SUL SERVIZIO E NON NEL TEMA
// Per annullare servono la chiave Printify, quella Printful e un token Admin di
// Shopify con permesso di rimborso. Nessuna delle tre puo' arrivare nel
// browser: chiunque legga il sorgente della pagina svuoterebbe il negozio. Il
// tema fa una domanda a questo servizio e mostra la risposta, niente altro.
//
// COME SI RITROVA L'ORDINE DAL FORNITORE
// Nessun archivio locale, e non serve: perla-printify-order-sync.js manda a
// entrambi i fornitori external_id = id dell'ordine Shopify. Printful lo sa
// cercare da solo (/orders/@<external_id>); Printify no, e allora si scorrono
// le ultime pagine dei suoi ordini confrontando external_id. Un ordine da
// annullare e' sempre recente, quindi guardare indietro qualche pagina basta.
//
// COME SI DIMOSTRA DI ESSERE IL PROPRIETARIO
// Numero d'ordine + email, confrontati con Shopify: le stesse due cose che
// Shopify chiede nella sua pagina "stato ordine". Chi sbaglia riceve sempre la
// stessa risposta generica -- non si distingue "ordine inesistente" da "email
// che non corrisponde", altrimenti la pagina diventa un modo per scoprire chi
// ha comprato. E c'e' un tetto ai tentativi per indirizzo IP.
//
// QUELLO CHE QUESTO FILE NON FA
// "Cambiare" un ordine gia' pagato non e' una modifica: e' un annullamento con
// rimborso piu' un ordine nuovo. Su un prodotto stampato su richiesta non
// esiste altro modo, e provare a modificare la riga lasciando il pagamento dov'e'
// creerebbe solo disallineamenti fra Shopify e il fornitore. Quindi entrambi i
// pulsanti passano di qui: la differenza e' solo il messaggio che legge il
// cliente.
//
// Variabili d'ambiente nuove (vedi config/printify.env.example):
//   SHOPIFY_SHOP_DOMAIN   perlaitaly-store.myshopify.com
//   SHOPIFY_ADMIN_TOKEN   token Admin API con read_orders + write_orders
// Senza queste due il modulo non si monta e il resto del servizio continua a
// funzionare: annullare e' una funzione in piu', non una dipendenza.

const express = require('express');

const VERSIONE_API_SHOPIFY = '2025-07';

// Stati in cui la stampa NON e' ancora partita e si puo' ancora fermare tutto.
// Fuori da queste liste (in produzione, spedito, gia' annullato) non si tocca.
const PRINTFUL_ANNULLABILE = ['draft', 'pending', 'onhold'];
const PRINTIFY_ANNULLABILE = ['pending', 'on-hold', 'payment-not-received'];

// Tetto ai tentativi per indirizzo IP. Serve contro chi prova coppie
// numero+email a raffica, non contro il cliente che sbaglia a digitare -- e
// dietro la rete di un operatore mobile un solo IP puo' essere mezza citta',
// quindi il tetto non puo' essere stretto. Venti in un quarto d'ora fermano
// l'enumerazione (indovinare numero E email insieme non si fa in venti colpi)
// senza chiudere fuori nessuno.
const FINESTRA_MS = 15 * 60 * 1000;
const TENTATIVI_MAX = 20;
const tentativi = new Map();

function troppiTentativi(ip) {
  const adesso = Date.now();
  const vecchi = tentativi.get(ip) || [];
  const recenti = vecchi.filter(function (t) { return adesso - t < FINESTRA_MS; });
  recenti.push(adesso);
  tentativi.set(ip, recenti);
  // La mappa non deve crescere all'infinito su un servizio che sta su per mesi.
  if (tentativi.size > 5000) {
    for (const [chiave, lista] of tentativi) {
      if (!lista.some(function (t) { return adesso - t < FINESTRA_MS; })) tentativi.delete(chiave);
    }
  }
  return recenti.length > TENTATIVI_MAX;
}

// --- validazione ai confini -------------------------------------------------

function numeroOrdinePulito(valore) {
  if (typeof valore !== 'string') return null;
  const pulito = valore.trim().replace(/^#/, '');
  // Shopify accetta numeri e prefissi tipo "PI-1042": lettere, cifre, - e _.
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(pulito)) return null;
  return pulito;
}

function emailPulita(valore) {
  if (typeof valore !== 'string') return null;
  const pulita = valore.trim().toLowerCase();
  if (pulita.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(pulita)) return null;
  return pulita;
}

// --- Shopify ----------------------------------------------------------------

async function shopifyGraphQL(query, variables, env) {
  const risposta = await fetch(
    'https://' + env.SHOPIFY_SHOP_DOMAIN + '/admin/api/' + VERSIONE_API_SHOPIFY + '/graphql.json',
    {
      method: 'POST',
      headers: {
        'X-Shopify-Access-Token': env.SHOPIFY_ADMIN_TOKEN,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: query, variables: variables }),
    }
  );
  const testo = await risposta.text();
  if (!risposta.ok) {
    throw new Error('Shopify ha risposto ' + risposta.status + ': ' + testo.slice(0, 300));
  }
  const dati = JSON.parse(testo);
  if (dati.errors && dati.errors.length) {
    throw new Error('Shopify: ' + dati.errors.map(function (e) { return e.message; }).join('; '));
  }
  return dati.data;
}

const QUERY_ORDINE = `
  query TrovaOrdine($q: String!) {
    orders(first: 5, query: $q) {
      nodes {
        id
        name
        email
        createdAt
        cancelledAt
        displayFulfillmentStatus
        displayFinancialStatus
        totalPriceSet { shopMoney { amount currencyCode } }
      }
    }
  }`;

async function trovaOrdineShopify(numero, email, env) {
  // Si cerca per numero e si confronta l'email dopo: query name:X email:Y
  // farebbe filtrare a Shopify, ma un OR implicito su alcuni campi renderebbe
  // il confronto meno prevedibile di uno fatto qui, a mano.
  const dati = await shopifyGraphQL(QUERY_ORDINE, { q: 'name:' + numero }, env);
  const trovati = (dati.orders && dati.orders.nodes) || [];
  for (const o of trovati) {
    if ((o.email || '').trim().toLowerCase() === email) return o;
  }
  return null;
}

const MUTATION_ANNULLA = `
  mutation Annulla($id: ID!) {
    orderCancel(orderId: $id, reason: CUSTOMER, refund: true, restock: true, notifyCustomer: true) {
      job { id }
      orderCancelUserErrors { field message }
    }
  }`;

async function annullaOrdineShopify(idOrdine, env) {
  const dati = await shopifyGraphQL(MUTATION_ANNULLA, { id: idOrdine }, env);
  const errori = (dati.orderCancel && dati.orderCancel.orderCancelUserErrors) || [];
  if (errori.length) {
    throw new Error(errori.map(function (e) { return e.message; }).join('; '));
  }
}

// --- Printful ---------------------------------------------------------------

async function printfulOrdine(idShopify, env) {
  if (!env.PRINTFUL_API_KEY) return null;
  const risposta = await fetch('https://api.printful.com/orders/@' + encodeURIComponent(idShopify), {
    headers: { Authorization: 'Bearer ' + env.PRINTFUL_API_KEY },
  });
  if (risposta.status === 404) return null;
  if (!risposta.ok) {
    throw new Error('Printful ha risposto ' + risposta.status + ' cercando l\'ordine ' + idShopify);
  }
  const dati = await risposta.json();
  const o = dati.result;
  if (!o) return null;
  return { fornitore: 'printful', id: o.id, stato: String(o.status || '').toLowerCase() };
}

async function printfulAnnulla(idShopify, env) {
  const risposta = await fetch('https://api.printful.com/orders/@' + encodeURIComponent(idShopify), {
    method: 'DELETE',
    headers: { Authorization: 'Bearer ' + env.PRINTFUL_API_KEY },
  });
  if (!risposta.ok) {
    const testo = await risposta.text();
    throw new Error('Printful non ha annullato (' + risposta.status + '): ' + testo.slice(0, 200));
  }
}

// --- Printify ---------------------------------------------------------------

// Printify non sa cercare per external_id: si scorrono le ultime pagine. Un
// ordine annullabile e' per forza recente (non e' ancora andato in stampa),
// quindi tre pagine da cinquanta sono abbondanti; oltre si smette invece di
// consumare la quota dell'API.
const PAGINE_PRINTIFY = 3;

async function printifyOrdine(idShopify, env) {
  if (!env.PRINTIFY_API_KEY || !env.PRINTIFY_SHOP_ID) return null;
  for (let pagina = 1; pagina <= PAGINE_PRINTIFY; pagina++) {
    const risposta = await fetch(
      'https://api.printify.com/v1/shops/' + env.PRINTIFY_SHOP_ID + '/orders.json?page=' + pagina + '&limit=50',
      { headers: { Authorization: 'Bearer ' + env.PRINTIFY_API_KEY } }
    );
    if (!risposta.ok) {
      throw new Error('Printify ha risposto ' + risposta.status + ' elencando gli ordini');
    }
    const dati = await risposta.json();
    const elenco = dati.data || [];
    if (!elenco.length) return null;
    for (const o of elenco) {
      const esterno = String(
        o.external_id || (o.metadata && o.metadata.shop_order_id) || ''
      );
      if (esterno === String(idShopify)) {
        return { fornitore: 'printify', id: o.id, stato: String(o.status || '').toLowerCase() };
      }
    }
  }
  return null;
}

async function printifyAnnulla(idPrintify, env) {
  const risposta = await fetch(
    'https://api.printify.com/v1/shops/' + env.PRINTIFY_SHOP_ID + '/orders/' + idPrintify + '/cancel.json',
    { method: 'POST', headers: { Authorization: 'Bearer ' + env.PRINTIFY_API_KEY } }
  );
  if (!risposta.ok) {
    const testo = await risposta.text();
    throw new Error('Printify non ha annullato (' + risposta.status + '): ' + testo.slice(0, 200));
  }
}

// --- la regola --------------------------------------------------------------

function ancoraFermabile(ordineFornitore) {
  if (!ordineFornitore) return true; // nessun ordine dal fornitore: niente da fermare
  const lista = ordineFornitore.fornitore === 'printful' ? PRINTFUL_ANNULLABILE : PRINTIFY_ANNULLABILE;
  return lista.indexOf(ordineFornitore.stato) !== -1;
}

async function statoOrdine(numero, email, env) {
  const ordine = await trovaOrdineShopify(numero, email, env);
  if (!ordine) return { trovato: false };

  if (ordine.cancelledAt) {
    return { trovato: true, ordine: ordine, annullabile: false, motivo: 'gia_annullato', fornitori: [] };
  }
  if (ordine.displayFulfillmentStatus === 'FULFILLED') {
    return { trovato: true, ordine: ordine, annullabile: false, motivo: 'gia_spedito', fornitori: [] };
  }

  const idShopify = String(ordine.id).split('/').pop();
  const fornitori = [];
  // I due fornitori si interrogano in sequenza e non in parallelo: entrambi
  // hanno un tetto di richieste al minuto e Printful lo fa notare in fretta.
  const daPrintful = await printfulOrdine(idShopify, env);
  if (daPrintful) fornitori.push(daPrintful);
  const daPrintify = await printifyOrdine(idShopify, env);
  if (daPrintify) fornitori.push(daPrintify);

  const bloccanti = fornitori.filter(function (f) { return !ancoraFermabile(f); });
  return {
    trovato: true,
    ordine: ordine,
    fornitori: fornitori,
    annullabile: bloccanti.length === 0,
    motivo: bloccanti.length ? 'stampa_iniziata' : null,
  };
}

// --- risposte al cliente ----------------------------------------------------

// Sempre la stessa frase per "non trovato" e per "email che non corrisponde":
// distinguerle direbbe a un estraneo quali ordini esistono.
const NON_TROVATO = {
  esito: 'non_trovato',
  messaggio: 'Non troviamo un ordine con questo numero e questa email. Controlla la mail di conferma: il numero è in alto, e l\'indirizzo dev\'essere quello con cui hai ordinato.',
};

const MESSAGGI = {
  gia_annullato: 'Questo ordine è già stato annullato. Se hai pagato, il rimborso arriva sul metodo che hai usato.',
  gia_spedito: 'Questo ordine è già partito, quindi non possiamo più fermarlo. Scrivici e troviamo una soluzione: il reso resta possibile sui prodotti non personalizzati.',
  stampa_iniziata: 'La stampa è già iniziata, quindi non possiamo più annullarlo: il pezzo è unico e sta venendo fatto adesso. Scrivici e vediamo cosa possiamo fare.',
};

function costruisciRouter(env) {
  const router = express.Router();
  // Il lettore di JSON si mette SULLE DUE ROTTE, non su router.use(): un
  // router.use senza percorso gira su ogni richiesta che passa di qui, quindi
  // leggerebbe anche il corpo del webhook ordini -- e quello deve restare i
  // byte grezzi, perche' l'HMAC di Shopify si verifica sui byte. Provato:
  // montato come router.use, ogni ordine in arrivo rispondeva 500 e non veniva
  // piu' evaso. Un limite basso perche' qui dentro arrivano due campi corti.
  const leggiJson = express.json({ limit: '4kb' });

  router.post('/ordine/stato', leggiJson, async function (req, res) {
    const ip = req.ip || 'sconosciuto';
    if (troppiTentativi(ip)) {
      return res.status(429).json({ esito: 'troppi_tentativi', messaggio: 'Troppi tentativi. Riprova fra un quarto d\'ora.' });
    }
    const numero = numeroOrdinePulito(req.body && req.body.numero);
    const email = emailPulita(req.body && req.body.email);
    if (!numero || !email) return res.status(400).json(NON_TROVATO);

    try {
      const stato = await statoOrdine(numero, email, env);
      if (!stato.trovato) return res.status(404).json(NON_TROVATO);
      return res.json({
        esito: 'ok',
        numero: stato.ordine.name,
        totale: stato.ordine.totalPriceSet.shopMoney.amount,
        valuta: stato.ordine.totalPriceSet.shopMoney.currencyCode,
        annullabile: stato.annullabile,
        messaggio: stato.annullabile ? null : MESSAGGI[stato.motivo],
      });
    } catch (err) {
      console.error('Stato ordine non recuperato:', err.message);
      return res.status(502).json({ esito: 'errore', messaggio: 'Non riusciamo a controllare l\'ordine in questo momento. Riprova fra qualche minuto o scrivici.' });
    }
  });

  router.post('/ordine/annulla', leggiJson, async function (req, res) {
    const ip = req.ip || 'sconosciuto';
    if (troppiTentativi(ip)) {
      return res.status(429).json({ esito: 'troppi_tentativi', messaggio: 'Troppi tentativi. Riprova fra un quarto d\'ora.' });
    }
    const numero = numeroOrdinePulito(req.body && req.body.numero);
    const email = emailPulita(req.body && req.body.email);
    if (!numero || !email) return res.status(400).json(NON_TROVATO);

    try {
      // Si ricontrolla adesso, non ci si fida di quello che il browser ha letto
      // un minuto fa: nel frattempo la titolare puo' aver mandato in stampa.
      const stato = await statoOrdine(numero, email, env);
      if (!stato.trovato) return res.status(404).json(NON_TROVATO);
      if (!stato.annullabile) {
        return res.status(409).json({ esito: 'non_annullabile', messaggio: MESSAGGI[stato.motivo] });
      }

      // Prima i fornitori, poi Shopify. In quest'ordine: se il fornitore
      // rifiuta, l'ordine Shopify resta in piedi e il cliente lo rivede
      // com'era. Al contrario avremmo rimborsato un pezzo che si stampa lo
      // stesso -- merce persa e soldi restituiti.
      for (const f of stato.fornitori) {
        const idShopify = String(stato.ordine.id).split('/').pop();
        if (f.fornitore === 'printful') await printfulAnnulla(idShopify, env);
        else await printifyAnnulla(f.id, env);
        console.log('Annullato ordine ' + f.fornitore + ' ' + f.id + ' (Shopify ' + stato.ordine.name + ')');
      }

      await annullaOrdineShopify(stato.ordine.id, env);
      console.log('Annullato e rimborsato ordine Shopify ' + stato.ordine.name);

      return res.json({
        esito: 'annullato',
        numero: stato.ordine.name,
        messaggio: 'Fatto: l\'ordine ' + stato.ordine.name + ' è annullato e non verrà stampato. Il rimborso torna sul metodo che hai usato, di solito in pochi giorni lavorativi. Ti arriva anche una email di conferma.',
      });
    } catch (err) {
      // Se si e' fermato a meta' -- fornitore annullato, Shopify no -- lo si
      // dice chiaro nei log: e' il caso che vuole una mano umana.
      console.error('Annullamento non riuscito per ordine ' + numero + ':', err.message);
      return res.status(502).json({
        esito: 'errore',
        messaggio: 'Qualcosa non ha funzionato durante l\'annullamento. Non riprovare: scrivici subito e sistemiamo noi a mano.',
      });
    }
  });

  return router;
}

// Si monta solo se ci sono le chiavi: senza, il resto del servizio parte lo
// stesso e la pagina del tema mostra "scrivici" invece di un errore.
function montaSuApp(app, env) {
  if (!env.SHOPIFY_SHOP_DOMAIN || !env.SHOPIFY_ADMIN_TOKEN) {
    console.warn('Annullamento ordini non attivo: mancano SHOPIFY_SHOP_DOMAIN / SHOPIFY_ADMIN_TOKEN.');
    return false;
  }
  app.use(costruisciRouter(env));
  console.log('Annullamento ordini attivo su POST /ordine/stato e POST /ordine/annulla');
  return true;
}

module.exports = {
  montaSuApp,
  costruisciRouter,
  // esportati per i collaudi
  numeroOrdinePulito,
  emailPulita,
  ancoraFermabile,
  azzeraTentativi: function () { tentativi.clear(); },
  TENTATIVI_MAX,
  PRINTFUL_ANNULLABILE,
  PRINTIFY_ANNULLABILE,
};
