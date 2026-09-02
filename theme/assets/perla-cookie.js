(function () {
  'use strict';

  // ROUND 49 -- il banner dei cookie.
  //
  // PERCHE' ESISTE
  // Sulla home pubblicata, prima di questo file, "customerPrivacy",
  // "consent-tracking" e "privacyBanner" comparivano ZERO volte: il banner non
  // era brutto, non c'era. E snippets/perla-analytics.liquid tiene Clarity,
  // GA4 e Meta dietro analyticsProcessingAllowed(). Senza banner nessuno puo'
  // dire di si', quindi i dati non erano pochi: erano zero per costruzione.
  // Questo file non e' un adempimento, e' l'interruttore della misurazione.
  //
  // COSA STA QUI E COSA STA NEL TEMA
  // Qui c'e' solo il comportamento. Il disegno e le parole stanno in
  // snippets/perla-cookie.liquid, perche' un testo legale si deve poter
  // correggere senza toccare il codice, e perche' cosi' la barra esiste nel
  // documento gia' servito -- niente lampo di pagina senza banner mentre il
  // JavaScript arriva.
  //
  // NON SI TOCCANO I COOKIE A MANO
  // La documentazione Shopify lo vieta esplicitamente: leggere o scrivere i
  // cookie di consenso da soli significa rompersi alla prossima versione. Si
  // passa sempre da setTrackingConsent().

  var ATTESA_MASSIMA = 40;          // 40 x 250ms = dieci secondi, come in perla-analytics
  var PASSO_ATTESA = 250;

  // Il banner nativo di Shopify, se acceso in Impostazioni -> Privacy dei
  // clienti. Cercarlo e' l'unico modo per non ritrovarsi due barre in fondo
  // alla pagina: chi accende quello non deve dover ricordarsi di spegnere
  // questo, in nessuno dei due ordini.
  var NATIVO = ['#shopify-pc__banner', '.shopify-pc__banner', '#shopify-pc__prefs'];

  function trova(sel, dentro) { return (dentro || document).querySelector(sel); }

  function apiPronta() {
    return !!(window.Shopify
      && window.Shopify.customerPrivacy
      && typeof window.Shopify.customerPrivacy.setTrackingConsent === 'function');
  }

  // Stessa attesa gia' provata in perla-analytics.liquid: nel <head>
  // window.Shopify.customerPrivacy spesso non esiste ancora, e un controllo
  // fatto li' risponderebbe "no" a tutti.
  function quandoPronta(fai) {
    if (apiPronta()) { fai(); return; }
    if (window.Shopify && typeof window.Shopify.loadFeatures === 'function') {
      window.Shopify.loadFeatures(
        [{ name: 'consent-tracking-api', version: '0.1' }],
        function (errore) { if (!errore && apiPronta()) fai(); }
      );
      return;
    }
    var tentativi = 0;
    var attesa = setInterval(function () {
      if (apiPronta()) { clearInterval(attesa); fai(); }
      else if (++tentativi > ATTESA_MASSIMA) { clearInterval(attesa); }
    }, PASSO_ATTESA);
  }

  function bannerNativoInPagina() {
    if (window.privacyBanner) return true;
    for (var i = 0; i < NATIVO.length; i++) if (trova(NATIVO[i])) return true;
    return false;
  }

  function consensoAttuale() {
    try {
      return window.Shopify.customerPrivacy.currentVisitorConsent() || {};
    } catch (e) {
      return {};
    }
  }

  // QUANDO SI MOSTRA, E PERCHE' NON BASTA shouldShowBanner()
  // La via ufficiale e' shouldShowBanner(): tiene conto della regione del
  // visitatore, delle impostazioni del negozio e di una scelta gia' fatta.
  // Ma quel metodo dice "true" solo per le regioni CONFIGURATE nel pannello
  // Shopify, e finche' nessuno ha configurato niente risponde false ovunque:
  // il banner non comparirebbe a nessuno e sembrerebbe funzionare. Quindi:
  // se Shopify non ci dice di mostrarlo ma questo visitatore non ha MAI
  // espresso una scelta, si chiede lo stesso. Chiedere a chi non serviva e'
  // un fastidio; non chiedere a chi serviva e' una multa.
  function daMostrare() {
    var cp = window.Shopify.customerPrivacy;
    try {
      if (typeof cp.shouldShowBanner === 'function' && cp.shouldShowBanner()) return true;
    } catch (e) { /* si prosegue col ripiego */ }
    var c = consensoAttuale();
    // '' = non ha risposto; 'yes'/'no' = ha risposto, e non lo si disturba.
    return !c.analytics && !c.marketing && !c.preferences;
  }

  function avvia() {
    var radice = trova('[data-perla-cookie]');
    if (!radice) return;

    // Se c'e' il banner nativo, questo resta nascosto com'e' nato.
    if (bannerNativoInPagina()) return;

    var barra = trova('[data-perla-cookie-barra]', radice);
    var pannello = trova('[data-perla-cookie-pannello]', radice);
    var analisi = trova('[data-cookie-segnale="analytics"]', radice);
    var marketing = trova('[data-cookie-segnale="marketing"]', radice);
    var chiSiApriva = null;

    function mostra(el, si) { if (el) el.hidden = !si; }

    function scegli(consenso) {
      try {
        window.Shopify.customerPrivacy.setTrackingConsent(consenso, function () {});
      } catch (e) { /* meglio una barra che non si chiude di una scelta persa */ }
      mostra(barra, false);
      mostra(pannello, false);
      mostra(radice, false);
      if (chiSiApriva && chiSiApriva.focus) { chiSiApriva.focus(); chiSiApriva = null; }
    }

    function tutto(valore) {
      return { analytics: valore, marketing: valore, preferences: valore };
    }

    // I due interruttori partono da quello che il visitatore ha gia' scelto,
    // non da "tutto acceso": riaprire le preferenze deve mostrare lo stato
    // vero, altrimenti un "salva" distratto riaccende quello che era spento.
    function riempiInterruttori() {
      var c = consensoAttuale();
      if (analisi) analisi.checked = c.analytics === 'yes';
      if (marketing) marketing.checked = c.marketing === 'yes';
    }

    var fuoco = [];
    function apriPannello(partenza) {
      chiSiApriva = partenza || null;
      riempiInterruttori();
      mostra(radice, true);
      mostra(barra, false);
      mostra(pannello, true);
      fuoco = [analisi, marketing, trova('[data-cookie="salva"]', radice),
        trova('[data-cookie="chiudi"]', radice)].filter(Boolean);
      if (fuoco[0] && fuoco[0].focus) fuoco[0].focus();
    }

    function chiudiPannello() {
      mostra(pannello, false);
      // Se non aveva ancora scelto, la barra torna: chiudere le preferenze
      // non e' una risposta, e far sparire tutto varrebbe come un "si'".
      if (daMostrare()) { mostra(radice, true); mostra(barra, true); }
      else mostra(radice, false);
      if (chiSiApriva && chiSiApriva.focus) { chiSiApriva.focus(); chiSiApriva = null; }
    }

    function al(sel, fai) {
      var el = trova(sel, radice);
      if (el) el.addEventListener('click', function (ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        fai(el);
      });
      return el;
    }

    al('[data-cookie="accetta"]', function () { scegli(tutto(true)); });
    al('[data-cookie="rifiuta"]', function () { scegli(tutto(false)); });
    al('[data-cookie="preferenze"]', function (el) { apriPannello(el); });
    al('[data-cookie="chiudi"]', function () { chiudiPannello(); });
    al('[data-cookie="salva"]', function () {
      scegli({
        analytics: !!(analisi && analisi.checked),
        marketing: !!(marketing && marketing.checked),
        // "preferences" sono i cookie che ricordano lingua e paese: seguono
        // l'analisi, che e' la scelta che il cliente capisce davvero.
        preferences: !!(analisi && analisi.checked)
      });
    });

    // Il collegamento nel piede: il consenso si deve poter ritirare con la
    // stessa facilita' con cui e' stato dato. Sta fuori dalla radice, quindi
    // si cerca in tutto il documento.
    var riapri = document.querySelector('[data-perla-cookie-apri]');
    if (riapri) riapri.addEventListener('click', function (ev) {
      if (ev && ev.preventDefault) ev.preventDefault();
      apriPannello(riapri);
    });

    document.addEventListener('keydown', function (ev) {
      if (!pannello || pannello.hidden) return;
      if (ev.key === 'Escape') { chiudiPannello(); return; }
      if (ev.key !== 'Tab' || fuoco.length === 0) return;
      // Trappola del fuoco: dentro un dialogo modale il Tab non deve poter
      // uscire e finire sui link della pagina dietro, che sono inerti.
      var i = fuoco.indexOf(document.activeElement);
      var passo = ev.shiftKey ? -1 : 1;
      var prossimo = fuoco[(i + passo + fuoco.length) % fuoco.length];
      if (prossimo && prossimo.focus) { ev.preventDefault(); prossimo.focus(); }
    });

    if (daMostrare()) { mostra(radice, true); mostra(barra, true); }
  }

  quandoPronta(avvia);
})();
