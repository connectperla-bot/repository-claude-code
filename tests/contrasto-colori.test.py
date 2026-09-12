#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I colori del tema si leggono? Il contrasto, calcolato, non guardato.

IL GUASTO CHE QUESTA PROVA CERCA
Un colore sbagliato non rompe niente. La pagina si carica, il testo c'e', il
sito sembra a posto -- e una parte dei clienti semplicemente non legge quella
riga. Non lo segnala nessuno: chi non riesce a leggere se ne va.

COSA E' STATO TROVATO IL 12 SETTEMBRE
L'impostazione color_gold_deep si chiamava "Champagne Alloy (hover)" e valeva
#B9986A. Ma base.css non la usa per gli hover: la usa come COLORE DEL TESTO in
una cinquantina di regole -- .eyebrow, .product__vendor, .price__sale,
.stat__label, .brand__sub, .trust-item__icon, .card__rating, .stars,
.cart-line__hallmark, .variant-group__label .value e altre. Misurato:

    #B9986A su crema #F3E9DA        2,25:1     ne servono 4,5
    #B9986A su fondo #FCFAF6        2,60:1     ne servono 4,5
    bianco su #B9986A (bottone oro
      in hover, .btn--gold:hover)   2,71:1     ne servono 4,5

Meno della meta' del minimo, sul testo piccolo di tutto il sito. Nessun
controllo lo vedeva perche' nessun controllo guardava i colori.

PERCHE' NON BASTA "sembra leggibile"
Il contrasto non si giudica a occhio: dipende dalla luminanza relativa, che
non e' la luminosita' percepita. #B9986A e #8F601F sembrano due ori simili e
stanno uno a 2,25 e l'altro a 4,53. Per questo qui si calcola.

LE COPPIE SONO QUELLE VERE
Non tutte le combinazioni possibili -- solo quelle che il tema mette davvero
una sopra l'altra, lette dai fogli di stile. Una prova che segnala coppie
inesistenti si impara a ignorare.

Uso:  python3 tests/contrasto-colori.test.py
"""
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
SCHEMA = os.path.join(RADICE, "theme", "config", "settings_schema.json")

# WCAG 2.1: 4,5:1 per il testo normale, 3:1 per il testo grande (>=24px, o
# >=18,66px in grassetto) e per gli elementi grafici che portano significato.
NORMALE, GRANDE = 4.5, 3.0

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
    return re.sub(r"^\s*/\*.*?\*/\s*", "", testo, flags=re.S)


def colori():
    """id -> #RRGGBB, dai default dello schema del tema."""
    dati = json.loads(senza_commento(open(SCHEMA, encoding="utf-8").read()))
    fuori = {}

    def scava(nodo):
        if isinstance(nodo, list):
            for x in nodo:
                scava(x)
        elif isinstance(nodo, dict):
            if nodo.get("type") == "color" and nodo.get("id") and nodo.get("default"):
                fuori[nodo["id"]] = nodo["default"]
            for v in nodo.values():
                scava(v)
    scava(dati)
    return fuori


def rgb(esa):
    esa = esa.lstrip("#")
    if len(esa) == 3:
        esa = "".join(c * 2 for c in esa)
    return tuple(int(esa[i:i + 2], 16) for i in (0, 2, 4))


def luminanza(c):
    def canale(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * canale(r) + 0.7152 * canale(g) + 0.0722 * canale(b)


def contrasto(a, b):
    la, lb = luminanza(rgb(a)), luminanza(rgb(b))
    alto, basso = max(la, lb), min(la, lb)
    return (alto + 0.05) / (basso + 0.05)


C = colori()
BIANCO = "#FFFFFF"

# (davanti, dietro, soglia, dove sta nel tema)
COPPIE = [
    (C["color_gold_deep"], C["color_cream"], NORMALE,
     ".eyebrow, .stat__label e le altre: testo piccolo sulle sezioni crema"),
    (C["color_gold_deep"], C["color_bg"], NORMALE,
     ".product__vendor, .price__sale, .card__rating: testo sul fondo pagina"),
    (C["color_gold_deep"], BIANCO, NORMALE,
     ".cart-line__hallmark e le schede bianche"),
    (BIANCO, C["color_gold_deep"], NORMALE,
     ".btn--gold:hover e .card__add.is-added: scritta bianca sul bottone oro"),
    (C["color_ink"], C["color_gold"], NORMALE,
     ".btn--gold e .badge--sale: scritta inchiostro sull'oro brillante"),
    (C["color_gold"], C["color_footer_bg"], NORMALE,
     ".footer a:hover e .footer__name span: oro sul piede navy"),
    (C["color_gold"], C["color_ink"], NORMALE,
     ".lang-switch--menu: oro nel menu del telefono, su inchiostro"),
    (C["color_text"], C["color_bg"], NORMALE, "il testo corrente della pagina"),
    (C["color_text"], C["color_cream"], NORMALE, "il testo sulle sezioni crema"),
    (C["color_footer_text"], C["color_footer_bg"], NORMALE, "il testo del piede"),
    (C["color_ink"], C["color_bg"], NORMALE, "i titoli"),
]

print("\nIl contrasto dei colori del tema")


def ci_sono_tutti():
    attesi = ["color_ink", "color_text", "color_bg", "color_cream", "color_gold",
              "color_gold_deep", "color_line", "color_footer_bg", "color_footer_text"]
    mancanti = [a for a in attesi if a not in C]
    assert not mancanti, (
        "questi colori non stanno piu' nello schema del tema: %s. La prova "
        "leggerebbe una tavolozza incompleta e passerebbe senza guardare "
        "niente." % ", ".join(mancanti))


prova("lo schema del tema dichiara tutti i colori attesi", ci_sono_tutti)


def leggibili():
    rotte = []
    for davanti, dietro, soglia, dove in COPPIE:
        c = contrasto(davanti, dietro)
        if c < soglia - 0.005:
            rotte.append("%s su %s = %.2f:1 (ne servono %.1f) — %s"
                         % (davanti, dietro, c, soglia, dove))
    assert not rotte, (
        "queste combinazioni non si leggono:\n        " + "\n        ".join(rotte))


prova("ogni coppia che il tema usa davvero sta sopra la soglia", leggibili)


def oro_profondo_e_profondo():
    """Nominata a parte perche' e' quella che si e' gia' rotta una volta.

    Il nome dell'impostazione ("Champagne Alloy") invita a schiarirla, e chi
    la schiarisce non ha modo di sapere che sta scurendo il testo di mezzo
    sito. Qui sotto il numero e' scritto: sopra 4,5 sul crema, che e' il fondo
    piu' chiaro su cui quel colore finisce.
    """
    c = contrasto(C["color_gold_deep"], C["color_cream"])
    assert c >= 4.5 - 0.005, (
        "color_gold_deep e' %s e sul crema fa %.2f:1. Non e' un accento: e' il "
        "colore del testo in una cinquantina di regole di base.css, e sotto "
        "4,5:1 quel testo diventa illeggibile per chi non ha la vista di un "
        "ventenne. Il piu' chiaro che passa, in questa tinta, e' #8F601F."
        % (C["color_gold_deep"], c))


prova("l'oro profondo e' abbastanza profondo da farci leggere sopra",
      oro_profondo_e_profondo)


def il_calcolo_e_giusto():
    """Una prova che calcola male passerebbe sempre. Due valori noti."""
    assert abs(contrasto("#000000", "#FFFFFF") - 21.0) < 0.01, "nero su bianco deve fare 21:1"
    assert abs(contrasto("#777777", "#FFFFFF") - 4.48) < 0.02, "#777 su bianco deve fare 4,48:1"


prova("il calcolo del contrasto da' i valori noti", il_calcolo_e_giusto)

print("\n  %d verifiche\n" % fatte)
