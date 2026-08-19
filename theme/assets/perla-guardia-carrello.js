(function () {
  'use strict';

  // ROUND 45 -- LA GUARDIA SUL CARRELLO.
  //
  // IL DIFETTO CHE CHIUDE
  // Nello studio di personalizzazione, quando il caricamento su /upload
  // fallisce, il .catch del tema SVUOTA il dato:
  //     bakedImageId = ""  ->  writePropData()  ->  propData.value = ""
  // e il gestore di "aggiungi al carrello" non guarda mai se il caricamento e'
  // riuscito: `ensure.then(...)` prosegue e basta, perche' composeAndUpload()
  // ha un .catch interno e quindi la promessa risolve SEMPRE.
  //
  // Il prodotto entra in carrello con properties[_Personalizzazione] vuota, il
  // pulsante dice "Aggiunto!", e il messaggio d'errore resta in un paragrafo
  // che nel frattempo nessuno guarda. A valle,
  // perla-printify-order-sync.js scarta le righe con valore vuoto.
  //
  // Risultato: il cliente paga, riceve la conferma d'ordine, e non si stampa
  // niente. Nessun log, nessuna segnalazione. Lo scopre lui.
  //
  // PERCHE' QUI E NON DENTRO global.js
  // global.js e' minificato in un file unico da 89 kB: mettere la guardia li'
  // significa riscriverlo tutto a ogni ritocco. Qui la regola sta in un file
  // leggibile, si rilegge in un minuto, e si toglie togliendo una riga da
  // layout/theme.liquid.
  //
  // COME RICONOSCE IL GUASTO, SENZA FALSI POSITIVI
  // Due segnali, che devono valere ENTRAMBI, presi dentro il form che si sta
  // inviando (non da tutta la pagina):
  //
  //   1. il campo del design e' vuoto;
  //   2. lo studio sta MOSTRANDO un errore
  //      ([data-photo-status] con la classe product-personalize__status--error,
  //      che setPhotoStatus toglie da sola appena un caricamento riesce).
  //
  // Serve il secondo segnale perche' il campo vuoto, da solo, e' anche il caso
  // legittimo di chi non vuole personalizzare niente: la tela vuota non genera
  // composito di proposito (hasContent nel tema), ed e' un caso che il
  // servizio ordini gestisce apposta. Bloccare quello sarebbe peggio del
  // difetto.
  //
  // FASE DI CATTURA
  // Il tema registra il proprio submit sul form in fase di risalita. Questo
  // ascoltatore sta su document in fase di CATTURA, quindi parte prima, e
  // stopImmediatePropagation() impedisce che il gestore del tema parta del
  // tutto -- altrimenti la riga finirebbe in carrello lo stesso.

  var CLASSE_ERRORE = 'product-personalize__status--error';
  var MESSAGGIO = 'Il tuo design non è stato caricato, quindi non possiamo ' +
    'stamparlo. Aspetta qualche secondo e riprova: se l’errore resta, ' +
    'ricarica la pagina.';

  function eUnFormCarrello(form) {
    if (!form || form.nodeName !== 'FORM') return false;
    var action = form.getAttribute('action') || '';
    return action.indexOf('/cart/add') !== -1;
  }

  function designMancante(form) {
    var campi = form.querySelectorAll('[data-photo-prop-data]');
    // Nessun campo del design: prodotto non personalizzabile, non ci riguarda.
    if (!campi.length) return false;
    var qualcunoVuoto = false;
    for (var i = 0; i < campi.length; i++) {
      if (!campi[i].value) qualcunoVuoto = true;
    }
    if (!qualcunoVuoto) return false;
    // Vuoto per guasto o vuoto per scelta? Lo dice lo stato dell'editor.
    return !!form.querySelector('[data-photo-status].' + CLASSE_ERRORE);
  }

  function avvisa(form) {
    var stato = form.querySelector('[data-photo-status]');
    if (stato) {
      stato.textContent = MESSAGGIO;
      stato.classList.add(CLASSE_ERRORE);
      if (typeof stato.scrollIntoView === 'function') {
        stato.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }
    // Il tema mette is-loading sul pulsante PRIMA di chiamare il submit: se non
    // si toglie, il cliente resta con un pulsante che gira per sempre.
    var bottone = form.querySelector('[data-add-btn]');
    if (bottone) {
      bottone.classList.remove('is-loading');
      bottone.disabled = false;
    }
  }

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!eUnFormCarrello(form)) return;
    if (!designMancante(form)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    avvisa(form);
  }, true);
})();
