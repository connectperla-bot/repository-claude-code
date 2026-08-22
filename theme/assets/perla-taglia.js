/* Consiglio della taglia a partire da peso e razza.
 *
 * PERCHE' ESISTE
 * Le descrizioni dei collari finiscono tutte con la stessa frase: "se hai un
 * dubbio scrivici razza e peso del tuo cane: ti diciamo noi quale prendere".
 * Era un invito a scrivere un'email prima di comprare, cioe' un ordine perso su
 * due. Qui la stessa risposta arriva sulla scheda, in un secondo.
 *
 * COSA MISURA DAVVERO
 * Per il collare conta la circonferenza del collo, non il peso: la fonte
 * migliore e' il metro da sarta, la seconda e' la razza, la terza e' il peso.
 * Il pannello le accetta in quest'ordine e dice sempre da quale delle tre e'
 * uscito il consiglio -- un consiglio che non spiega da dove viene non e' un
 * consiglio, e' un'ipotesi travestita.
 *
 * LA REGOLA DI CONFINE
 * "Scegli la taglia in cui la misura cade in mezzo" e' scritta nella pagina
 * Guida alle taglie e nelle descrizioni: qui si applica alla lettera scegliendo
 * l'intervallo con la distanza relativa minore dal proprio centro. Quando due
 * intervalli sono equivalenti si prende il piu' grande, come dice la stessa
 * pagina: una fibbia stringe, non allunga.
 *
 * I NUMERI
 * Gli intervalli non sono inventati: collare S 30-45, M 35-52, L 38-60 cm
 * vengono dal catalogo Printful (printful-catalog/749.json e la nota in
 * scripts/varianti-fornitore.js); bandane 44/54/64 cm da 630.json; ciotole
 * 530/950 ml da 678.json; cucce e bandane americane dai titoli delle varianti
 * Printify. Se il fornitore cambia misure, questi vanno rifatti.
 */
(function () {
  'use strict';

  // [pesoMin, pesoMax, colloMin, colloMax] -- kg e cm da adulto.
  // Il collo non si ricava dal peso: un levriero di 30 kg ha il collo di un
  // labrador di 30 kg piu' quattro centimetri, e un carlino di 8 kg ha il collo
  // di un jack russell di 8 kg piu' cinque. Dove la differenza conta, e'
  // scritta qui.
  var RAZZE = {
    'akita': [32, 45, 48, 58], 'alaskan malamute': [34, 43, 50, 60],
    'australian shepherd': [18, 32, 38, 48], 'barboncino nano': [3, 6, 22, 28],
    'barboncino toy': [2, 4, 18, 24], 'barboncino medio': [9, 14, 30, 38],
    'basset hound': [20, 29, 40, 50], 'beagle': [9, 14, 30, 40],
    'bearded collie': [18, 27, 38, 46], 'bichon frise': [4, 8, 24, 30],
    'bobtail': [27, 45, 46, 58], 'border collie': [14, 20, 34, 44],
    'boxer': [25, 32, 45, 55], 'bracco italiano': [25, 40, 44, 54],
    'breton': [14, 18, 34, 42], 'bulldog francese': [8, 14, 34, 43],
    'bulldog inglese': [18, 25, 42, 52], 'bull terrier': [22, 32, 42, 52],
    'cane corso': [40, 50, 55, 68], 'carlino': [6, 9, 32, 40],
    'cavalier king charles': [5, 8, 26, 33], 'chihuahua': [1.5, 3, 18, 24],
    'chow chow': [20, 32, 42, 52], 'cocker spaniel': [12, 15, 32, 40],
    'collie': [18, 30, 38, 48], 'corgi': [10, 14, 32, 40],
    'dalmata': [24, 32, 42, 52], 'dobermann': [32, 45, 48, 58],
    'dogo argentino': [35, 45, 52, 64], 'dogue de bordeaux': [45, 60, 58, 70],
    'fox terrier': [7, 9, 28, 35], 'golden retriever': [25, 34, 42, 52],
    'jack russell': [6, 8, 26, 34], 'husky': [20, 27, 40, 50],
    'labrador retriever': [25, 36, 42, 54], 'lagotto romagnolo': [11, 16, 32, 40],
    'levriero afghano': [23, 27, 42, 52], 'levriero italiano': [3, 5, 22, 28],
    'levriero whippet': [10, 16, 32, 40], 'maltese': [3, 4, 20, 26],
    'maremmano': [30, 45, 50, 62], 'mastino napoletano': [50, 70, 60, 75],
    'pastore australiano': [18, 32, 38, 48], 'pastore belga': [20, 30, 40, 50],
    'pastore tedesco': [22, 40, 44, 56], 'pechinese': [4, 6, 24, 30],
    'pinscher nano': [4, 6, 22, 28], 'pitbull': [16, 27, 40, 52],
    'pomerania': [2, 3, 18, 24], 'rottweiler': [42, 60, 55, 70],
    'san bernardo': [64, 82, 62, 78], 'schnauzer nano': [5, 8, 26, 33],
    'schnauzer medio': [14, 20, 34, 42], 'segugio italiano': [18, 28, 36, 46],
    'setter inglese': [20, 30, 38, 48], 'setter irlandese': [24, 32, 40, 50],
    'shar pei': [18, 25, 42, 52], 'shiba inu': [8, 11, 30, 38],
    'shih tzu': [4, 8, 25, 32], 'siberian husky': [20, 27, 40, 50],
    'spinone italiano': [28, 39, 44, 54], 'springer spaniel': [18, 25, 36, 44],
    'staffordshire bull terrier': [11, 17, 36, 46], 'terranova': [54, 68, 58, 72],
    'volpino italiano': [3, 5, 20, 26], 'weimaraner': [25, 40, 42, 54],
    'west highland terrier': [6, 10, 28, 35], 'yorkshire terrier': [2, 3, 18, 24],
    'zwergpinscher': [4, 6, 22, 28],
  };

  // Peso -> collo, solo quando la razza non si sa (meticci compresi). E' una
  // stima, e il pannello lo dichiara invece di far finta di niente.
  var COLLO_DA_PESO = [[2, 20], [5, 27], [8, 31], [12, 35], [18, 40],
                       [25, 44], [35, 50], [45, 55], [60, 62], [90, 70]];

  // Ogni tipo dice su COSA decide e quali intervalli hanno le sue taglie.
  // 'collo': centimetri di circonferenza. 'peso': chilogrammi.
  var TABELLE = {
    collare_eu: { su: 'collo', unita: 'cm', taglie: [
      { chiave: 'S', da: 30, a: 45 }, { chiave: 'M', da: 35, a: 52 }, { chiave: 'L', da: 38, a: 60 } ] },
    bandana_eu: { su: 'peso', unita: 'kg', taglie: [
      { chiave: 'S', da: 0, a: 10, nota: 'lato 44 cm' },
      { chiave: 'M', da: 10, a: 25, nota: 'lato 54 cm' },
      { chiave: 'L', da: 25, a: 90, nota: 'lato 64 cm' } ] },
    bandana: { su: 'peso', unita: 'kg', taglie: [
      { chiave: '20" × 10"', da: 0, a: 12 }, { chiave: '27" × 13"', da: 12, a: 90 } ] },
    cuccia: { su: 'peso', unita: 'kg', taglie: [
      { chiave: '28" × 18"', da: 0, a: 11 }, { chiave: '40" × 30"', da: 11, a: 27 },
      { chiave: '50" × 40"', da: 27, a: 90 } ] },
    ciotola_eu: { su: 'peso', unita: 'kg', taglie: [
      { chiave: '530 ml', da: 0, a: 12 }, { chiave: '950 ml', da: 12, a: 90 } ] },
  };

  function normalizza(s) {
    return String(s == null ? '' : s)
      .replace(/[×✕✖]/g, 'x').replace(/[“”″]/g, '"')
      .replace(/\s+/g, ' ').trim().toLowerCase();
  }

  function colloDaPeso(kg) {
    var t = COLLO_DA_PESO;
    if (kg <= t[0][0]) return t[0][1];
    for (var i = 1; i < t.length; i++) {
      if (kg <= t[i][0]) {
        var q = (kg - t[i - 1][0]) / (t[i][0] - t[i - 1][0]);
        return Math.round(t[i - 1][1] + q * (t[i][1] - t[i - 1][1]));
      }
    }
    return t[t.length - 1][1];
  }

  // Distanza relativa dal centro dell'intervallo: 0 al centro, 1 ai bordi,
  // oltre 1 fuori. Cosi' "cade in mezzo" diventa un numero confrontabile fra
  // intervalli di ampiezza diversa -- il collare S e' largo 15 cm, l'L 22.
  function scarto(v, t) {
    var centro = (t.da + t.a) / 2;
    var mezzo = (t.a - t.da) / 2 || 1;
    return Math.abs(v - centro) / mezzo;
  }

  // Il migliore e' lo scarto piu' basso; a parita' vince la taglia PIU' GRANDE,
  // che e' la regola della pagina Guida alle taglie ("se la misura cade fra due
  // taglie, prendi la piu' grande"). Il confronto e' contro il minimo assoluto e
  // non contro il candidato del momento: confrontandolo col candidato, tre
  // taglie ciascuna un filo peggiore della precedente si passavano il testimone
  // fino in fondo, e vinceva la piu' grande anche quando non era pari.
  function scegli(tab, valore) {
    var punteggi = tab.taglie.map(function (t) { return scarto(valore, t); });
    var minimo = Math.min.apply(null, punteggi);
    var scelto = 0;
    for (var i = 0; i < punteggi.length; i++) {
      if (punteggi[i] <= minimo + 0.02) scelto = i;   // le taglie sono in ordine crescente
    }
    return { t: tab.taglie[scelto], s: punteggi[scelto] };
  }

  function inizializza(radice) {
    var tipo = radice.getAttribute('data-tipo');
    var tab = TABELLE[tipo];
    if (!tab) { radice.remove(); return; }

    var modulo = document.querySelector('[data-product-form]');
    if (!modulo) { radice.remove(); return; }

    // Le pastiglie della taglia. Se il tema non le ha disegnate (variante
    // unica) non c'e' niente da consigliare.
    var pastiglie = modulo.querySelectorAll('.variant-pills input[type="radio"]');
    if (pastiglie.length < 2) { radice.remove(); return; }

    // Il pannello nasce in fondo alla pagina perche' e' una sezione a se':
    // qui va a stare sotto ai bottoni della taglia, dove serve.
    var gruppo = modulo.querySelector('.variant-group');
    if (gruppo && gruppo.parentNode) gruppo.parentNode.insertBefore(radice, gruppo.nextSibling);

    var peso = radice.querySelector('[data-taglia-peso]');
    var razza = radice.querySelector('[data-taglia-razza]');
    var collo = radice.querySelector('[data-taglia-collo]');
    var esito = radice.querySelector('[data-taglia-esito]');
    var bottone = radice.querySelector('[data-taglia-calcola]');
    var apri = radice.querySelector('[data-taglia-apri]');
    var corpo = radice.querySelector('[data-taglia-corpo]');

    // L'elenco razze vive qui e non nel markup: settanta nomi ripetuti in
    // Liquid sarebbero settanta nomi da tenere allineati a mano con la tabella.
    var elenco = radice.querySelector('[data-taglia-razze]');
    if (elenco && !elenco.childNodes.length) {
      var nomi = Object.keys(RAZZE).sort();
      for (var n = 0; n < nomi.length; n++) {
        var opt = document.createElement('option');
        // Iniziali maiuscole solo per l'occhio: il confronto passa da normalizza().
        opt.value = nomi[n].replace(/(^|\s)\S/g, function (c) { return c.toUpperCase(); });
        elenco.appendChild(opt);
      }
    }

    if (apri && corpo) {
      apri.addEventListener('click', function () {
        var chiuso = corpo.hasAttribute('hidden');
        if (chiuso) corpo.removeAttribute('hidden'); else corpo.setAttribute('hidden', '');
        apri.setAttribute('aria-expanded', chiuso ? 'true' : 'false');
      });
    }

    function dillo(testo, ok) {
      esito.textContent = testo;
      esito.classList.toggle('is-ok', !!ok);
      esito.removeAttribute('hidden');
    }

    function calcola() {
      var kg = parseFloat(String(peso && peso.value || '').replace(',', '.'));
      var nomeRazza = normalizza(razza && razza.value);
      var datiRazza = RAZZE[nomeRazza];
      var cm = collo ? parseFloat(String(collo.value || '').replace(',', '.')) : NaN;

      var valore, fonte;
      if (tab.su === 'collo') {
        if (cm > 0) { valore = cm; fonte = 'dalla misura del collo che hai inserito'; }
        else if (datiRazza) { valore = (datiRazza[2] + datiRazza[3]) / 2; fonte = 'dalla taglia tipica di un ' + (razza.value || '').trim() + ' adulto — se puoi, misura il collo: è più preciso'; }
        else if (kg > 0) { valore = colloDaPeso(kg); fonte = 'stimata dal peso (circa ' + Math.round(valore) + ' cm di collo) — è una stima, il metro da sarta è meglio'; }
        else { dillo(radice.getAttribute('data-testo-vuoto'), false); return; }
      } else {
        if (kg > 0) { valore = kg; fonte = 'dal peso che hai inserito'; }
        else if (datiRazza) { valore = (datiRazza[0] + datiRazza[1]) / 2; fonte = 'dal peso tipico di un ' + (razza.value || '').trim() + ' adulto'; }
        else { dillo(radice.getAttribute('data-testo-vuoto'), false); return; }
      }

      var scelta = scegli(tab, valore);
      if (!scelta) { dillo(radice.getAttribute('data-testo-vuoto'), false); return; }

      // Fuori tabella: meglio dirlo che consigliare a caso.
      if (scelta.s > 1.6) {
        dillo(radice.getAttribute('data-testo-fuori'), false);
        return;
      }

      var voluta = normalizza(scelta.t.chiave);
      var trovata = null;
      for (var i = 0; i < pastiglie.length; i++) {
        if (normalizza(pastiglie[i].value) === voluta) { trovata = pastiglie[i]; break; }
      }
      if (!trovata) { dillo(radice.getAttribute('data-testo-fuori'), false); return; }

      if (!trovata.checked) {
        trovata.checked = true;
        // Il tema ascolta 'change' sulle pastiglie per aggiornare prezzo,
        // immagine e id della variante: senza questo cambierebbe solo il
        // pallino, e nel carrello finirebbe la taglia sbagliata.
        trovata.dispatchEvent(new Event('change', { bubbles: true }));
      }

      dillo(radice.getAttribute('data-testo-ok')
        .replace('[taglia]', scelta.t.chiave)
        .replace('[perche]', fonte)
        + (scelta.t.nota ? ' (' + scelta.t.nota + ')' : ''), true);
    }

    if (bottone) bottone.addEventListener('click', calcola);
    [peso, razza, collo].forEach(function (campo) {
      if (!campo) return;
      campo.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); calcola(); }
      });
    });
  }

  function avvia() {
    var nodi = document.querySelectorAll('[data-consiglia-taglia]');
    for (var i = 0; i < nodi.length; i++) inizializza(nodi[i]);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', avvia);
  else avvia();

  // L'elenco delle razze serve anche al markup, per la tendina di ricerca.
  window.PerlaRazze = Object.keys(RAZZE);
})();
