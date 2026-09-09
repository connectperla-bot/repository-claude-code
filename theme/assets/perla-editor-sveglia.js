(function () {
  'use strict';

  // ROUND 48 -- L'EDITOR CHE DORME, E LO SCHERMO INTERO CHE SCAPPA.
  //
  // ============================================================ IL PRIMO
  // "L'editor si addormenta e quando provo a personalizzare la prima volta
  //  esce 'testo' bianco e spostato invece della scritta."
  //
  // Tre sintomi, una causa sola. Il servizio di composizione sta su Render nel
  // piano gratuito: si spegne dopo ~15 minuti di silenzio e la prima richiesta
  // dopo deve aspettare che riparta. Misurato: 24,0 secondi a freddo contro
  // 0,52 a caldo, quarantasei volte tanto.
  //
  // La catena, letta dentro assets/global.js:
  //
  //   1. si preme "+ Testo": il livello nasce con scritto dentro la parola
  //      "Testo" (fabric.IText("Testo", ...)), poi enterEditing/selectAll
  //      perche' basti digitare per sostituirla;
  //   2. 700 ms dopo (COMPOSE_DEBOUNCE) parte composeAndUpload, che porta con
  //      se' quello che c'e' sul riquadro in quel momento: la parola "Testo";
  //   3. il servizio e' freddo, quella richiesta resta appesa 24 secondi;
  //   4. nel frattempo il cliente scrive il nome vero. Ogni nuova composizione
  //      trova la guardia `composing` accesa e si limita a restituire la
  //      PROMESSA VECCHIA (`return composing ? (composePending=1,
  //      currentComposePromise) : ...`);
  //   5. arriva il primo risultato, writePropData lo scrive nel campo che
  //      finira' in carrello, e lo stato dice "Design pronto.". Mostrando
  //      "Testo".
  //
  // Il bianco viene dallo stesso freddo: il motivo di sfondo arriva da
  // <endpoint>/pattern-source, cioe' lo stesso servizio addormentato, e il suo
  // errore finisce in un `.catch(function(){})` vuoto. Senza sfondo il fondo
  // resta ignoto, setDefaultTextColor sceglie il ramo "fondo scuro" e
  // l'inchiostro esce #f8f4ec. Lo spostamento viene dal riquadro misurato
  // prima che il motivo arrivasse.
  //
  // COSA FA QUESTO FILE, E COSA NO
  // Sveglia il servizio al primo segno che qualcuno sta per personalizzare,
  // cosi' quando la composizione parte davvero ci mette mezzo secondo invece
  // di ventiquattro: la corsa del punto 4 non ha piu' il tempo di succedere.
  // E quando l'attesa c'e' lo stesso, lo DICE, invece di far credere che sia
  // tutto pronto.
  //
  // Non chiude la guardia `composing` del punto 4, che sta dentro global.js:
  // 89 kB minificati su una riga sola. Va chiusa li', con un contatore di
  // generazione che scarti i risultati vecchi invece di scriverli. Finche' non
  // e' fatto, questo file rende la corsa improbabile, non impossibile: e'
  // scritto qui perche' nessuno lo scambi per una cura definitiva.
  //
  // ============================================================ IL SECONDO
  // "A schermo intero da telefono scorre la pagina dietro invece dell'editor,
  //  e l'ingrandimento non funziona benissimo."
  //
  // Scorrimento: l'unico blocco era `body.pd-open { overflow: hidden }` in
  // assets/perla-studio.css, che su iOS non tiene -- il body non e' l'elemento
  // che scorre. E dentro il modale ci sono TRE contenitori che scorrono uno
  // dentro l'altro (.pd-modal__panel, .pd-modal__body,
  // .fabric-studio__viewport) ma `overscroll-behavior: contain` era scritto
  // solo sul piu' interno: appena il riquadro finisce, lo scorrimento passa al
  // pannello e da li' alla pagina.
  //
  // Ingrandimento: non esiste una sola riga di touchmove o gesturestart in
  // tutto global.js. Pizzicare non faceva niente, e restavano i tre pulsantini
  // dello zoom. Qui il pizzico c'e', e muove quei pulsanti invece di
  // disegnare da capo: e' la strada gia' provata, e lo zoom resta uno solo.
  //
  // Resta fuori anche qui una cosa che sta in global.js: applyViewZoom ha un
  // 560 scritto a mano che duplica un max-height che nel CSS vale
  // min(560px, 62vh) sul telefono e none a schermo intero coricato, e
  // canvasW/canvasH/defaultZoom si calcolano una volta sola all'avvio e non
  // vengono piu' rifatti quando i pannelli entrano nel modale.
  //
  // ============================================================ PERCHE' QUI
  // Stessa ragione di assets/perla-guardia-carrello.js, che sta accanto a
  // questo nello stesso punto di caricamento: global.js e' minificato in un
  // file unico, e ogni ritocco li' dentro vuol dire riscriverlo tutto. Questo
  // file si aggancia solo agli hook data-* che il markup gia' espone e alle
  // classi che il tema gia' mette: se non venisse caricato affatto, l'editor
  // tornerebbe esattamente com'era.

  var EDITOR = '[data-photo-customizer]';

  function primo(sel, radice) { return (radice || document).querySelector(sel); }
  function tutti(sel, radice) {
    return Array.prototype.slice.call((radice || document).querySelectorAll(sel));
  }

  // Il telefono e' l'unico posto dove i difetti qui sopra si vedono, ed e'
  // anche l'unico dove le contromisure sono innocue: bloccare il body con
  // position:fixed su un computer sposterebbe la pagina della larghezza della
  // barra di scorrimento a ogni apertura.
  function eUnDito() {
    return window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  }

  /* ------------------------------------------------------------------ */
  /* 1. LA SVEGLIA                                                       */
  /* ------------------------------------------------------------------ */

  // Attese fra un tentativo e il successivo. Sommate fanno 35 secondi, cioe'
  // piu' dei 24 misurati: un riavvio lento rientra, e non si insiste oltre.
  var ATTESE = [1500, 3000, 6000, 10000, 15000];

  // I codici con cui la piattaforma dice "il tuo processo NON e' ancora su".
  // Tutto il resto -- 200, 404, 401, 500 -- vuol dire che un processo c'e' e
  // risponde, ed e' l'unica cosa che serve sapere. Misurato in produzione il
  // 01/09/2026: prima chiamata 503 dopo 10,6 s (Render sta avviando), seconda
  // 404 dopo 12,7 s (il servizio e' su, ma quella build non ha ancora la rotta
  // /health), terza 404 dopo 0,48 s. Chiedere un 200 faceva dichiarare morto
  // un servizio perfettamente vivo: vedi sveglia().
  var AVVIO_IN_CORSO = [502, 503, 504];

  var svegliaChiesta = false;
  var servizioPronto = false;
  var rinunciato = false;

  function indirizzoSalute() {
    var root = primo(EDITOR);
    if (!root) return '';
    var endpoint = root.getAttribute('data-upload-endpoint') || '';
    if (!endpoint) return '';
    try {
      var u = new URL(endpoint);
      u.pathname = u.pathname.replace(/\/upload\/?$/, '') + '/health';
      u.search = '';
      return u.toString();
    } catch (e) {
      return '';
    }
  }

  function sveglia() {
    if (svegliaChiesta) return;
    svegliaChiesta = true;
    var url = indirizzoSalute();
    if (!url) return;               // servizio non configurato: niente da svegliare

    var passo = 0;
    function tenta() {
      fetch(url, { method: 'GET', cache: 'no-store' })
        .then(function (r) {
          // QUALUNQUE risposta che non sia un errore di avvio vuol dire che il
          // servizio e' sveglio: ha un processo che ascolta. Un 404 lo dice
          // benissimo -- e succede davvero, perche' finche' il ramo non e'
          // unito Render serve una build che la rotta /health non ce l'ha.
          // Nella prima versione qui c'era `if (!r.ok) throw`: quel 404
          // mandava la sveglia a esaurire tutti i tentativi e poi a mostrare
          // "il servizio non risponde" a un cliente il cui servizio rispondeva
          // in mezzo secondo. Il falso allarme e' peggio del silenzio.
          if (AVVIO_IN_CORSO.indexOf(r.status) !== -1) throw new Error('sta partendo');
          servizioPronto = true;
          togliAttesa();
        })
        .catch(function () {
          if (passo >= ATTESE.length) { rinunciato = true; diLaVerita(); return; }
          setTimeout(tenta, ATTESE[passo++]);
        });
    }
    tenta();
  }

  /* ------------------------------------------------------------------ */
  /* 2. L'ATTESA DETTA, NON NASCOSTA                                     */
  /* ------------------------------------------------------------------ */

  // Elemento nostro, non [data-photo-status]: quello lo scrive global.js con
  // setPhotoStatus, e due mani sullo stesso paragrafo vuol dire messaggi che
  // si cancellano a vicenda. La classe e' la stessa solo per ereditarne lo
  // stile.
  var CLASSE = 'product-personalize__status perla-attesa';

  function mostraAttesa() {
    if (servizioPronto) return;
    tutti(EDITOR).forEach(function (root) {
      if (primo('.perla-attesa', root)) return;
      var p = document.createElement('p');
      p.className = CLASSE;
      p.setAttribute('role', 'status');
      p.setAttribute('aria-live', 'polite');
      p.textContent = rinunciato
        ? 'L’editor ci sta mettendo piu’ del solito. Puoi comporre il disegno lo stesso: prima di aggiungere al carrello aspetta che dica "Design pronto".'
        : 'Sto preparando l’editor, un momento. Intanto puoi gia’ scrivere.';
      root.appendChild(p);
    });
  }

  function togliAttesa() {
    tutti('.perla-attesa').forEach(function (p) {
      if (p.parentNode) p.parentNode.removeChild(p);
    });
  }

  function diLaVerita() {
    togliAttesa();
    mostraAttesa();
  }

  /* ------------------------------------------------------------------ */
  /* 3. QUANDO SVEGLIARE                                                 */
  /* ------------------------------------------------------------------ */

  // NON al caricamento della pagina, e non appena l'editor entra nello
  // schermo: quella sarebbe una chiamata per ogni visita, il servizio non si
  // spegnerebbe quasi mai e le ore gratuite di Render finirebbero. Si sveglia
  // al primo tocco su una pagina che HA un editor -- chi tocca sta guardando
  // il prodotto, e da li' alla personalizzazione passano secondi, che e'
  // esattamente il vantaggio che serve.
  //
  // Il messaggio d'attesa invece compare solo quando il dito arriva DENTRO
  // l'editor: non ha senso far preoccupare chi sta ancora scegliendo la
  // taglia.
  function occhio(e) {
    if (!primo(EDITOR)) return;
    sveglia();
    var t = e.target;
    if (t && t.closest && t.closest(EDITOR) && !servizioPronto) mostraAttesa();
  }

  document.addEventListener('pointerdown', occhio, true);
  document.addEventListener('focusin', occhio, true);

  /* ------------------------------------------------------------------ */
  /* 4. IL MOTIVO DI SFONDO CHE NON ARRIVA                               */
  /* ------------------------------------------------------------------ */

  // Se lo sfondo non carica, il fondo resta ignoto e l'inchiostro esce chiaro
  // su chiaro. Un secondo tentativo con un parametro diverso costa niente e
  // recupera il caso piu' comune, cioe' la richiesta partita mentre il
  // servizio era ancora giu'. Uno solo: se fallisce anche quello il problema
  // non e' il tempo.
  function riprovaSfondo(img) {
    if (img.__perlaRiprovato) return;
    img.__perlaRiprovato = true;
    var src = img.getAttribute('src');
    if (!src) return;
    setTimeout(function () {
      img.setAttribute('src', src + (src.indexOf('?') === -1 ? '?' : '&') + 'perla=1');
    }, 2000);
  }

  tutti('[data-pattern-source-img]').forEach(function (img) {
    img.addEventListener('error', function () { riprovaSfondo(img); });
  });

  /* ------------------------------------------------------------------ */
  /* 5. SCHERMO INTERO: LA PAGINA DIETRO STA FERMA                       */
  /* ------------------------------------------------------------------ */

  var scrollSalvato = 0;
  var bloccato = false;

  function blocca() {
    if (bloccato || !eUnDito()) return;
    bloccato = true;
    scrollSalvato = window.scrollY || window.pageYOffset || 0;
    var b = document.body;
    b.style.position = 'fixed';
    b.style.top = (-scrollSalvato) + 'px';
    b.style.left = '0';
    b.style.right = '0';
    b.style.width = '100%';
  }

  function sblocca() {
    if (!bloccato) return;
    bloccato = false;
    var b = document.body;
    b.style.position = '';
    b.style.top = '';
    b.style.left = '';
    b.style.right = '';
    b.style.width = '';
    window.scrollTo(0, scrollSalvato);
  }

  // I tre contenitori annidati: senza `contain` sui due esterni, lo
  // scorrimento che finisce nel riquadro prosegue nel pannello e poi nella
  // pagina. Si mette una volta sola all'avvio, non serve aspettare l'apertura.
  ['.pd-modal__panel', '.pd-modal__body'].forEach(function (sel) {
    var el = primo(sel);
    if (el) el.style.overscrollBehavior = 'contain';
  });

  function schermoInteroAperto() {
    // A schermo intero il riquadro deve poter usare lo schermo: il CSS lo
    // libera solo col telefono coricato (@media orientation: landscape),
    // mentre in verticale restava tappato a 62vh dentro un modale che occupa
    // tutto.
    tutti('.pd-modal__body [data-fabric-viewport]').forEach(function (v) {
      v.style.maxHeight = 'none';
    });
    blocca();
  }

  function schermoInteroChiuso() {
    tutti('[data-fabric-viewport]').forEach(function (v) { v.style.maxHeight = ''; });
    sblocca();
  }

  // La classe la mette e la toglie global.js (initPhotoStudioFullscreen). Si
  // guarda quella invece di agganciarsi ai pulsanti: cosi' vale anche per le
  // chiusure con Esc e con il velo, senza doverle conoscere una per una.
  if (window.MutationObserver) {
    var eraAperto = document.body.classList.contains('pd-open');
    new MutationObserver(function () {
      var aperto = document.body.classList.contains('pd-open');
      if (aperto === eraAperto) return;
      eraAperto = aperto;
      if (aperto) schermoInteroAperto(); else schermoInteroChiuso();
    }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }

  /* ------------------------------------------------------------------ */
  /* 6. PIZZICARE PER INGRANDIRE                                         */
  /* ------------------------------------------------------------------ */

  // Muove i pulsanti dello zoom che esistono gia' invece di applicare una
  // seconda trasformazione: due zoom sullo stesso riquadro si sommerebbero e
  // il riquadro non corrisponderebbe piu' all'area di stampa, che e' il modo
  // di far arrivare il nome deformato in stampa.
  //
  // Il passo di quei pulsanti e' 0,5. Le soglie qui sotto (1,22 e 0,82) sono
  // scelte perche' un pizzico normale ne faccia scattare uno per volta e non
  // tre di fila.
  var SOGLIA_SU = 1.22;
  var SOGLIA_GIU = 0.82;

  function distanza(t) {
    var dx = t[0].clientX - t[1].clientX;
    var dy = t[0].clientY - t[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function pizzico(viewport) {
    if (viewport.__perlaPizzico) return;
    viewport.__perlaPizzico = true;

    var root = viewport.closest(EDITOR);
    if (!root) return;
    var su = primo('[data-view-zoom-in]', root);
    var giu = primo('[data-view-zoom-out]', root);
    if (!su && !giu) return;

    var partenza = 0;

    viewport.addEventListener('touchstart', function (e) {
      if (e.touches.length === 2) partenza = distanza(e.touches);
    }, { passive: true });

    viewport.addEventListener('touchmove', function (e) {
      if (e.touches.length !== 2 || !partenza) return;
      // Senza questo il browser fa il suo zoom sulla pagina intera, che e'
      // l'altra meta' della lamentela: si muove tutto tranne l'editor.
      e.preventDefault();
      var r = distanza(e.touches) / partenza;
      if (r > SOGLIA_SU && su) { su.click(); partenza = distanza(e.touches); }
      else if (r < SOGLIA_GIU && giu) { giu.click(); partenza = distanza(e.touches); }
    }, { passive: false });

    viewport.addEventListener('touchend', function (e) {
      if (e.touches.length < 2) partenza = 0;
    }, { passive: true });
  }

  tutti('[data-fabric-viewport]').forEach(pizzico);

  // I riquadri della medaglietta (fronte e retro) e quelli spostati dentro il
  // modale sono gli stessi elementi, ma il tema puo' ricostruire la sezione
  // (editor tema, cambio variante): si riaggancia quello che compare, e la
  // guardia __perlaPizzico evita il doppio ascoltatore.
  if (window.MutationObserver) {
    new MutationObserver(function () {
      tutti('[data-fabric-viewport]').forEach(pizzico);
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
})();
