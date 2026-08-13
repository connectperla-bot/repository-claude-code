'use strict';

// Client Contrado (API "Helix"), terzo fornitore dopo Printify e Printful.
// Stessa interfaccia degli altri due: fulfillOrder(ctx).
// Specifica ufficiale: https://api.contrado.app/helix/swagger/v1/swagger.json
//
// DUE DIFFERENZE SOSTANZIALI rispetto a Printify e Printful. Non sono
// dettagli implementativi: cambiano cosa si puo' vendere con questo fornitore.
//
// 1. NESSUN FILE DI STAMPA NELL'ORDINE.
//    La riga d'ordine Contrado e' { storeProductId, variantId, selectedOptions,
//    quantity, price }: nessun campo per un'immagine, un URL o un id di
//    upload (verificato sullo schema StoreLineItemRequestViewModel della
//    specifica). Si puo' solo ordinare un prodotto che esiste GIA' nel
//    negozio Contrado, con il design gia' applicato li' dentro.
//    Conseguenza pratica: i prodotti Contrado sono a DESIGN FISSO. Lo studio
//    di personalizzazione del sito ("Crea il Tuo Design") non puo' funzionare
//    con questo fornitore, perche' il composito del cliente non avrebbe dove
//    viaggiare. Vedi il controllo esplicito in fulfillOrder().
//
// 2. NESSUNO STATO DI BOZZA.
//    Printify ha "Send to production" e Printful ha "Draft orders": in
//    entrambi l'ordine si crea e resta li' in attesa di approvazione manuale,
//    che e' la modalita' voluta dalla titolare "all'inizio" (vedi ROUND 35 in
//    perla-printify-order-sync.js). POST /orders/create su Contrado invece
//    inserisce l'ordine e basta: parte in produzione.
//    Per non perdere quel controllo, qui l'invio e' DISATTIVO di default e va
//    acceso con CONTRADO_INVIO_AUTOMATICO=true. Finche' e' spento, la riga
//    non viene inviata e viene segnalata per l'inserimento manuale dal
//    pannello Contrado -- stesso trattamento delle altre righe che
//    richiedono un controllo (vedi isolamento errori nel sync ordini).

const HOST = 'https://api.contrado.app';
const BASE = '/helix/v1';

// Contrado accetta questi codici cultura; determinano valuta e prezzi.
// Un codice non valido fa rifiutare l'ordine ("Invalid culture code" tra le
// regole di validazione documentate).
const CULTURE_VALIDE = [
  'en-GB', 'en-US', 'it-IT', 'de-DE', 'fr-FR', 'ja-JP', 'es-ES',
  'en-AU', 'en-CA', 'en-IE', 'en-NZ', 'sv-SE', 'nl-NL',
];

function indirizzoDestinatario(order) {
  const sp = order.shipping_address || {};
  return {
    name: [sp.first_name, sp.last_name].filter(Boolean).join(' '),
    company: sp.company || '',
    address1: sp.address1 || '',
    address2: sp.address2 || '',
    city: sp.city || '',
    stateCode: sp.province_code || '',
    stateName: sp.province || '',
    countryCode: sp.country_code || '',
    country: sp.country || '',
    postCode: sp.zip || '',
    phone: sp.phone || '',
    email: order.email || '',
  };
}

// La variante Contrado viaggia nella SKU della variante Shopify, com'e' gia'
// per i prodotti Printify di questo negozio (dove la SKU e' l'id Printify).
// Cosi' la taglia scelta dal cliente (cuccia 28x18 / 40x30 / 50x40) arriva
// giusta senza una tabella di corrispondenza da tenere allineata a mano.
function variantePerRiga(item, config) {
  const sku = (item.sku || '').trim();
  if (sku) return sku;
  if (config.variantId) return String(config.variantId);
  return null;
}

async function creaOrdineSuContrado(order, item, config, env) {
  const cultureCode = env.CONTRADO_CULTURE_CODE || 'it-IT';
  if (CULTURE_VALIDE.indexOf(cultureCode) === -1) {
    throw new Error(
      'CONTRADO_CULTURE_CODE non valido ("' + cultureCode + '"). Valori ammessi: ' + CULTURE_VALIDE.join(', ') + '.'
    );
  }

  const variantId = variantePerRiga(item, config);
  if (!variantId) {
    throw new Error(
      'Variante Contrado non determinabile per la riga "' + (item.title || item.id) + '": ' +
      'la variante Shopify non ha SKU e non e\' impostato un variantId di riserva. ' +
      'La SKU della variante Shopify deve contenere il variantId Contrado ' +
      '(lo leggi con: node scripts/contrado-catalog.js --varianti ' + config.productId + ').'
    );
  }

  const quantita = item.quantity || 1;
  // Il prezzo per riga e' quello che il cliente ha davvero pagato su Shopify.
  const prezzoUnitario = Number(item.price || 0);

  const corpo = {
    // L'id ordine Shopify come riferimento esterno: e' anche la chiave con
    // cui rileggere lo stato (GET /orders/by-reference/{referenceId}/status)
    // senza doversi salvare l'id interno Contrado.
    externalReferenceId: String(order.id),
    recipient: indirizzoDestinatario(order),
    lineItem: [{
      storeProductId: Number(config.productId),
      externalReferenceId: String(item.id),
      variantId: String(variantId),
      selectedOptions: config.options || [],
      quantity: quantita,
      price: prezzoUnitario,
    }],
    totalAmount: Number((prezzoUnitario * quantita).toFixed(2)),
    currencyCode: order.currency || 'EUR',
    // false: se un ordine con lo stesso externalReferenceId esiste gia',
    // Contrado lo rifiuta invece di duplicarlo. E' la rete contro i
    // ritentativi del webhook Shopify.
    forceInsert: false,
    cultureCode: cultureCode,
  };

  const risposta = await fetch(HOST + BASE + '/orders/create', {
    method: 'POST',
    headers: Object.assign({
      'X-API-KEY': env.CONTRADO_API_KEY,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    }, env.CONTRADO_STORE_ID ? { 'X-Store-Id': String(env.CONTRADO_STORE_ID) } : {}),
    body: JSON.stringify(corpo),
  });

  const testo = await risposta.text();
  let json = null;
  try { json = JSON.parse(testo); } catch (e) { /* gestito sotto */ }

  if (!risposta.ok) {
    const msg = (json && json.message) || testo.slice(0, 300);
    throw new Error('Errore creazione ordine Contrado (' + risposta.status + '): ' + msg);
  }
  // Helix risponde 200 anche quando rifiuta: l'esito vero e' in success.
  if (json && json.success === false) {
    throw new Error('Contrado ha rifiutato l\'ordine: ' + (json.message || 'nessun messaggio'));
  }
  return (json && json.data) || {};
}

async function fulfillOrder(ctx) {
  const { order, item, front, back, config, env } = ctx;

  if (!env.CONTRADO_API_KEY) {
    throw new Error('CONTRADO_API_KEY non impostata: la riga non puo\' essere evasa su Contrado.');
  }
  if (!config || !config.productId) {
    throw new Error(
      'Prodotto Contrado non configurato per questo tipo. Imposta CONTRADO_<TIPO>_PRODUCT_ID ' +
      'in config/printify.local.env (gli storeProductId si leggono con: node scripts/contrado-catalog.js --prodotti).'
    );
  }

  // Salvagente. Se una riga arriva qui con una personalizzazione del cliente,
  // qualcosa e' stato configurato male a monte: un prodotto Contrado con lo
  // studio di personalizzazione attivo. Inviare l'ordine comunque
  // stamperebbe il design fisso e butterebbe via la foto o il nome che il
  // cliente ha scelto e pagato -- un pacco sbagliato consegnato senza che
  // nessuno se ne accorga. Meglio fermarsi e farlo vedere.
  if (front || back) {
    throw new Error(
      'Riga con personalizzazione su un prodotto Contrado ("' + (item.title || item.id) + '"): ' +
      'l\'API Contrado non trasporta file di stampa, quindi il design del cliente andrebbe perso. ' +
      'Togli lo studio di personalizzazione da questo prodotto Shopify, oppure spostalo su un ' +
      'fornitore che la supporta (Printify o Printful).'
    );
  }

  if (env.CONTRADO_INVIO_AUTOMATICO !== 'true') {
    throw new Error(
      'Invio automatico a Contrado disattivo (CONTRADO_INVIO_AUTOMATICO diverso da "true"): ' +
      'la riga "' + (item.title || item.id) + '" dell\'ordine ' + order.id + ' va inserita a mano dal pannello Contrado. ' +
      'A differenza di Printify e Printful, l\'API Contrado non ha uno stato di bozza: ' +
      'accendere questo interruttore significa mandare gli ordini direttamente in produzione.'
    );
  }

  const risultato = await creaOrdineSuContrado(order, item, config, env);
  return {
    provider: 'contrado',
    orderId: risultato.referenceId || null,
    // Su Contrado non esiste il passaggio di approvazione: se l'ordine e'
    // stato creato, e' gia' in lavorazione.
    sentToProduction: true,
  };
}

module.exports = { fulfillOrder };
