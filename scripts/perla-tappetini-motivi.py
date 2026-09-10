#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I file di stampa del tappetino: la piastrella vera, stesa alla misura vera.

PERCHE' NON BASTAVA QUELLO CHE C'ERA
perla-file-stampa-motivi.py sa gia' fare file per il tappetino, ma per
RITAGLIO: prende l'originale piu' grande e ne taglia un rettangolo del
rapporto giusto. Su un pezzo grande come questo il conto non torna -- lanciato
sui sette motivi del nucleo ne ha promossi due e bocciati cinque con
"SCARSO, non caricare", perche' un motivo nato per un collare alto 2,5 cm non
ha abbastanza pixel per riempire 48 centimetri di tappetino.

E disegnare i motivi a codice non e' la risposta: era gia' stato provato su
tutto il catalogo, e il giudizio della titolare -- "davvero brutti, fatti a
cavolo" -- e' scritto in testa a perla-piastrelle-originali.py. Quella strada
resta chiusa.

LA STRADA E' LA TERZA, ED ESISTE GIA'
Se un motivo si ripete, esiste il suo PERIODO: un rettangolo che contiene
tutto il disegno e si affianca senza giunzioni. Ritagliato quello una volta,
lo si porta alla misura fisica voluta e si riempie qualunque area di stampa,
a qualunque misura, senza mai ingrandire niente. E' esattamente cio' che
perla-rifai-motivi.py fa gia' per bandane, cucce e ciotole; qui si applica al
tappetino, e non c'e' una riga di logica nuova -- solo la scelta dei motivi e
il passo.

IL PASSO E' QUELLO DELLA BANDANA, DI PROPOSITO
13 cm. Il tappetino e' l'altro pezzo grande e piatto del catalogo, e chi
compra bandana e tappetino insieme deve vedere lo stesso disegno alla stessa
grana. La conversione in pixel la fa perla-scala-stampa.py, che per il
tappetino ha due voci diverse: le due misure hanno rapporti diversi (1,31 e
1,60), quindi ogni motivo esce in DUE file e non in uno ingrandito.

USO
    python3 scripts/perla-tappetini-motivi.py            # scrive i file
    python3 scripts/perla-tappetini-motivi.py --provino  # + un foglio da guardare
"""
import argparse
import importlib.util
import os
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ORIGINALI = os.path.join(RADICE, "generated-designs", "motivi-stampa", "_originali")
USCITA = os.path.join(RADICE, "generated-designs", "tappetini")

# Il passo della bandana: vedi la docstring.
PASSO_CM = 13.0

# Le due misure del blueprint 623/10, con la chiave di perla-scala-stampa.py.
MISURE = [("piccolo", "tappetino-piccolo"), ("grande", "tappetino-grande")]

# I motivi, e da quale originale viene ognuno. Sono le famiglie che il negozio
# vende gia' su bandana e ciotola: il tappetino entra in una collezione che
# esiste, non ne apre una a parte. Si parte dagli originali della BANDANA
# perche' sono gli unici quadrati e a piena risoluzione (4125x4125): su un
# pezzo largo 48 cm una piastrella ricavata da un nastro alto 2,5 cm sarebbe
# di nuovo il difetto da cui si e' partiti.
#
# I sei sono scelti guardando il foglio di contatto degli originali, non
# leggendo i nomi dei file: "damasco-reale" e' un rametto di salvia su crema e
# "paisley-cammeo" e' un fondo quasi piatto, mentre il damasco vero sta in
# "damasco-diamante". Un tappetino e' grande e sta per terra: se due dei sei
# sono quasi uguali, in vetrina se ne vede uno.
#
# Sei registri diversi, uno per famiglia di colore del catalogo:
MOTIVI = [
    ("Barocco",       "bandana-barocco.jpg"),          # navy e oro
    ("Damasco",       "bandana-damasco-diamante.jpg"),  # ruggine e oro
    ("Medaglioni",    "bandana-medaglioni.jpg"),        # bordeaux e oro
    ("Terracotta",    "bandana-terracotta.jpg"),        # corallo e oro
    ("Tartan",        "bandana-tartan.jpg"),            # verde e oro
    ("Ramo d'Ulivo",  "bandana-ulivo-nuovo.jpg"),       # salvia su crema
]


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tessere = _modulo("perla_piastrelle_originali",
                  os.path.join(QUI, "perla-piastrelle-originali.py"))


def chiave(nome):
    """Il nome del file: 'Ramo d'Ulivo' -> 'ramo-dulivo'."""
    fuori = []
    for c in nome.lower():
        if c.isalnum():
            fuori.append(c)
        elif fuori and fuori[-1] != "-":
            fuori.append("-")
    return "".join(fuori).strip("-")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--provino", action="store_true",
                   help="scrive anche un foglio con tutti i motivi affiancati")
    a.add_argument("--passo", type=float, default=PASSO_CM)
    opz = a.parse_args()

    os.makedirs(USCITA, exist_ok=True)
    print("%-16s %-9s %-13s %-7s %-11s %s"
          % ("motivo", "misura", "area", "scala", "ripetizioni", "giunzione"))
    print("-" * 74)

    provini, esito = [], 0
    for nome, sorgente in MOTIVI:
        percorso = os.path.join(ORIGINALI, sorgente)
        if not os.path.exists(percorso):
            print("%-16s MANCA l'originale %s" % (nome, sorgente))
            esito = 1
            continue
        t, info = tessere.piastrella(percorso)
        for etichetta, tipo in MISURE:
            im, det = tessere.stendi(t, tipo, opz.passo)
            fuori = os.path.join(USCITA, "tappetino-%s-%s.jpg" % (etichetta, chiave(nome)))
            im.save(fuori, quality=94)
            print("%-16s %-9s %-13s %-7.3f %-11.1f %s"
                  % (nome, etichetta, "%dx%d" % im.size, det["scala"],
                     det["ripetizioni"], "sfumata" if info["cucita"] else "esatta"))
            # La regola che non si discute: mai ingrandire. Se la scala
            # superasse 1 vorrebbe dire stirare l'originale, ed e' il difetto
            # che ha impastato la linea americana.
            if det["scala"] > 1.0 + 1e-6:
                print("   ! scala oltre 1: l'originale verrebbe ingrandito")
                esito = 1
            if etichetta == "piccolo":
                provini.append((nome, im))
    if opz.provino and provini:
        lato = 460
        foglio = Image.new("RGB", (lato * 3, lato * ((len(provini) + 2) // 3)), "white")
        for i, (_, im) in enumerate(provini):
            piccola = im.copy()
            piccola.thumbnail((lato, lato))
            foglio.paste(piccola, ((i % 3) * lato, (i // 3) * lato))
        dove = os.path.join(USCITA, "_provino.jpg")
        foglio.save(dove, quality=88)
        print("\nprovino: %s" % os.path.relpath(dove, RADICE))
    return esito


if __name__ == "__main__":
    sys.exit(main())
