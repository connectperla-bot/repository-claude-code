/* Perla — le due foto della card si alternano da sole.
 *
 * PERCHE' ESISTE
 * Ogni prodotto ha due foto, ma la seconda si vedeva solo passando il mouse.
 * Da telefono il mouse non c'e': meta' del catalogo restava invisibile a chi
 * compra, che e' proprio chi guarda le schede da telefono.
 *
 * COSA FA, E COSA NON FA
 * Non anima niente: mette e toglie la classe .is-alterna, e sono le due righe
 * in perla-tocco.css a scambiare le opacita' che base.css dissolve gia' in
 * .6s al passaggio del mouse. Se questo file non si carica, la card resta
 * esattamente com'era prima.
 *
 * UN BATTITO SOLO PER TUTTA LA PAGINA
 * Un intervallo per card farebbe sfarfallare la griglia a caso, e sedici
 * timer indipendenti sono sedici sveglie che il browser deve tenere. Qui c'e'
 * un solo setInterval: tutte le card visibili cambiano insieme, e si legge
 * come una scelta invece che come un difetto.
 *
 * LE QUATTRO REGOLE CHE LO TENGONO CIVILE
 *  1. solo le card visibili almeno a meta' (IntersectionObserver). Le altre
 *     non entrano nel giro, quindi il browser non scarica la seconda foto di
 *     prodotti che nessuno sta guardando: su una collezione da sessanta pezzi
 *     e' la differenza fra qualche foto e sessanta.
 *  2. fermo quando la scheda del browser e' in secondo piano: un carosello
 *     che gira in una scheda che nessuno guarda consuma batteria e basta.
 *  3. il mouse comanda lui. La card sotto il puntatore esce dal battito
 *     finche' non ci si toglie -- se no chi si ferma a guardare la seconda
 *     foto se la vede portare via a meta'.
 *  4. spento del tutto con prefers-reduced-motion, come il resto del tema.
 *
 * L'INTERRUTTORE
 * settings.card_auto_swap nel tema. Il markup della card scrive
 * data-carosello-card sul contenitore quando e' acceso: senza quell'attributo
 * questo file non fa niente e non costa niente.
 */
(function () {
  'use strict';

  var PASSO_MS = 2000;

  function avvia() {
    var radice = document.querySelector('[data-carosello-card]');
    if (!radice) return;

    var menoMovimento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    if (menoMovimento && menoMovimento.matches) return;

    var visibili = new Set();
    var acceso = false;
    var battito = null;

    function schede() {
      return document.querySelectorAll('.card.has-second');
    }

    var osservatore = null;
    if ('IntersectionObserver' in window) {
      osservatore = new IntersectionObserver(function (voci) {
        voci.forEach(function (v) {
          if (v.isIntersecting) visibili.add(v.target);
          else {
            visibili.delete(v.target);
            v.target.classList.remove('is-alterna');
          }
        });
      }, { threshold: 0.5 });
    }

    function registra() {
      schede().forEach(function (card) {
        if (card.__perlaCarosello) return;
        card.__perlaCarosello = true;
        // Il mouse ha la precedenza: mentre ci sta sopra la card esce dal
        // battito, e la classe se ne va cosi' :hover resta l'unico a decidere.
        card.addEventListener('mouseenter', function () {
          card.classList.remove('is-alterna');
        });
        if (osservatore) osservatore.observe(card);
        else visibili.add(card);
      });
    }

    function passo() {
      if (document.hidden) return;
      acceso = !acceso;
      visibili.forEach(function (card) {
        if (card.matches(':hover')) {
          card.classList.remove('is-alterna');
          return;
        }
        card.classList.toggle('is-alterna', acceso);
      });
    }

    function parti() {
      if (battito) return;
      battito = setInterval(passo, PASSO_MS);
    }
    function fermati() {
      if (!battito) return;
      clearInterval(battito);
      battito = null;
    }

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) fermati();
      else parti();
    });

    registra();
    parti();

    // Le collezioni caricano altre card scorrendo (filtri, paginazione
    // infinita): senza questo le nuove resterebbero ferme sulla prima foto.
    if ('MutationObserver' in window) {
      new MutationObserver(function () { registra(); })
        .observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', avvia);
  } else {
    avvia();
  }
})();
