#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controlla il catalogo pubblico e segnala i difetti che si vedono davvero.

PERCHE' ESISTE
Una scansione a mano ha trovato, in una volta sola: quarantanove prodotti con
la marca "Printify" invece di Perla, centoundici con il tipo "Pets" invece del
tipo italiano, ottantanove titoli con le virgolette dritte in mezzo ad altri
con quelle curve, e quattrocentoquarantacinque immagini su quattrocento-
quarantacinque senza testo alternativo. Nessuno di questi si nota guardando
una scheda: si notano solo contandoli tutti insieme.

Sono anche difetti che RIENTRANO da soli. Ogni prodotto nuovo importato da un
fornitore arriva con la sua marca, il suo tipo e le sue virgolette, e nessuno
se ne accorge finche' non se ne contano di nuovo cento. Per questo il
controllo e' uno script e non una nota.

COSA NON SERVE
Nessuna chiave: legge /products.json, che e' pubblico e contiene quello che
vede un cliente. Quindi controlla lo stato REALE del negozio, non quello che
l'Admin crede -- ed e' proprio quella la differenza che conta, visto che i
cataloghi di mercato mostrano linee diverse a paesi diversi.

USO
    python3 scripts/perla-controlla-catalogo.py
    python3 scripts/perla-controlla-catalogo.py --negozio https://altro.com

Esce con 1 se trova qualcosa, cosi' si puo' mettere in una verifica automatica.
"""
import collections
import json
import re
import subprocess
import sys

NEGOZIO = "https://perlaitaly.com"

# I valori attesi. Sono la decisione presa, non un'opinione: la marca e' una
# sola, il tipo di prodotto e' in italiano e specifico (serve a Google Shopping
# e ai filtri del tema), le virgolette sono quelle tipografiche.
MARCA = "PERLA ITALIA"
TIPI = {"Collare", "Bandana", "Ciotola", "Guinzaglio", "Medaglietta",
        "Cuccia", "Tappetino"}


def scarica(negozio):
    prodotti = []
    for pagina in (1, 2, 3):
        r = subprocess.run(
            ["curl", "-sfL", "-m", "90",
             "%s/products.json?limit=250&page=%d" % (negozio, pagina)],
            capture_output=True, text=True)
        if r.returncode != 0:
            break
        try:
            parte = json.loads(r.stdout).get("products", [])
        except ValueError:
            break
        if not parte:
            break
        prodotti += parte
    return prodotti


def linea_eu(p):
    """Vero se il prodotto e' della linea europea (fornitore Printful).

    Le due linee vivono in cataloghi di mercato separati: chi naviga
    dall'Europa vede solo la prima, chi naviga dagli Stati Uniti solo la
    seconda. Diverse regole valgono per l'una e per l'altra, e confonderle
    riempie il controllo di falsi allarmi."""
    h = p["handle"]
    return "fornitore-europeo" in h or bool(
        re.match(r"^(collare|bandana|ciotola|guinzaglio|medaglietta|cuccia)-eu-", h))


def controlla(prodotti):
    """Ogni voce e' (titolo del difetto, elenco dei prodotti colpiti)."""
    difetti = []

    marche = collections.Counter(p["vendor"] for p in prodotti)
    fuori = [p["handle"] for p in prodotti if p["vendor"] != MARCA]
    if fuori:
        difetti.append(("marca diversa da %r (trovate: %s)"
                        % (MARCA, dict(marche)), fuori))

    tipi = [p["handle"] for p in prodotti if p["product_type"] not in TIPI]
    if tipi:
        visti = collections.Counter(p["product_type"] for p in prodotti
                                    if p["product_type"] not in TIPI)
        difetti.append(("tipo di prodotto non previsto (%s)" % dict(visti), tipi))

    dritte = [p["handle"] for p in prodotti if '"' in p["title"]]
    if dritte:
        difetti.append(('virgolette dritte nel titolo invece di quelle curve',
                        dritte))

    doppio = [p["handle"] for p in prodotti if "  " in p["title"]]
    if doppio:
        difetti.append(("doppio spazio nel titolo", doppio))

    # Le descrizioni: vuote o cosi' corte da non dire niente.
    corte = []
    for p in prodotti:
        testo = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p["body_html"] or ""))
        if len(testo.strip()) < 200:
            corte.append(p["handle"])
    if corte:
        difetti.append(("descrizione assente o sotto i 200 caratteri", corte))

    # Prezzi impossibili. Zero vuol dire quasi sempre una variante dimenticata.
    zero = [p["handle"] for p in prodotti
            if any(float(v["price"]) <= 0 for v in p["variants"])]
    if zero:
        difetti.append(("prezzo a zero", zero))

    # Un prodotto con una sola foto converte male: non e' un errore, e' una
    # mancanza, e va vista.
    sole = [p["handle"] for p in prodotti if len(p["images"]) < 2]
    if sole:
        difetti.append(("meno di due fotografie", sole))

    # Nomi delle opzioni. "Size" e' giusto sulla linea americana e sbagliato su
    # quella europea: senza questa distinzione il controllo segnalerebbe
    # quarantanove prodotti corretti a ogni esecuzione, e in due settimane
    # nessuno lo guarderebbe piu'.
    inglesi = [p["handle"] for p in prodotti
               if linea_eu(p)
               and any(o["name"] in ("Size", "Color", "Style") for o in p["options"])]
    if inglesi:
        difetti.append(("nome dell'opzione in inglese sulla linea europea", inglesi))

    # Prezzi diversi per lo stesso tipo, DENTRO la stessa linea: due listini
    # per lo stesso prodotto sono quasi sempre un aggiornamento lasciato a
    # meta'. Fra EU e USA invece la differenza e' voluta -- costi di
    # produzione diversi -- e un cliente non vede mai le due insieme.
    for nome, gruppo in (("europea", [p for p in prodotti if linea_eu(p)]),
                         ("americana", [p for p in prodotti if not linea_eu(p)])):
        per_tipo = collections.defaultdict(set)
        for p in gruppo:
            per_tipo[p["product_type"]].add(min(float(v["price"]) for v in p["variants"]))
        misti = ["%s: %s" % (t, sorted(v)) for t, v in per_tipo.items() if len(v) > 1]
        if misti:
            difetti.append(("prezzo di partenza diverso dentro lo stesso tipo, "
                            "linea %s" % nome, misti))

    return difetti


def main(argv):
    negozio = NEGOZIO
    if "--negozio" in argv:
        negozio = argv[argv.index("--negozio") + 1]

    prodotti = scarica(negozio)
    if not prodotti:
        print("Nessun prodotto scaricato da %s: il negozio risponde?" % negozio)
        return 2
    print("%d prodotti pubblici da %s\n" % (len(prodotti), negozio))

    difetti = controlla(prodotti)
    if not difetti:
        print("Nessun difetto.")
        return 0

    for titolo, colpiti in difetti:
        print("%s — %d" % (titolo, len(colpiti)))
        for c in colpiti[:6]:
            print("    %s" % c)
        if len(colpiti) > 6:
            print("    ... e altri %d" % (len(colpiti) - 6))
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
