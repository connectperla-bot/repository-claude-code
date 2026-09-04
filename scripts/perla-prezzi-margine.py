#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il prezzo di ogni variante, ricavato dal costo vero e da un margine solo.

LA REGOLA, DETTA DALLA PROPRIETARIA IL 4 SETTEMBRE
"Devi uniformare il prezzo con questa regola: considera che io pago l'IVA sia
su Printful che Printify e che voglio un margine del 20% su ogni prodotto."

Quindi una scala sola per tutto il catalogo:

    prezzo = costo / (1 - 0,20)

dove `costo` e' quello che il negozio paga DAVVERO: prodotto + spedizione +
IVA. La spedizione entra nel costo perche' al cliente e' gratuita -- lo dice
l'informativa sulle spedizioni: "La spedizione e' gratuita, senza minimo
d'ordine. Il costo e' gia' compreso nel prezzo che vedi sul prodotto".

"Margine" e' sul PREZZO DI VENDITA, non ricarico sul costo: (prezzo - costo) /
prezzo. E' la stessa definizione che usa gia' perla-verifica-margini.py, ed e'
quella che risponde alla domanda "di ogni euro incassato, quanto mi resta".
Un ricarico del 20% sul costo darebbe prezzi piu' bassi e margini del 16,7%.

QUESTO FILE PRIMA ERA UN'ALTRA COSA, e vale la pena dirlo. Conteneva una
tabella di quattordici righe scritta a mano il 22 agosto, con una scala di
margini a scaglioni (42% fino a 25$, poi 40, 35, 30) e una spedizione europea
DICHIARATA perche' non si riusciva a leggerla. Adesso i costi si leggono tutti
dal vivo -- ci pensa perla-verifica-margini.py, che questo script importa
invece di ricopiare -- e la scala a scaglioni non c'e' piu': una regola sola.

L'ARROTONDAMENTO VA VERSO L'ALTO
Al primo ,90 sopra il prezzo obiettivo, mai sotto: arrotondando per difetto il
margine scenderebbe sotto il 20% proprio sui prodotti in bilico, che sono
quelli per cui la regola esiste.

USO
    python3 scripts/perla-prezzi-margine.py                 # tabella, non tocca
    python3 scripts/perla-prezzi-margine.py --margine 25    # un'altra asticella
    python3 scripts/perla-prezzi-margine.py --scrivi        # prepara le mutation

--scrivi NON tocca il negozio: prepara l'input di productVariantsBulkUpdate in
generated-designs/prezzi-da-scrivere.json, da rileggere prima di applicarlo.
E' la stessa scelta di perla-editor-allinea.py e perla-eu-foto-shopify.py: in
config/printify.local.env non c'e' un token Admin di Shopify e non ci deve
stare, perche' un token che riscrive i prezzi di tutto il catalogo e' molto
piu' potere di quanto serva a un listino che si rifa' ogni tanto.
"""
import argparse
import collections
import importlib.util
import json
import math
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
USCITA = os.path.join(RADICE, "generated-designs", "prezzi-da-scrivere.json")

MARGINE = 0.20

# L'UNICA ECCEZIONE ALLA REGOLA, DECISA DALLA PROPRIETARIA IL 4 SETTEMBRE
#
# La ciotola europea costa 41,24 (prodotto + spedizione + IVA): col 20% il
# prezzo verrebbe 51,90, e le sembrava alto. Prima ha tolto la 950 ml e messo
# la 530 a 50,90; poi, guardandola in vetrina, l'ha voluta sotto i cinquanta
# "cosi' almeno si vede il 4". Quindi 49,90, cioe' un margine del 17,4%.
#
# 49,90 e non 49,80: ogni prezzo del negozio finisce per ,90 -- e' la
# terminazione su cui e' costruito al_90() qui sotto -- e a 49,80 la ciotola
# sarebbe l'unico prezzo del catalogo fuori passo. Il 4 si vede uguale.
#
# Il prezzo scritto qui VINCE sul calcolo. Senza questa riga il listino
# riproporrebbe 51,90 a ogni giro, e qualcuno prima o poi lo riscriverebbe sul
# negozio pensando di correggere un errore. La deroga corrispondente sta in
# DEROGHE dentro perla-verifica-margini.py, cosi' il controllo la riconosce
# invece di bocciarla.
PREZZO_DECISO = {("ciotola-eu", "530 ml"): 49.90}


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


margini = _modulo("perla_verifica_margini",
                  os.path.join(QUI, "perla-verifica-margini.py"))


def al_90(eur):
    """Il primo prezzo che finisce per ,90 non inferiore a `eur`."""
    return math.ceil(eur - 0.90 - 1e-9) + 0.90


def listino(margine):
    """(righe, senza_costo). Ogni riga porta prezzo di oggi e prezzo nuovo."""
    margini.ambiente()
    tasso, quando = margini.cambio_usd_eur()
    iva_vera = margini.iva_da_un_ordine_printify()
    iva_pf = iva_vera if iva_vera is not None else margini.IVA_PRINTIFY

    costo = dict(margini.costi_printful())
    costo.update(margini.costi_printify(tasso))

    righe, senza = [], []
    for p in margini.chiedi(margini.VETRINA)["products"]:
        t = margini.tipo_di(p)
        for v in p["variants"]:
            c = costo.get((t, v["title"]))
            if c is None and t in margini.PRINTFUL:
                # le taglie EU costano uguale: si accetta un'etichetta qualunque
                candidati = [x for (tt, _), x in costo.items() if tt == t]
                c = max(candidati) if candidati else None
            if c is None:
                senza.append((p["title"], v["title"]))
                continue
            printify = t in margini.PRINTIFY.values()
            c_iva = c * (1 + iva_pf) if printify else c
            prezzo = float(v["price"])
            # Il prezzo deciso a mano vince sulla regola: e' l'unico modo per
            # non riproporre 51,90 sulla ciotola a ogni listino. Vedi DEROGHE e
            # PREZZO_DECISO -- le due tabelle raccontano la stessa decisione,
            # una per il controllo e una per il calcolo.
            deciso = PREZZO_DECISO.get((t, v["title"]))
            nuovo = deciso if deciso is not None else al_90(c_iva / (1 - margine))
            righe.append({
                "prodotto": p["title"], "taglia": v["title"],
                "fornitore": "Printify" if printify else "Printful",
                # productVariantsBulkUpdate vuole il prodotto E la variante:
                # senza l'id del prodotto l'input non si puo' nemmeno scrivere.
                "prodotto_id": p["id"], "variante": v["id"],
                "costo": round(c_iva, 2),
                "prezzo": prezzo, "nuovo": nuovo,
                "margine_ora": round(100 * (prezzo - c_iva) / prezzo, 1),
                "margine_nuovo": round(100 * (nuovo - c_iva) / nuovo, 1)})
    return righe, senza, tasso, quando


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--margine", type=float, default=100 * MARGINE,
                   help="margine sul prezzo di vendita, in percento")
    a.add_argument("--scrivi", action="store_true",
                   help="prepara l'input delle mutation, senza toccare il negozio")
    opz = a.parse_args()
    margine = opz.margine / 100.0

    righe, senza, tasso, quando = listino(margine)
    print("cambio 1 USD = %.4f EUR (%s)" % (tasso, quando))
    print("margine voluto: %.0f%% sul prezzo di vendita\n" % opz.margine)

    # Una riga per FAMIGLIA: le venti bandane con lo stesso costo e lo stesso
    # prezzo sono una decisione sola, e venti righe uguali la nasconderebbero.
    fam = collections.OrderedDict()
    for r in righe:
        chiave = (r["prodotto"].split("“")[0].strip() or r["prodotto"],
                  r["taglia"], r["fornitore"], r["costo"], r["prezzo"], r["nuovo"])
        fam[chiave] = fam.get(chiave, 0) + 1

    print("%-13s %-14s %-9s %8s %8s %8s %8s %6s" % (
        "famiglia", "taglia", "fornitore", "costo", "ora", "nuovo", "delta", "quante"))
    print("-" * 88)
    for (nome, taglia, forn, costo, prezzo, nuovo), quante in sorted(fam.items()):
        print("%-13s %-14s %-9s %8.2f %8.2f %8.2f %+8.2f %6d" % (
            nome[:13], taglia[:14], forn, costo, prezzo, nuovo, nuovo - prezzo, quante))

    giu = sum(1 for r in righe if r["nuovo"] < r["prezzo"] - 0.005)
    su = sum(1 for r in righe if r["nuovo"] > r["prezzo"] + 0.005)
    print("\n%d varianti: %d scendono, %d salgono, %d restano uguali"
          % (len(righe), giu, su, len(righe) - giu - su))
    peggiore = min(righe, key=lambda r: r["margine_nuovo"])
    print("margine piu' basso dopo: %.1f%% (%s %s)"
          % (peggiore["margine_nuovo"], peggiore["prodotto"], peggiore["taglia"]))
    if senza:
        print("Senza costo noto (%d): %s" % (len(senza), ", ".join(
            "%s %s" % s for s in senza[:5])))

    if opz.scrivi:
        da_fare = [r for r in righe if abs(r["nuovo"] - r["prezzo"]) > 0.005]
        per_prodotto = collections.defaultdict(list)
        for r in da_fare:
            per_prodotto[r["prodotto"]].append(r)
        os.makedirs(os.path.dirname(USCITA), exist_ok=True)
        with open(USCITA, "w") as fh:
            json.dump(da_fare, fh, indent=1, ensure_ascii=False)
        print("\n%d varianti da cambiare su %d prodotti, in %s"
              % (len(da_fare), len(per_prodotto), os.path.relpath(USCITA, RADICE)))
        print("Si applicano con productVariantsBulkUpdate, un prodotto per volta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
