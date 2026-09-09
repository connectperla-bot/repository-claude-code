'use strict';

// CHE VERSIONE STA GIRANDO, E LE COSE CHE LE MANCANO.
//
// PERCHE' ESISTE. Il 9 settembre 2026 Render ha detto "deploy failed" e non
// c'era modo di rispondere alla domanda successiva, che e' l'unica che conta:
// il negozio sta servendo il codice vecchio o quello nuovo? I tre servizi
// stanno sul piano gratuito, i cui log non si conservano; l'unico modo per
// saperlo e' stato mandare un ordine di prova vero e andare a guardare cosa
// era arrivato dall'altra parte. Funziona, ma e' un'indagine da mezz'ora per
// una cosa che deve costare una riga.
//
// E c'e' un secondo modo di sbagliare, piu' insidioso del deploy fallito: il
// deploy RIUSCITO a cui manca una variabile d'ambiente. Il servizio parte,
// risponde, sembra sano, e poi fallisce solo quando arriva l'ordine di un
// cliente vero -- perche' quella chiave serviva li'. E' gia' successo due
// volte (ROUND 33 e ROUND 45, vedi i commenti in render.yaml).
//
// Quindi /health dice tre cose: quale commit sta girando, se le chiavi che
// servono ci sono, e quali mancano.
//
// NON ESCE MAI UN VALORE. Solo il NOME della variabile e un si'/no. I nomi
// stanno gia' in chiaro in render.yaml e in config/printify.env.example, che
// sono nel repository: non si scopre niente di nuovo. I valori invece non
// devono uscire da qui nemmeno per sbaglio, ed e' per questo che questa
// funzione non ha modo di stamparli -- vede le chiavi, non i contenuti.
//
// Le variabili RENDER_* le mette Render da solo a ogni deploy: non vanno
// configurate. Fuori da Render (sul portatile) semplicemente non ci sono, e
// la versione risulta "sconosciuta", che e' la verita'.

function versione(env) {
  const commit = env.RENDER_GIT_COMMIT || '';
  return {
    commit: commit ? commit.slice(0, 7) : 'sconosciuto',
    ramo: env.RENDER_GIT_BRANCH || 'sconosciuto',
    istanza: env.RENDER_INSTANCE_ID || 'locale',
  };
}

// chiaviRichieste: senza queste il servizio non fa il suo mestiere.
// chiaviUtili:     senza queste funziona, ma peggio (e va detto).
function salute(env, servizio, chiaviRichieste, chiaviUtili) {
  const richieste = chiaviRichieste || [];
  const utili = chiaviUtili || [];

  const configurate = {};
  const mancanti = [];
  const mancantiUtili = [];

  // Una variabile impostata alla stringa vuota su Render e' l'errore piu'
  // difficile da vedere: c'e', ma non vale niente. Qui conta come mancante.
  function valorizzata(k) {
    return typeof env[k] === 'string' && env[k].trim() !== '';
  }

  for (const k of richieste) {
    configurate[k] = valorizzata(k);
    if (!configurate[k]) mancanti.push(k);
  }
  for (const k of utili) {
    configurate[k] = valorizzata(k);
    if (!configurate[k]) mancantiUtili.push(k);
  }

  return {
    ok: mancanti.length === 0,
    servizio: servizio,
    versione: versione(env),
    configurazione: configurate,
    mancanti: mancanti,
    mancantiUtili: mancantiUtili,
  };
}

module.exports = { salute, versione };
