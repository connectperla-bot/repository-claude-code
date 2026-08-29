#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rimette in centro i motivi europei e ci ricompone sopra il marchio.

PERCHE' ESISTE
La titolare ha scritto: "non vedo i cambiamenti dei prodotti nel negozio, ad
esempio la bandana antracite ha ancora il logo trasparente che fa vedere un
puntino nero e la bandana cammei cipria e' decentrata". Aveva ragione due
volte. Tutte le correzioni della tornata precedente sono andate sulla linea
AMERICANA (Printify); la linea EUROPEA (Printful), 66 prodotti, non era mai
stata toccata. E l'audit --eu che era stato aggiunto controlla la MISURA dei
motivi, non cosa c'e' dentro: per questo diceva "66 motivi alla misura giusta"
mentre due prodotti erano sbagliati.

I TRE DIFETTI, GUARDATI E MISURATI
1. IL MARCHIO SEMITRASPARENTE. Otto nativi portano una firma d'angolo che e'
   perla-combined-logo.png incollato male: la scritta "Perla" lascia passare il
   motivo e al centro della perla c'e' un buco che lascia passare il fondo --
   rosso sul terracotta, verde sul tartan, blu sul marinara, quasi nero
   sull'antracite. E' il "puntino nero". Visto a 1:1 su tutti e otto.
2. LA FASE. Diciotto nativi quadrati su diciannove hanno la ripetizione
   sbilanciata: su "Cammei Cipria" (bandana-paisley-rosa) le cartelle
   "PERLA ITALIA" sono intere in alto e a destra e tagliate a sinistra e in
   basso. Non e' il PERIODO a essere sbagliato -- 1366 x 3 = 4098 su 4125, 27
   px di resto -- ma la FASE, cioe' dove cade il primo motivo rispetto al
   bordo. Averle confuse e' l'errore che mi ha fatto scrivere "0 nativi
   asimmetrici" in una misura precedente.
3. LA FASCIA VUOTA. collare-damasco-verde ha il 34% di bianco piatto sopra e
   il 34% sotto: nel mockup e' un collare BIANCO con una striscia salvia in
   mezzo. guinzaglio-petrolio ha bande piatte simili, ma sono del colore del
   fondo -- quello va bene, ed e' il motivo per cui il controllo confronta il
   colore della banda col centro invece di fidarsi della sola uniformita'.

COME SI RICENTRA SENZA INVENTARE PIXEL
Con uno spostamento CIRCOLARE: il motivo si ripete, quindi farlo scorrere non
crea nessun pixel nuovo. Lo scorrimento pero' porta il bordo destro
dell'originale a toccare il sinistro, e li' nasce una cucitura. La domanda
giusta non e' "c'e' una cucitura" ma "si vede piu' di quanto si veda il motivo
stesso": la cucitura vale un salto di fase pari al resto (27 px su un periodo
di 1366, il 2%), e misurata sui nativi veri sta fra 1,00 e 1,28 volte lo
stesso salto preso altrove nell'immagine. Cioe' non si distingue dalla
normale variazione interna del disegno. Il confronto lo fa cucitura(), e se
un nativo non lo passa non viene ricentrato.

DOVE VA IL MARCHIO SULLA BANDANA EUROPEA
Non al centro. Printful stampa un quadrato 44x44 e lo fotografa steso: nel
mockup si vede tutto, orlo compreso. Il centro del quadrato e' anche la piega
diagonale con cui la bandana si annoda, e un marchio li' finirebbe a cavallo
della piega. Resta quindi la firma d'angolo che i motivi hanno gia' addosso,
tirata dentro perche' non tocchi l'orlo: vedi GEOMETRIA["bandana_eu"] in
marchio.py.

QUALI PRODOTTI PRENDONO UN MARCHIO NUOVO, E QUALI NO
Solo le bandane. Collari, ciotole e guinzagli portano tutti gia' addosso il
monogramma PI o la scritta "PERLA ITALIA", ripetuti dentro il motivo e nei
suoi colori -- guardati uno per uno a 1:1. Aggiungerci sopra una cartella
crema sarebbe il "marchio doppio" gia' corretto una volta in 962ade7. Su
quelli si corregge la fase e basta.

USO
    python3 scripts/perla-eu-motivi-corretti.py                  # misura, non tocca
    python3 scripts/perla-eu-motivi-corretti.py --costruisci --tipo bandana
    python3 scripts/perla-eu-motivi-corretti.py --costruisci --motivo Antracite
    python3 scripts/perla-eu-motivi-corretti.py --costruisci --tutti
    python3 scripts/perla-eu-motivi-corretti.py --carica --tutti

--carica scrive su Cloudinary con un public_id NUOVO (<id>-v2) e aggiorna
perla-eu-prodotti.json. Non sovrascrive mai l'originale: riscrivendo lo stesso
public_id la URL versionata gia' in giro continuerebbe a servire la vecchia
immagine, e l'originale sarebbe perso.
"""
import argparse
import hashlib
import math
import json
import os
import re
import sys
import time
import urllib.request

from PIL import Image, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marchio  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
PRODOTTI = os.path.join(QUI, "perla-eu-prodotti.json")
CONFIG = os.path.join(RADICE, "config", "printify.local.env")
NATIVI = os.path.join(RADICE, "generated-designs", "motivi-stampa", "_originali")
USCITA = os.path.join(RADICE, "generated-designs", "eu-motivi-corretti")
MISURE = os.path.join(USCITA, "_misure.json")

# Le aree di stampa Printful, verificate contro i nativi scaricati.
AREE = {
    "Collare": (7169, 315),
    "Bandana": (4125, 4125),
    "Ciotola": (6496, 803),
    "Guinzaglio": (12389, 219),
}

# Il tipo di marchio.GEOMETRIA da usare quando il marchio va composto. Solo la
# bandana: vedi la docstring.
GEOMETRIA_EU = {"Bandana": "bandana_eu"}

# Sopra questa frazione di periodo la ripetizione e' visibilmente storta. Sotto,
# ricentrare sarebbe un cambio gratuito su un prodotto gia' in vendita.
SBILANCIO_MASSIMO = 0.25

# Sopra questo rapporto la linea di margine non si ripete un periodo piu' in
# dentro: e' un bordo disegnato, e la fase su quell'asse non si tocca.
# Misurato: dove la giunzione guardata a 1:1 non si vede il rapporto sta a
# 1,0-1,3; dove si vede sta a 2,2-30.
BORDO_MASSIMO = 2.0
# Piu' un margine assoluto: su un disegno piatto lo scarto fra linee attaccate
# e' zero, e senza margine qualunque differenza, anche di un livello su 255,
# passerebbe per bordo. Sotto due livelli non si vede niente, in nessun caso.
BORDO_TOLLERATO = 2.0

# Sopra questa correlazione col file del logo la firma nativa c'e'. Sui
# diciannove nativi europei gli otto firmati stanno fra 0,58 e 0,89 e tutti
# gli altri sotto 0,51: in mezzo non c'e' niente.
SOGLIA_FIRMA = 0.55

# Il suffisso del motivo corretto su Cloudinary. Non si sovrascrive mai
# l'originale: resta li' come marcia indietro.
SUFFISSO = "-v2"

# Quanto vale "banda piatta" e "banda di un altro colore".
PIATTA = 3.0
BANDA_ESTRANEA = 40.0


# ==========================================================================
# MISURA
# ==========================================================================

def profilo(im, asse):
    """La media dei pixel per colonna (asse 0) o per riga (asse 1).

    Fatta da Pillow con un resize BOX, non con un ciclo Python: su un
    guinzaglio da 12389 px la differenza e' fra un decimo di secondo e un
    minuto.
    """
    g = im.convert("L")
    w, h = g.size
    if asse == 0:
        return list(g.resize((w, 1), Image.BOX).getdata())
    return list(g.resize((1, h), Image.BOX).getdata())


def periodo(p):
    """Ogni quanti pixel il motivo si ripete. Torna (k, scarto) o (None, None).

    Si prende il k con lo scarto minimo. Se anche il minimo e' alto il motivo
    non e' periodico e non c'e' nessuna fase da correggere.
    """
    n = len(p)
    if n < 64:
        return None, None
    kmin, kmax = max(8, n // 40), n // 2
    passo = max(1, (n - kmin) // 400)
    migliore = None
    for k in range(kmin, kmax + 1):
        idx = range(0, n - k, passo)
        s = sum(abs(p[i] - p[i + k]) for i in idx) / max(1, len(list(idx)))
        if migliore is None or s < migliore[1]:
            migliore = (k, s)
    return migliore


def _piegato(p, k):
    """La media di tutte le ripetizioni: un periodo solo, ripulito dal rumore."""
    f = [0.0] * k
    conta = [0] * k
    for i, v in enumerate(p):
        f[i % k] += v
        conta[i % k] += 1
    return [f[i] / conta[i] for i in range(k)]


def fase(p, k):
    """Dove cade il motivo, e di quanto e' sbilanciato fra i due bordi.

    Torna (m, bersaglio, sbilancio). m e' la posizione del motivo dentro il
    primo periodo -- il punto che si stacca di piu' dalla media, che su questi
    disegni e' il centro della cartella o del medaglione.

    DUE BERSAGLI, NON UNO. Con W-1 = q*k + s le fasi che lasciano lo stesso
    margine ai due bordi sono due: s/2 e (s+k)/2. Sembrano equivalenti e non lo
    sono, perche' il motivo si ripete anche FUORI dai bordi: quello che conta
    non e' solo la simmetria ma quanto dista il bordo dal motivo piu' vicino,
    di qua o di la'. Le due fasi danno distanze molto diverse, e quale delle
    due vinca dipende da s:

        bandana   k=1366  s=27    s/2 = 13    il motivo cade sul bordo
                                  (s+k)/2 = 696  il bordo cade nel vuoto
        a righe   k=200   s=199   s/2 = 99    il bordo cade nel vuoto
                                  (s+k)/2 = 199  il motivo cade sul bordo

    Quindi si calcolano tutte e due e si tiene quella che tiene il bordo piu'
    lontano dal motivo. Nella prima versione ne avevo scritta una sola, prima
    s/2 e poi (s+k)/2, e ogni volta funzionava su meta' dei casi: su "Cammei
    Cipria" le cartelle restavano tagliate a meta' da tutti e due i lati.
    """
    f = _piegato(p, k)
    media = sum(f) / len(f)
    # IL CENTRO DEL MOTIVO, NON IL SUO PRIMO PIXEL. Prendere il massimo scarto
    # sbaglia in due modi: su un motivo largo lo scarto e' un altopiano e
    # max() restituisce il primo indice invece del centro, e se l'altopiano
    # scavalca lo zero (il motivo a cavallo del bordo) l'indice cade
    # dall'altra parte. La media circolare, che e' la fase della prima
    # armonica, non ha nessuno dei due problemi: su una barra centrata a 8 px
    # che scavalca lo zero risponde 8, dove max() rispondeva 0.
    peso = [abs(v - media) for v in f]
    sn = sum(w * math.sin(2 * math.pi * i / k) for i, w in enumerate(peso))
    cs = sum(w * math.cos(2 * math.pi * i / k) for i, w in enumerate(peso))
    m = (math.atan2(sn, cs) * k / (2 * math.pi)) % k
    s = (len(p) - 1) % k

    def distanza_dal_bordo(u):
        u = u % k
        return min(u, k - u)

    bersaglio = max((s / 2.0, (s + k) / 2.0 % k), key=distanza_dal_bordo)
    d = abs(m - bersaglio)
    return m, bersaglio, min(d, k - d) / float(k)


def _colonna(im, x):
    w, h = im.size
    return list(im.crop((x, 0, x + 1, h)).getdata())


def _riga(im, y):
    w, h = im.size
    return list(im.crop((0, y, w, y + 1)).getdata())


def _scarto(a, b):
    return sum(abs(p[i] - q[i]) for p, q in zip(a, b) for i in range(3)) / (3.0 * len(a))


def bordo_disegnato(im, asse, k):
    """La linea di bordo si ripete un periodo piu' in dentro, si' o no?

    Torna (peggiore, adiacenti). Se il motivo e' una carta da parati vera, la
    prima colonna e' quasi uguale a quella un periodo dopo, e l'ultima a
    quella un periodo prima. Se invece il disegno ha un BORDO -- una riga
    decorativa lungo il margine, che i motivi di questo catalogo hanno spesso
    -- quel bordo non si ripete da nessuna parte, e si vede subito.

    PERCHE' QUESTO CONTROLLO E NON ALTRI DUE CHE HO PROVATO PRIMA.
    Il bordo e' il vero motivo per cui a volte non si puo' ricentrare: la
    finestra che si fa scorrere parte dal margine, quindi si porta dietro il
    bordo e glielo pianta in mezzo. Su bandana-onde-dorate il filo rosa del
    margine alto e' finito a un decimo dell'altezza, una riga dritta su tutto
    il nero. Guardata a 1:1, non deducibile dai numeri che avevo.

    I due tentativi precedenti misuravano l'effetto e non la causa, e per
    questo non tagliavano dove serviva: lo scarto fra i due bordi opposti, e
    poi lo scarto medio a un periodo di distanza preso in punti a caso. Con
    questo, invece, i due casi limite si separano da soli: su
    bandana-diamanti il bordo vale 1,2 volte lo scarto fra colonne attaccate
    (e la giunzione, guardata, non si vede), su bandana-onde-dorate 4,6 (e si
    vede benissimo).
    """
    rgb = im.convert("RGB")
    w, h = rgb.size
    n = w if asse == 0 else h
    prendi = (lambda i: _colonna(rgb, i)) if asse == 0 else (lambda i: _riga(rgb, i))
    if k >= n - 1:
        return None, None
    primo = _scarto(prendi(0), prendi(k))
    ultimo = _scarto(prendi(n - 1), prendi(n - 1 - k))
    punti = range(n // 10, 9 * n // 10, max(1, (4 * n // 5) // 10))
    adiacenti = sum(_scarto(prendi(x), prendi(x + 1)) for x in punti) / len(punti)
    return max(primo, ultimo), adiacenti


def bande_vuote(im):
    """Le bande piatte in alto e in basso che NON sono del colore del fondo.

    Torna (alto, basso) in pixel. Una banda uniforme del colore del motivo e'
    normale -- guinzaglio-petrolio e' verde petrolio pieno e va benissimo. Una
    banda BIANCA su un motivo salvia e' un'area di stampa non riempita, ed e'
    il difetto di collare-damasco-verde: il collare esce bianco con una riga
    verde in mezzo.
    """
    w, h = im.size
    stretta = im.convert("RGB").resize((min(w, 600), h), Image.BOX)
    dev = [ImageStat.Stat(stretta.crop((0, y, stretta.width, y + 1))).stddev
           for y in range(h)]
    centro = ImageStat.Stat(stretta.crop((0, int(0.45 * h), stretta.width,
                                          int(0.55 * h) + 1))).mean

    def conta(indici):
        n = 0
        for y in indici:
            if max(dev[y]) >= PIATTA:
                break
            riga = ImageStat.Stat(stretta.crop((0, y, stretta.width, y + 1))).mean
            if sum(abs(riga[i] - centro[i]) for i in range(3)) / 3.0 < BANDA_ESTRANEA:
                break
            n += 1
        return n

    return conta(range(h)), conta(range(h - 1, -1, -1))


def trova_marchio(im):
    """Quanto il nativo somiglia a perla-combined-logo.png nell'angolo firma.

    Torna (correlazione, riquadro in frazione). Sopra SOGLIA_FIRMA la firma
    c'e': misurato sui diciannove nativi europei, gli otto che la portano
    stanno fra 0,58 e 0,89 e tutti gli altri sotto 0,51.

    LA GRIGLIA DEVE ESSERE FINE. Alla prima passata cercavo su tre posizioni
    per tre, distanti l'una dall'altra il 3% del lato: il modello e' alto
    48 px su 240, e bastavano due pixel di scarto perche' la correlazione
    crollasse da 0,89 a 0,32. Quattro nativi su otto passavano per non
    firmati, e la loro firma sarebbe rimasta sul prodotto sotto quella nuova.
    """
    logo = Image.open(marchio.MARCHIO)
    logo = logo.crop(logo.getchannel("A").getbbox())
    n = 240
    piccola = im.convert("L").resize((n, n), Image.LANCZOS)
    pixel = list(piccola.getdata())

    migliore = (0.0, None)
    for alto in (0.16, 0.20, 0.24):
        th = max(8, round(alto * n))
        tw = max(6, round(th * logo.width / logo.height))
        t = logo.resize((tw, th), Image.LANCZOS)
        maschera = list(t.getchannel("A").getdata())
        livelli = list(t.convert("L").getdata())
        idx = [i for i, a in enumerate(maschera) if a > 200]
        if len(idx) < 40:
            continue
        T = [livelli[i] for i in idx]
        mt = sum(T) / len(T)
        st = math.sqrt(sum((v - mt) ** 2 for v in T) / len(T)) or 1.0
        for y0 in range(round(0.62 * n), round(0.90 * n) - th, 2):
            for x0 in range(round(0.68 * n), round(0.96 * n) - tw, 2):
                W = [pixel[(y0 + i // tw) * n + x0 + i % tw] for i in idx]
                mw = sum(W) / len(W)
                sw = math.sqrt(sum((v - mw) ** 2 for v in W) / len(W)) or 1.0
                r = sum((W[k] - mw) * (T[k] - mt)
                        for k in range(len(W))) / (len(W) * sw * st)
                if r > migliore[0]:
                    migliore = (r, (x0 / float(n), y0 / float(n),
                                    (x0 + tw) / float(n), (y0 + th) / float(n)))
    return migliore


# ==========================================================================
# CORREZIONE
# ==========================================================================

def sposta(im, dx, dy):
    """Spostamento circolare. Nessun pixel nuovo: solo pixel spostati."""
    w, h = im.size
    dx, dy = dx % w, dy % h
    if not dx and not dy:
        return im
    fuori = Image.new(im.mode, (w, h))
    fuori.paste(im, (dx, dy))
    if dx:
        fuori.paste(im.crop((w - dx, 0, w, h)), (0, dy))
    if dy:
        fuori.paste(im.crop((0, h - dy, w, h)), (dx, 0))
    if dx and dy:
        fuori.paste(im.crop((w - dx, h - dy, w, h)), (0, 0))
    return fuori


def _asse(im, asse, note):
    """(spostamento, larghezza della finestra) per un asse, o (0, None)."""
    nome = "orizzontale" if asse == 0 else "verticale"
    p = profilo(im, asse)
    k, _ = periodo(p)
    if not k:
        return 0, None
    m, bersaglio, sbil = fase(p, k)
    if sbil <= SBILANCIO_MASSIMO:
        note.append("fase %s gia' a posto (%.2f periodi)" % (nome, sbil))
        return 0, None
    q = len(p) // k
    if q < 1:
        return 0, None
    bordo, adiacenti = bordo_disegnato(im, asse, k)
    if bordo is None or bordo > BORDO_MASSIMO * adiacenti + BORDO_TOLLERATO:
        note.append("fase %s storta (%.2f) ma NON toccata: il margine e' un "
                    "bordo disegnato, non parte della ripetizione (%.1f contro "
                    "%.1f fra linee attaccate), e spostarlo lo pianterebbe in "
                    "mezzo al motivo" % (nome, sbil, bordo or 0, adiacenti or 0))
        return 0, None
    d = int(round(bersaglio - m)) % k
    note.append("fase %s ricentrata: +%d px dentro una finestra di %d periodi "
                "da %d px (sbilancio %.2f, bordo %.1f contro %.1f fra linee "
                "attaccate)" % (nome, d, q, k, sbil, bordo, adiacenti))
    return d, q * k


def ricentra(im, note):
    """Porta la ripetizione a margini uguali, senza lasciare una cucitura.

    NON si sposta l'immagine intera in circolo. Farlo porterebbe il bordo
    destro a toccare il sinistro, e quei due bordi non combaciano: sono a
    27 px di fase l'uno dall'altro e il salto si vede come una riga dritta.

    Si prende invece una FINESTRA larga un numero intero di periodi -- che
    quindi combacia con se' stessa -- la si fa scorrere in circolo li' dentro,
    e la si affianca fino a coprire l'area. Tutte le giunzioni cadono cosi' a
    un periodo esatto, dove il disegno riparte da solo. Misurato: costano meno
    di due colonne attaccate.

    E' lo stesso ragionamento di _fascia_orizzontale() in
    perla-build-eu-print-files.py, portato anche sulla fase.
    """
    w, h = im.size
    quadrato = abs(w - h) < 2
    dx, fx = _asse(im, 0, note)
    # Su collare, ciotola e guinzaglio il verticale non e' una ripetizione: e'
    # il disegno della fascia, coi suoi bordi. Farlo scorrere spezzerebbe la
    # fascia in due.
    dy, fy = _asse(im, 1, note) if quadrato else (0, None)
    if not dx and not dy:
        return im

    fx = fx or w
    fy = fy or h
    finestra = sposta(im.crop((0, 0, fx, fy)), dx, dy)
    fuori = Image.new(im.mode, (w, h))
    for y in range(0, h, fy):
        for x in range(0, w, fx):
            fuori.paste(finestra, (x, y))
    return fuori


def togli_marchio(im, riquadro, note):
    """Copre la firma d'angolo con un pezzo di motivo preso a un periodo esatto.

    Un periodo esatto vuol dire che il pezzo incollato e' lo STESSO disegno,
    nella stessa fase: non e' una toppa inventata ne' un ricalco sfocato. Il
    bordo della toppa viene sfumato per assorbire il piccolo scarto che resta.
    """
    w, h = im.size
    # L'UNIONE, non il riquadro del riconoscimento. trova_marchio() restituisce
    # il riquadro del MODELLO, che e' il logo e basta: la firma stampata nel
    # nativo e' piu' larga, e coprendo solo il modello resta fuori una falce
    # d'oro sul lato destro -- vista sulla prima "Antracite" costruita.
    # marchio.MEDAGLIONE e' l'estensione vera, misurata sul nativo dal fondo
    # piu' pulito; si prende il rettangolo che contiene tutti e due.
    s = min(riquadro[0], marchio.MEDAGLIONE[0])
    a = min(riquadro[1], marchio.MEDAGLIONE[1])
    d = max(riquadro[2], marchio.MEDAGLIONE[2])
    b = max(riquadro[3], marchio.MEDAGLIONE[3])
    box = (max(0, int(s * w) - 12), max(0, int(a * h) - 12),
           min(w, int(d * w) + 12), min(h, int(b * h) + 12))
    k, _ = periodo(profilo(im, 0))
    if not k:
        note.append("marchio nativo NON tolto: motivo senza periodo riconoscibile")
        return im

    # IL SALTO DEVE SCAVALCARE IL MARCHIO, non solo essere un periodo. Su
    # bandana-paisley-cammeo il periodo riconosciuto e' 108 px -- la trama
    # fine, non la cartella -- e una toppa presa a 108 px conterrebbe ancora
    # tre quarti del medaglione, che e' largo 1030. Si sale di multipli finche'
    # la finestra di partenza non tocca piu' quella da coprire.
    larghezza = box[2] - box[0]
    salti = []
    for n in range(1, 40):
        if n * k >= larghezza:
            salti += [-n * k, n * k]
    for salto in salti:
        sx, dx = box[0] + salto, box[2] + salto
        if sx >= 0 and dx <= w:
            break
    else:
        note.append("marchio nativo NON tolto: nessuna copia del motivo a un "
                    "periodo di distanza dentro l'immagine")
        return im

    toppa = im.crop((sx, box[1], dx, box[3]))
    sfuma = 24
    maschera = Image.new("L", toppa.size, 255)
    for i in range(sfuma):
        v = round(255 * (i + 1) / float(sfuma + 1))
        maschera.paste(v, (i, 0, i + 1, toppa.size[1]))
        maschera.paste(v, (toppa.size[0] - i - 1, 0, toppa.size[0] - i, toppa.size[1]))
        maschera.paste(v, (0, i, toppa.size[0], i + 1))
        maschera.paste(v, (0, toppa.size[1] - i - 1, toppa.size[0], toppa.size[1] - i))
    fuori = im.copy()
    fuori.paste(toppa, (box[0], box[1]), maschera)
    note.append("marchio nativo tolto e coperto col motivo a %+d px (un periodo)"
                % salto)
    return fuori


def colore_di_fondo(im):
    """Il colore piu' frequente, non la media.

    La media di una fascia decorata tira verso il grigio: sul damasco verde
    salvia il fondo vero e' un verde chiaro, e la media della fascia coi
    ghirigori crema sopra dava un grigio-verde spento che accanto alla fascia
    si vedeva. Il colore piu' frequente e' invece il fondo su cui il motivo e'
    disegnato, che e' quello che serve.
    """
    piccola = im.convert("RGB").resize((240, max(1, im.height * 240 // im.width)),
                                       Image.BOX)
    conta = {}
    for p in piccola.getdata():
        chiave = (p[0] // 8, p[1] // 8, p[2] // 8)
        voce = conta.setdefault(chiave, [0, 0, 0, 0])
        voce[0] += 1
        for i in range(3):
            voce[i + 1] += p[i]
    n, r, g, b = max(conta.values(), key=lambda v: v[0])
    return (r // n, g // n, b // n)


def riempi_banda(im, alto, basso, note):
    """Estende il fondo del motivo sulle bande di stampa rimaste bianche.

    Non si ingrandisce la fascia -- da 107 px a 315 sarebbe tre volte, cioe'
    sgranata -- e non si impila, perche' la fascia ha i suoi bordi crema e
    impilarla darebbe un collare a righe che nessuno ha disegnato. Si allunga
    il colore di fondo che sta gia' li' dentro, che e' l'unica cosa che non
    inventa niente.
    """
    w, h = im.size
    fuori = im.copy()
    fondo = colore_di_fondo(im.crop((0, alto, w, h - basso)))
    if alto:
        fuori.paste(fondo, (0, 0, w, alto))
    if basso:
        fuori.paste(fondo, (0, h - basso, w, h))
    note.append("bande di stampa bianche riempite col fondo del motivo "
                "(%d px sopra, %d px sotto)" % (alto, basso))
    return fuori


def costruisci(percorso, tipo):
    """Il motivo corretto, e l'elenco di cosa gli e' stato fatto."""
    note = []
    im = Image.open(percorso).convert("RGB")
    attesa = AREE[tipo]
    if im.size != attesa:
        note.append("ATTENZIONE: %dx%d invece di %dx%d" % (im.size + attesa))

    alto, basso = bande_vuote(im)
    if alto + basso > 0.02 * im.height:
        im = riempi_banda(im, alto, basso, note)

    base = os.path.basename(percorso)
    if base in marchio.NATIVI_CON_MEDAGLIONE:
        corr, riquadro = trova_marchio(im)
        if riquadro and corr >= SOGLIA_FIRMA:
            im = togli_marchio(im, riquadro, note)
        else:
            note.append("marchio nativo atteso ma non trovato (correlazione %.2f)"
                        % corr)

    im = ricentra(im, note)

    if marchio.serve(base) and tipo in GEOMETRIA_EU:
        im, riquadri = marchio.componi(im, GEOMETRIA_EU[tipo])
        note.append("marchio composto: %d riquadro/i, il primo a (%d, %d) %dx%d"
                    % ((len(riquadri),) + tuple(round(v) for v in riquadri[0])))
    elif marchio.serve(base):
        note.append("il marchio servirebbe ma %s non ha una geometria EU: "
                    "lasciato com'e'" % tipo)

    if not note:
        note.append("niente da correggere")
    return im, note


# ==========================================================================
# CATALOGO E CLOUDINARY
# ==========================================================================

def catalogo():
    """(tipo, motivo, voce) per ogni prodotto EU con un motivo vero."""
    with open(PRODOTTI) as fh:
        dati = json.load(fh)
    fuori = []
    for voce in dati:
        m = re.match(r'(\w+)\s+"(.+)"', voce.get("title", ""))
        if not m:
            continue
        tipo, motivo = m.group(1), m.group(2)
        if motivo == "Crea il Tuo Design" or tipo not in AREE:
            # la base neutra dello studio di personalizzazione non e' un motivo
            continue
        fuori.append((tipo, motivo, voce))
    return fuori


def nativo_di(tipo, motivo):
    nome = "%s-%s.jpg" % (tipo.lower(),
                          motivo.lower().replace(" ", "-").replace("'", ""))
    return os.path.join(NATIVI, nome)


def scarica(voce, percorso):
    if os.path.exists(percorso):
        return
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    urllib.request.urlretrieve(voce["pattern"], percorso)


def variabili():
    fuori = {}
    with open(CONFIG) as fh:
        for riga in fh:
            if "=" in riga and not riga.strip().startswith("#"):
                c, v = riga.split("=", 1)
                fuori[c.strip()] = v.strip()
    return fuori


def carica_cloudinary(percorso, public_id, env):
    """Carica con un public_id NUOVO. Non sovrascrive mai.

    La firma copre i parametri in ordine alfabetico, public_id prima di
    timestamp: e' la stessa regola di uploadToCloudinary() in
    perla-upload-endpoint.js, e sbagliare l'ordine fa rispondere 401.
    """
    nome, chiave, segreto = (env.get("CLOUDINARY_CLOUD_NAME"),
                             env.get("CLOUDINARY_API_KEY"),
                             env.get("CLOUDINARY_API_SECRET"))
    if not (nome and chiave and segreto):
        raise SystemExit("servono CLOUDINARY_CLOUD_NAME, _API_KEY e _API_SECRET "
                         "in config/printify.local.env")
    ts = str(int(time.time()))
    firma = hashlib.sha1(
        ("public_id=%s&timestamp=%s%s" % (public_id, ts, segreto)).encode()).hexdigest()

    limite = "-----------------------------perla%s" % ts
    corpo = []

    def campo(chiave_, valore):
        corpo.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                      % (limite, chiave_, valore)).encode())

    campo("api_key", chiave)
    campo("public_id", public_id)
    campo("timestamp", ts)
    campo("signature", firma)
    with open(percorso, "rb") as fh:
        dati = fh.read()
    corpo.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
                  "filename=\"%s\"\r\nContent-Type: image/jpeg\r\n\r\n"
                  % (limite, os.path.basename(percorso))).encode())
    corpo.append(dati)
    corpo.append(("\r\n--%s--\r\n" % limite).encode())

    req = urllib.request.Request(
        "https://api.cloudinary.com/v1_1/%s/image/upload" % nome,
        data=b"".join(corpo),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % limite})
    with urllib.request.urlopen(req, timeout=300) as risposta:
        return json.loads(risposta.read().decode())["secure_url"]


# ==========================================================================
# COMANDI
# ==========================================================================

def misura_tutto(voci):
    righe = {}
    print("%-12s %-24s %-9s %s" % ("tipo", "motivo", "marchio", "cosa c'e' da fare"))
    for tipo, motivo, voce in voci:
        percorso = nativo_di(tipo, motivo)
        scarica(voce, percorso)
        im = Image.open(percorso).convert("RGB")
        note = []
        alto, basso = bande_vuote(im)
        if alto + basso > 0.02 * im.height:
            note.append("banda vuota %d+%d px" % (alto, basso))
        p = profilo(im, 0)
        k, _ = periodo(p)
        if k:
            _, _, sbil = fase(p, k)
            if sbil > SBILANCIO_MASSIMO:
                note.append("fase orizzontale %.2f" % sbil)
        if abs(im.width - im.height) < 2:
            pv = profilo(im, 1)
            kv, _ = periodo(pv)
            if kv:
                _, _, sv = fase(pv, kv)
                if sv > SBILANCIO_MASSIMO:
                    note.append("fase verticale %.2f" % sv)
        base = os.path.basename(percorso)
        if base in marchio.NATIVI_CON_MEDAGLIONE:
            stato = "firma"
            note.append("firma d'angolo da rifare")
        elif base in marchio.NATIVI_SENZA_MARCHIO:
            stato = "assente"
            note.append("marchio da comporre")
        else:
            stato = "nel motivo"
        print("%-12s %-24s %-9s %s"
              % (tipo, motivo, stato, "; ".join(note) or "-"))
        righe["%s/%s" % (tipo, motivo)] = {
            "banda": [alto, basso], "periodo": k, "marchio": stato, "note": note}
    os.makedirs(USCITA, exist_ok=True)
    with open(MISURE, "w") as fh:
        json.dump(righe, fh, indent=1)
    da_fare = sum(1 for v in righe.values() if v["note"])
    print("\n%d motivi, %d da correggere. Misure in %s"
          % (len(righe), da_fare, os.path.relpath(MISURE, RADICE)))


def costruisci_tutto(voci, carica, env, rifai=False):
    os.makedirs(USCITA, exist_ok=True)
    indice_path = os.path.join(USCITA, "_indice.json")
    indice = {}
    if os.path.exists(indice_path):
        with open(indice_path) as fh:
            indice = json.load(fh)

    for tipo, motivo, voce in voci:
        percorso = nativo_di(tipo, motivo)
        scarica(voce, percorso)
        uscita = os.path.join(USCITA, os.path.basename(percorso))
        print("\n=== %s \"%s\"" % (tipo, motivo))
        # SI CARICA ESATTAMENTE IL FILE CHE E' STATO GUARDATO. Prima il
        # caricamento faceva anche ricostruire, e su 62 motivi sono quaranta
        # minuti buttati -- ma soprattutto: quello che finisce su Cloudinary
        # non sarebbe piu' il file su cui e' passato l'occhio, e il protocollo
        # di questa sessione e' guardare i mockup PRIMA di applicare. Per
        # rifarli davvero c'e' --rifai.
        if os.path.exists(uscita) and not rifai:
            print("    gia' costruito: %s" % os.path.relpath(uscita, RADICE))
        else:
            im, note = costruisci(percorso, tipo)
            salva(im, uscita)
            for n in note:
                print("    " + n)
            indice.setdefault(voce["handle"], {})["note"] = note
        indice.setdefault(voce["handle"], {})["file"] = os.path.relpath(uscita, RADICE)
        indice[voce["handle"]]["originale"] = voce["pattern"]

        if carica:
            # IL SUFFISSO SI METTE UNA VOLTA SOLA. Il public_id si ricava dal
            # pattern che sta nel manifesto, e dopo il primo caricamento li'
            # dentro c'e' gia' un "-v2": rilanciando si otteneva
            # "...-v2-v2.jpg", e al giro dopo "-v2-v2-v2". Visto succedere
            # sulla bandana "Antracite", caricata una volta da sola per prova
            # e poi di nuovo col gruppo.
            vecchio = voce["pattern"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
            while vecchio.endswith(SUFFISSO):
                vecchio = vecchio[:-len(SUFFISSO)]
            public_id = vecchio + SUFFISSO
            url = carica_cloudinary(uscita, public_id, env)
            indice[voce["handle"]]["nuovo"] = url
            voce["pattern"] = url
            print("    caricato: %s" % url)
        with open(indice_path, "w") as fh:
            json.dump(indice, fh, indent=1)

    if carica:
        with open(PRODOTTI) as fh:
            dati = json.load(fh)
        nuovo = {voce["handle"]: voce["pattern"] for _, _, voce in voci}
        for v in dati:
            if v["handle"] in nuovo:
                v["pattern"] = nuovo[v["handle"]]
        with open(PRODOTTI, "w") as fh:
            json.dump(dati, fh, indent=1, ensure_ascii=False)
        print("\nperla-eu-prodotti.json aggiornato. Gli originali restano su "
              "Cloudinary col loro public_id: sono la marcia indietro.")


def salva(im, percorso):
    """Scrive il JPEG, scendendo di qualita' solo se supera il limite Cloudinary."""
    for qualita in (95, 90, 84, 78):
        im.save(percorso, quality=qualita, subsampling=0, optimize=True)
        if os.path.getsize(percorso) <= 9.5 * 1024 * 1024:
            return qualita
    raise SystemExit("%s resta sopra il limite anche a qualita' 78" % percorso)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--costruisci", action="store_true",
                    help="scrive i motivi corretti in generated-designs/eu-motivi-corretti")
    ap.add_argument("--carica", action="store_true",
                    help="carica su Cloudinary con un public_id nuovo e aggiorna il catalogo")
    ap.add_argument("--tipo", action="append", help="Collare, Bandana, Ciotola, Guinzaglio")
    ap.add_argument("--motivo", action="append")
    ap.add_argument("--tutti", action="store_true")
    ap.add_argument("--rifai", action="store_true",
                    help="ricostruisce anche i motivi gia' presenti")
    args = ap.parse_args()

    voci = catalogo()
    if args.tipo:
        voluti = {t.capitalize() for t in args.tipo}
        voci = [v for v in voci if v[0] in voluti]
    if args.motivo:
        voluti = {m.lower() for m in args.motivo}
        voci = [v for v in voci if v[1].lower() in voluti]
    if not voci:
        raise SystemExit("nessun prodotto scelto")
    if not (args.tipo or args.motivo or args.tutti):
        misura_tutto(voci)
        return
    if args.carica and not args.costruisci:
        raise SystemExit("--carica va usato insieme a --costruisci")
    if args.costruisci:
        costruisci_tutto(voci, args.carica, variabili() if args.carica else {},
                         args.rifai)
    else:
        misura_tutto(voci)


if __name__ == "__main__":
    main()
