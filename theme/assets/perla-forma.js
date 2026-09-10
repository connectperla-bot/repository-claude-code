/* Quando la variante cambia l'AREA DI STAMPA, la scheda si rifa'.
 *
 * IL PROBLEMA
 * Sui tre prodotti americani nuovi le varianti non condividono l'area di
 * stampa: il tondo della medaglietta e' 756x907, il cuore 756x827, l'osso
 * 744x496 -- rapporti 0,83 / 0,91 / 1,50. La tela dell'editor deve avere le
 * proporzioni dell'area, se no il nome esce stampato deformato (il perche' e'
 * scritto per esteso nel commento ROUND 24 di
 * snippets/perla-photo-customizer-side.liquid). Con un rapporto solo, il
 * tondo si vedeva come un ovale e l'osso sarebbe uscito schiacciato del 65%.
 *
 * PERCHE' RICARICA E NON AGGIORNA
 * La tela Fabric si costruisce UNA VOLTA sulle misure del riquadro
 * (new fabric.Canvas(canvasEl, {width: canvasW, height: canvasH}) dentro
 * runPhotoCustomizer, assets/global.js) e l'export si rimappa sullo stesso
 * rapporto letto all'avvio. Cambiare il riquadro dopo non ridimensiona
 * niente: si otterrebbe una tela che SEMBRA giusta e stampa storto, che e'
 * peggio del difetto di partenza. global.js e' minificato su una riga sola e
 * la sua sorgente non sta nel repository (la source map di Shopify contiene
 * il minificato, non il sorgente), quindi non si puo' aggiungere un
 * ridimensionamento la' dentro: sarebbe una modifica alla cieca sul percorso
 * che porta il file in stampa.
 *
 * Nemmeno rifare solo la sezione basta: initAll() si riaggancia su
 * shopify:section:load, ma assets/perla-studio-ui.js (trascina-e-rilascia,
 * stato vuoto, anteprima del nome) e gli altri perla-* si agganciano solo su
 * DOMContentLoaded. Una sezione ricostruita tornerebbe con l'editor a meta'
 * dei suoi pezzi. Quindi si ricarica la pagina con ?variant=<id>: Liquid
 * rende la tela con il rapporto giusto, la sagoma giusta e la finestra
 * giusta, e tutti gli script ripartono interi.
 *
 * COSA NON FA
 * Sulle varianti che cambiano solo colore -- che sono la maggioranza: 5
 * colori per forma sulla medaglietta, 7 per taglia sul collare -- l'area e'
 * la stessa e qui non succede niente. Si ricarica solo quando l'area cambia
 * davvero, e solo dopo aver chiesto se nell'editor c'e' gia' del lavoro.
 *
 * I dati arrivano da [data-perla-forme], scritto da
 * sections/main-product.liquid leggendo snippets/perla-forme-varianti.liquid.
 */
(function () {
  'use strict';

  var CHIAVE_SCROLL = 'perla-forma-scroll';

  function json(el) {
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  /* Il filtro `t` di Shopify restituisce la frase gia' passata per
   * l'escape HTML, e dentro a un <script type="application/json"> nessuno
   * la disfa: la finestra di conferma mostrerebbe "un&#39;area di stampa".
   * Si disfano qui le cinque entita' che quell'escape produce -- a mano, e
   * non con innerHTML, che su un testo qualsiasi sarebbe un buco. */
  var ENTITA = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };

  function testo(s) {
    return String(s || '').replace(/&(amp|lt|gt|quot|#39);/g, function (e) { return ENTITA[e]; });
  }

  function opzioniScelte(sez) {
    var scelte = [];
    var campi = sez.querySelectorAll('[data-option-index]');
    for (var i = 0; i < campi.length; i++) {
      var c = campi[i];
      if (c.type === 'radio' && !c.checked) continue;
      scelte[parseInt(c.getAttribute('data-option-index'), 10)] = c.value;
    }
    return scelte;
  }

  /* La variante si ricava dalle pastiglie, non dal campo nascosto: questo
   * file gira come <script defer> nel corpo della sezione, quindi il suo
   * ascoltatore e' registrato PRIMA di quello di global.js (che si registra
   * dentro DOMContentLoaded) e leggerebbe un valore vecchio di un giro. */
  function varianteScelta(sez, prodotto) {
    var scelte = opzioniScelte(sez);
    for (var i = 0; i < prodotto.variants.length; i++) {
      var v = prodotto.variants[i], uguale = true;
      for (var k = 0; k < v.options.length; k++) {
        if (v.options[k] !== scelte[k]) { uguale = false; break; }
      }
      if (uguale) return v;
    }
    return null;
  }

  function editorPieno(sez) {
    // [data-layer-panel] perde l'attributo hidden appena c'e' il primo
    // livello: e' il segnale che global.js emette per quello stato, gia'
    // usato da perla-studio-ui.js per lo stesso scopo.
    if (sez.querySelector('[data-layer-panel]:not([hidden])')) return true;

    // ROUND 59 -- ANCHE IL SOLO NOME SCRITTO E' LAVORO DA NON BUTTARE.
    //
    // Il pannello dei livelli da solo non basta. Cambiare taglia ricarica la
    // pagina, e la ricarica azzera l'editor: chi aveva SCRITTO UN NOME senza
    // che il pannello si fosse aperto se lo vedeva cancellare senza che
    // nessuno glielo chiedesse. E' il caso piu' comune di tutti -- sul collare
    // il nome E' la personalizzazione -- ed era anche il piu' silenzioso.
    //
    // [data-photo-prop-name-text] e' lo specchio vivo di collectNameText():
    // writePropData lo riscrive a ogni giro, quindi se c'e' scritto qualcosa
    // li' dentro, il cliente ha scritto qualcosa.
    var campi = sez.querySelectorAll('[data-photo-prop-name-text]');
    for (var i = 0; i < campi.length; i++) {
      if ((campi[i].value || '').trim()) return true;
    }
    // E il campo del design pieno vuol dire che una composizione e' gia'
    // riuscita: buttarla senza chiedere sarebbe buttare anche l'attesa.
    var dati = sez.querySelectorAll('[data-photo-prop-data]');
    for (var j = 0; j < dati.length; j++) {
      if ((dati[j].value || '').trim()) return true;
    }
    return false;
  }

  function ricarica(url, id) {
    try { sessionStorage.setItem(CHIAVE_SCROLL, String(window.scrollY)); } catch (e) {}
    var separatore = url.indexOf('?') === -1 ? '?' : '&';
    window.location.href = url + separatore + 'variant=' + id;
  }

  function riportaScroll() {
    var y;
    try {
      y = sessionStorage.getItem(CHIAVE_SCROLL);
      sessionStorage.removeItem(CHIAVE_SCROLL);
    } catch (e) { return; }
    if (y === null || y === undefined) return;
    y = parseInt(y, 10);
    if (!y || y < 0) return;
    // dopo il caricamento delle immagini, se no l'altezza della pagina non
    // e' ancora quella definitiva e si atterra nel posto sbagliato
    window.addEventListener('load', function () {
      window.scrollTo(0, y);
    });
  }

  function avvia() {
    var dati = document.querySelector('[data-perla-forme]');
    if (!dati) return;
    var conf = json(dati);
    if (!conf || !conf.varianti) return;
    var sez = dati.closest('[data-product]') || document;
    var jsonProdotto = sez.querySelector('[data-product-json]');
    if (!jsonProdotto) return;
    var prodotto = json(jsonProdotto);
    if (!prodotto || !prodotto.variants) return;

    var firmaOra = conf.varianti[String(conf.attuale)];
    var campi = sez.querySelectorAll('[data-option-index]');

    function ripensaci(precedenti) {
      for (var i = 0; i < campi.length; i++) {
        var c = campi[i];
        var idx = parseInt(c.getAttribute('data-option-index'), 10);
        if (c.type === 'radio') {
          var vuole = c.value === precedenti[idx];
          if (c.checked !== vuole) {
            c.checked = vuole;
            if (vuole) c.dispatchEvent(new Event('change', { bubbles: true }));
          }
        }
      }
    }

    for (var i = 0; i < campi.length; i++) {
      (function (campo) {
        var primaDi = null;
        campo.addEventListener('mousedown', function () { primaDi = opzioniScelte(sez); });
        campo.addEventListener('keydown', function () { primaDi = opzioniScelte(sez); });
        campo.addEventListener('change', function () {
          var v = varianteScelta(sez, prodotto);
          if (!v) return;
          var firma = conf.varianti[String(v.id)];
          if (!firma || firma === firmaOra) return;
          if (editorPieno(sez) && !window.confirm(testo(conf.avviso))) {
            if (primaDi) ripensaci(primaDi);
            return;
          }
          var riquadro = sez.querySelector('.product-personalize');
          if (riquadro) riquadro.classList.add('is-rifacendo');
          ricarica(conf.url, v.id);
        });
      })(campi[i]);
    }
  }

  riportaScroll();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', avvia);
  } else {
    avvia();
  }
})();
