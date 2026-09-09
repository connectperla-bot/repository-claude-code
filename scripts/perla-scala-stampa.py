#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quanti pixel vale un centimetro, su ogni prodotto del catalogo.

PERCHE' ESISTE
E' il pezzo che mancava, e da cui nasce meta' dei difetti visibili sul negozio.

Le aree di stampa sono dichiarate in due posti diversi -- `AREE` in
perla-eu-print-files.py per la linea europea, `AREE` in perla-usa-file-stampa.py
per quella americana -- ma solo in PIXEL. Un motivo pero' non si guarda in
pixel: si guarda in centimetri, perche' e' li' che finisce, cucito su un
oggetto che il cliente tiene in mano.

Cosa succede senza questa tabella, misurato sui mockup del 23 agosto:

    il medaglione disegnato per la bandana ha un passo di ~500 px.
    Sulla bandana (4125 px di lato) sono 8 ripetizioni: giusto.
    Sul collare (315 px di altezza) e' mezza ripetizione: si vede una fetta
    di due medaglioni tagliati, non un motivo.

Lo stesso numero, 500, e' corretto su un prodotto e assurdo sull'altro. Il
numero giusto da tenere fermo non e' il passo in pixel: e' il passo in
CENTIMETRI. Questa tabella e' la conversione, dichiarata una volta sola.

DA DOVE VENGONO I CENTIMETRI
Dove ho una misura dichiarata dal fornitore o gia' scritta nel repository, la
uso e lo dico. Dove non ce l'ho -- l'endpoint printfiles di Printful vuole la
chiave, e i file in printful-catalog/ contengono solo le varianti -- la ricavo
dalla misura fisica del prodotto che vendiamo, che sta nelle tabelle taglie
del tema (theme/assets/perla-taglia.js). Ogni voce porta scritto da dove
arriva: chi rilegge non deve indovinare quali numeri sono solidi.

LA REGOLA CHE CONTA DAVVERO
`passo_px` converte centimetri in pixel ed e' la funzione che si usa quasi
sempre. Ma sui pezzi molto stretti -- il guinzaglio e' alto 219 px, il collare
315 -- un passo "giusto in centimetri" puo' comunque non entrare nel lato
corto. Per questo c'e' `passo_sicuro`, che accetta il passo desiderato e lo
riduce quel tanto che basta perche' il lato corto ne contenga almeno
RIPETIZIONI_MINIME intere. E' la protezione contro l'unico difetto che sul
prodotto finito non si puo' piu' correggere: il motivo tagliato.

USO
    from perla_scala_stampa import AREE, passo_px, passo_sicuro
    a = AREE["collare-eu"]
    p = passo_sicuro("collare-eu", passo_px("collare-eu", 2.6))
"""
from collections import namedtuple

# Sotto questa soglia il motivo non si legge piu' come motivo: sul lato corto
# se ne vede una fetta invece di una ripetizione, ed e' esattamente il difetto
# segnalato su collare "Medaglioni", ciotola "Medaglioni" e guinzaglio
# "Medaglioni". Due ripetizioni intere sono il minimo perche' l'occhio capisca
# che quello e' un disegno che si ripete e non una macchia tagliata.
RIPETIZIONI_MINIME = 2.0

# larghezza/altezza in pixel dell'area di stampa, larghezza/altezza in cm del
# pezzo stampato, e da dove viene la misura in centimetri.
Area = namedtuple("Area", "px_w px_h cm_w cm_h fonte")

AREE = {
    # --- linea europea (Printful) -----------------------------------------
    # I pixel vengono da AREE in perla-eu-print-files.py, dove erano stati
    # ricavati dagli asset nativi del tema.
    "bandana-eu": Area(
        4125, 4125, 53.0, 53.0,
        "lato dichiarato nella docstring di perla-motivi-nuovi.py (~53 cm)"),
    "collare-eu": Area(
        7169, 315, 56.9, 2.5,
        "altezza 2,5 cm dichiarata in perla-motivi-nuovi.py; la lunghezza "
        "segue dai px alla stessa densita'"),
    # La ciotola si stampa come una fascia che avvolge il cilindro: la
    # larghezza dell'area e' la CIRCONFERENZA, non il diametro. Alla densita'
    # del collare (126 px/cm) i 6496 px fanno 51,6 cm di giro, cioe' una
    # ciotola di ~16,4 cm di diametro: coerente con i formati 530/950 ml che
    # vendiamo (theme/assets/perla-taglia.js).
    "ciotola-eu": Area(
        6496, 803, 51.6, 6.4,
        "circonferenza dedotta dalla densita' del collare, coerente con i "
        "530/950 ml della tabella taglie"),
    # Nastro da 1,5 m, la misura standard del guinzaglio Printful. I 219 px
    # di altezza fanno allora 2,2 cm di larghezza: piu' stretto del collare,
    # ed e' il pezzo su cui i motivi grandi falliscono per primi.
    "guinzaglio-eu": Area(
        12389, 219, 152.0, 2.7,
        "lunghezza 1,52 m (standard Printful); la larghezza segue dai px"),

    # --- linea americana (Printify) ---------------------------------------
    # I pixel vengono da AREE in perla-usa-file-stampa.py: sempre la variante
    # piu' grande del blueprint.
    # 50" x 40" = 127 x 101,6 cm, la cuccia grande (tabella taglie del tema).
    "cuccia-usa": Area(
        15600, 12600, 127.0, 101.6,
        'variante 50" x 40" del blueprint 419'),
    # 27" x 13" = 68,6 x 33 cm, la bandana grande.
    "bandana-usa": Area(
        4275, 2325, 68.6, 33.0,
        'variante 27" x 13", dalla tabella taglie del tema'),
    "collare-usa": Area(
        9519, 338, 75.6, 2.7,
        "densita' della bandana americana applicata ai px dell'area"),
    "ciotola-usa": Area(
        2760, 750, 51.6, 14.0,
        "stessa circonferenza della ciotola europea"),
    # La medaglietta e' un tondo da 2 pollici: 5,08 cm.
    "medaglietta-usa": Area(
        810, 900, 5.08, 5.64,
        'tondo da 2" del blueprint; l\'altezza include il ponticello'),
}


def px_per_cm(tipo):
    """Quanti pixel vale un centimetro su questo prodotto.

    Si misura sul lato CORTO. Sul lato lungo il rapporto e' quasi sempre lo
    stesso, ma quando differisce e' perche' il pezzo viene arrotolato o
    cucito, e in quel caso il lato corto e' quello che si vede disteso.
    """
    a = AREE[tipo]
    return a.px_h / a.cm_h


def passo_px(tipo, passo_cm):
    """Da centimetri a pixel. E' la conversione che oggi manca ovunque."""
    return max(2.0, passo_cm * px_per_cm(tipo))


def ripetizioni(tipo, passo):
    """Quante ripetizioni intere entrano nel lato corto dell'area."""
    return AREE[tipo].px_h / float(passo)


def passo_intero(dimensione, passo):
    """Il passo piu' vicino a quello chiesto che divide la tela un numero
    INTERO di volte.

    PERCHE' SERVE, e non e' pignoleria.
    `_piastrella` disegna anche le celle oltre il bordo, quindi dentro
    l'immagine non c'e' mai una giunzione. Ma se il passo non divide la tela,
    il bordo cade a meta' cella: il motivo finisce tagliato a sinistra in un
    punto e a destra in un altro, ed e' esattamente l'effetto "decentrato"
    segnalato sul negozio -- motivi interi da una parte e mozzi dall'altra.
    Con un passo che divide, il bordo cade FRA due celle: i motivi restano
    interi e i margini sono uguali ai due lati.

    In piu' rende la piastrella richiudibile: il bordo destro continua nel
    sinistro. Non serve al file di stampa, che si usa una volta sola, ma e' la
    proprieta' che una prova automatica sa misurare, e cosi' la cucitura non
    puo' rientrare di nascosto.
    """
    n = max(1, int(round(dimensione / float(passo))))
    return dimensione / float(n)


def passo_sicuro(tipo, passo, minime=RIPETIZIONI_MINIME):
    """Il passo desiderato, ridotto quanto basta perche' il motivo non esca
    tagliato dal lato corto.

    Torna il passo invariato quando gia' ci sta: la riduzione scatta solo sui
    pezzi stretti, che sono poi gli unici dove il difetto si vede.
    """
    massimo = AREE[tipo].px_h / float(minime)
    return min(float(passo), massimo)


def tabella():
    """Le righe da stampare, per controllare i numeri a colpo d'occhio."""
    righe = []
    for tipo in sorted(AREE):
        a = AREE[tipo]
        righe.append((tipo, a.px_w, a.px_h, a.cm_w, a.cm_h, px_per_cm(tipo), a.fonte))
    return righe


if __name__ == "__main__":
    print("%-16s %13s %14s %9s  %s" % ("prodotto", "pixel", "cm", "px/cm", "fonte dei cm"))
    for tipo, pw, ph, cw, ch, d, fonte in tabella():
        print("%-16s %6d x %-6d %5.1f x %-5.1f %8.1f  %s"
              % (tipo, pw, ph, cw, ch, d, fonte))
    print()
    print("Un motivo con passo 3 cm, in pixel, su ogni prodotto:")
    for tipo in sorted(AREE):
        grezzo = passo_px(tipo, 3.0)
        sicuro = passo_sicuro(tipo, grezzo)
        nota = "" if abs(sicuro - grezzo) < 0.5 else "  <- ridotto: non ci stava"
        print("  %-16s %6.0f px  (%.1f ripetizioni sul lato corto)%s"
              % (tipo, sicuro, ripetizioni(tipo, sicuro), nota))
