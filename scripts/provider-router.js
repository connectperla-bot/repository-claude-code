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
const PERLA_EU_COUNTRIES = [
  'IT', 'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DE', 'DK', 'EE', 'FI', 'FR',
  'GR', 'HU', 'IE', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK',
  'SI', 'ES', 'SE', 'GB', 'ME', 'MC', 'SM', 'UA', 'RU',
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

// ROUND 36 -- Contrado, linea premium a design fisso con etichetta a marchio
// Perla (l'etichetta si configura in Contrado Store Account e vale per tutti
// gli ordini: non e' un campo dell'ordine). Fabbrica a Londra, spedizione in
// tutto il mondo.
//
// Due differenze rispetto ai tipi _eu qui sopra, ed e' il motivo per cui
// serve una mappa separata invece di aggiungerli a EU_CAPABLE_TYPES:
//
//  * NIENTE VINCOLO DI PAESE. I tipi _eu vanno su Printful solo se la
//    spedizione e' in EU, perche' quel fornitore esiste per evitare la dogana
//    ai clienti europei. Contrado invece e' l'unico posto dove questi
//    prodotti esistono: un ordine dagli Stati Uniti per una cuccia_lux deve
//    andare comunque su Contrado, non su Printify.
//  * NIENTE RIPIEGO SU PRINTIFY. Per i tipi _eu il ripiego e' sicuro: il
//    collare Printify esiste ed e' un prodotto sensato. Per i tipi _lux no:
//    ripiegare vorrebbe dire evadere l'ordine di una cuccia premium con la
//    cuccia Printify da 64,99 euro -- prodotto diverso, qualita' diversa,
//    senza l'etichetta a marchio per cui il cliente ha pagato. Qui si
//    restituisce 'contrado' anche senza chiave configurata, cosi' il client
//    solleva un errore esplicito che il sync ordini registra per un
//    controllo manuale (vedi providers/contrado-client.js).
const CONTRADO_TYPES = {
  cuccia_lux: 'contrado',
  guinzaglio_lux: 'contrado',
  bandana_lux: 'contrado',
  ciotola_lux: 'contrado',
  tappetino_lux: 'contrado',
  coperta_lux: 'contrado',
};

const printifyClient = require('./providers/printify-client');
const printfulClient = require('./providers/printful-client');
const contradoClient = require('./providers/contrado-client');

const CLIENTS = {
  printify: printifyClient,
  printful: printfulClient,
  contrado: contradoClient,
};

function isEuShipping(order) {
  const country = order.shipping_address && order.shipping_address.country_code;
  return !!country && PERLA_EU_COUNTRIES.indexOf(country) !== -1;
}

// Ritorna il NOME del fornitore da usare (non il client): utile per i log e
// per i test, separato da chooseClient cosi' si puo' verificare la regola
// senza dover chiamare API vere.
function chooseProviderName(productType, order, env) {
  // Prima di tutto il resto: i tipi _lux esistono solo su Contrado, in
  // qualunque paese e con o senza chiave configurata (vedi CONTRADO_TYPES).
  if (CONTRADO_TYPES[productType]) {
    return CONTRADO_TYPES[productType];
  }
  const euProvider = EU_CAPABLE_TYPES[productType];
  if (euProvider && isEuShipping(order) && env[euProvider.toUpperCase() + '_API_KEY']) {
    return euProvider;
  }
  return 'printify';
}

function chooseClient(productType, order, env) {
  return CLIENTS[chooseProviderName(productType, order, env)];
}

module.exports = { chooseClient, chooseProviderName, isEuShipping, PERLA_EU_COUNTRIES, EU_CAPABLE_TYPES, CONTRADO_TYPES };
