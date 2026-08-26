/* ============================================================================
   Perla — ROUND 33/19. Miglioramenti dell'editor di personalizzazione.

   REGOLA DI QUESTO FILE: non tocca assets/global.js e non parla mai con
   Printify/Printful. Si aggancia soltanto agli hook data-* che il markup gia'
   espone, e quando aggiunge una foto lo fa passando i file all'<input
   type="file"> esistente — cioe' esattamente la stessa strada del click su
   "+ Foto". Il percorso che porta il composito alla stampa (composeAndUpload /
   writePropData in global.js) resta intatto: se questo file non venisse
   caricato del tutto, l'editor funzionerebbe come nel Round 16.

   Sette interventi:
     0. Invito a ruotare/schermo intero sui prodotti lunghi e stretti.
     1. Trascina-e-rilascia una foto sul riquadro.
     2. Stato vuoto: nasconde/mostra il suggerimento in base al pannello livelli.
     3. Anteprima del nome che segue davvero il font/colore scelto.
     4. Stati di caricamento, errore e "riprova" sull'anteprima reale.
     5. Galleria prodotto: via i file di stampa, che non sono fotografie.
     6. Ogni livello resta dentro l'area di stampa, non solo il marchio.
   ========================================================================= */
(function () {
  'use strict';

  var STR = (window.Perla && window.Perla.strings) || {};
  var IT = (document.documentElement.lang || 'it').toLowerCase().indexOf('it') === 0;

  function each(list, fn) { Array.prototype.forEach.call(list || [], fn); }
  function qs(root, sel) { return root ? root.querySelector(sel) : null; }
  function slice(list) { return Array.prototype.slice.call(list || []); }

  /* -------------------------------------------------------------------------
     0. PRODOTTI LUNGHI E STRETTI SUL TELEFONO

     L'area di stampa di alcuni prodotti e' una striscia lunghissima, e il
     riquadro ricava l'altezza dalla larghezza disponibile. Su un telefono in
     verticale (circa 330px utili) viene fuori questo:

       collare        25.20 : 1  ->   13 px
       collare_eu     22.76 : 1  ->   14 px
       guinzaglio_eu  56.57 : 1  ->    6 px
       ciotola_eu      8.09 : 1  ->   41 px

     La regola qui e' che si deve continuare a vedere TUTTA la striscia in una
     volta sola: niente riquadro piu' largo dello schermo, niente scorrimento
     laterale, niente frecce. L'unico modo per guadagnare altezza restando
     interi e' guadagnare larghezza, quindi si indirizza la persona dove la
     larghezza c'e' davvero: telefono in orizzontale + schermo intero.

     Da 330px in verticale si passa a circa 800-880px in orizzontale a schermo
     intero (il modale toglie i margini, vedi assets/perla-studio.css): il
     collare passa da 13 a circa 34 px, il guinzaglio EU da 6 a 15. Poco, ma
     e' il massimo possibile senza tagliare la striscia o deformarla — il
     rapporto d'aspetto non e' negoziabile, deve combaciare con l'area di
     stampa reale o il disegno arriverebbe deformato.

     UN PULSANTE SOLO (correzione)
     Questo riquadro creava anche un secondo pulsante "Apri a schermo intero"
     che non faceva altro che premere quello gia' presente nella barra degli
     strumenti. Sul telefono se ne vedevano due, a 190 px di distanza, con
     testi diversi per la stessa identica azione: sembrava che uno dei due
     dovesse fare qualcos'altro. Ora resta la sola spiegazione — che serve,
     perche' dice PERCHE' conviene — e il pulsante e' quello vero, che qui
     sotto viene marcato `is-primary` cosi' si nota.
     ---------------------------------------------------------------------- */
  var WIDE_RATIO = 6;   // sopra questo rapporto la striscia e' inservibile in verticale

  function isNarrow() { return window.matchMedia('(max-width: 749px)').matches; }
  function isPortrait() { return window.matchMedia('(orientation: portrait)').matches; }

  function initWideHint(customizer) {
    var ratio = parseFloat(customizer.getAttribute('data-print-ratio'));
    if (!ratio || !isFinite(ratio) || ratio < WIDE_RATIO) return;

    var viewport = qs(customizer, '[data-fabric-viewport]');
    var fsBtn = qs(customizer, '[data-photo-fullscreen-open]');
    if (!viewport || !viewport.parentNode) return;

    // Su questi prodotti lo schermo intero non e' un extra, e' la strada
    // normale: il pulsante smette di essere un comando secondario.
    if (fsBtn) fsBtn.classList.add('is-primary');

    var hint = document.createElement('div');
    hint.className = 'photo-studio__rotate-hint';
    hint.setAttribute('data-rotate-hint', '');

    var p = document.createElement('p');
    p.className = 'photo-studio__rotate-hint-text';
    hint.appendChild(p);

    viewport.parentNode.insertBefore(hint, viewport);

    function sync() {
      if (!isNarrow()) { hint.hidden = true; return; }
      hint.hidden = false;
      if (isPortrait()) {
        p.textContent = STR.rotateHint || (IT
          ? 'Questo prodotto è una striscia molto lunga e stretta. Gira il telefono in orizzontale e apri lo schermo intero: lo vedrai il più grande possibile, tutto insieme.'
          : 'This product is a long, narrow strip. Turn your phone sideways and open fullscreen to see all of it as large as it gets.');
      } else {
        p.textContent = STR.rotateHintLandscape || (IT
          ? 'Apri lo schermo intero per guadagnare ancora un po’ di spazio.'
          : 'Open fullscreen to gain a little more room.');
      }
    }

    sync();
    window.addEventListener('resize', sync);
    window.addEventListener('orientationchange', sync);
  }

  /* -------------------------------------------------------------------------
     1. TRASCINA E RILASCIA

     Il rilascio non carica niente da solo: costruisce un DataTransfer, lo
     assegna all'input file gia' presente e gli manda un evento 'change'. Da
     li' in poi e' global.js a gestire tutto, identico al click su "+ Foto".
     Se il browser non supporta DataTransfer costruibile (Safari < 14.1) la
     funzione esce e resta il pulsante, che ha sempre funzionato.
     ---------------------------------------------------------------------- */
  function initDragAndDrop(customizer) {
    var wrap = qs(customizer, '[data-fabric-wrap]');
    var input = qs(customizer, '[data-photo-input]');
    if (!wrap || !input) return;

    var depth = 0;

    function accepted(dt) {
      if (!dt) return false;
      if (dt.types && Array.prototype.indexOf.call(dt.types, 'Files') === -1) return false;
      return true;
    }

    wrap.addEventListener('dragenter', function (e) {
      if (!accepted(e.dataTransfer)) return;
      e.preventDefault();
      depth++;
      wrap.classList.add('is-dragover');
    });

    wrap.addEventListener('dragover', function (e) {
      if (!accepted(e.dataTransfer)) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });

    wrap.addEventListener('dragleave', function () {
      depth = Math.max(0, depth - 1);
      if (depth === 0) wrap.classList.remove('is-dragover');
    });

    wrap.addEventListener('drop', function (e) {
      if (!accepted(e.dataTransfer)) return;
      e.preventDefault();
      depth = 0;
      wrap.classList.remove('is-dragover');

      var dropped = e.dataTransfer.files;
      if (!dropped || !dropped.length) return;

      // Stesso filtro dell'attributo accept dell'input: se qualcuno trascina un
      // PDF o un HEIC non lo passiamo a global.js, che si aspetta un'immagine
      // nei formati che Printify accetta.
      var ok = [];
      each(dropped, function (f) {
        if (/^image\/(png|jpeg|webp)$/.test(f.type)) ok.push(f);
      });
      if (!ok.length) return;

      var DT = window.DataTransfer;
      if (typeof DT !== 'function') return;
      var box;
      try { box = new DT(); } catch (err) { return; }
      if (!box.items || typeof box.items.add !== 'function') return;

      ok.forEach(function (f) { box.items.add(f); });
      input.files = box.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  /* -------------------------------------------------------------------------
     2. STATO VUOTO

     Non serve sapere niente di Fabric: global.js toglie l'attributo hidden da
     [data-layer-panel] appena esiste almeno un livello, quindi quell'attributo
     e' gia' il segnale "la tela non e' piu' vuota". Un MutationObserver su di
     lui basta, senza ispezionare il canvas.
     ---------------------------------------------------------------------- */
  function initEmptyState(customizer) {
    var empty = qs(customizer, '[data-studio-empty]');
    var layers = qs(customizer, '[data-layer-panel]');
    if (!empty || !layers) return;

    function sync() {
      var isEmpty = layers.hasAttribute('hidden');
      if (isEmpty) empty.removeAttribute('hidden');
      else empty.setAttribute('hidden', '');
    }

    sync();
    new MutationObserver(sync).observe(layers, { attributes: true, attributeFilter: ['hidden'] });
  }

  /* -------------------------------------------------------------------------
     3. ANTEPRIMA DEL NOME COERENTE COL FONT SCELTO

     .name-inline-preview e' l'anteprima sotto al campo del nome (la inserisce
     global.js). Aveva il font fisso su Cormorant Garamond nel CSS: chi
     sceglieva Caveat o Montserrat vedeva qui un carattere diverso da quello
     che sarebbe stato davvero inciso. Ora il CSS legge tre custom properties
     e questa funzione le tiene allineate allo swatch attivo.

     Delegato su document: l'anteprima puo' non esistere ancora quando questo
     file gira, e lo studio viene spostato dentro/fuori dal modale a schermo
     intero (initPhotoStudioFullscreen), quindi i riferimenti diretti
     scadrebbero.
     ---------------------------------------------------------------------- */
  function applyNameStyle(scope) {
    var preview = qs(scope, '.name-inline-preview');
    if (!preview) return;

    var font = qs(scope, '.name-font-swatch.is-active');
    if (font) {
      var family = font.getAttribute('data-name-font');
      var weight = font.getAttribute('data-name-weight');
      if (family) preview.style.setProperty('--name-preview-font', family);
      if (weight) preview.style.setProperty('--name-preview-weight', weight);
    }

    var swatch = qs(scope, '.name-color-swatch.is-active');
    var colour = swatch && swatch.getAttribute('data-name-color-swatch');
    if (!colour) {
      var picker = qs(scope, '[data-name-color-picker]');
      if (picker && picker.value) colour = picker.value;
    }
    if (colour) preview.style.setProperty('--name-preview-color', colour);
  }

  function scopeOf(el) {
    return (el && el.closest && (el.closest('[data-photo-customizer]') || el.closest('.product-personalize'))) || document;
  }

  function initNameStyle() {
    // global.js aggiorna la classe .is-active DOPO il proprio handler di click:
    // il rinvio di un tick evita di leggere lo stato precedente.
    document.addEventListener('click', function (e) {
      var hit = e.target.closest && e.target.closest('[data-name-font], [data-name-color-swatch]');
      if (!hit) return;
      var scope = scopeOf(hit);
      setTimeout(function () { applyNameStyle(scope); }, 0);
    });

    document.addEventListener('input', function (e) {
      if (!e.target.matches || !e.target.matches('[data-name-color-picker]')) return;
      applyNameStyle(scopeOf(e.target));
    });

    each(document.querySelectorAll('[data-photo-customizer]'), applyNameStyle);
  }

  /* -------------------------------------------------------------------------
     4. ANTEPRIMA REALE: CARICAMENTO, ERRORE, RIPROVA

     La generazione passa dai server del fornitore e impiega 9-12 secondi
     (6 tentativi x 1,5s su Printify, 8 x 1,5s su Printful — vedi
     scripts/perla-upload-endpoint.js), e puo' rispondere 504 "anteprima non
     pronta, riprova tra qualche secondo". Prima il pulsante non dava alcun
     segnale: sembrava rotto, e sul 504 l'unica via d'uscita era ricaricare la
     pagina perdendo tutto il design.

     Non intercettiamo la fetch di global.js (sarebbe fragile): mettiamo lo
     stato di attesa al click, e lasciamo che sia la comparsa dei mockup o la
     scrittura di un messaggio da parte di global.js a chiudere l'attesa.
     ---------------------------------------------------------------------- */
  function initMockupFeedback(panel) {
    var btn = qs(panel, '[data-generate-mockup], [data-generate-mockup-shared]');
    var status = qs(panel, '[data-mockup-gen-status], [data-mockup-gen-status-shared]');
    var shelf = qs(panel, '[data-real-mockups], [data-real-mockups-shared]');
    if (!btn || !status) return;

    var mine = false; // distingue le scritture di questo file da quelle di global.js

    var retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'product-personalize__retry';
    retry.textContent = STR.mockupRetry || (IT ? 'Riprova' : 'Try again');
    retry.hidden = true;
    retry.addEventListener('click', function () { btn.click(); });
    status.parentNode.insertBefore(retry, status.nextSibling);

    function setState(name) {
      status.classList.remove('product-personalize__status--pending',
        'product-personalize__status--error',
        'product-personalize__status--success');
      if (name) status.classList.add('product-personalize__status--' + name);
    }

    btn.addEventListener('click', function () {
      if (btn.disabled) return;
      retry.hidden = true;
      mine = true;
      status.textContent = STR.mockupPending || (IT ? 'Preparo l’anteprima…' : 'Building your preview…');
      setState('pending');
      setTimeout(function () { mine = false; }, 0);
    });

    // global.js ha scritto un messaggio: l'attesa e' finita, in un modo o
    // nell'altro. Se nel frattempo sono comparse delle anteprime e' andata
    // bene; altrimenti e' un errore e offriamo di riprovare.
    new MutationObserver(function () {
      if (mine) return;
      var text = (status.textContent || '').trim();
      if (!text) { setState(null); retry.hidden = true; return; }
      var got = shelf && !shelf.hasAttribute('hidden') && shelf.children.length > 0;
      setState(got ? 'success' : 'error');
      retry.hidden = !!got;
    }).observe(status, { childList: true, characterData: true, subtree: true });

    // Le anteprime possono comparire senza che venga scritto alcun messaggio:
    // in quel caso il successo va rilevato da qui.
    if (shelf) {
      new MutationObserver(function () {
        if (shelf.hasAttribute('hidden') || !shelf.children.length) return;
        if (!status.classList.contains('product-personalize__status--pending')) return;
        mine = true;
        status.textContent = '';
        setState(null);
        retry.hidden = true;
        setTimeout(function () { mine = false; }, 0);
      }).observe(shelf, { attributes: true, attributeFilter: ['hidden'], childList: true });
    }
  }

  /* -------------------------------------------------------------------------
     5. GALLERIA PRODOTTO: VIA I FILE DI STAMPA (ROUND 19)

     I prodotti EU portano in galleria, dopo il mockup, il proprio file di
     stampa. Su un collare quel file e' 1200 x 53 pixel, una striscia; la
     scheda prodotto lo chiede a width 1200 per la slide e 1400 per
     l'ingrandimento, cioe' lo gonfia di dodici volte dentro un riquadro alto
     quanto la foto principale. E' la "foto sgranata" che si vede scorrendo le
     immagini del prodotto.

     snippets/card-product.liquid gia' evitava lo stesso file come foto al
     passaggio del mouse (Round 18); la galleria non era coperta.

     Perche' qui e non nel Liquid: la galleria vive in tre cicli separati
     dentro un file da 44 KB (slide, pallini, miniature) e i tre indici devono
     restare allineati fra loro e con global.js, che naviga per indice. Qui
     bastano gli hook data-* gia' esposti, e dopo ogni rimozione si
     rinumerano tutti e tre gli elenchi.

     NIENTE viene cancellato da Shopify: quei file sono gli stessi a cui punta
     custom.editor_pattern_image, cioe' lo sfondo dell'area di stampa
     nell'editor. Restano dove sono, semplicemente non si mostrano come se
     fossero fotografie.
     ---------------------------------------------------------------------- */
  var MIN_RATIO = 0.55;   // un mockup fotografico sta sempre vicino al quadrato
  var MAX_RATIO = 1.7;

  function initGalleryClean() {
    var gal = document.querySelector('[data-gallery]');
    if (!gal) return;
    if (gal.querySelectorAll('[data-slide]').length < 2) return;

    function reindex() {
      slice(gal.querySelectorAll('[data-slide]')).forEach(function (s, i) {
        s.setAttribute('data-slide', String(i));
      });
      slice(gal.querySelectorAll('[data-gallery-dot]')).forEach(function (d, i) {
        d.setAttribute('data-gallery-dot', String(i));
        d.setAttribute('aria-label', String(i + 1));
      });
      slice(gal.querySelectorAll('[data-thumb]')).forEach(function (t, i) {
        t.setAttribute('data-index', String(i));
      });
    }

    function drop(slide) {
      var idx = slide.getAttribute('data-slide');
      var dot = gal.querySelector('[data-gallery-dot="' + idx + '"]');
      var thumb = gal.querySelector('[data-thumb][data-index="' + idx + '"]');
      if (dot && dot.parentNode) dot.parentNode.removeChild(dot);
      if (thumb && thumb.parentNode) thumb.parentNode.removeChild(thumb);
      if (slide.parentNode) slide.parentNode.removeChild(slide);
    }

    // true se qualche immagine non era ancora caricata: le proporzioni si
    // leggono da naturalWidth/naturalHeight, che prima valgono zero.
    function sweep() {
      var waiting = false;
      var doomed = [];

      slice(gal.querySelectorAll('[data-slide]')).forEach(function (slide, i) {
        if (i === 0) return;           // la prima resta sempre: mai una galleria vuota
        var img = slide.querySelector('img');
        if (!img) return;
        if (!img.naturalWidth || !img.naturalHeight) { waiting = true; return; }
        var r = img.naturalWidth / img.naturalHeight;
        if (r < MIN_RATIO || r > MAX_RATIO) doomed.push(slide);
      });

      if (doomed.length) {
        doomed.forEach(drop);
        reindex();
        if (gal.querySelectorAll('[data-slide]').length < 2) {
          var dots = gal.querySelector('[data-gallery-dots]');
          var thumbs = gal.querySelector('.product__thumbs');
          if (dots) dots.hidden = true;
          if (thumbs) thumbs.hidden = true;
        }
      }
      return waiting;
    }

    if (!sweep()) return;

    // Le slide oltre la prima hanno loading="lazy": possono caricarsi molto
    // dopo. Si riprova a ogni caricamento e una volta sola a fine pagina.
    slice(gal.querySelectorAll('[data-slide] img')).forEach(function (img) {
      img.addEventListener('load', sweep, { once: true });
      img.addEventListener('error', sweep, { once: true });
    });
    window.addEventListener('load', sweep, { once: true });
  }

  /* -------------------------------------------------------------------------
     6. OGNI LIVELLO RESTA DENTRO L'AREA DI STAMPA

     IL DIFETTO, TROVATO NEL CODICE
     In assets/global.js il guardiano che tiene un livello dentro i bordi si
     chiama keepLogoInBounds, e viene agganciato da installLogo:

         obj.on('moving',   keepLogoInBounds)
         obj.on('scaling',  keepLogoInBounds)
         obj.on('rotating', keepLogoInBounds)

     installLogo pero' si usa SOLO sul marchio, e keepLogoInBounds al suo
     interno guarda soltanto la variabile logoLayer: su qualunque altro
     oggetto non fa niente. Cercato in tutto il file, `nameLayer.on(` non
     compare nemmeno una volta.

     Quindi il nome del cane, i testi aggiuntivi, le foto e gli adesivi non
     hanno nessun limite: si trascinano fuori dal riquadro e ci restano.
     Quello che sta fuori dall'area non viene stampato e il cliente non se ne
     accorge — ordina un collare col nome e riceve un collare senza nome.
     E' il difetto piu' caro dell'editor, perche' si scopre solo col pacco in
     mano.

     PERCHE' SI CORREGGE DA QUI E NON DA global.js
     global.js e' un bundle minificato da 89 KB su due righe. Cambiarlo vuol
     dire ricaricarlo per intero, e un solo carattere sbagliato li' dentro
     spegne tutto il JavaScript del negozio — carrello compreso. Qui invece si
     aggiunge un ascoltatore in piu' su ogni livello: se questo file sparisse,
     l'editor tornerebbe esattamente com'e' oggi.

     COME SI TROVA LA TELA
     Le istanze di fabric.Canvas non sono raggiungibili dal DOM, e global.js
     tiene la sua in una variabile locale (`fc`). Si avvolge allora renderAll,
     che ogni tela chiama sempre e comunque, e la prima chiamata la consegna.
     Cosi' non c'e' nessun vincolo di ordine di caricamento: se la tela e'
     nata prima di questo file, la prossima renderAll la registra lo stesso.
     Il costo e' un confronto booleano per fotogramma.

     LA REGOLA DEL LIMITE
     Se il livello e' piu' piccolo dell'area, ci deve stare dentro tutto.
     Se e' piu' grande — una foto usata come sfondo, un motivo — allora e'
     l'area a dover restare dentro il livello: cosi' non si lascia mai un
     angolo bianco, e insieme non si impedisce di spostarlo.

     LA SCALA NON SI TOCCA MAI. E' una scelta di chi disegna, non un difetto:
     e' la lezione della medaglietta "Blue & Gold", dove "ingrandire fino a
     coprire" aveva peggiorato un prodotto che era gia' giusto.

     IL MARCHIO RESTA A global.js, che gli applica limiti piu' stretti
     (logoSafeBounds) e una scala minima sua: metterci le mani sopra da qui
     vorrebbe dire avere due guardiani che si contraddicono.
     ---------------------------------------------------------------------- */

  function areaSicura(fc, tondo) {
    var w = fc.getWidth();
    var h = fc.getHeight();
    // Margine proporzionale: su un collare la tela e' alta 14 px e i 4 px
    // fissi del marchio si mangerebbero piu' di meta' dell'altezza.
    var m = Math.max(1, Math.min(4, Math.min(w, h) * 0.04));
    if (!tondo) return { left: m, top: m, right: w - m, bottom: h - m };
    // Medaglietta: l'area e' un quadrato ma il prodotto e' un tondo. Si usa il
    // rettangolo inscritto nel cerchio, gli stessi numeri che global.js usa
    // gia' per il marchio, cosi' i due limiti raccontano la stessa forma.
    var cx = w / 2, cy = h / 2;
    var hw = (w * 0.92 / 2) / Math.SQRT2;
    var hh = (h * 0.92 / 2) / Math.SQRT2;
    return { left: cx - hw, top: cy - hh, right: cx + hw, bottom: cy + hh };
  }

  // Di quanto va spostato un segmento [p, p+len] per rispettare [a, b].
  function rientro(p, len, a, b) {
    if (len <= b - a) {                 // ci sta dentro: deve starci tutto
      if (p < a) return a - p;
      if (p + len > b) return b - (p + len);
      return 0;
    }
    if (p > a) return a - p;            // piu' grande dell'area: deve coprirla
    if (p + len < b) return b - (p + len);
    return 0;
  }

  function prendiInCura(fc) {
    fc.__perlaCurata = true;            // per primo: evita il rientro ricorsivo

    var el = fc.lowerCanvasEl;
    var root = el && el.closest ? el.closest('[data-photo-customizer]') : null;
    var tondo = !!root && (root.getAttribute('data-product-type') || '') === 'medaglietta';

    function dentro(obj) {
      if (!obj || obj.group) return;                 // figlio di una selezione
      if (obj.__perlaKind === 'logo') return;        // ci pensa gia' global.js
      obj.setCoords();
      var b = obj.getBoundingRect();
      var a = areaSicura(fc, tondo);
      var dx = rientro(b.left, b.width, a.left, a.right);
      var dy = rientro(b.top, b.height, a.top, a.bottom);
      if (!dx && !dy) return;
      obj.left += dx;
      obj.top += dy;
      obj.setCoords();
    }

    function sorveglia(obj) {
      if (!obj || obj.__perlaSorvegliato) return;
      obj.__perlaSorvegliato = true;
      obj.on('moving', function () { dentro(obj); });
      obj.on('scaling', function () { dentro(obj); });
      obj.on('rotating', function () { dentro(obj); });
    }

    fc.getObjects().forEach(sorveglia);
    fc.on('object:added', function (e) { sorveglia(e.target); });

    // Una selezione multipla e' un oggetto nuovo, creato al volo e mai
    // "aggiunto": va sorvegliata quando nasce, o trascinando due livelli
    // insieme si esce lo stesso.
    fc.on('selection:created', function (e) { sorveglia(e.target || (e.selected && e.selected[0])); });
    fc.on('selection:updated', function (e) { sorveglia(e.target || (e.selected && e.selected[0])); });

    // Ultima rete: qualunque cosa sia successa, a fine manovra si controlla.
    // global.js ha gia' il suo object:modified (compone il file di stampa);
    // il nostro e' registrato dopo, ma i livelli sono gia' rientrati durante
    // il trascinamento, quindi quello che global.js compone e' gia' giusto.
    fc.on('object:modified', function (e) {
      dentro(e.target);
      fc.requestRenderAll();
    });
  }

  function agganciaFabric() {
    var F = window.fabric;
    if (!F || !F.Canvas || !F.Canvas.prototype) return false;
    if (F.Canvas.prototype.__perlaAggancio) return true;
    F.Canvas.prototype.__perlaAggancio = true;
    var render = F.Canvas.prototype.renderAll;
    F.Canvas.prototype.renderAll = function () {
      if (!this.__perlaCurata) {
        try { prendiInCura(this); } catch (err) { this.__perlaCurata = true; }
      }
      return render.apply(this, arguments);
    };
    return true;
  }

  function initLimiti() {
    if (agganciaFabric()) return;
    // global.js carica fabric.js da un CDN solo quando serve l'editor: puo'
    // arrivare molto dopo di noi. Si aspetta, ma non per sempre.
    var scade = Date.now() + 90000;
    var t = setInterval(function () {
      if (agganciaFabric() || Date.now() > scade) clearInterval(t);
    }, 200);
  }

  /* ---------------------------------------------------------------------- */
  function init() {
    each(document.querySelectorAll('[data-photo-customizer]'), function (c) {
      initWideHint(c);
      initDragAndDrop(c);
      initEmptyState(c);
      initMockupFeedback(c);
    });
    // Pannello mockup condiviso della medaglietta: vive fuori dai due editor
    // fronte/retro, quindi non e' coperto dal ciclo qui sopra.
    each(document.querySelectorAll('[data-shared-mockup]'), initMockupFeedback);
    initNameStyle();
    initGalleryClean();
    initLimiti();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
