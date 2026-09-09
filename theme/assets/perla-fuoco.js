/* Chi naviga con il Tab deve VEDERE quello che ha messo a fuoco.
 *
 * IL DIFETTO, MISURATO
 * Sulla scheda prodotto, da desktop: si mette a fuoco "Aggiungi al carrello"
 * e la pagina non si muove. window.scrollY resta 0, il pulsante resta a
 * y=1693 su una finestra alta 900. Cioe' il fuoco della tastiera e' su un
 * pulsante che non si vede. Chi naviga con la tastiera preme Invio al buio,
 * o piu' probabilmente si arrende.
 *
 * PERCHE' SUCCEDE
 * Lo smooth-scroll di assets/motion.js (desktop >= 1000px) mette tutta la
 * pagina dentro un <div class="scroll-wrap"> in position:fixed e la fa
 * scorrere con un transform. La rotella del mouse continua a funzionare --
 * la finestra scorre davvero e il transform la insegue -- ma il browser, per
 * portare un elemento a fuoco sotto gli occhi, cerca un antenato scorribile:
 * dentro un elemento fisso non ne trova nessuno, e sta fermo. Per lo stesso
 * motivo scrollIntoView() non fa niente su questa pagina.
 *
 * COSA FA QUESTO FILE
 * Quando il fuoco arriva su qualcosa che sta fuori dallo schermo, sposta la
 * finestra quel tanto che basta a farlo vedere. Solo per il fuoco DA
 * TASTIERA (:focus-visible): un clic col mouse non deve far saltare la
 * pagina sotto le dita di chi ha appena cliccato.
 *
 * LA MATEMATICA, E PERCHE' NON BASTA window.scrollY
 * Con lo smooth-scroll acceso il transform insegue la finestra con un
 * ritardo: nell'istante del fuoco, rect.top dice dove l'elemento si vede
 * ADESSO, mentre window.scrollY dice dove la finestra sta ANDANDO. Sommarli
 * porterebbe troppo in la'. motion.js pubblica la posizione vera del
 * transform in window.__perlaScrollY: si usa quella quando c'e', e si ricade
 * su window.scrollY quando lo smooth-scroll e' spento (telefono, schermo
 * stretto, o chi ha chiesto meno animazioni).
 */
(function () {
  'use strict';

  // quanto respiro lasciare sopra l'elemento messo a fuoco
  var MARGINE = 120;

  function offsetPagina() {
    // motion.js la aggiorna a ogni fotogramma; senza smooth-scroll non esiste
    return typeof window.__perlaScrollY === 'number' ? window.__perlaScrollY : window.scrollY;
  }

  function daTastiera(el) {
    // Il fuoco da mouse non deve muovere la pagina. :focus-visible e' la
    // regola del browser su cosa merita un anello di fuoco, ed e' la stessa
    // distinzione che serve qui. Se il browser non la conosce si preferisce
    // NON muovere niente: meglio non aiutare che far saltare la pagina.
    try { return el.matches(':focus-visible'); } catch (e) { return false; }
  }

  function fuoriDallaFinestra(r) {
    return r.top < 0 || r.bottom > window.innerHeight;
  }

  document.addEventListener('focusin', function (e) {
    var el = e.target;
    if (!el || !el.getBoundingClientRect || el === document.body) return;
    if (!daTastiera(el)) return;

    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;   // elemento nascosto
    if (!fuoriDallaFinestra(r)) return;            // si vede gia': non si tocca

    // dove sta l'elemento nella pagina intera, non nella finestra
    var assoluta = r.top + offsetPagina();
    var meta = Math.max(0, assoluta - MARGINE);

    var pianoPiano = !window.matchMedia
      || !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    try {
      window.scrollTo({ top: meta, behavior: pianoPiano ? 'smooth' : 'auto' });
    } catch (err) {
      window.scrollTo(0, meta);   // browser vecchi: senza opzioni
    }
  }, true);
})();
