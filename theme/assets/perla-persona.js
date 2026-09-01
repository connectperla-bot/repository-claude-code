/* Dal robot a una persona vera.
 *
 * COSA FA
 * Due strade verso la stessa porta:
 *   1. un collegamento "Parla con una persona" sempre visibile in fondo
 *      all'assistente, per chi non ha voglia di spiegarsi con un robot;
 *   2. l'apertura automatica quando la risposta del servizio porta
 *      apri_chat (vedi scripts/perla-assistant-bot.js).
 *
 * PERCHE' INTERCETTA fetch INVECE DI STARE IN global.js
 * La bolla dell'assistente e' disegnata in snippets/assistant.liquid ma la
 * chiamata al servizio la fa assets/global.js, ottantanove chilobyte di file
 * generato. Riscriverlo per intero per aggiungere tre righe e' il modo piu'
 * rapido di rompere il negozio. Qui si ascolta soltanto: si guarda passare la
 * risposta dell'endpoint dell'assistente -- riconosciuto per indirizzo, non a
 * caso -- e si lascia intatto tutto il resto. Ogni altra fetch della pagina
 * passa senza essere toccata.
 *
 * COM'E' FATTA INBOX, LETTO NEL SUO SORGENTE
 * Adesso Inbox e' installata, e il gancio non si tira piu' a indovinare.
 * Arriva da cdn.shopify.com/storefront/web-components/chat.js: e' un web
 * component con shadow DOM che dichiara due parti, `activator` (la bolla) e
 * `dialog` (il pannello). La bolla e' un <button part="activator">.
 *
 * La versione precedente di questo file tentava per primo
 * window.ShopifyChat.open(). Cercato nel sorgente del componente: ZERO
 * occorrenze di ShopifyChat. Era un tentativo a vuoto, ed e' stato tolto.
 *
 * PERCHE' SI CERCA PER `part` E NON PER NOME DEL TAG
 * Oggi l'elemento si chiama <shopify-chat> -- misurato sulla pagina, non
 * dedotto -- ma il nome puo' cambiare domani senza che nessuno avvisi.
 * `part="activator"` invece e' un contratto pubblico, esiste proprio per far
 * stilare la bolla dall'esterno: e' la cosa piu' stabile a cui appendersi.
 *
 * MISURATO SULL'ELEMENTO VERO, NON SU UN FINTO
 * La prima prova diceva "due bolle, non funziona". Il difetto stava nella
 * prova: fingeva Inbox con un elemento inventato, mentre la pagina aveva gia'
 * il vero <shopify-chat>, e questo file agganciava giustamente quello. Sulla
 * cosa vera: una bolla sola, e dopo "Parla con una persona" si riaccende e si
 * apre senza portare via dalla pagina.
 *
 * UNA BOLLA SOLA
 * Il negozio ha gia' il suo assistente in basso a destra
 * (.assistant { position:fixed; right:1rem; bottom:1rem; z-index:950 }), e
 * Inbox si mette nello stesso angolo a z-index 2147483000: la copre. Due chat
 * sovrapposte sono lo stesso difetto del tasto doppio a schermo intero.
 * Qui la bolla di Inbox si spegne, e torna visibile solo quando il cliente
 * chiede una persona: da quel momento e' lei la chat.
 *
 * SI SPEGNE, NON SI RIMUOVE
 * opacity 0 e pointer-events none invece di display none: il componente resta
 * disegnato e misurabile -- un web component nascosto mentre si inizializza
 * puo' sbagliare i propri calcoli -- e i clic passano attraverso, quindi la
 * bolla dell'assistente sotto resta premibile.
 */
(function () {
  'use strict';

  function contatti() {
    var a = document.querySelector('.assistant__action[href^="/pages"], .assistant__action[href^="/apps"]');
    return (a && a.getAttribute('href')) || '/pages/contact';
  }

  // chat.js e' un modulo asincrono: il componente compare dopo di noi, e non
  // sempre con una mutazione visibile fuori dal suo shadow root. Si guarda a
  // intervalli, per mezzo minuto, e poi si smette: se dopo trenta secondi non
  // c'e', non ci sara'.
  var ATTESA_MS = 30000;
  var OGNI_MS = 400;
  var inbox = null;

  function trovaInbox() {
    if (inbox && document.contains(inbox.host)) return inbox;
    inbox = null;
    var nodi = document.querySelectorAll('*');
    for (var i = 0; i < nodi.length; i++) {
      var el = nodi[i];
      // solo elementi personalizzati: il trattino nel nome e' la regola HTML
      if (!el.shadowRoot || el.tagName.indexOf('-') === -1) continue;
      var bolla = el.shadowRoot.querySelector('[part~="activator"]');
      if (bolla) { inbox = { host: el, bolla: bolla }; return inbox; }
    }
    return null;
  }

  function spegniBolla() {
    var t = trovaInbox();
    if (!t) return false;
    if (t.host.getAttribute('data-perla-inbox') !== 'spenta') {
      t.host.setAttribute('data-perla-inbox', 'spenta');
      t.host.style.opacity = '0';
      t.host.style.pointerEvents = 'none';
    }
    return true;
  }

  function accendiBolla(t) {
    t.host.setAttribute('data-perla-inbox', 'accesa');
    t.host.style.opacity = '';
    t.host.style.pointerEvents = '';
  }

  function sorvegliaBolla() {
    if (spegniBolla()) return;
    var scade = Date.now() + ATTESA_MS;
    var battito = setInterval(function () {
      if (spegniBolla() || Date.now() > scade) clearInterval(battito);
    }, OGNI_MS);
  }

  function apriInbox() {
    var t = trovaInbox();
    if (t) {
      accendiBolla(t);
      try { t.bolla.click(); return true; } catch (e) { /* si scende ai contatti */ }
    }
    // Nessuna chat raggiungibile: meglio la pagina contatti che un pulsante
    // che non fa niente.
    window.location.href = contatti();
    return false;
  }

  // ---- il collegamento sempre presente --------------------------------------

  function aggiungiCollegamento() {
    var piede = document.querySelector('[data-assistant] .assistant__actions');
    if (!piede || piede.querySelector('[data-parla-con-persona]')) return;
    var radice = document.querySelector('[data-assistant]');
    var etichetta = (radice && radice.getAttribute('data-assistant-persona-label')) ||
                    'Parla con una persona';
    var a = document.createElement('button');
    a.type = 'button';
    a.className = 'assistant__action';
    a.setAttribute('data-parla-con-persona', '');
    a.textContent = etichetta;
    a.addEventListener('click', function () { apriInbox(); });
    piede.insertBefore(a, piede.firstChild);
  }

  // ---- l'ascolto sulle risposte dell'assistente -----------------------------

  function indirizzoAssistente() {
    var el = document.querySelector('[data-assistant]');
    return (el && el.getAttribute('data-assistant-ai-endpoint')) || '';
  }

  function ascolta() {
    var originale = window.fetch;
    if (typeof originale !== 'function' || originale.__perlaPersona) return;

    var patched = function (risorsa) {
      var esito = originale.apply(this, arguments);
      var indirizzo = indirizzoAssistente();
      if (!indirizzo) return esito;

      var url = '';
      try {
        url = typeof risorsa === 'string' ? risorsa : (risorsa && risorsa.url) || '';
      } catch (e) { return esito; }
      if (url.indexOf(indirizzo) !== 0) return esito;

      // Si legge una COPIA: consumare il corpo qui lascerebbe global.js con
      // un flusso gia' letto, e la risposta non comparirebbe piu' in chat.
      return esito.then(function (risposta) {
        try {
          risposta.clone().json().then(function (d) {
            if (d && d.apri_chat) setTimeout(apriInbox, 900);
          }).catch(function () {});
        } catch (e) { /* non e' JSON: non ci riguarda */ }
        return risposta;
      });
    };
    patched.__perlaPersona = true;
    window.fetch = patched;
  }

  function avvia() {
    if (!document.querySelector('[data-assistant]')) return;
    aggiungiCollegamento();
    ascolta();
    sorvegliaBolla();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', avvia);
  else avvia();
})();
