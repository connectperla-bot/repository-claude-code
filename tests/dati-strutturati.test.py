#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I dati strutturati della scheda prodotto: quelli che legge Google.

IL GUASTO CHE QUESTA PROVA CERCA
Questo blocco non lo vede nessuno. Non e' in pagina, non da' errore, non
compare nei log: e' un <script> che leggono solo i motori di ricerca. Se
dentro c'e' una virgola di troppo, Google butta via tutto il blocco e il
prodotto perde le informazioni ricche nel risultato di ricerca. Se dentro c'e'
un dato sbagliato, Google se lo tiene per buono.

COSA E' STATO TROVATO IL 12 SETTEMBRE
La marca dichiarata era {{ shop.name }}, cioe' "PERLA ITALIA" tutto maiuscolo.
Su Shopify il campo marca dice "Perla Italia", e perla-controlla-catalogo.py
lo impone con un commento che spiega il perche': il maiuscolo appartiene al
cartiglio stampato sul tessuto, non al campo che finisce nel feed di Google.
Il controllo del catalogo passava -- guardava Shopify -- mentre questa pagina
diceva un'altra cosa. Due fonti, due risposte, nessuno che le confrontasse.

E la descrizione arrivava con le entita' HTML dentro: Google leggeva
«Collare &quot;Barocco&quot;» alla lettera.

LE DUE COSE CHE QUI NON CI DEVONO ESSERE
- aggregateRating: il negozio non ha ancora nessuna recensione. Dichiarare un
  punteggio medio significherebbe inventarselo, ed e' il genere di cosa per
  cui Google toglie le informazioni ricche a tutto il sito. Va messo il giorno
  che le recensioni ci sono, non prima.
- una politica di reso sola. La pagina ne dichiara due -- 30 giorni sui
  prodotti non personalizzati, nessun ripensamento su quelli personalizzati,
  che e' l'esclusione di legge sui beni fatti su misura. Un 30 giorni buttato
  su tutto prometterebbe a Google qualcosa che il cliente non ottiene.

COSA CONTROLLA, E COME
Legge il Liquid, non la pagina servita: cosi' gira senza rete e blocca il
difetto prima che arrivi sul tema. Per il JSON simula le due strade di ogni
{% if %} -- quella presa e quella no -- e verifica che il risultato sia JSON
valido in tutte e due: e' li' che si nasconde la virgola di troppo.

Uso:  python3 tests/dati-strutturati.test.py
"""
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
FILE = os.path.join(RADICE, "theme", "snippets", "meta-tags.liquid")

COMMENTO = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", re.S)
BLOCCO = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

fatte = 0


def prova(nome, fn):
    global fatte
    try:
        fn()
        print("  ok   " + nome)
        fatte += 1
    except AssertionError as e:
        print("  FALLITO   %s\n        %s" % (nome, e))
        sys.exit(1)


GREZZO = open(FILE, encoding="utf-8").read()
CODICE = COMMENTO.sub("", GREZZO)          # senza i commenti: solo quello che esce
PRODOTTO = ""
for b in BLOCCO.findall(CODICE):
    if '"@type": "Product"' in b:
        PRODOTTO = b
        break


def finto_json(testo, rami_veri):
    """Il blocco Liquid come JSON, scegliendo una strada per ogni {% if %}.

    In ordine: le stringhe che contengono un {{ ... }} diventano "X" intere --
    se no "https:{{ url }}" si spezzerebbe in due virgolette; i cicli rendono
    un giro solo, con la virgola fra un elemento e l'altro spenta (e' cosi'
    che rende davvero una lista di un'immagine); poi si sceglie il ramo degli
    if. Quel che resta deve essere JSON valido, ed e' li' che si nasconde la
    virgola di troppo.
    """
    t = testo
    # senza re.S: una stringa JSON non attraversa le righe, e con il punto
    # che mangia anche gli a capo questa sostituzione inghiottiva mezzo blocco.
    t = re.sub(r'"[^"\n]*\{\{[^\n]*?\}\}[^"\n]*"', '"X"', t)
    t = re.sub(r"\{%-?\s*unless\b.*?-?%\}.*?\{%-?\s*endunless\s*-?%\}", "", t, flags=re.S)
    for _ in range(10):
        m = re.search(r"\{%-?\s*for\s[^%]*?-?%\}(.*?)\{%-?\s*endfor\s*-?%\}", t, re.S)
        if not m:
            break
        t = t[:m.start()] + m.group(1) + t[m.end():]
    for _ in range(20):
        m = re.search(r"\{%-?\s*if\s[^%]*?-?%\}(.*?)(?:\{%-?\s*else\s*-?%\}(.*?))?\{%-?\s*endif\s*-?%\}",
                      t, re.S)
        if not m:
            break
        tenuto = (m.group(1) if rami_veri else (m.group(2) or ""))
        t = t[:m.start()] + tenuto + t[m.end():]
    t = re.sub(r"\{%-?.*?-?%\}", "", t, flags=re.S)
    t = re.sub(r"\{\{.*?\}\}", '"X"', t, flags=re.S)
    return t


print("\nI dati strutturati della scheda prodotto")


def il_blocco_c_e():
    assert PRODOTTO, (
        "in %s non c'e' piu' un blocco ld+json di tipo Product: la scheda "
        "prodotto non direbbe piu' niente a Google, e nessun'altra prova se ne "
        "accorgerebbe." % os.path.relpath(FILE, RADICE))


prova("la scheda prodotto dichiara un Product", il_blocco_c_e)


def json_valido_in_tutte_e_due_le_strade():
    rotte = []
    for rami, nome in ((True, "col ramo vero"), (False, "col ramo falso")):
        testo = finto_json(PRODOTTO, rami)
        try:
            d = json.loads(testo)
        except ValueError as e:
            rotte.append("%s: %s\n        %s" % (nome, e, " ".join(testo.split())[:220]))
            continue
        assert d.get("@type") == "Product"
    assert not rotte, (
        "il JSON non si legge, e Google butterebbe via tutto il blocco:\n        "
        + "\n        ".join(rotte))


prova("il JSON resta valido sia che gli if passino sia che no",
      json_valido_in_tutte_e_due_le_strade)


def la_marca_viene_dal_prodotto():
    """La marca puo' passare per una variabile: si segue fino alla fonte."""
    riga = [l for l in PRODOTTO.splitlines() if '"brand"' in l]
    assert riga, "la marca non e' piu' dichiarata nei dati strutturati"
    r = riga[0]
    m = re.search(r'"name"\s*:\s*\{\{\s*([A-Za-z0-9_.]+)', r)
    assert m, "non si capisce da dove venga la marca: %s" % r.strip()
    fonte = m.group(1)
    if not fonte.startswith("product.vendor"):
        # e' una variabile: si guarda dove viene assegnata
        a = re.search(r"assign\s+%s\s*=\s*([^-%%]+)" % re.escape(fonte), CODICE)
        assert a, ("la marca viene da %r, che non risulta assegnato da nessuna "
                   "parte in questo file." % fonte)
        fonte = a.group(1).strip()
    assert "product.vendor" in fonte, (
        "la marca non viene piu' dal campo marca del prodotto, ma da: %s\n        "
        "shop.name e' \"PERLA ITALIA\" tutto maiuscolo -- il nome del negozio, "
        "non la marca -- e mandarlo a Google rimette in piedi la differenza fra "
        "quello che dice Shopify e quello che dice la pagina." % fonte)


prova("la marca viene dal campo marca del prodotto, non dal nome del negozio",
      la_marca_viene_dal_prodotto)


def niente_punteggio_inventato():
    assert "aggregateRating" not in CODICE, (
        "c'e' un aggregateRating nei dati strutturati. Il negozio non ha "
        "recensioni: quel punteggio sarebbe inventato, e Google toglie le "
        "informazioni ricche a tutto il sito quando se ne accorge. Va messo "
        "quando le recensioni ci sono davvero, prendendolo da Judge.me.")
    assert "aggregateRating" in GREZZO, (
        "e' sparito anche il commento che spiega perche' aggregateRating non "
        "c'e'. Senza quello, il prossimo che guarda lo aggiunge in buona fede.")


prova("nessun punteggio medio finche' non ci sono recensioni vere",
      niente_punteggio_inventato)


def il_reso_resta_due_cose():
    assert "hasMerchantReturnPolicy" in PRODOTTO, "la politica di reso non e' piu' dichiarata"
    assert "MerchantReturnFiniteReturnWindow" in PRODOTTO and "merchantReturnDays" in PRODOTTO, (
        "sparita la finestra di 30 giorni sui prodotti non personalizzati")
    assert "MerchantReturnNotPermitted" in PRODOTTO, (
        "sparito il caso dei prodotti personalizzati, dove il reso per "
        "ripensamento non e' previsto. Dichiarare 30 giorni anche su quelli "
        "prometterebbe a Google una cosa che il cliente non ottiene.")


prova("il reso resta due politiche, come le dichiara la pagina",
      il_reso_resta_due_cose)


def le_entita_vengono_sciolte():
    assert "&quot;" in CODICE and "replace:" in CODICE, (
        "e' sparita la decodifica delle entita' HTML. page_description esce con "
        "&quot; e &#39; gia' dentro, perche' e' fatto per finire in un "
        "attributo; nel JSON Google le leggerebbe alla lettera.")
    i_amp = CODICE.find("'&amp;'")
    assert i_amp > CODICE.find("'&quot;'") and i_amp > CODICE.find("'&lt;'"), (
        "&amp; non e' piu' l'ultima sostituzione: cosi' decodifica due volte "
        "quello appena scritto dalle altre.")


prova("le entita' HTML vengono sciolte, e &amp; per ultimo",
      le_entita_vengono_sciolte)


def i_campi_che_google_chiede():
    mancanti = [c for c in ("\"sku\"", "itemCondition", "priceValidUntil",
                            "priceCurrency", "availability")
                if c not in PRODOTTO]
    assert not mancanti, (
        "mancano dall'offerta: %s. Senza questi Google segnala la scheda come "
        "incompleta e non le da' le informazioni ricche." % ", ".join(mancanti))


prova("l'offerta porta sku, condizione, valuta, disponibilita' e scadenza prezzo",
      i_campi_che_google_chiede)

print("\n  %d verifiche\n" % fatte)
