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

    // La striscia ora si vede tutta fin dall'apertura (sezione 9), quindi lo
    // schermo intero non e' piu' l'unica strada: resta pero' quello che la fa
    // vedere piu' grande, ed e' l'azione che conviene di piu' qui.
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
          ? 'Questo prodotto è una striscia lunga e stretta: qui sopra la vedi tutta intera. Usa «+» per ingrandire e lavorare sui dettagli, «Reset» per tornare a vederla tutta. Girando il telefono in orizzontale diventa più grande.'
          : 'This product is a long, narrow strip: above you can see all of it. Use “+” to zoom in on the details and “Reset” to fit it back. Turning your phone sideways makes it bigger.');
      } else {
        p.textContent = STR.rotateHintLandscape || (IT
          ? 'Usa «+» per ingrandire la striscia e lavorare sui dettagli, «Reset» per tornare a vederla tutta.'
          : 'Use “+” to zoom in on the details and “Reset” to fit the whole strip back.');
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

  /* -------------------------------------------------------------------------
     7. IL FILE DI STAMPA ALLA RISOLUZIONE CHE L'AREA CHIEDE

     IL DIFETTO, MISURATO
     In assets/global.js, buildComposite() esporta sempre 2000 px sul lato
     lungo, qualunque sia l'area di stampa:

         var EXPORT_BASE = 2000,
             exportW = ratio >= 1 ? EXPORT_BASE : Math.round(EXPORT_BASE * ratio),
             multiplier = exportW / canvasW;

     Confrontato con le aree vere (scripts/perla-scala-stampa.py):

         guinzaglio EU  12389x219    ->  2000x35     3% dei pixel
         cuccia USA     15600x12600  ->  2000x1615   2%
         collare EU      7169x315    ->  2000x88     8%
         ciotola EU      6496x803    ->  2000x247    9%
         bandana EU      4125x4125   ->  2000x2000  24%

     Il fornitore riceve quell'immagine e la ingrandisce fino all'area: un nome
     scritto su una tela alta 35 px e portato a 219 non e' piu' una scritta, e'
     una sbavatura. E' questo che si vede come "la scritta viene rimpicciolita",
     ed e' anche la seconda causa -- indipendente dalla risoluzione delle
     sorgenti -- del "sembrano impastati" da cui e' partito tutto.

     Le proporzioni invece sono giuste: misurato in Chromium, l'inchiostro
     occupa 0,5043 della tela nell'anteprima e 0,5025 nel file di stampa. Non
     e' un problema di scala, e' di risoluzione.

     COSA FA
     Avvolge toDataURL e alza il moltiplicatore SOLO quando ne arriva uno --
     cioe' solo per il file di stampa. L'anteprima (updateMockupPreview chiama
     toDataURL senza moltiplicatore) resta identica a oggi.

     I TRE LIMITI, E PERCHE' QUESTI
       LATO_MAX 4096 e PIXEL_MAX 16 Mpx: oltre, Safari su iPhone smette di
       disegnare la tela e toDataURL torna un'immagine vuota. Meglio quattro
       volte i pixel su tutti i telefoni che sedici su nessuno.

       BYTE_MAX: perla-upload-endpoint.js rifiuta oltre MAX_UPLOAD_MB (10 di
       default, ma sul server puo' essere piu' basso). Si misura il risultato e
       se sfora si scende, invece di produrre un file che verrebbe respinto --
       il caricamento non si rompe mai, al massimo si accontenta.

     PERCHE' DA QUI E NON DA global.js: stessa ragione del punto 6. Un bundle
     minificato da 89 KB non si riscrive a mano per cambiare una costante.
     ---------------------------------------------------------------------- */
  var LATO_MAX = 4096;              // lato massimo che ogni telefono regge
  var PIXEL_MAX = 16e6;             // e la stessa soglia espressa in area
  var BYTE_MAX = 8 * 1024 * 1024;   // sotto MAX_UPLOAD_MB, con margine

  function quantoSiPuoAlzare(fc, mult) {
    var w = fc.getWidth() * mult;
    var h = fc.getHeight() * mult;
    if (!(w > 0) || !(h > 0)) return 1;
    var perLato = LATO_MAX / Math.max(w, h);
    var perArea = Math.sqrt(PIXEL_MAX / (w * h));
    var k = Math.min(perLato, perArea);
    return k > 1 ? k : 1;           // non si scende mai sotto quello che c'era
  }

  function copia(o) {
    var n = {};
    for (var k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) n[k] = o[k]; }
    return n;
  }

  function byte(dataUrl) {
    var virgola = dataUrl.indexOf(',');
    return Math.round((dataUrl.length - virgola - 1) * 0.75);
  }

  /* -------------------------------------------------------------------------
     8. SCRIVERE IL NOME NON DEVE ALLARGARE LA PAGINA

     IL DIFETTO, RIPRODOTTO
     Sui prodotti a disegno fisso non c'e' nessun campo di testo: il nome si
     scrive DENTRO la tela. Per farlo Fabric crea una textarea invisibile e la
     attacca al <body> alle coordinate del cursore NEL DOCUMENTO:

         this.hiddenTextarea.style.cssText =
           "position: absolute; top: " + t.top + "; left: " + t.left + ...

     Su un collare la tela e' larga 2208 px, quindi quelle coordinate stanno
     oltre i mille. Misurato a 390 px:

         prima di toccare niente   body.scrollWidth   390
         entrando in scrittura     body.scrollWidth  1084   left: 1077 px
         digitando                                          left: 1183 -> 1311

     Il corpo si allarga a ogni carattere. Su un telefono vero e' questo che fa
     rimpicciolire la pagina e scorrere verso sinistra mentre si scrive.

     LA CORREZIONE
     La textarea diventa `fixed` e resta ancorata in alto a sinistra della
     finestra. Fixed non partecipa al calcolo della larghezza del documento,
     quindi la pagina non si allarga piu'; l'elemento resta a fuoco e la
     tastiera continua a funzionare, che e' l'unica cosa per cui serve.

     COSA SI PERDE
     Fabric usa quella posizione per ancorare il riquadro di composizione delle
     tastiere orientali (IME). Su un negozio italiano il compromesso e' facile:
     meglio l'ancoraggio dell'IME in alto a sinistra che la pagina che scappa a
     ogni lettera.
     ---------------------------------------------------------------------- */

  function fissaTextarea(obj) {
    var ta = obj && obj.hiddenTextarea;
    if (!ta) return;
    ta.style.position = 'fixed';
    ta.style.left = '0px';
    ta.style.top = '0px';
    // 16px: sotto questa misura Safari su iPhone ingrandisce la pagina da solo
    // quando un campo prende il fuoco. La textarea e' invisibile lo stesso,
    // perche' Fabric le mette opacity 0.
    ta.style.fontSize = '16px';
    ta.style.width = '1px';
    ta.style.height = '1px';
  }

  /* -------------------------------------------------------------------------
     9. IL NASTRO SI VEDE TUTTO, E SI INGRANDISCE PER LAVORARCI

     IL DIFETTO, MISURATO
     snippets/perla-photo-customizer-side.liquid parte dall'ALTEZZA e lascia
     scorrere la larghezza, per non deformare le proporzioni di stampa:

         studio_h = 2200 / rapporto   (poi limitato fra 80 e 200)
         studio_w = studio_h * rapporto

     Sul collare (22,76:1) vengono 2208 x 97 px dentro una finestra di 350.
     A 390 px di schermo, misurato:

         verticale                 350 x 97   su 2208 x 97   ->  16%
         verticale schermo intero  352 x 97   su 2208 x 97   ->  16%
         orizzontale               760 x 97   su 2208 x 97   ->  34%
         orizzontale + intero      825 x 97   su 2208 x 97   ->  37%

     Lo schermo intero NON cambia niente: sedici per cento prima, sedici dopo.
     Il guinzaglio e' peggio: rapporto 56,57, altezza al minimo di 80, striscia
     larga 4526 px, cioe' circa il sette per cento visibile.

     COSA FA ORA
     All'apertura la striscia sta tutta dentro: si scala di
     `larghezza finestra / larghezza striscia` e la si centra in una banda
     comoda. Si vede un collare intero, sottile e fermo -- che e' quello che il
     prodotto e'. Chi vuole personalizzare ingrandisce con i pulsanti che gia'
     ci sono, e a quel punto la striscia si sposta DENTRO il suo riquadro:
     la pagina non si muove mai di lato.

     PERCHE' CON transform E NON CAMBIANDO width/height
     La tela ha larghezza e altezza in attributi; ridimensionarla via CSS senza
     `height:auto` la deforma, e un riquadro fuori proporzione manda in stampa
     il nome schiacciato. Il transform invece scala tutto insieme, ed e' anche
     il meccanismo che global.js usa gia': fabric calcola il puntatore da
     getBoundingClientRect, che i transform li comprende.

     CHI VINCE SULLO STILE (misurato, non supposto)
     global.js tiene il suo `viewZoom` e nella sua `applyViewZoom` riscrive
     `fabricWrap.style.transform`. Il primo tentativo era registrare i nostri
     ascoltatori sui pulsanti e contare di girare per ultimi: NON funziona.
     Provato nel browser, premendo «+» restava `scale(1.5)`, cioe' il valore
     suo -- lo studio di global.js si avvia dopo di noi, quindi i suoi
     ascoltatori sono registrati dopo i nostri e parlano per ultimi.

     Sull'ordine di registrazione non si puo' fare affidamento. Quindi i tre
     pulsanti si prendono in FASE DI CATTURA sul contenitore, dove si passa
     prima che l'evento arrivi al pulsante, e li' si ferma la propagazione: gli
     ascoltatori di global.js non vengono mai chiamati. Vale solo sui nastri,
     dove initNastro e' attivo; su tutti gli altri prodotti lo zoom del tema
     resta quello di sempre.

     L'osservatore sullo `style` resta come rete: confronta con la stringa che
     abbiamo scritto noi e riscrive solo se qualcuno l'ha cambiata davvero --
     cosi' non reagisce a se stesso e si ferma da solo.
     ---------------------------------------------------------------------- */

  var BANDA_MIN = 96;      // altezza minima della fascia, perche' si veda
  var BANDA_LAVORO = 320;  // altezza a cui si arriva col massimo ingrandimento
  var PASSO = 1.8;

  function initNastro(customizer) {
    var viewport = qs(customizer, '[data-fabric-viewport]');
    var wrap = qs(customizer, '[data-fabric-wrap]');
    if (!viewport || !wrap) return;

    var largaW = wrap.offsetWidth;
    var altaW = wrap.offsetHeight;
    var finestra = viewport.clientWidth;
    // Senza misure non si decide niente: se lo studio non e' ancora visibile
    // meglio lasciare tutto com'e' che scalare per zero e sparire.
    if (!largaW || !altaW || !finestra) return;
    // Solo dove serve: se la striscia ci sta gia', non si tocca niente.
    if (largaW <= finestra + 1) return;

    var fit = finestra / largaW;
    var massimo = Math.max(1, Math.min(6, BANDA_LAVORO / altaW));
    var scala = fit;
    var atteso = '';
    var tutta = true;

    function applica() {
      var alta = Math.max(BANDA_MIN, Math.round(altaW * scala));
      var vuoto = Math.max(0, (alta - altaW * scala) / 2);
      atteso = 'translateY(' + vuoto.toFixed(1) + 'px) scale(' + scala.toFixed(4) + ')';
      wrap.style.transformOrigin = '0 0';
      wrap.style.transform = atteso;
      viewport.style.height = alta + 'px';
      tutta = scala <= fit + 1e-6;
      // A "tutta" non c'e' niente da scorrere: la striscia sta gia' tutta
      // dentro. Il riquadro pero' resta largo quanto la striscia NON scalata
      // (il transform non cambia lo spazio occupato), quindi lo scorrimento
      // esiste ancora e porta solo sul vuoto. Misurato sul guinzaglio: il
      // riquadro nasce a scrollLeft 2088, cioe' esattamente a meta', e la
      // striscia finisce a -2068 px, fuori dallo schermo a sinistra. Ecco
      // perche' sembrava che non ci fosse niente da personalizzare.
      //
      // Non ho trovato chi lo sposta -- non e' nessuno degli script del tema.
      // Invece di indovinare la causa, si toglie l'effetto: finche' si vede
      // tutta, lo scorrimento laterale del riquadro e' chiuso e la posizione
      // torna a zero. Appena si ingrandisce, riapre: li' serve davvero.
      viewport.style.overflowX = tutta ? 'hidden' : 'auto';
      if (tutta) viewport.scrollLeft = 0;
      customizer.setAttribute('data-nastro-zoom', tutta ? 'tutta' : 'ingrandita');
    }

    function cambia(fattore) {
      var prima = scala;
      scala = Math.max(fit, Math.min(massimo, scala * fattore));
      if (Math.abs(scala - prima) < 1e-6) return;
      // si ingrandisce attorno al centro di cio' che si sta guardando, non
      // attorno al bordo sinistro: altrimenti a ogni "+" si perde il punto
      var centro = (viewport.scrollLeft + viewport.clientWidth / 2) / prima;
      applica();
      viewport.scrollLeft = Math.max(0, centro * scala - viewport.clientWidth / 2);
    }

    // In cattura sul contenitore: si passa di qui prima che l'evento arrivi al
    // pulsante, e la propagazione si ferma. Vedi la nota sopra sul perche'
    // registrarsi sul pulsante non basta.
    customizer.addEventListener('click', function (e) {
      var b = e.target && e.target.closest
        ? e.target.closest('[data-view-zoom-in],[data-view-zoom-out],[data-view-zoom-reset]')
        : null;
      if (!b || !customizer.contains(b)) return;
      e.preventDefault();
      e.stopPropagation();
      if (b.hasAttribute('data-view-zoom-in')) cambia(PASSO);
      else if (b.hasAttribute('data-view-zoom-out')) cambia(1 / PASSO);
      else { scala = fit; applica(); }
    }, true);

    // `overflow:hidden` non impedisce a uno script di scorrere lo stesso
    // (un riquadro nascosto resta scorribile da codice): se succede, si torna
    // subito a zero. Quando e' ingrandita non si tocca: li' scorre l'utente.
    viewport.addEventListener('scroll', function () {
      if (tutta && viewport.scrollLeft !== 0) viewport.scrollLeft = 0;
    });

    // Rete di sicurezza: se lo stile diventa diverso da quello che abbiamo
    // scritto noi, lo si rimette. Il confronto con `atteso` fa si' che la
    // riscrittura non richiami l'osservatore all'infinito.
    new MutationObserver(function () {
      if (wrap.style.transform !== atteso) applica();
    }).observe(wrap, { attributes: true, attributeFilter: ['style'] });

    // Quando la finestra cambia misura, "tutta" cambia misura con lei.
    //
    // Non basta ascoltare `resize`: lo schermo intero di questo tema e' una
    // classe CSS, non l'API del browser, quindi il riquadro si allarga senza
    // che la finestra cambi e nessun `resize` arriva. Un ResizeObserver sul
    // riquadro li prende tutti e due -- rotazione e schermo intero -- perche'
    // guarda la cosa giusta: quanto spazio c'e' davvero.
    function rimisura() {
      var ora = viewport.clientWidth;
      if (!ora || ora === finestra) return;
      finestra = ora;
      var eraTutta = scala <= fit + 1e-6;
      fit = ora / largaW;
      scala = eraTutta ? fit : Math.max(fit, scala);
      applica();
    }
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(rimisura).observe(viewport);
    }
    window.addEventListener('resize', rimisura);
    window.addEventListener('orientationchange', function () {
      setTimeout(rimisura, 250);   // la rotazione arriva prima della nuova misura
    });

    applica();
    return { fit: fit, massimo: massimo };
  }

  function agganciaScrittura(F) {
    if (!F.IText || !F.IText.prototype || F.IText.prototype.__perlaTextarea) return;
    F.IText.prototype.__perlaTextarea = true;

    var creata = F.IText.prototype.initHiddenTextarea;
    F.IText.prototype.initHiddenTextarea = function () {
      var r = creata.apply(this, arguments);
      fissaTextarea(this);
      return r;
    };

    // Fabric la rimette al posto del cursore ogni volta che il cursore si
    // muove, quindi non basta sistemarla alla nascita.
    //
    // I DUE NOMI. In fabric 5.3 il metodo si chiama `updateTextareaPosition`,
    // senza trattino basso; nelle versioni piu' vecchie era `_update...`.
    // La prima stesura avvolgeva solo quello col trattino: la guardia
    // `typeof === 'function'` non trovava niente e passava oltre in silenzio,
    // e nella misura la textarea usciva con `left: 147.779px` invece di zero.
    // Si avvolgono tutti e due, e almeno uno dei due c'e' per forza.
    ['updateTextareaPosition', '_updateTextareaPosition'].forEach(function (nome) {
      var spostata = F.IText.prototype[nome];
      if (typeof spostata !== 'function') return;
      F.IText.prototype[nome] = function () {
        var r = spostata.apply(this, arguments);
        fissaTextarea(this);       // Fabric l'ha appena rimessa dove non deve
        return r;
      };
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

    // La risoluzione del file di stampa. StaticCanvas e' l'antenato di Canvas:
    // avvolgerlo qui copre entrambi con un solo aggancio.
    var base = F.StaticCanvas && F.StaticCanvas.prototype;
    if (base && !base.__perlaRisoluzione) {
      base.__perlaRisoluzione = true;
      var esporta = base.toDataURL;
      base.toDataURL = function (opz) {
        // Nessun moltiplicatore = anteprima sullo schermo: non si tocca.
        if (!opz || opz.multiplier == null || opz.__perlaAlzato) {
          return esporta.apply(this, arguments);
        }
        var k = quantoSiPuoAlzare(this, opz.multiplier);
        if (k <= 1.0001) return esporta.apply(this, arguments);

        var prova = copia(opz);
        prova.__perlaAlzato = true;
        prova.multiplier = opz.multiplier * k;

        var url;
        try {
          url = esporta.call(this, prova);
        } catch (err) {
          return esporta.apply(this, arguments);   // memoria: si torna a prima
        }
        // Se il file e' troppo pesante per il caricamento si scende, fino al
        // massimo a quello che l'editor produceva prima: peggio di cosi' no.
        var giri = 0;
        while (byte(url) > BYTE_MAX && prova.multiplier > opz.multiplier && giri < 4) {
          giri++;
          prova.multiplier = Math.max(opz.multiplier, prova.multiplier / 1.5);
          try { url = esporta.call(this, prova); } catch (err) { break; }
        }
        return url;
      };
    }
    agganciaScrittura(F);
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

  /* -------------------------------------------------------------------------
     10. IL RECESSO SI DICE PRIMA DI PAGARE, NON DOPO

     PERCHE' STA QUI E NON SOLO NELL'INFORMATIVA
     Sui beni confezionati su misura il diritto di recesso di quattordici
     giorni non si applica -- art. 59, comma 1, lettera c) del Codice del
     Consumo, che recepisce l'art. 16 della direttiva 2011/83/UE. Ma
     l'esclusione vale solo se il consumatore ne e' stato informato PRIMA di
     essere vincolato dal contratto. Scriverlo soltanto nella pagina Resi non
     basta: nessuno la apre prima di comprare.

     Se non lo si dice qui, l'esclusione non opera e un collare con sopra il
     nome del cane torna indietro entro quattordici giorni -- e lo paghiamo
     noi, perche' rivenderlo e' impossibile.

     DOVE
     In fondo al riquadro di personalizzazione, cioe' l'ultima cosa che si
     legge dopo aver scritto il nome e prima di premere "aggiungi al carrello".
     Non e' un avvertimento in rosso: e' la stessa frase che diremmo a voce a
     qualcuno che ci porge un collare da incidere.

     Compare SOLO dove esiste `[data-photo-customizer]`, cioe' esattamente sui
     prodotti personalizzabili: sugli altri non ha senso e non appare.
     ---------------------------------------------------------------------- */

  function initAvvisoRecesso(customizer) {
    if (qs(customizer, '[data-avviso-recesso]')) return;   // gia' messo

    var avviso = document.createElement('p');
    avviso.className = 'photo-studio__note';
    avviso.setAttribute('data-avviso-recesso', '');
    avviso.textContent = STR.recessoNote || (IT
      // Apostrofi tipografici e accenti veri: questo lo legge un cliente, non
      // e' un commento nel codice. La prima stesura diceva "non si puo'
      // restituire" con l'apostrofo al posto dell'accento, e in mezzo al resto
      // del sito -- che usa le virgolette curve ovunque -- si vedeva.
      ? 'Lo stampiamo apposta per te dopo l\u2019ordine: per legge un pezzo personalizzato non si pu\u00f2 restituire per ripensamento. Se arriva difettoso o sbagliato lo rifacciamo noi, spese comprese.'
      : 'We print it for you after you order, so by law a personalised item can\u2019t be returned for a change of mind. If it arrives faulty or wrong, we remake it at our cost.');

    customizer.appendChild(avviso);
  }

  /* ---------------------------------------------------------------------- */
  function init() {
    each(document.querySelectorAll('[data-photo-customizer]'), function (c) {
      initWideHint(c);
      initNastro(c);
      initAvvisoRecesso(c);
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
