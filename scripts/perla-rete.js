'use strict';

// UNA CHIAMATA IN USCITA CHE NON PUO' RESTARE APPESA.
//
// PERCHE' SERVE
// fetch in Node non ha un timeout di suo: se Shopify, Printify o Printful
// smettono di rispondere -- non con un errore, proprio smettono -- la nostra
// chiamata aspetta finche' il sistema operativo non chiude la connessione, che
// possono essere minuti. Nel frattempo il cliente ha la rotellina che gira, e
// il servizio tiene occupata una connessione per niente.
//
// Su /ordine/annulla e' peggio che altrove: quella pagina rimborsa dei soldi, e
// il cliente che non riceve risposta ricarica e riprova. Meglio dirgli "non ci
// riusciamo adesso" dopo quindici secondi che lasciarlo davanti a una pagina
// che non finisce mai.
//
// LE DUE MISURE
//   LETTURA (15s)  chiedere lo stato di un ordine. Se un fornitore ci mette
//                  piu' di quindici secondi a dire com'e' messo un ordine, non
//                  ce lo dira' comunque.
//   SCRITTURA (30s) annullare, creare un ordine, caricare un file. Piu' lunga
//                  perche' dall'altra parte c'e' del lavoro vero, e perche'
//                  interrompere a meta' una scrittura lascia le cose in un
//                  posto scomodo: meglio dare tempo.
//
// Un timeout NON e' un annullamento: se scade mentre il fornitore stava
// eseguendo, l'operazione puo' essere andata a buon fine lo stesso. Per questo
// l'errore lo dice, e chi chiama deve ricontrollare lo stato invece di
// ripetere alla cieca.

const LETTURA_MS = 15000;
const SCRITTURA_MS = 30000;

/**
 * Come fetch, ma con una scadenza.
 *
 * @param {string} url
 * @param {object} [opzioni]   le stesse di fetch
 * @param {number} [ms]        quanto aspettare; per difetto la misura lettura
 * @returns {Promise<Response>}
 * @throws  Error con .scaduta = true se e' scaduta, cosi' chi chiama puo'
 *          distinguere "non ha risposto" da "ha risposto male".
 */
async function chiedi(url, opzioni, ms) {
  const attesa = ms || LETTURA_MS;
  try {
    return await fetch(url, Object.assign({}, opzioni, {
      signal: AbortSignal.timeout(attesa),
    }));
  } catch (err) {
    // TimeoutError arriva da AbortSignal.timeout, AbortError da un abort
    // esterno: per chi chiama sono la stessa cosa.
    if (err && (err.name === 'TimeoutError' || err.name === 'AbortError')) {
      const e = new Error(
        'Nessuna risposta entro ' + (attesa / 1000).toFixed(1).replace(/\.0$/, '') + 's da ' + soloHost(url) +
        '. L\'operazione potrebbe essere andata a buon fine lo stesso: ricontrollare lo stato prima di ripetere.'
      );
      e.scaduta = true;
      e.host = soloHost(url);
      throw e;
    }
    throw err;
  }
}

/** Come chiedi(), con la misura piu' lunga: per chi scrive, non per chi legge. */
function scrivi(url, opzioni) {
  return chiedi(url, opzioni, SCRITTURA_MS);
}

/** Solo l'host, per non finire l'URL intera (con eventuali chiavi) nei log. */
function soloHost(url) {
  try {
    return new URL(String(url)).host;
  } catch (e) {
    return 'il fornitore';
  }
}

module.exports = { chiedi, scrivi, LETTURA_MS, SCRITTURA_MS };
