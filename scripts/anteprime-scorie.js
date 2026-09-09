'use strict';

// Quali prodotti temporanei dell'anteprima si possono buttare.
//
// PERCHE' ESISTE UN FILE PER TRE RIGHE
// /generate-mockup crea su Printify un prodotto usa-e-getta, ne prende le
// immagini e lo cancella dieci minuti dopo con un setTimeout. Prima non si
// puo': Printify serve le immagini del mockup finche' il prodotto esiste, e
// cancellarlo subito spegnerebbe l'anteprima sotto gli occhi del cliente --
// difetto gia' visto e corretto una volta ("schermo blu, l'anteprima non si
// apre").
//
// Ma un setTimeout vive quanto il processo, e il servizio gira sul piano
// gratuito di Render, che lo addormenta dopo un quarto d'ora senza richieste.
// Se si spegne -- o si riavvia per un deploy -- prima che il timer scatti,
// quel prodotto resta su Printify per sempre. Verificato il 9 settembre 2026:
// tre anteprime generate per la prova, tre prodotti rimasti nel catalogo.
//
// Da qui la spazzata all'avvio, in perla-upload-endpoint.js. La regola sta
// pero' qui, staccata dalla chiamata di rete, per due motivi: e' l'unico
// pezzo che puo' fare danno, e si puo' provare senza parlare con Printify.
//
// IL DANNO DA EVITARE non e' lasciare una scoria: e' cancellare l'anteprima
// che un cliente sta guardando in quel momento. Percio' il titolo deve
// combaciare esatto, l'eta' deve superare la soglia, e una data che non si
// legge vale "lascia stare" -- cancellare non si disfa.

const ANTEPRIMA_TITOLO = 'Perla - Anteprima temporanea';
const ANTEPRIMA_ETA_MIN = 15;

function scorieDaButtare(elenco, adesso) {
  const limite = adesso - ANTEPRIMA_ETA_MIN * 60 * 1000;
  return (elenco || []).filter(function (p) {
    if (!p || p.title !== ANTEPRIMA_TITOLO) return false;
    // Il controllo sulla data non basta che sia "finita": new Date(null) vale
    // zero, cioe' il 1970, che e' finito e vecchissimo -- un prodotto senza
    // created_at sarebbe finito nel mucchio da cancellare. Il test lo ha
    // trovato prima che ci finisse davvero. Serve una stringa, e una data che
    // sta dopo l'epoca.
    if (typeof p.created_at !== 'string' || !p.created_at) return false;
    const nato = new Date(p.created_at).getTime();
    if (!isFinite(nato) || nato <= 0) return false;
    return nato < limite;
  });
}

module.exports = { scorieDaButtare, ANTEPRIMA_TITOLO, ANTEPRIMA_ETA_MIN };
