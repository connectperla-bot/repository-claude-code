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
 * LA PARTE CHE VA CONFERMATA
 * Shopify Inbox non e' ancora installato sul negozio, quindi il gancio per
 * aprirlo non ho potuto provarlo dal vivo: si tentano nell'ordine i modi noti
 * e, se nessuno risponde, si finisce sulla pagina contatti invece di lasciare
 * il cliente davanti a un pulsante che non fa niente. Appena Inbox e'
 * installato basta guardare quale dei tentativi va a segno e tenere solo
 * quello.
 */
(function () {
  'use strict';

  function contatti() {
    var a = document.querySelector('.assistant__action[href^="/pages"], .assistant__action[href^="/apps"]');
    return (a && a.getAttribute('href')) || '/pages/contact';
  }

  // I tentativi, dal piu' pulito al piu' grossolano. Ognuno torna true se ha
  // trovato qualcosa da aprire.
  var TENTATIVI = [
    function () {   // l'interfaccia che Inbox espone quando c'e'
      if (window.ShopifyChat && typeof window.ShopifyChat.open === 'function') {
        window.ShopifyChat.open();
        return true;
      }
      return false;
    },
    function () {   // il pulsante dell'incorporamento, sotto i suoi vari nomi
      var b = document.querySelector(
        '#ShopifyChat button, [id^="ShopifyChat"] button, ' +
        '.shopify-chat-launcher, [data-shopify-chat-launcher], ' +
        'button[aria-label*="chat" i]'
      );
      if (b) { b.click(); return true; }
      return false;
    },
  ];

  function apriInbox() {
    for (var i = 0; i < TENTATIVI.length; i++) {
      try { if (TENTATIVI[i]()) return true; } catch (e) { /* si prova il prossimo */ }
    }
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
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', avvia);
  else avvia();
})();
