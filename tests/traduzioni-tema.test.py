#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ogni `| t` del tema trova la sua traduzione, in tutte e due le lingue?

IL GUASTO CHE QUESTA PROVA CERCA
Liquid non si lamenta per una chiave che manca: stampa in pagina
`Translation missing: it.qualcosa` e tira dritto. Il difetto non si vede da
nessuna parte -- non nei log, non in npm test, non nell'audit del catalogo --
finche' non lo vede un cliente in vetrina.

LE TRADUZIONI STANNO IN DUE POSTI, E CONFONDERLI COSTA CARO
Questa prova nasce da un FALSO ALLARME, ed e' il motivo per cui e' scritta
cosi'. L'11 settembre sections/perla-consiglia-taglia.liquid risultava usare
tredici chiavi `taglia.*` che in theme/locales/ non esistono. Sembrava che
pubblicare il tema avrebbe mostrato "Translation missing" in ogni campo del
consigliatore di taglia. Non era vero: quella sezione porta le tredici
stringhe dentro il proprio `{% schema %}`, nel blocco "locales", e Shopify le
risolve da li'. In vetrina "Translation missing" compare zero volte, su tutti
e due i temi.

Quindi la regola vera, e che questa prova applica, e':

  - una SEZIONE con un blocco "locales" nel suo schema risolve le proprie
    chiavi prima li', poi nei file di lingua globali;
  - tutto il resto (snippet, layout, template) risolve solo nei file globali,
    perche' le traduzioni di schema sono legate al file che le dichiara.

Una prova che ignorasse il primo caso darebbe lo stesso falso allarme al
prossimo che la guarda -- e un allarme che si sa gia' essere falso e' peggio
di nessun allarme, perche' insegna a non guardare.

COSA NON CONTROLLA
Che la traduzione sia giusta, o che sia davvero tradotta: `en.json` potrebbe
contenere l'italiano e questa prova sarebbe verde. Controlla che la chiave si
risolva, che e' la differenza fra una pagina che si legge e una che mostra il
nome di una variabile al cliente.

Uso:  python3 tests/traduzioni-tema.test.py
"""
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
TEMA = os.path.join(RADICE, "theme")
LINGUE = {
    "it": os.path.join(TEMA, "locales", "it.default.json"),
    "en": os.path.join(TEMA, "locales", "en.json"),
}

# `{{ 'sections.product.quantity' | t }}` e `{% ... 'x.y' | t ... %}`, con le
# virgolette in tutti e due i versi e spazi a piacere attorno alla barra.
CHIAVE = re.compile(r"""['"]([a-z0-9_]+(?:\.[a-z0-9_]+)+)['"]\s*\|\s*t(?:ranslate)?\b""",
                    re.IGNORECASE)
SCHEMA = re.compile(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}", re.S)

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


def senza_commento(testo):
    """I file di lingua di Shopify iniziano con un blocco /* ... */."""
    return re.sub(r"^\s*/\*.*?\*/\s*", "", testo, flags=re.S)


def globali():
    return {l: json.loads(senza_commento(open(p, encoding="utf-8").read()))
            for l, p in LINGUE.items()}


def locali_di_sezione(testo):
    """Il blocco "locales" dello schema, se c'e'. Lingua -> albero."""
    m = SCHEMA.search(testo)
    if not m:
        return {}
    try:
        return (json.loads(m.group(1)) or {}).get("locales", {}) or {}
    except ValueError:
        return {}


def risolvi(albero, chiave):
    nodo = albero
    for pezzo in chiave.split("."):
        if not isinstance(nodo, dict) or pezzo not in nodo:
            return None
        nodo = nodo[pezzo]
    return nodo if isinstance(nodo, (str, dict)) else None


def file_del_tema():
    for cartella, _, file in os.walk(TEMA):
        if os.path.basename(cartella) == "locales":
            continue
        for f in sorted(file):
            if f.endswith((".liquid", ".json")):
                yield os.path.join(cartella, f)


GLOBALI = globali()
USATE = []          # (chiave, percorso relativo, locali della sezione)
for percorso in file_del_tema():
    testo = open(percorso, encoding="utf-8", errors="replace").read()
    suoi = locali_di_sezione(testo)
    rel = os.path.relpath(percorso, RADICE)
    for c in set(CHIAVE.findall(testo)):
        USATE.append((c, rel, suoi))

print("\nLe traduzioni del tema")


def ce_ne_sono():
    assert len({c for c, _, _ in USATE}) > 100, (
        "trovate solo %d chiavi diverse: l'espressione che le cerca non funziona "
        "piu', e una prova che non guarda niente passa sempre"
        % len({c for c, _, _ in USATE}))


prova("il tema chiede piu' di cento chiavi diverse", ce_ne_sono)


def tutte_risolvono():
    rotte = []
    for chiave, dove, suoi in sorted(USATE):
        for lingua in sorted(LINGUE):
            if risolvi(suoi.get(lingua, {}), chiave) is not None:
                continue          # la risolve la sezione, col suo schema
            if risolvi(GLOBALI[lingua], chiave) is not None:
                continue          # la risolve il file di lingua
            rotte.append("%s: %s  (la chiede %s)" % (lingua, chiave, dove))
    assert not rotte, (
        "queste chiavi non si risolvono: in pagina il cliente leggerebbe "
        "\"Translation missing\" al loro posto.\n        "
        + "\n        ".join(rotte[:20])
        + ("\n        ... e altre %d" % (len(rotte) - 20) if len(rotte) > 20 else ""))


prova("ogni chiave si risolve, in italiano e in inglese", tutte_risolvono)


def le_sezioni_traducono_in_tutte_e_due():
    """Uno schema con le stringhe in una lingua sola e' meta' lavoro.

    E' il rischio vero di questo meccanismo: le traduzioni di sezione non
    stanno nei file di lingua, quindi nessuno le vede quando controlla che
    i due locali siano pari.
    """
    zoppe = []
    for percorso in file_del_tema():
        suoi = locali_di_sezione(open(percorso, encoding="utf-8", errors="replace").read())
        if not suoi:
            continue
        rel = os.path.relpath(percorso, RADICE)

        def foglie(nodo, pre=""):
            for k, v in nodo.items():
                if isinstance(v, dict):
                    for x in foglie(v, pre + k + "."):
                        yield x
                else:
                    yield pre + k
        per_lingua = {l: set(foglie(suoi.get(l, {}))) for l in LINGUE}
        if per_lingua["it"] != per_lingua["en"]:
            manca = (per_lingua["it"] ^ per_lingua["en"])
            zoppe.append("%s: %s" % (rel, ", ".join(sorted(manca)[:6])))
    assert not zoppe, (
        "queste sezioni traducono in una lingua e non nell'altra:\n        "
        + "\n        ".join(zoppe))


prova("le sezioni con traduzioni proprie le hanno in tutte e due le lingue",
      le_sezioni_traducono_in_tutte_e_due)


def il_consigliatore_taglia():
    """Le tredici del consigliatore: nominate una per una, non per caso.

    Stanno nello schema della sezione. Se qualcuno le sposta nei file di
    lingua globali va bene lo stesso -- la prova sopra se ne accorge -- ma
    qui si chiede che ci siano DA QUALCHE PARTE, perche' sono le stringhe
    di un pannello intero.
    """
    attese = ["apri", "calcola", "collo", "collo_ph", "esito_fuori", "esito_ok",
              "esito_vuoto", "guida", "nota", "peso", "peso_ph", "razza", "razza_ph"]
    p = os.path.join(TEMA, "sections", "perla-consiglia-taglia.liquid")
    suoi = locali_di_sezione(open(p, encoding="utf-8").read())
    for lingua in sorted(LINGUE):
        for k in attese:
            v = (risolvi(suoi.get(lingua, {}), "taglia." + k)
                 or risolvi(GLOBALI[lingua], "taglia." + k))
            assert isinstance(v, str) and v.strip(), (
                "taglia.%s non si risolve in %s: il consigliatore di taglia "
                "mostrerebbe \"Translation missing\" in quel campo" % (k, lingua))


prova("le tredici del consigliatore di taglia si risolvono nelle due lingue",
      il_consigliatore_taglia)


def i_due_locali_hanno_le_stesse_chiavi():
    def foglie(nodo, pre=""):
        for k, v in nodo.items():
            if isinstance(v, dict):
                for x in foglie(v, pre + k + "."):
                    yield x
            else:
                yield pre + k
    it, en = set(foglie(GLOBALI["it"])), set(foglie(GLOBALI["en"]))
    solo_it, solo_en = sorted(it - en), sorted(en - it)
    assert not solo_it and not solo_en, (
        "i due file di lingua si sono separati.\n        solo in it: %s\n        solo in en: %s"
        % (", ".join(solo_it[:10]) or "nessuna", ", ".join(solo_en[:10]) or "nessuna"))


prova("i due file di lingua contengono le stesse chiavi", i_due_locali_hanno_le_stesse_chiavi)

print("\n  %d verifiche\n" % fatte)
