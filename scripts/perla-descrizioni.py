#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le descrizioni delle schede prodotto scritte a mano, in un posto solo.

PERCHE' STANNO QUI E NON DENTRO GLI SCRIPT CHE LE USANO
Sono testo, non codice: chi le rilegge per correggere una virgola non deve
passare in mezzo alle chiamate all'API di Printify, e chi tocca l'API non
deve scorrere trecento righe di HTML per arrivare alla funzione dopo.

LA FORMA E' QUELLA DEGLI ALTRI 114 PRODOTTI -- Dettagli, Taglie,
Personalizzazione, Cura, Spedizione, Sicurezza -- perche' la scheda di un
prodotto nuovo non deve sembrare di un altro negozio.

SPEDIZIONE lo dice l'informativa vera del negozio, non un numero inventato:
"Per gli Stati Uniti mettiamo in conto 10 - 20 giorni lavorativi". Se quella
pagina cambia, cambia anche questa riga.
"""

# La sezione che manca a tutti e 48 i prodotti Printify: ce l'hanno tutti e
# 66 gli europei e nessuno degli americani. Il verbo cambia perche' due di
# questi si incidono e non si stampano.
SPEDIZIONE_USA = (
    u"<p><strong>Spedizione</strong></p>"
    u"<p>%s e spedit%s da un laboratorio negli Stati Uniti. Consegna in "
    u"10 \u2013 20 giorni lavorativi, produzione compresa. "
    u"Spedizione gratuita.</p>")


def spedizione(verbo=u"Stampato", genere=u"o"):
    return SPEDIZIONE_USA % (verbo, genere)


# Le descrizioni tengono le sezioni degli altri 114 prodotti -- Dettagli,
# Taglie, Personalizzazione, Cura, Spedizione -- perche' la scheda di un
# prodotto nuovo non deve sembrare di un altro negozio. La riga sui caratteri
# incidibili sta solo dove si incide davvero.
DESCRIZIONI = {
    "collare-pelle": u"""<p>Pelle vera e una fibbia di metallo: il collare che si incide, non si stampa. Il nome del tuo animale e il tuo numero restano nel cuoio, scavati dal laser, e non si scoloriscono con l'acqua ne' si consumano con l'uso.</p>
<p><strong>Dettagli</strong></p>
<ul>
<li>Pelle sintetica robusta, morbida al collo, cucita e rifinita a mano</li>
<li>Incisione a laser sulla fascia esterna: il segno e' nel materiale, non sopra</li>
<li>Fibbia e anello in metallo, argento o nero secondo il colore scelto</li>
<li>Sette colori: nero, blu, grigio, rosa, cuoio naturale, rosso, verde acqua</li>
</ul>
<p><strong>Taglie</strong></p>
<ul>
<li>Small, Medium, Large, Extra Large — misura il collo del tuo animale e aggiungi due dita di agio</li>
<li>Nel dubbio scegli la taglia sopra: la fibbia recupera, la pelle no</li>
</ul>
<p><strong>Personalizzazione</strong></p>
<ul>
<li>Scrivi nome e numero nello studio di personalizzazione: fino a circa venti caratteri stanno comodi, oltre le lettere si stringono</li>
<li>L'incisione e' monocroma per forza: quello che decide la resa e' la forma della lettera, non il colore</li>
<li>Rileggi il testo prima di ordinare — ogni pezzo viene inciso apposta e non si puo' rifare</li>
</ul>
<p><strong>Cura</strong></p>
<ul>
<li>Pulisci con un panno umido e asciuga subito</li>
<li>Evita l'ammollo prolungato e i detergenti aggressivi</li>
</ul>
<p><strong>Spedizione</strong></p>
<p>Inciso e spedito da un laboratorio negli Stati Uniti. Consegna in 10 – 20 giorni lavorativi, produzione compresa. Spedizione gratuita.</p>
<p><strong>Sicurezza</strong></p>
<ul>
<li>Disegnato in Italia, con gusto italiano</li>
<li>Sorveglia sempre il tuo animale. Il collare serve all'uso quotidiano e all'identificazione — non sostituisce l'addestramento o la sorveglianza</li>
</ul>""",
    "medaglietta-incisa": u"""<p>Alluminio anodizzato e un laser che toglie il colore per scrivere: dove incide, il metallo torna lucido. E' un contrasto che non stinge e non si stacca, perche' non c'e' niente di appoggiato sopra.</p>
<p><strong>Dettagli</strong></p>
<ul>
<li>Medaglietta in alluminio anodizzato, leggera e silenziosa sul collare</li>
<li>Incisione a laser: il segno chiaro e' il metallo sotto, non una vernice</li>
<li>Tre forme: cerchio, cuore, osso</li>
<li>Cinque colori: nero, blu, argento, rosso, rosa</li>
<li>Anello di aggancio incluso, si mette su quasi tutti i collari</li>
</ul>
<p><strong>Taglie</strong></p>
<ul>
<li>Taglia unica</li>
</ul>
<p><strong>Personalizzazione</strong></p>
<ul>
<li>Nome sul davanti e numero di telefono dietro e' la scelta piu' usata: fino a circa quindici caratteri per riga restano leggibili a distanza di braccio</li>
<li>Meglio poche parole grandi che molte piccole — su un disco di due centimetri e mezzo si legge solo cio' che e' grande</li>
<li>Controlla il testo prima di ordinare: ogni medaglietta viene incisa apposta per te</li>
</ul>
<p><strong>Cura</strong></p>
<ul>
<li>Pulisci con un panno morbido leggermente umido</li>
<li>Evita detergenti abrasivi, che opacizzano l'anodizzazione</li>
</ul>
<p><strong>Spedizione</strong></p>
<p>Incisa e spedita da un laboratorio negli Stati Uniti. Consegna in 10 – 20 giorni lavorativi, produzione compresa. Spedizione gratuita.</p>
<p><strong>Sicurezza</strong></p>
<ul>
<li>Disegnata in Italia, con gusto italiano</li>
<li>Sorveglia sempre il tuo animale. La medaglietta serve all'identificazione — non sostituisce l'addestramento o la sorveglianza</li>
</ul>""",
    "giacchetto": u"""<p>Un parka vero per il cane: tessuto khaki, cappuccio bordato di pelo e la schiena libera per il tuo disegno. Quello che metti sul dorso si vede da lontano, ed e' l'unico punto in cui questo capo chiede di essere personale.</p>
<p><strong>Dettagli</strong></p>
<ul>
<li>Parka imbottito color khaki, taglio che copre dorso e fianchi</li>
<li>Cappuccio con bordo di pelo sintetico, staccabile dallo sguardo ma non dal capo</li>
<li>Stampa sul dorso a colori pieni, morbida al tatto e lavabile</li>
<li>Apertura per il guinzaglio e chiusura regolabile sotto la pancia</li>
</ul>
<p><strong>Taglie</strong></p>
<ul>
<li>Sei taglie, da XS a 2XL — misura la schiena dal collo alla base della coda</li>
<li>Il parka deve stare comodo sopra il pelo d'inverno: nel dubbio prendi la taglia sopra</li>
</ul>
<p><strong>Personalizzazione</strong></p>
<ul>
<li>Carica una foto, un motivo o un nome nello studio di personalizzazione: il disegno va sul dorso</li>
<li>Le immagini grandi e definite rendono meglio: sul dorso di un XS il disegno viene ridotto parecchio</li>
<li>Guarda l'anteprima prima di ordinare — ogni capo viene stampato apposta per te</li>
</ul>
<p><strong>Cura</strong></p>
<ul>
<li>Lavaggio in lavatrice a freddo, rovescio, con capi di colore simile</li>
<li>Asciugatura all'aria: il calore rovina sia l'imbottitura sia la stampa</li>
</ul>
<p><strong>Spedizione</strong></p>
<p>Stampato e spedito da un laboratorio negli Stati Uniti. Consegna in 10 – 20 giorni lavorativi, produzione compresa. Spedizione gratuita.</p>
<p><strong>Sicurezza</strong></p>
<ul>
<li>Disegnato in Italia, con gusto italiano</li>
<li>Sorveglia sempre il tuo animale. Il capo serve a coprire dal freddo — non sostituisce l'addestramento o la sorveglianza</li>
</ul>""",
}


# ==========================================================================
# IL PREZZO, PRIMA DI PUBBLICARE E NON DOPO
# ==========================================================================

def prezzi(prod, prodotto, tasso, riserva, margine):
    """(id variante -> prezzo in centesimi, righe da stampare).

    La regola non e' scritta qui: al_90() e la definizione di margine
    arrivano da perla-prezzi-margine.py, che e' l'unico posto dove stanno.
    Qui c'e' solo il pezzo che quel listino non puo' fare -- leggere il costo
    di un prodotto che su Shopify ANCORA NON C'E'.

    E si fa prima di pubblicare apposta. perla-prezzi-margine.py legge i
    prezzi dalla vetrina pubblica: per usarlo bisognerebbe pubblicare, e il
    prodotto starebbe in vendita a 99,00 -- il segnaposto della creazione --
    per tutto il tempo che passa fra la pubblicazione e la correzione.
    """
    spedizione = None
    d = carica.api("GET", "/v1/catalog/blueprints/%d/print_providers/%d/shipping.json"
                   % (prod["blueprint"], prod["provider"]), token=prod["_token"])
    for profilo in d.get("profiles", []):
        # gli Stati Uniti sono l'unico paese fuori dalla UE in cui il negozio
        # spedisce, e questa linea ai clienti europei non si vede nemmeno:
        # il perche' sta per intero in perla-verifica-margini.py
        if "US" in profilo.get("countries", []):
            spedizione = profilo["first_item"]["cost"] / 100.0
            break
    if spedizione is None:
        raise RuntimeError("nessun profilo di spedizione verso gli USA per %s"
                           % prod["chiave"])

    fuori, righe = {}, []
    for v in prodotto["variants"]:
        if not v.get("is_enabled"):
            continue
        costo = (v["cost"] / 100.0 + spedizione) * tasso * (1 + riserva)
        prezzo = listino.al_90(costo / (1 - margine))
        fuori[v["id"]] = int(round(prezzo * 100))
        righe.append((v["title"], costo, prezzo,
                      100 * (prezzo - costo) / prezzo))
    return fuori, righe, spedizione
