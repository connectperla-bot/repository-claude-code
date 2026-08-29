// Google Analytics 4 per Perla Italia — pixel personalizzato di Shopify.
//
// DOVE VA INCOLLATO
// Shopify admin -> Impostazioni -> Eventi cliente (Customer events) ->
// Aggiungi pixel personalizzato. Nome: "GA4". Si incolla tutto questo file e
// si preme Salva, poi Connetti.
//
// PERCHE' NON L'HO INSTALLATO IO
// Shopify non ha una mutation per creare un pixel personalizzato: si fa solo
// dall'admin. Tutto il resto — il codice, gli eventi, il consenso — e' gia'
// fatto qui.
//
// PERCHE' QUI E NON NEL TEMA
// Il pixel gira anche sul CHECKOUT, che il tema non tocca: senza, l'acquisto
// non verrebbe mai registrato e Analytics mostrerebbe visite senza vendite.
// E il consenso lo gestisce Shopify, invece di doverlo rifare a mano.
//
// PERCHE' CLARITY NON STA QUI
// I pixel girano in un iframe isolato apposta per non poter leggere la pagina.
// Clarity serve a registrare la pagina — mappe di calore e riproduzione delle
// sessioni — quindi qui dentro si caricherebbe senza errori e non
// registrerebbe niente: il modo peggiore di sbagliare, perche' sembra
// funzionare. Clarity sta nel tema, in snippets/perla-analytics.liquid.

// ==========================================================================
// L'UNICA RIGA DA CAMBIARE
// L'ID di misurazione GA4. Si trova in Google Analytics -> Amministrazione ->
// Flussi di dati -> il flusso del sito -> "ID misurazione", in alto a destra.
// Comincia sempre con G-.
// ==========================================================================
const ID_MISURAZIONE = 'G-XXXXXXXXXX';

// ==========================================================================

if (!ID_MISURAZIONE || ID_MISURAZIONE === 'G-XXXXXXXXXX') {
  // Nessun ID: non si carica niente. Meglio zero dati che dati sbagliati
  // mandati a una proprieta' che non esiste.
  console.warn('[Perla] GA4: manca ID_MISURAZIONE, il pixel non fa niente.');
} else {
  avvia();
}

function avvia() {
  // IL CONSENSO PRIMA DI TUTTO
  // Il negozio vende in Italia e ha una Cookie Policy: senza consenso
  // all'analisi non parte niente. Shopify tiene il consenso e lo espone qui;
  // `analyticsProcessingAllowed()` e' falso finche' il cliente non accetta, e
  // torna vero appena accetta, senza bisogno di ricaricare.
  let attivo = false;
  let codaEventi = [];

  function consentito() {
    try {
      return api.customerPrivacy.analyticsProcessingAllowed();
    } catch (e) {
      // Se l'API non risponde si sta zitti: e' la scelta prudente.
      return false;
    }
  }

  function carica() {
    if (attivo) return;
    attivo = true;
    const s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID_MISURAZIONE;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    gtag('js', new Date());
    // send_page_view: false perche' la pagina la mandiamo noi sull'evento
    // page_viewed di Shopify: qui dentro l'URL della pagina non e' quella che
    // vede il cliente, e lasciandolo fare a gtag finirebbero tutte le visite
    // sullo stesso indirizzo dell'iframe.
    gtag('config', ID_MISURAZIONE, { send_page_view: false });
    codaEventi.forEach(function (e) { gtag('event', e[0], e[1]); });
    codaEventi = [];
  }

  function manda(nome, dati) {
    if (!consentito()) return;
    if (!attivo) { codaEventi.push([nome, dati]); carica(); return; }
    gtag('event', nome, dati);
  }

  // Se il consenso arriva dopo (il cliente accetta il banner a pagina gia'
  // aperta), Shopify emette questo evento e da li' in poi si registra.
  api.customerPrivacy.subscribe('visitorConsentCollected', function () {
    if (consentito() && !attivo) carica();
  });

  // ------------------------------------------------------------------
  // GLI EVENTI
  // Nomi e forma sono quelli standard di GA4 (ecommerce): usandoli, i
  // rapporti "Monetizzazione" di Analytics si riempiono da soli. Inventare
  // nomi propri qui vuol dire doversi costruire ogni rapporto a mano.
  // ------------------------------------------------------------------

  function soldi(m) {
    return m ? Number(m.amount) : undefined;
  }

  function riga(v, quantita) {
    return {
      item_id: v.product && v.product.id,
      item_name: v.product && v.product.title,
      item_variant: v.title,
      item_brand: v.product && v.product.vendor,
      price: soldi(v.price),
      quantity: quantita || 1,
    };
  }

  analytics.subscribe('page_viewed', function (evento) {
    manda('page_view', {
      page_location: evento.context.window.location.href,
      page_title: evento.context.document.title,
    });
  });

  analytics.subscribe('product_viewed', function (evento) {
    const v = evento.data.productVariant;
    manda('view_item', {
      currency: v.price && v.price.currencyCode,
      value: soldi(v.price),
      items: [riga(v)],
    });
  });

  analytics.subscribe('product_added_to_cart', function (evento) {
    const l = evento.data.cartLine;
    manda('add_to_cart', {
      currency: l.cost.totalAmount.currencyCode,
      value: soldi(l.cost.totalAmount),
      items: [riga(l.merchandise, l.quantity)],
    });
  });

  analytics.subscribe('checkout_started', function (evento) {
    const c = evento.data.checkout;
    manda('begin_checkout', {
      currency: c.currencyCode,
      value: soldi(c.totalPrice),
      items: c.lineItems.map(function (l) { return riga(l.variant, l.quantity); }),
    });
  });

  analytics.subscribe('checkout_completed', function (evento) {
    const c = evento.data.checkout;
    manda('purchase', {
      // transaction_id serve a GA4 per non contare due volte lo stesso
      // ordine se il cliente ricarica la pagina di ringraziamento.
      transaction_id: c.order && c.order.id,
      currency: c.currencyCode,
      value: soldi(c.totalPrice),
      tax: soldi(c.totalTax),
      shipping: c.shippingLine && soldi(c.shippingLine.price),
      items: c.lineItems.map(function (l) { return riga(l.variant, l.quantity); }),
    });
  });
}
