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

  // ROUND 48 -- DUE MOTIVI IN PIU' PER FERMARSI.
  //
  // Il difetto segnalato: "quando provo a personalizzare la prima volta esce
  // 'testo' bianco e spostato invece della scritta". La causa sta in
  // assets/global.js e si legge per esteso in assets/perla-editor-sveglia.js;
  // qui interessa cosa arriva in carrello.
  //
  //   1. COMPOSIZIONE ANCORA IN CORSO. composeAndUpload ha una guardia
  //      `composing` che, mentre un caricamento e' in volo, restituisce la
  //      PROMESSA VECCHIA invece di comporre di nuovo. Quando quella vecchia
  //      atterra, writePropData scrive il SUO composito nel campo del carrello
  //      e lo stato dice "Design pronto." -- anche se intanto il cliente ha
  //      cambiato il disegno. Comprare in quella finestra vuol dire pagare una
  //      cosa e riceverne un'altra.
  //
  //   2. IL SEGNAPOSTO MAI SOSTITUITO. "+ Testo" crea il livello gia' pieno:
  //      new fabric.IText("Testo", {left: canvasW/2 + cascadeOffset(), top:
  //      canvasH/2 + cascadeOffset(), ...}). Chi lo aggiunge e non ci scrive
  //      dentro manda in stampa la parola "Testo", al centro del prodotto --
  //      ed e' anche il "spostato" della segnalazione, perche' il nome vero
  //      nasce invece a canvasH*.85.
  //
  // Tutti e due si riconoscono dal DOM, senza toccare global.js: writePropData
  // riversa collectNameText() dentro [data-photo-prop-name-text] a ogni giro,
  // quindi quel campo e' uno specchio vivo di cosa c'e' scritto sul riquadro.
  //
  // SUL FALSO POSITIVO DEL PUNTO 2
  // Chi volesse davvero stampare la parola "Testo" viene fermato a torto. Su
  // un collare per cani non capitera', e i due errori non pesano uguale:
  // fermarlo a torto costa un messaggio da leggere, lasciarlo passare costa un
  // ordine pagato e sbagliato.

  // ROUND 50 -- IL BUCO CHE LA GUARDIA NON POTEVA VEDERE, E IL BOTTONE CHE CRESCE.
  //
  // Segnalazione: "l'aggiunta al carrello non funziona alcune volte, tipo su
  // quello personalizzato a cui aggiungi il nome; se clicco aggiungi il
  // bottone diventa enorme per poco ma non ha effetto".
  //
  // Sono due guasti, e nascono tutti e due dallo stesso punto: e' il clic su
  // "Aggiungi al carrello" a far partire la composizione del disegno.
  //
  //   IL BUCO. I controlli qui sopra guardano il campo del design PRIMA che il
  //   gestore del tema parta. Ma se il disegno non era ancora stato composto,
  //   a comporlo e' quel clic: global.js chiama __perlaEnsureComposed() e
  //   aspetta. Se il caricamento fallisce li' dentro, composeAndUpload() se lo
  //   mangia --
  //       .catch(function(){ bakedImageId=""; writePropData();
  //                          setPhotoStatus(status, composeError, true) })
  //   -- la promessa RISOLVE lo stesso, e il tema prosegue: FormData(form),
  //   POST a /cart/add, "Aggiunto!". La guardia era gia' passata. E' lo stesso
  //   danno di ROUND 45 (il cliente paga e non si stampa niente) da un ingresso
  //   che ROUND 45 non copriva.
  //
  //   L'ATTESA SENZA FONDO. `ensure.then(...)` non ha alcun limite. Il servizio
  //   che compone sta su un piano gratuito e si addormenta: misurato il 3
  //   settembre 2026, la prima chiamata ha impiegato 12,6 secondi, le
  //   successive 0,5. Dodici secondi con un bottone che gira sono, per chi
  //   guarda, "non ha effetto".
  //
  //   IL BOTTONE ENORME. Non e' un difetto di stile: il tema scrive nel
  //   bottone P.strings.composing al posto di "Aggiungi al carrello", e il
  //   bottone si allarga per contenerlo.
  //
  // COME SI CHIUDONO SENZA RISCRIVERE IL CARRELLO
  // Questo ascoltatore sta in fase di CATTURA, quindi parte prima del gestore
  // del tema; e il tema legge `pr.__perlaEnsureComposed` solo dopo, quando
  // parte lui. In quella finestra si puo' sostituire quella funzione con una
  // che fa le stesse cose piu' due: si arrende dopo LIMITE_COMPOSIZIONE, e
  // ricontrolla il campo del design DOPO che la composizione e' finita.
  //
  // Quando si arrende, RIFIUTA con un oggetto che porta `.description`, perche'
  // il ramo d'errore del tema e' gia' scritto cosi':
  //     .catch(function(err){ txt.textContent = err && err.description
  //                             ? err.description : P.strings.cartError; ... })
  // quindi il messaggio compare da solo, is-loading viene tolto dal codice del
  // tema, e -- la cosa che conta -- il fetch a /cart/add NON parte mai. Nessuna
  // logica del carrello duplicata qui dentro.

  var CLASSE_ERRORE = 'product-personalize__status--error';
  var SEGNAPOSTO = 'Testo';
  var COMPONENDO_DI_SCORTA = 'Preparazione dell\'immagine...';

  var MESSAGGIO = 'Il tuo design non è stato caricato, quindi non possiamo ' +
    'stamparlo. Aspetta qualche secondo e riprova: se l’errore resta, ' +
    'ricarica la pagina.';
  var MESSAGGIO_ATTESA = 'Sto ancora preparando il disegno: se lo aggiungi ' +
    'adesso rischi di ordinare la versione di un attimo fa. Un secondo e ' +
    'riprova.';
  var MESSAGGIO_SEGNAPOSTO = 'C’è un riquadro di testo con scritto ancora ' +
    '«Testo»: tocca la scritta e cambiala, oppure cancella il riquadro. ' +
    'Altrimenti «Testo» verrebbe stampato davvero.';

  // ROUND 50 -- quanto si aspetta, e cosa si dice.
  var LIMITE_COMPOSIZIONE = 20000;   // 12,6 s misurati a freddo: 20 lascia margine

  // Due lunghezze per lo stesso guasto, perche' finiscono in due posti diversi:
  // sul BOTTONE ci sta una riga corta, nel paragrafo di stato sotto l'editor
  // c'e' spazio per dire cosa fare.
  var BOTTONE_NON_PRONTO = 'Disegno non pronto';
  var MESSAGGIO_LENTO = 'Il disegno non è ancora pronto: il servizio che ' +
    'lo prepara ci sta mettendo troppo. Aspetta qualche secondo e riprova.';

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

  // Il testo che global.js mette mentre compone. Si legge dalle stringhe del
  // tema (che seguono la lingua della vetrina) con lo stesso ripiego che usa
  // global.js, cosi' i due non possono divergere. Letto a ogni controllo e non
  // una volta sola: window.Perla e' definito nel <head>, ma dipendere
  // dall'ordine di caricamento per una stringa non vale il rischio.
  function testoComponendo() {
    var P = window.Perla || {};
    return ((P.strings && P.strings.composing) || COMPONENDO_DI_SCORTA).trim();
  }

  function composizioneInCorso(form) {
    var atteso = testoComponendo();
    var stati = form.querySelectorAll('[data-photo-status]');
    for (var i = 0; i < stati.length; i++) {
      if ((stati[i].textContent || '').trim() === atteso) return true;
    }
    return false;
  }

  function segnapostoRimasto(form) {
    // collectNameText() unisce i livelli con " / ": va guardato pezzo per
    // pezzo, altrimenti "Rocky / Testo" -- nome scritto sul primo riquadro e
    // segnaposto dimenticato sul secondo -- passerebbe liscio.
    var campi = form.querySelectorAll('[data-photo-prop-name-text]');
    for (var i = 0; i < campi.length; i++) {
      var pezzi = (campi[i].value || '').split(' / ');
      for (var j = 0; j < pezzi.length; j++) {
        if (pezzi[j].trim() === SEGNAPOSTO) return true;
      }
    }
    return false;
  }

  // Un motivo solo per volta, nell'ordine in cui conviene dirli: prima il
  // guasto, poi l'attesa, poi la svista. Restituisce null quando si puo'
  // comprare.
  function motivoPerFermare(form) {
    if (!form.querySelectorAll('[data-photo-prop-data]').length) return null;
    if (designMancante(form)) return MESSAGGIO;
    if (composizioneInCorso(form)) return MESSAGGIO_ATTESA;
    if (segnapostoRimasto(form)) return MESSAGGIO_SEGNAPOSTO;
    return null;
  }

  function avvisa(form, messaggio) {
    var stato = form.querySelector('[data-photo-status]');
    if (stato) {
      stato.textContent = messaggio || MESSAGGIO;
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


  // --- ROUND 50: il limite di attesa e la misura del bottone ---------------

  // Vero solo dentro l'invio del form. L'anteprima "mockup reale" chiama la
  // stessa __perlaEnsureComposed, ma li' un rifiuto non c'entra niente: quel
  // pulsante ha un suo ramo d'errore e un suo messaggio.
  var dentroAlCarrello = false;

  function conLimite(promessa, ms) {
    return new Promise(function (risolvi, rifiuta) {
      var scattato = false;
      var timer = setTimeout(function () {
        scattato = true;
        rifiuta({ description: BOTTONE_NON_PRONTO, perlaDettaglio: MESSAGGIO_LENTO });
      }, ms);
      Promise.resolve(promessa).then(function (valore) {
        if (scattato) return;
        clearTimeout(timer);
        risolvi(valore);
      }, function (errore) {
        if (scattato) return;
        clearTimeout(timer);
        rifiuta(errore);
      });
    });
  }

  function fermata(form, dettaglio) {
    avvisa(form, dettaglio);
    return { description: BOTTONE_NON_PRONTO, perlaDettaglio: dettaglio };
  }

  // Si sostituisce una volta sola per radice: `originale` resta nella chiusura,
  // e la sostituta la richiama sempre, quindi il percorso del tema non cambia.
  // ROUND 59 -- LE DUE VOLTE IN CUI QUESTA GUARDIA NON SI APPLICAVA, IN SILENZIO.
  //
  // 1. QUI SOTTO C'ERA UN'USCITA. "Se __perlaEnsureComposed non e' ancora una
  //    funzione non c'e' niente da avvolgere" -- vero, ma la conclusione era
  //    sbagliata: si rinunciava per sempre. E il momento in cui quella
  //    funzione non c'e' ancora e' esattamente il caso lento, cioe' quello per
  //    cui la guardia e' stata scritta. Adesso si RIPROVA: il tema legge
  //    pr.__perlaEnsureComposed solo quando parte lui, quindi c'e' tempo.
  //
  // 2. LA FINESTRA ERA LARGA UN MACROTASK. `setTimeout(..., 0)` presume che il
  //    gestore del tema chiami __perlaEnsureComposed in modo sincrono. Oggi lo
  //    fa. Il giorno che global.js mettesse un await prima, limite e
  //    ricontrollo salterebbero senza dire niente -- e global.js e' minificato
  //    e fuori dal repository, quindi quel giorno non lo vedremmo arrivare.
  //    Adesso la finestra si chiude quando il bottone torna a riposo, oppure
  //    dopo FINESTRA_MASSIMA: un limite di sicurezza, non un'ipotesi.
  function avvolgiComposizione(form, radice) {
    if (radice.__perlaLimiteMesso) return;
    var originale = radice.__perlaEnsureComposed;
    if (typeof originale !== 'function') return;
    radice.__perlaLimiteMesso = true;
    radice.__perlaEnsureComposed = function () {
      var promessa = originale.apply(radice, arguments);
      if (!dentroAlCarrello) return promessa;
      return conLimite(promessa, LIMITE_COMPOSIZIONE).then(function (valore) {
        // IL RICONTROLLO. Qui la composizione e' finita: se ha fallito, il
        // campo e' vuoto e lo stato porta la classe d'errore -- esattamente
        // cio' che designMancante() sa riconoscere. Prima di adesso questo
        // controllo non poteva esistere, perche' la composizione non era
        // ancora partita.
        var motivo = motivoPerFermare(form);
        if (motivo) throw fermata(form, motivo);
        return valore;
      });
    };
  }

  // Quanto si insiste ad avvolgere, e ogni quanto. Fabric.js a freddo ci mette
  // qualche secondo: venti tentativi ogni 250 ms fanno cinque secondi, che e'
  // piu' di quanto serva e comunque meno del limite di composizione.
  var TENTATIVI_AVVOLGI = 20;
  var PAUSA_AVVOLGI = 250;

  // LA FINESTRA RESTA LARGA UN MACROTASK, ED E' UNA SCELTA.
  //
  // Sembra fragile: presume che il gestore del tema chiami
  // __perlaEnsureComposed in modo sincrono. Oggi lo fa; se domani ci mettesse
  // un await davanti, limite e ricontrollo salterebbero senza dirlo.
  //
  // Ho provato ad allargarla -- a tempo, e poi legandola a is-loading sul
  // pulsante -- e tutte e due le volte ho rotto una garanzia piu' importante:
  // l'anteprima "mockup reale" chiama la STESSA funzione, e con la finestra
  // aperta si prendeva il limite del carrello e un messaggio d'errore che con
  // lei non c'entra niente. C'e' una prova che lo dice a voce, in
  // tests/guardia-carrello.test.js: "l'anteprima mockup non eredita ne' limite
  // ne' ricontrollo".
  //
  // Fra un difetto ipotetico (il tema che diventa asincrono) e un difetto
  // reale (l'anteprima che rifiuta a sproposito) si tiene stretto il secondo.
  // Se un giorno global.js diventa asincrono, il segnale giusto non e' il
  // tempo ne' is-loading: e' che il tema stesso dica quando sta comprando.

  function proteggiComposizione(form) {
    var radici = form.querySelectorAll('[data-photo-customizer]');
    if (!radici.length) return;

    // Non piu' un tentativo solo: se Fabric.js non ha ancora acceso l'editor,
    // si riprova. Vedi la nota su avvolgiComposizione.
    var rimasti = TENTATIVI_AVVOLGI;
    (function riprova() {
      var mancanti = 0;
      for (var i = 0; i < radici.length; i++) {
        avvolgiComposizione(form, radici[i]);
        if (!radici[i].__perlaLimiteMesso) mancanti++;
      }
      if (mancanti && --rimasti > 0) setTimeout(riprova, PAUSA_AVVOLGI);
    })();

    dentroAlCarrello = true;
    setTimeout(function () { dentroAlCarrello = false; }, 0);
  }

  // La misura si prende PRIMA che il tema cambi la scritta, e si rimette a
  // posto appena il bottone torna a riposo. Non si lascia incollata: una
  // larghezza in pixel sopravvissuta a una rotazione dello schermo farebbe
  // sbordare il bottone.
  function fissaLarghezza(form) {
    var bottone = form.querySelector('[data-add-btn]');
    if (!bottone || bottone.__perlaLarghezzaFissa) return;
    if (typeof bottone.getBoundingClientRect !== 'function') return;
    var largo = Math.ceil(bottone.getBoundingClientRect().width);
    if (!largo) return;
    var prima = bottone.style.width;
    bottone.__perlaLarghezzaFissa = true;
    bottone.style.width = largo + 'px';

    var timer = null;
    var osservatore = null;
    function libera() {
      if (timer) { clearTimeout(timer); timer = null; }
      if (osservatore) { osservatore.disconnect(); osservatore = null; }
      bottone.style.width = prima;
      bottone.__perlaLarghezzaFissa = false;
    }
    // Rete di sicurezza: comunque vada -- errore, pagina lasciata a meta',
    // osservatore mai chiamato -- la misura non resta appesa e l'osservatore
    // non resta acceso. E' il difetto che ROUND 50 va a cercare altrove, e
    // sarebbe brutto introdurlo proprio qui.
    timer = setTimeout(libera, LIMITE_COMPOSIZIONE + 5000);
    if (typeof MutationObserver !== 'function') return;
    osservatore = new MutationObserver(function () {
      if (bottone.classList.contains('is-loading')) return;
      if (bottone.classList.contains('is-added')) return;
      libera();
    });
    osservatore.observe(bottone, { attributes: true, attributeFilter: ['class'] });
  }

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!eUnFormCarrello(form)) return;
    var motivo = motivoPerFermare(form);
    if (motivo) {
      e.preventDefault();
      e.stopImmediatePropagation();
      avvisa(form, motivo);
      return;
    }
    // Si passa. Da qui comanda il gestore del tema: ROUND 50 gli mette accanto
    // il limite di attesa, il ricontrollo dopo la composizione e la misura del
    // bottone -- presa prima che sia lui a cambiare la scritta.
    proteggiComposizione(form);
    fissaLarghezza(form);
  }, true);
})();
