'use strict';

// Sceglie la variante da ordinare allo stampatore in base alla taglia che il
// cliente ha davvero scelto e pagato.
//
// PERCHE' ESISTE
// Fino a ROUND 42 handleCustomItem passava allo stampatore un SOLO id di
// variante per tipo prodotto, preso da una variabile d'ambiente
// (COLLARE_VARIANT_ID, CUCCIA_VARIANT_ID, ...), identico per ogni ordine. La
// taglia scelta dal cliente non veniva letta da nessuna parte: ne'
// item.variant_title ne' le opzioni della riga d'ordine comparivano nel
// codice. Chi comprava una cuccia 50"x40" a 119,99 EUR riceveva la variante
// fissa configurata -- e lo stesso valeva per taglia E finitura del collare,
// che ha dodici varianti.
//
// Riguarda solo gli ordini PERSONALIZZATI, quelli che passano di qui: gli
// altri li sincronizza l'app dello stampatore, che le taglie le mappa da
// sola. Ma la personalizzazione e' il motivo per cui esiste il negozio.
//
// DA DOVE VENGONO GLI ID
// Da printify-blueprints/*.json, gia' nel repository (salvati il 2026-07-10
// dall'API Printify). I titoli delle varianti Printify coincidono con i
// titoli delle varianti Shopify -- e' quello che rende possibile
// l'abbinamento senza nessuna configurazione da mantenere a mano.
//
// SE UN TITOLO NON CORRISPONDE
// Si solleva un errore invece di ripiegare sulla variante fissa. Un ordine
// che si ferma e finisce nei log e' recuperabile a mano; un ordine spedito
// nella taglia sbagliata e' un reso e un cliente perso. Il chiamante
// elabora ogni riga nel suo try/catch, quindi si ferma solo quella riga.

// tipo prodotto -> titolo variante Shopify -> id variante dello stampatore
//
// DUE TITOLI PER LO STESSO ID
// I titoli su Shopify sono ancora quelli inglesi in pollici ereditati da
// Printify ('28" x 18"', 'S / Black Onyx / TPU'). Vanno tradotti in italiano e
// in centimetri, ma il giorno che si cambiano gli ordini gia' in carrello
// arrivano ancora col titolo vecchio: se la mappa conoscesse solo i nuovi,
// quegli ordini si fermerebbero. Elencando entrambi la traduzione si puo' fare
// senza finestre di rischio, e i vecchi si potranno togliere piu' avanti.
const VARIANTI = {
  // printify-blueprints/784_93.json (Dog Collar, provider C4)
  collare: {
    'S / Black Onyx / TPU': 74897,   'S / Onice': 74897,
    'S / Gun Metal / TPU': 74898,    'S / Canna di fucile': 74898,
    'S / Vintage Brass / TPU': 74900, 'S / Ottone anticato': 74900,
    'M / Black Onyx / TPU': 74901,   'M / Onice': 74901,
    'M / Gun Metal / TPU': 74902,    'M / Canna di fucile': 74902,
    'M / Vintage Brass / TPU': 74904, 'M / Ottone anticato': 74904,
    'L / Black Onyx / TPU': 74905,   'L / Onice': 74905,
    'L / Gun Metal / TPU': 74906,    'L / Canna di fucile': 74906,
    'L / Vintage Brass / TPU': 74908, 'L / Ottone anticato': 74908,
    'XL / Black Onyx / TPU': 74909,  'XL / Onice': 74909,
    'XL / Gun Metal / TPU': 74910,   'XL / Canna di fucile': 74910,
    'XL / Vintage Brass / TPU': 74912, 'XL / Ottone anticato': 74912,
  },
  // printify-blueprints/419_10.json (Pet Bed, provider MWW On Demand)
  cuccia: {
    '28" x 18"': 61436, 'Piccola (71 x 46 cm)': 61436,
    '40" x 30"': 61437, 'Media (102 x 76 cm)': 61437,
    '50" x 40"': 61435, 'Grande (127 x 102 cm)': 61435,
  },
  // printify-blueprints/562_70.json (Pet Bandana, provider Printed Mint)
  bandana: {
    '20" x 10"': 101403, 'Piccola (51 x 25 cm)': 101403,
    '27" x 13"': 101404, 'Grande (69 x 33 cm)': 101404,
  },
  // printify-blueprints/566_70.json (Pet Tag, provider Printed Mint) -- una
  // sola variante, ma elencata lo stesso: se domani ne aggiungono un'altra,
  // il controllo esiste gia'
  medaglietta: {
    '1"': 70870, 'Unica (2,5 cm)': 70870,
  },

  // ---- linea EU, fornitore Printful (printful-catalog/*.json) -------------
  //
  // ROUND 44 -- fino a ieri questi tipi non erano qui dentro, e finivano nel
  // ramo "variante unica" di scegliVariante(): un solo id preso da variabile
  // d'ambiente, uguale per ogni ordine. Andava bene finche' si vendeva una
  // taglia sola. Nel momento in cui si aggiungono M e L, senza queste mappe
  // ogni ordine partirebbe come S -- lo stesso difetto di ROUND 42, spostato
  // sulla linea europea.
  //
  // Le tre misure costano identiche allo stampatore (bandana 10,15 EUR,
  // collare 17,23 EUR), quindi si vendono allo stesso prezzo: il titolo della
  // variante e' l'unica cosa che cambia, ed e' esattamente cio' che qui si
  // traduce in id.

  // printful-catalog/630.json -- S 44x44, M 54x54, L 64x64 cm
  bandana_eu: {
    'S': 16031, 'S / Piccola (44 cm)': 16031, 'Piccola (44 cm)': 16031,
    'M': 16032, 'M / Media (54 cm)': 16032,   'Media (54 cm)': 16032,
    'L': 16033, 'L / Grande (64 cm)': 16033,  'Grande (64 cm)': 16033,
  },
  // printful-catalog/749.json -- collo S 30-45, M 35-52, L 38-60 cm
  collare_eu: {
    'S': 19186, 'S / Collo 30-45 cm': 19186, 'Collo 30-45 cm': 19186,
    'M': 19187, 'M / Collo 35-52 cm': 19187, 'Collo 35-52 cm': 19187,
    'L': 19188, 'L / Collo 38-60 cm': 19188, 'Collo 38-60 cm': 19188,
  },
  // printful-catalog/678.json -- 530 ml e 950 ml
  ciotola_eu: {
    '18 oz': 16785, '530 ml': 16785, 'Piccola (530 ml)': 16785,
    '32 oz': 16786, '950 ml': 16786, 'Grande (950 ml)': 16786,
  },
  // guinzaglio_eu resta fuori di proposito: Printful lo fa in una misura sola
  // (1,83 m), quindi non c'e' niente da scegliere e vale la configurazione.
};

// I titoli veri contengono il segno di moltiplicazione (U+00D7), le virgolette
// tipografiche e spazi variabili a seconda di chi li ha scritti. Confrontarli
// alla lettera farebbe fallire ordini buoni, quindi si normalizza prima.
function normalizza(titolo) {
  return String(titolo == null ? '' : titolo)
    .replace(/[×✕✖]/g, 'x')      // × e simili -> x
    .replace(/[‘’ʼ]/g, "'")      // apostrofi tipografici
    .replace(/[“”″]/g, '"')      // virgolette tipografiche e doppio primo
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function indiceNormalizzato(mappa) {
  const fuori = {};
  for (const chiave of Object.keys(mappa)) {
    fuori[normalizza(chiave)] = mappa[chiave];
  }
  return fuori;
}

/**
 * @param {string} productType  es. 'cuccia', 'collare_eu'
 * @param {string} variantTitle il titolo della variante scelta dal cliente
 * @param {object} config       la voce di PRODUCT_TYPE_CONFIG, con variantId
 * @returns {number} l'id della variante da ordinare allo stampatore
 */
function scegliVariante(productType, variantTitle, config) {
  const mappa = VARIANTI[productType];

  // Tipi a variante unica (tutta la linea EU, dove ogni prodotto Shopify ha
  // una sola variante): non c'e' niente da scegliere, vale il valore
  // configurato.
  if (!mappa) {
    return config && config.variantId;
  }

  const trovata = indiceNormalizzato(mappa)[normalizza(variantTitle)];
  if (trovata) return trovata;

  throw new Error(
    'Variante "' + variantTitle + '" non riconosciuta per il tipo "' + productType +
    '". Le varianti previste sono: ' + Object.keys(mappa).join(', ') + '. ' +
    'L\'ordine NON e\' stato inviato in stampa di proposito: spedirlo con la ' +
    'variante di ripiego significherebbe mandare al cliente una taglia diversa ' +
    'da quella che ha pagato. Se hai cambiato i nomi delle opzioni su Shopify, ' +
    'aggiorna VARIANTI in scripts/varianti-fornitore.js con i nuovi titoli.'
  );
}

module.exports = { scegliVariante, normalizza, VARIANTI };
