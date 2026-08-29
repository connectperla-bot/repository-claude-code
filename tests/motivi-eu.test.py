#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cosa deve reggere in perla-eu-motivi-corretti.py.

I difetti che questi controlli inseguono sono TUTTI arrivati in catalogo o
sono usciti dalla prima versione dello script, e nessuno di loro si vedeva
nei numeri che c'erano prima:

  * il bersaglio della fase a s/2 metteva il motivo a cavallo del bordo e lo
    tagliava a meta' da tutte e due le parti, restando "bilanciato";
  * lo spostamento circolare dell'immagine intera lasciava una riga dritta
    dove il bordo destro andava a toccare il sinistro;
  * la toppa che copre la firma nativa veniva presa a un periodo troppo corto
    e conteneva ancora tre quarti del medaglione;
  * il riquadro da coprire era quello del MODELLO e non quello della firma
    stampata, e restava fuori una falce d'oro.
"""
import os
import sys

from PIL import Image, ImageDraw

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

import marchio                                              # noqa: E402
motivi = __import__("perla-eu-motivi-corretti")             # noqa: E402

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


def a_righe(larghezza, altezza, periodo, fase_, colore=(210, 60, 60),
            fondo=(240, 236, 228), spesso=None):
    """Un motivo finto: barre verticali larghe un decimo del periodo.

    Serve perche' i controlli sulla fase abbiano un motivo di cui si sa GIA'
    dove sta, invece di misurarlo su un nativo vero e credere al risultato.

    LE BARRE VANNO DISEGNATE ANCHE FUORI DAI BORDI. Fermarsi all'ultima che
    ci sta dentro sembra equivalente e non lo e': l'ultima barra cadeva a 808
    px su 1000 e da li' in poi restava fondo, quindi la colonna 999 non
    somigliava a quella un periodo prima e bordo_disegnato() la dichiarava --
    correttamente -- un bordo, rifiutando il ricentraggio. Il controllo aveva
    ragione: era questo motivo finto a non essere una vera carta da parati.
    Una carta da parati continua oltre il taglio, ed e' cosi' che sono fatti i
    nativi veri.
    """
    im = Image.new("RGB", (larghezza, altezza), fondo)
    d = ImageDraw.Draw(im)
    spesso = spesso or max(2, periodo // 10)
    x = fase_ - (fase_ // periodo + 2) * periodo
    while x < larghezza + periodo:
        d.rectangle([x - spesso // 2, 0, x + spesso // 2, altezza], fill=colore)
        x += periodo
    return im


def centri(im, colore=(210, 60, 60)):
    """Le x dove cadono le barre, lette dall'immagine e non dedotte."""
    g = im.convert("RGB")
    w, h = g.size
    riga = list(g.crop((0, h // 2, w, h // 2 + 1)).getdata())
    fuori, dentro = [], []
    for x, p in enumerate(riga + [(255, 255, 255)]):
        if sum(abs(p[i] - colore[i]) for i in range(3)) < 90:
            dentro.append(x)
        elif dentro:
            fuori.append(sum(dentro) / float(len(dentro)))
            dentro = []
    return fuori


# ==========================================================================

def il_periodo_si_ritrova():
    im = a_righe(1200, 60, 137, 40)
    k, _ = motivi.periodo(motivi.profilo(im, 0))
    assert k is not None and abs(k - 137) <= 2, "periodo trovato %r invece di 137" % k


def il_bordo_cade_nel_vuoto():
    """Il bersaglio della fase non deve mettere il motivo SUL bordo.

    E' il difetto di "Cammei Cipria": con il bersaglio a s/2 la ripetizione
    risultava bilanciata e le cartelle restavano tagliate a meta' dai due lati.
    """
    k = 200
    p = motivi.profilo(a_righe(1000, 60, k, 3), 0)
    _, bersaglio, _ = motivi.fase(p, k)
    assert bersaglio >= k * 0.4, (
        "il bersaglio e' a %.0f px su un periodo di %d: cosi' il motivo finisce "
        "sul bordo e viene tagliato" % (bersaglio, k))


def i_due_margini_diventano_uguali():
    k = 200
    storta = a_righe(1000, 60, k, 8)
    prima = centri(storta)
    assert prima[0] < 20, "il finto motivo non parte attaccato al bordo: %r" % prima[:2]
    dopo = centri(motivi.ricentra(storta, []))
    sinistro, destro = dopo[0], 1000 - 1 - dopo[-1]
    assert abs(sinistro - destro) <= 3, (
        "margini %.0f a sinistra e %.0f a destra" % (sinistro, destro))
    assert sinistro > k * 0.35, (
        "margine di %.0f px su un periodo di %d: il motivo resta sul bordo"
        % (sinistro, k))


def ricentrare_non_inventa_pixel():
    """Stessa misura in uscita, e nessun colore nuovo.

    Lo spostamento e l'affiancamento riusano pixel che c'erano gia': se in
    uscita comparisse un colore che nell'originale non c'e', vorrebbe dire che
    qualcosa e' stato sfumato o ridimensionato.
    """
    storta = a_righe(1000, 60, 200, 8)
    dopo = motivi.ricentra(storta, [])
    assert dopo.size == storta.size, "%r invece di %r" % (dopo.size, storta.size)
    prima_colori = {c for _, c in storta.convert("RGB").getcolors(9999)}
    dopo_colori = {c for _, c in dopo.convert("RGB").getcolors(9999)}
    assert dopo_colori <= prima_colori, (
        "colori nuovi in uscita: %r" % sorted(dopo_colori - prima_colori)[:4])


def un_motivo_gia_a_posto_non_si_tocca():
    """Ricentrare per abitudine e' un cambio gratuito su un prodotto in vendita."""
    k = 200
    a_posto = a_righe(1000, 60, k, k // 2)
    note = []
    dopo = motivi.ricentra(a_posto, note)
    assert dopo.tobytes() == a_posto.tobytes(), "e' stato spostato lo stesso"
    assert any("gia' a posto" in n for n in note), note


def le_giunzioni_cadono_a_un_periodo_esatto():
    """La finestra affiancata deve essere larga un numero intero di periodi.

    E' quello che rende invisibile la giunzione: unita a un periodo esatto il
    disegno riparte da solo. Nella prima versione l'immagine intera veniva
    spostata in circolo e il bordo destro finiva contro il sinistro, che sono
    a 27 px di fase: si vedeva una riga dritta.
    """
    k = 137
    im = a_righe(1200, 60, k, 5)
    _, finestra = motivi._asse(im, 0, [])
    assert finestra and finestra % k == 0, (
        "finestra di %r px su un periodo di %d: non e' un multiplo intero"
        % (finestra, k))


def un_bordo_disegnato_ferma_il_ricentraggio():
    """Il margine che non si ripete e' un bordo, e spostarlo si vede.

    E' il difetto di bandana-onde-dorate: il filo rosa del margine alto
    finiva a un decimo dell'altezza come una riga dritta in mezzo al nero.
    """
    k = 137
    im = a_righe(1200, 400, k, 5)
    ImageDraw.Draw(im).rectangle([0, 0, 1199, 6], fill=(20, 20, 20))
    note = []
    d, finestra = motivi._asse(im, 1, note)
    assert d == 0 and finestra is None, "ha spostato lo stesso: %r" % note
    assert any("bordo disegnato" in n for n in note), note


def la_fascia_bianca_si_riempie_col_fondo():
    """collare-damasco-verde stampava bianco per due terzi dell'altezza."""
    im = Image.new("RGB", (600, 300), (255, 255, 255))
    im.paste(a_righe(600, 100, 60, 30, colore=(120, 150, 110),
                     fondo=(198, 214, 190)), (0, 100))
    alto, basso = motivi.bande_vuote(im)
    assert alto >= 90 and basso >= 90, "bande trovate: %d sopra, %d sotto" % (alto, basso)
    pieno = motivi.riempi_banda(im, alto, basso, [])
    angolo = pieno.getpixel((5, 5))
    assert sum(angolo) < 700, "l'angolo e' rimasto bianco: %r" % (angolo,)
    fondo = motivi.colore_di_fondo(im.crop((0, 100, 600, 200)))
    assert sum(abs(angolo[i] - fondo[i]) for i in range(3)) < 30, (
        "riempito con %r invece che col fondo del motivo %r" % (angolo, fondo))


def una_banda_del_colore_del_fondo_non_e_un_difetto():
    """guinzaglio-petrolio ha bande piatte, ma sono del colore del motivo."""
    im = Image.new("RGB", (600, 300), (18, 63, 69))
    im.paste(a_righe(600, 100, 60, 30, colore=(40, 90, 96), fondo=(18, 63, 69)), (0, 100))
    alto, basso = motivi.bande_vuote(im)
    assert alto == 0 and basso == 0, (
        "banda dello stesso colore scambiata per area vuota: %d + %d" % (alto, basso))


def la_toppa_scavalca_il_medaglione():
    """La copia da incollare non deve contenere la firma che deve coprire.

    Presa a un periodo qualsiasi non basta: su bandana-paisley-cammeo il
    periodo riconosciuto era 108 px e la firma e' larga oltre mille.
    """
    k = 90
    im = a_righe(2400, 2400, k, 30)
    d = ImageDraw.Draw(im)
    s, a, dd, b = marchio.MEDAGLIONE
    firma = (int(s * 2400), int(a * 2400), int(dd * 2400), int(b * 2400))
    d.ellipse(firma, fill=(255, 215, 0))
    pulita = motivi.togli_marchio(im, (0.78, 0.70, 0.86, 0.88), [])
    dentro = pulita.crop(firma).convert("RGB")
    oro = sum(1 for p in dentro.getdata()
              if p[0] > 200 and p[1] > 170 and p[2] < 90)
    assert oro < 0.01 * dentro.width * dentro.height, (
        "restano %d pixel d'oro della firma vecchia" % oro)


def la_firma_si_riconosce_solo_dove_c_e():
    """Il riconoscimento deve separare i nativi con la firma dagli altri.

    Su un motivo qualunque la correlazione col logo non deve arrivare alla
    soglia: sui diciannove nativi veri gli otto con la firma stanno fra 0,58 e
    0,89 e tutti gli altri sotto 0,51.
    """
    corr, _ = motivi.trova_marchio(a_righe(1200, 1200, 90, 20))
    assert corr < 0.55, "un motivo a righe passa per firmato (%.2f)" % corr


def il_marchio_composto_sta_dentro_la_bandana():
    area = (4125, 4125)
    riquadri = marchio.riquadri("bandana_eu", area, (1360, 2288))
    assert len(riquadri) == 1, "%d riquadri invece di uno" % len(riquadri)
    s, a, largo, alto = riquadri[0]
    # la cartella aggiunge il 14% in larghezza e il 7% in altezza
    assert s - largo * 0.14 > 0.03 * area[0], "la cartella esce a sinistra"
    assert s + largo * 1.14 < 0.97 * area[0], "la cartella esce a destra"
    assert a - alto * 0.07 > 0.03 * area[1], "la cartella esce in alto"
    assert a + alto * 1.07 < 0.97 * area[1], "la cartella esce in basso"


def solo_le_bandane_prendono_un_marchio_nuovo():
    """Collari, ciotole e guinzagli il monogramma ce l'hanno gia' dentro."""
    assert set(motivi.GEOMETRIA_EU) == {"Bandana"}, (
        "aggiungere una geometria per %s significa comporre una cartella crema "
        "sopra un motivo che il monogramma ce l'ha gia': e' il marchio doppio"
        % (set(motivi.GEOMETRIA_EU) - {"Bandana"}))


def gli_otto_nativi_con_la_firma_sono_dichiarati():
    assert len(marchio.NATIVI_CON_MEDAGLIONE) == 8, (
        "sono %d: la lista era ferma a quattro perche' i nativi erano quindici"
        % len(marchio.NATIVI_CON_MEDAGLIONE))
    for n in marchio.NATIVI_CON_MEDAGLIONE:
        assert marchio.serve(n), "%s ha una firma da rifare, quindi serve()" % n


def le_aree_sono_quelle_di_printful():
    for tipo, misura in motivi.AREE.items():
        assert misura[0] > 0 and misura[1] > 0, tipo
    assert motivi.AREE["Bandana"] == (4125, 4125)
    assert motivi.AREE["Guinzaglio"] == (12389, 219)


print("\nLa fase")
prova("il periodo si ritrova", il_periodo_si_ritrova)
prova("il bordo cade nel vuoto fra due motivi", il_bordo_cade_nel_vuoto)
prova("i due margini diventano uguali", i_due_margini_diventano_uguali)
prova("ricentrare non inventa pixel", ricentrare_non_inventa_pixel)
prova("un motivo gia' a posto non si tocca", un_motivo_gia_a_posto_non_si_tocca)
prova("le giunzioni cadono a un periodo esatto", le_giunzioni_cadono_a_un_periodo_esatto)
prova("un bordo disegnato ferma il ricentraggio", un_bordo_disegnato_ferma_il_ricentraggio)

print("\nLa fascia di stampa")
prova("la fascia bianca si riempie col fondo", la_fascia_bianca_si_riempie_col_fondo)
prova("una banda del colore del fondo non e' un difetto",
      una_banda_del_colore_del_fondo_non_e_un_difetto)

print("\nIl marchio")
prova("la toppa scavalca il medaglione", la_toppa_scavalca_il_medaglione)
prova("la firma si riconosce solo dove c'e'", la_firma_si_riconosce_solo_dove_c_e)
prova("il marchio composto sta dentro la bandana", il_marchio_composto_sta_dentro_la_bandana)
prova("solo le bandane prendono un marchio nuovo", solo_le_bandane_prendono_un_marchio_nuovo)
prova("gli otto nativi con la firma sono dichiarati",
      gli_otto_nativi_con_la_firma_sono_dichiarati)
prova("le aree sono quelle di Printful", le_aree_sono_quelle_di_printful)

print("\n%d verifiche superate." % superate)
if fallite:
    print("%d FALLITE" % len(fallite))
    sys.exit(1)
