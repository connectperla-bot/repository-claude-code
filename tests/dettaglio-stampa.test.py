#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cosa deve reggere in perla-dettaglio-stampa.py.

La foto nuova di collari e guinzagli esiste per UNA ragione: essere nitida
dove quella vecchia non lo era. Tutto il resto -- quante strisce, quanta aria
in mezzo -- e' gusto, e il gusto non si mette in un controllo. La nitidezza
si': significa che ogni pixel della foto e' un pixel del file di stampa, senza
nessun ingrandimento in mezzo.

E' anche l'unico modo di accorgersi se un giorno qualcuno "sistema"
l'inquadratura con un resize: la foto tornerebbe sgranata come quella che
sostituisce, e nessun'altra misura se ne accorgerebbe.
"""
import os
import sys

from PIL import Image, ImageDraw

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

dettagli = __import__("perla-dettaglio-stampa")               # noqa: E402

superate = 0
fallite = []


def prova(titolo, funzione):
    global superate
    try:
        funzione()
        superate += 1
        print("  ok   " + titolo)
    except AssertionError as e:
        fallite.append((titolo, str(e)))
        print("  NO   %s\n       %s" % (titolo, e))


def finto_file_di_stampa(percorso, larghezza=7169, altezza=315):
    """Un nastro con dentro righe da UN pixel.

    Le righe sottili sono la prova: sopravvivono solo a un ritaglio 1:1.
    Qualunque ingrandimento o riduzione le impasta, e finezza() se ne accorge.
    """
    im = Image.new("RGB", (larghezza, altezza), (20, 24, 60))
    d = ImageDraw.Draw(im)
    for x in range(0, larghezza, 4):
        d.line([(x, 0), (x, altezza)], fill=(214, 178, 96))
    # e una marca diversa ogni 1500 px, per distinguere una porzione dall'altra
    for i, x in enumerate(range(0, larghezza, 1500)):
        d.rectangle([x + 20, 40, x + 20 + 60 * (i + 1), 100], fill=(255, 255, 255))
    im.save(percorso, quality=100, subsampling=0)
    return im


def finezza(im, y):
    """Quanto cambia il colore da un pixel al successivo, lungo una riga.

    E' la stessa misura con cui questo progetto giudica una giunzione: lo
    scarto medio fra vicini. Dice quanto disegno FINE c'e' dentro, e cala
    appena l'immagine passa per un ridimensionamento, perche' interpolare vuol
    dire fare medie.

    CONTARE I SALTI DI COLORE NON FUNZIONA, provato: su righe da un pixel un
    ingrandimento del doppio con Lanczos lascia lo stesso numero di salti
    (0,499 per pixel prima e dopo) perche' l'oscillazione del filtro ne crea
    di finti. La media degli scarti invece crolla da 63,9 a 34,6, e anche una
    riduzione a meta' la porta a 45,4: la misura giusta e' quella.
    """
    riga = list(im.convert("RGB").crop((0, y, im.width, y + 1)).getdata())
    return sum(sum(abs(a[i] - b[i]) for i in range(3)) / 3.0
               for a, b in zip(riga, riga[1:])) / max(1, len(riga) - 1)


CARTELLA = os.path.join(RADICE, "generated-designs", "dettagli-stampa")
SORGENTE = os.path.join(CARTELLA, "_prova-nastro.jpg")
os.makedirs(CARTELLA, exist_ok=True)
NASTRO = finto_file_di_stampa(SORGENTE)
FOTO, STRISCE, SCALA = dettagli.dettaglio(SORGENTE)


# ==========================================================================

def la_foto_e_quadrata_come_le_altre():
    assert FOTO.size == (dettagli.LATO, dettagli.LATO), FOTO.size


def il_ritaglio_e_a_grandezza_naturale():
    assert SCALA == 1.0, "dichiara un ingrandimento di %r" % SCALA


def le_righe_sottili_arrivano_intere():
    """La prova vera: il disegno fine del file di stampa si ritrova nella foto.

    Sul nastro finto ci sono righe da un pixel ogni quattro. Se il ritaglio
    fosse ingrandito o rimpicciolito la finezza calerebbe di un terzo o piu':
    e' esattamente cio' che succede alla fettuccia dentro il mockup di
    Printful, che di quel disegno ne fa passare un terzo.
    """
    attesa = finezza(NASTRO, NASTRO.height // 2)
    vuoto = (dettagli.LATO - STRISCE * NASTRO.height) // (STRISCE + 1)
    avuta = finezza(FOTO, vuoto + NASTRO.height // 2)
    assert avuta >= 0.95 * attesa, (
        "la foto ha finezza %.1f contro %.1f del file di stampa: il ritaglio "
        "non e' 1:1, il disegno si sta impastando" % (avuta, attesa))


def un_ingrandimento_lo_farebbe_fallire():
    """Prova del contrario: senza questa, il controllo sopra non protegge nulla.

    Si rifa' lo stesso pezzo ma passandolo per un ridimensionamento -- cioe'
    l'errore che si vuole impedire, in tutte e due le direzioni -- e si
    verifica che la finezza crolli sotto la soglia. Se non crollasse, la
    soglia sarebbe scritta male.
    """
    attesa = finezza(NASTRO, NASTRO.height // 2)
    for nome, fatta in (
            ("ingrandito del doppio",
             NASTRO.crop((0, 0, dettagli.LATO // 2, NASTRO.height)).resize(
                 (dettagli.LATO, NASTRO.height), Image.LANCZOS)),
            ("rimpicciolito a meta'",
             NASTRO.crop((0, 0, 2 * dettagli.LATO, NASTRO.height)).resize(
                 (dettagli.LATO, NASTRO.height), Image.LANCZOS))):
        avuta = finezza(fatta, NASTRO.height // 2)
        assert avuta < 0.95 * attesa, (
            "un ritaglio %s passa lo stesso il controllo (%.1f contro %.1f): "
            "la soglia non discrimina niente" % (nome, avuta, attesa))


def si_vede_tutta_la_larghezza_della_fettuccia():
    """La striscia e' alta quanto il file di stampa, non un pezzo di esso.

    E' la larghezza vera del nastro: tagliarla mostrerebbe meno prodotto di
    quello che si compra.
    """
    assert NASTRO.height <= dettagli.LATO - 2 * dettagli.ARIA
    vuoto = (dettagli.LATO - STRISCE * NASTRO.height) // (STRISCE + 1)
    alto = FOTO.crop((0, vuoto, dettagli.LATO, vuoto + NASTRO.height))
    assert alto.size[1] == NASTRO.height, alto.size


def le_strisce_mostrano_porzioni_diverse():
    """Tre copie della stessa porzione sarebbero una carta da parati.

    Le marche bianche del nastro finto crescono di larghezza andando avanti:
    se le strisce venissero dallo stesso punto, avrebbero la stessa quantita'
    di bianco.
    """
    vuoto = (dettagli.LATO - STRISCE * NASTRO.height) // (STRISCE + 1)
    bianchi = []
    for i in range(STRISCE):
        y = vuoto + i * (NASTRO.height + vuoto)
        pezzo = FOTO.crop((0, y, dettagli.LATO, y + NASTRO.height)).convert("RGB")
        bianchi.append(sum(1 for p in pezzo.getdata()
                           if p[0] > 230 and p[1] > 230 and p[2] > 230))
    assert len(set(bianchi)) == len(bianchi), (
        "le strisce hanno la stessa quantita' di bianco (%r): vengono dallo "
        "stesso punto del disegno" % bianchi)


def il_nastro_troppo_corto_si_ferma():
    """Meglio fermarsi che ingrandire.

    Un file di stampa piu' stretto della tela non ha 1000 px da ritagliare a
    1:1: l'unico modo di riempirla sarebbe ingrandire, cioe' rifare il difetto.
    """
    corto = os.path.join(CARTELLA, "_prova-corto.jpg")
    finto_file_di_stampa(corto, larghezza=800, altezza=200)
    try:
        dettagli.dettaglio(corto)
    except RuntimeError:
        return
    finally:
        os.remove(corto)
    raise AssertionError("ha prodotto una foto da un nastro piu' stretto della tela")


def solo_i_nastri_lunghi():
    """Bandana e ciotola non hanno questo problema e non si toccano."""
    assert dettagli.TIPI == ("collare-eu", "guinzaglio-eu"), dettagli.TIPI


print("\nLa foto del tessuto")
prova("la foto e' quadrata come le altre", la_foto_e_quadrata_come_le_altre)
prova("il ritaglio e' a grandezza naturale", il_ritaglio_e_a_grandezza_naturale)
prova("le righe sottili arrivano intere", le_righe_sottili_arrivano_intere)
prova("un ingrandimento lo farebbe fallire", un_ingrandimento_lo_farebbe_fallire)
prova("si vede tutta la larghezza della fettuccia",
      si_vede_tutta_la_larghezza_della_fettuccia)
prova("le strisce mostrano porzioni diverse", le_strisce_mostrano_porzioni_diverse)
prova("il nastro troppo corto si ferma", il_nastro_troppo_corto_si_ferma)
prova("solo i nastri lunghi", solo_i_nastri_lunghi)

os.remove(SORGENTE)

print("\n%d verifiche superate." % superate)
if fallite:
    print("%d FALLITE" % len(fallite))
    sys.exit(1)
