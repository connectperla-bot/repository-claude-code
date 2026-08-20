'use strict';

// Decide QUALE fornitore deve produrre una riga d'ordine, in base al tipo
// prodotto e al paese di spedizione del cliente (dall'ordine Shopify).
//
// Regola attuale (2026-07, da rivedere quando merchOne/altri fornitori si
// aggiungono): collare e bandana spediti in EU vanno su Printful (fabbriche
// in Spagna/Lettonia, niente dogana per il cliente EU); tutto il resto
// (USA, o qualunque prodotto senza alternativa EU: medaglietta/ciotola/
// cuccia) resta su Printify come oggi. Se PRINTFUL_API_KEY non e' ancora
// impostata (account non esiste), si torna SEMPRE su Printify: nessun
// ordine puo' mai finire silenziosamente in un vicolo cieco.
//
// Elenco paesi preso 1:1 dal Market Shopify "Perla EU" gia' configurato
// (Impostazioni > Mercati) — stessa segmentazione che il negozio usa gia'
// per prezzi/valuta, non un elenco EU inventato qui.
//
// ROUND 46 -- via la Russia. Era in questo elenco e nel mercato Shopify, ma
// non aveva nessuna zona di spedizione: un cliente russo metteva i prodotti
// in carrello e non arrivava al checkout, perche' Shopify non sapeva quanto
// fargli pagare. Qui dentro contava davvero: chooseProviderName mandava quel
// paese su Printful come se fosse EU. Tolta da tutti e due i posti.
//
// Il Canada non c'e' mai stato: non e' in nessun mercato Shopify da quando e'
// stato chiuso "il resto del mondo", quindi non c'era niente da togliere.
const PERLA_EU_COUNTRIES = [
  'IT', 'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DE', 'DK', 'EE', 'FI', 'FR',
  'GR', 'HU', 'IE', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK',
  'SI', 'ES', 'SE', 'GB', 'ME', 'MC', 'SM', 'UA',
];

// Tipi prodotto per cui esiste (o potrebbe esistere) un fornitore EU
// alternativo a Printify. Aggiungere qui quando merchOne/altri confermano.
//
// ROUND 18 — collare_eu/bandana_eu, NON collare/bandana: Printful non vende
// un collare TPU ne' una bandana rettangolare equivalenti a quelli reali
// (il loro collare e' in tessuto, la loro bandana e' quadrata - verificato
// con ordini di prova reali). Sono quindi prodotti Shopify NUOVI e distinti;
// tenerli separati da collare/bandana significa che attivare
// PRINTFUL_API_KEY in futuro NON cambia il fornitore dei ~20 prodotti
// collare/bandana gia' in vendita.
const EU_CAPABLE_TYPES = {
  collare_eu: 'printful',
  bandana_eu: 'printful',
  // ROUND 28 -- ciotola_eu/guinzaglio_eu: stessi criteri di collare_eu/
  // bandana_eu sopra (prodotti Shopify nuovi e distinti, non varianti delle
  // ciotole/guinzagli Printify esistenti). Confermato via API Printful che
  // il loro catalogo ha "Pet Bowl" (id 678) e "Pet Leash" (id 745).
  ciotola_eu: 'printful',
  guinzaglio_eu: 'printful',
};

const printifyClient = require('./providers/printify-client');
const printfulClient = require('./providers/printful-client');

const CLIENTS = {
  printify: printifyClient,
  printful: printfulClient,
};

function isEuShipping(order) {
  const country = order.shipping_address && order.shipping_address.country_code;
  return !!country && PERLA_EU_COUNTRIES.indexOf(country) !== -1;
}

// Ritorna il NOME del fornitore da usare (non il client): utile per i log e
// per i test, separato da chooseClient cosi' si puo' verificare la regola
// senza dover chiamare API vere.
function chooseProviderName(productType, order, env) {
  const euProvider = EU_CAPABLE_TYPES[productType];
  if (euProvider && isEuShipping(order) && env[euProvider.toUpperCase() + '_API_KEY']) {
    return euProvider;
  }
  return 'printify';
}

function chooseClient(productType, order, env) {
  return CLIENTS[chooseProviderName(productType, order, env)];
}

module.exports = { chooseClient, chooseProviderName, isEuShipping, PERLA_EU_COUNTRIES, EU_CAPABLE_TYPES };
