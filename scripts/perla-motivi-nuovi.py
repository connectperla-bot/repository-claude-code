#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I motivi del catalogo Perla disegnati a codice.

ROUND 46 -- il file era nato con quattro motivi per la linea EU. Adesso ne
ospita altri sei, disegnati per la linea americana, dove 89 file di stampa
su 160 erano sotto risoluzione: le sorgenti erano immagini da 1248x832
stirate fino a 12750x9750, cioe' ingrandite dieci volte. Il codice non ha
questo problema -- gli si chiede la misura dell'area di stampa e la disegna
li'. Le nuove funzioni stanno in fondo e seguono la convenzione `passo`
descritta sotto; le quattro storiche continuano a prendere `u` e non sono
state toccate.

PERCHE' DISEGNATI E NON GENERATI
Sono tutti geometrici: un tartan e' una griglia di bande, le righe sono righe.
Per questa famiglia di disegni il codice batte un generatore di immagini su
tutto cio' che conta qui: i colori sono esattamente quelli del tema (nessuna
approssimazione), la ripetizione e' perfetta, la risoluzione e' vera a
qualunque misura e non ci sono artefatti da correggere.

COSA COLMANO
Il catalogo girava tutto attorno a navy/oro, bordeaux/oro, smeraldo/oro,
antracite/argento e avorio/rosa: tutti damascati scuri e affollati. Mancavano
quattro registri.

    Tartan      il classico invernale. Non c'era nulla di stagionale.
    Marinara    nessuna riga in catalogo. Registro estivo, mediterraneo.
    Terracotta  la palette era tutta fredda o dorata. Mancava il caldo.
    Lino        tutto era scuro e fitto. Mancava il pezzo per un cane bianco.

LA PALETTE
Presa dai token del tema (--color-ink, --color-gold, --color-cream, e cosi'
via), non scelta a occhio. La terracotta non e' un colore nuovo: --color-terra
esisteva gia' nel tema e non era mai finita su un prodotto.

LA SCALA
Il parametro u di ogni funzione e' la scala del motivo in pixel. I valori usati
in produzione sono scelti perche' la ripetizione abbia una misura fisica
sensata sul prodotto vero: la bandana e' circa 53 cm di lato (78 px/cm sui
4125 dell'area di stampa), il collare e' largo 2,5 cm e lungo circa 57 cm
(126 px/cm sui 7169). Un tartan con il sett da 8 cm sulla bandana vuole u=11;
lo stesso tartan sul collare, dove il sett deve stare in 2,6 cm, vuole u=6.

LA SCALA DEI MOTIVI NUOVI: `passo`
Le quattro funzioni storiche prendono `u`, una scala astratta. Le sei nuove
prendono `passo`, che e' la misura IN PIXEL di una ripetizione, ricavata dal
prodotto vero invece che scelta a occhio: una cuccia larga 127 cm su un'area
di stampa di 12750 px fa 100 px/cm, quindi un motivo che si ripete ogni
10 cm vuole passo=1000. Cosi' lo stesso disegno esce della stessa misura
fisica su pezzi di risoluzione diversa -- ed e' l'errore che si fa piu'
facilmente, perche' un motivo bello su una bandana e' invisibile su un
collare largo 2,5 cm.

USO
    from perla_motivi_nuovi import tartan, rombi, PALETTE, tessitura
    im = tessitura(tartan(4125, 4125, 11))                     # storiche: u
    im = tessitura(rombi(12750, 9750, 1000, PALETTE["navy"]))  # nuove: passo

Eseguito direttamente scrive un'anteprima di tutti i motivi.
"""
from PIL import Image, ImageDraw, ImageFilter
from collections import namedtuple
import math
import random

INK   = (19, 42, 74)      # --color-ink
GOLD  = (200, 134, 43)    # --color-gold
TAN   = (185, 152, 106)   # --color-gold-deep
CREAM = (243, 233, 218)   # --color-cream
TERRA = (226, 109, 92)    # --color-terra
BOSCO = (30, 61, 47)      # verde bosco, in famiglia con gli smeraldi gia' in catalogo
COTTO = (150, 62, 48)

# Le colorazioni della linea americana. Sono cinque tinte per motivo, prese a
# campione dai disegni attuali, cosi' che una stessa geometria possa uscire
# nella colorazione giusta invece che in una sola.
Palette = namedtuple("Palette", "fondo scuro tratto accento chiaro")

PALETTE = {
    "grigio":   Palette((92, 96, 100),  (44, 47, 50),   (150, 155, 158), (198, 202, 205), (236, 238, 239)),
    "navy":     Palette((22, 40, 74),   (11, 21, 42),   (176, 138, 62),  (216, 180, 98),  (243, 233, 218)),
    "bordeaux": Palette((94, 18, 30),   (56, 9, 17),    (176, 138, 62),  (216, 180, 98),  (243, 233, 218)),
    "porpora":  Palette((62, 30, 78),   (36, 15, 48),   (176, 138, 62),  (222, 186, 90),  (243, 233, 218)),
    "smeraldo": Palette((16, 74, 58),   (7, 42, 32),    (176, 138, 62),  (216, 180, 98),  (243, 233, 218)),
    "teal":     Palette((24, 132, 134), (9, 78, 84),    (128, 208, 204), (226, 244, 240), (247, 252, 250)),
    "avorio":   Palette((243, 236, 226),(212, 194, 180),(203, 146, 142), (226, 176, 170), (255, 252, 248)),
    "nero":     Palette((28, 26, 24),   (12, 11, 10),   (168, 132, 66),  (214, 178, 96),  (238, 224, 198)),
}

def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))

def tessitura(im, forza=7):
    """Granulosita' fine: senza, i campi piatti sembrano plastica."""
    w, h = im.size
    noise = Image.effect_noise((w, h), forza).convert("L")
    return Image.composite(im, Image.blend(im, Image.new("RGB", (w, h), (255,255,255)), 0.12), noise)

# --- 1. TARTAN ------------------------------------------------------------
def tartan(W, H, u):
    """Sett simmetrico: bande larghe di fondo, righe di accento, overcheck."""
    sett = [(BOSCO, 14), (INK, 4), (BOSCO, 6), (TERRA, 2), (BOSCO, 6),
            (INK, 4), (BOSCO, 14), (CREAM, 2), (GOLD, 1), (CREAM, 2)]
    def bande(lung):
        out, pos = [], 0
        while pos < lung:
            for col, larg in sett:
                px = max(1, round(larg * u))
                out.append((pos, min(pos + px, lung), col)); pos += px
                if pos >= lung: break
        return out
    im = Image.new("RGB", (W, H), BOSCO)
    d = ImageDraw.Draw(im)
    for x0, x1, c in bande(W):                 # ordito
        d.rectangle([x0, 0, x1, H], fill=c)
    ordito = im.copy()
    for y0, y1, c in bande(H):                 # trama, mescolata all'ordito
        striscia = Image.new("RGB", (W, y1 - y0), c)
        im.paste(Image.blend(ordito.crop((0, y0, W, y1)), striscia, 0.5), (0, y0))
    # diagonale del twill
    tw = Image.new("L", (W, H), 0)
    dt = ImageDraw.Draw(tw)
    passo = max(2, round(u))
    for k in range(-H, W, passo * 2):
        dt.line([(k, 0), (k + H, H)], fill=26, width=max(1, passo // 2))
    return Image.composite(Image.blend(im, Image.new("RGB", (W, H), (255,255,255)), .10), im, tw)

# --- 2. RIGHE MARINARE ----------------------------------------------------
def righe(W, H, u, verticali=False):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    lung = W if verticali else H
    schema = [(INK, 9), (CREAM, 5), (INK, 2), (CREAM, 5), (GOLD, 1), (CREAM, 5)]
    pos = 0
    while pos < lung:
        for col, larg in schema:
            px = max(1, round(larg * u))
            if verticali: d.rectangle([pos, 0, pos + px, H], fill=col)
            else:         d.rectangle([0, pos, W, pos + px], fill=col)
            pos += px
            if pos >= lung: break
    return im

# --- 3. TERRACOTTA --------------------------------------------------------
def terracotta(W, H, u):
    """Reticolo di rombi in cotto, con un piccolo rosone dorato agli incroci."""
    import math
    im = Image.new("RGB", (W, H), TERRA)
    d = ImageDraw.Draw(im)
    passo = max(10, round(30 * u))
    sp = max(1, round(1.3 * u))
    for k in range(-H, W + H, passo):
        d.line([(k, 0), (k + H, H)], fill=mix(TERRA, COTTO, .70), width=sp)
        d.line([(k, H), (k + H, 0)], fill=mix(TERRA, COTTO, .70), width=sp)
    r = max(1, round(1.5 * u))
    petalo = max(2, round(2.6 * u))
    y = 0; riga = 0
    while y < H + passo:
        x = 0 if riga % 2 == 0 else passo // 2
        while x < W + passo:
            for ang in range(0, 360, 90):
                dx = petalo * math.cos(math.radians(ang)); dy = petalo * math.sin(math.radians(ang))
                d.ellipse([x+dx-r, y+dy-r, x+dx+r, y+dy+r], fill=mix(TERRA, GOLD, .85))
            d.ellipse([x-r*.9, y-r*.9, x+r*.9, y+r*.9], fill=mix(CREAM, GOLD, .25))
            x += passo
        y += passo; riga += 1
    return im

# --- 4. MINIMAL CHIARO ----------------------------------------------------
def minimal(W, H, u):
    """Rametti radi su crema: il pezzo per un cane bianco."""
    import math
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    passo = max(14, round(64 * u))
    L = max(6, round(20 * u)); sp = max(1, round(1.6 * u))
    rnd = random.Random(7)
    y = 0; riga = 0
    while y < H + passo:
        x = 0 if riga % 2 == 0 else passo // 2
        while x < W + passo:
            a = math.radians(rnd.choice((-70, -55, 55, 70)))
            x2 = x + L * math.cos(a); y2 = y + L * math.sin(a)
            d.line([(x, y), (x2, y2)], fill=mix(TAN, CREAM, .15), width=sp)
            for t in (.34, .62, .88):
                fx = x + (x2-x)*t; fy = y + (y2-y)*t
                o = L * .34 * (1 - t*.35)
                for verso in (1, -1):
                    ex = fx + verso*o*math.sin(a)*-1; ey = fy + verso*o*math.cos(a)
                    d.ellipse([min(fx,ex), min(fy,ey), max(fx,ex), max(fy,ey)],
                              fill=mix(TAN, CREAM, .45), outline=mix(TAN, CREAM, .1), width=1)
            x += passo
        y += passo; riga += 1
    return im


# ==========================================================================
# I MOTIVI DELLA LINEA AMERICANA (convenzione `passo`, vedi la docstring)
# ==========================================================================

def _piastrella(W, H, px, py, cella, fondo, mezzo_salto=False, ss=2):
    """Ripete `cella` su tutta la tela. La cella riceve anche i suoi indici,
    cosi' un motivo puo' alternare (la spina di pesce vive di questo).
    Le celle oltre il bordo si disegnano lo stesso: e' quello che rende la
    ripetizione esatta invece che tagliata."""
    im = Image.new("RGB", (int(W * ss), int(H * ss)), fondo)
    d = ImageDraw.Draw(im)
    PX, PY = px * ss, py * ss
    ncol = int(W * ss / PX) + 3
    nrig = int(H * ss / PY) + 3
    for i in range(-1, ncol):
        sfasa = PY / 2 if (mezzo_salto and i % 2) else 0
        for j in range(-1, nrig):
            cella(d, i * PX + PX / 2, j * PY + PY / 2 + sfasa, PX, PY, i, j)
    return im.resize((int(W), int(H)), Image.LANCZOS) if ss > 1 else im


def _ogiva(cx, cy, w, h, n=40):
    """Il profilo a ogiva (la 'cipolla' del damasco): due archi che si
    incontrano a punta sopra e sotto. E' l'impalcatura di mezzo catalogo."""
    pts = []
    for k in range(n + 1):
        t = k / n
        pts.append((cx + w / 2 * math.sin(math.pi * t) ** 1.35, cy - h / 2 + h * t))
    for k in range(n + 1):
        t = 1 - k / n
        pts.append((cx - w / 2 * math.sin(math.pi * t) ** 1.35, cy - h / 2 + h * t))
    return pts


# --- 1. ROMBI ART DECO ----------------------------------------------------
def rombi(W, H, passo, pal):
    """Rombi concentrici a gradoni, con i triangoli d'angolo a ventaglio.

    La prima versione disegnava i raggi d'angolo come rette lunghe: uscendo
    dalla cella si incrociavano con quelli delle celle vicine e sopra il
    motivo restava una rete di graffi. Ora il ventaglio e' fatto di rombi
    concentrici centrati sull'ANGOLO, quindi non esce mai dal suo quadrante.
    """
    def cella(d, cx, cy, px, py, i, j):
        # ventaglio d'angolo (sta sotto: si disegna per primo)
        for ang in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ax, ay = cx + ang[0] * px / 2, cy + ang[1] * py / 2
            for k in range(5, 0, -1):
                r = px / 2 * (k / 5) * 0.46
                c = pal.tratto if k % 2 else pal.scuro
                d.polygon([(ax, ay - r), (ax + r, ay), (ax, ay + r), (ax - r, ay)], fill=c)
        for t, c in ((1.00, pal.scuro), (0.94, pal.tratto), (0.88, pal.scuro),
                     (0.66, pal.chiaro), (0.60, pal.fondo), (0.40, pal.tratto),
                     (0.34, pal.scuro), (0.14, pal.chiaro)):
            r = px / 2 * t
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=c)
    return _piastrella(W, H, passo, passo, cella, pal.scuro)


# --- 2. CHEVRON -----------------------------------------------------------
def chevron(W, H, passo, pal):
    """Zigzag a bande larghe, sfumate dal chiaro allo scuro."""
    n = 7
    def cella(d, cx, cy, px, py, i, j):
        h = py / n
        for k in range(n):
            t = k / (n - 1)
            c = mix(pal.chiaro, pal.scuro, t) if t < .5 else mix(pal.scuro, pal.tratto, (t - .5) * 2)
            y = cy - py / 2 + k * h
            d.polygon([(cx - px / 2, y + h * 1.6), (cx, y), (cx + px / 2, y + h * 1.6),
                       (cx + px / 2, y + h * 2.6), (cx, y + h), (cx - px / 2, y + h * 2.6)], fill=c)
    return _piastrella(W, H, passo, passo, cella, pal.fondo)


# --- 3. SPINA DI PESCE ----------------------------------------------------
def spinato(W, H, passo, pal):
    """Spina di pesce vera.

    Due tentativi sbagliati prima di questo: sovrapporre le due diagonali
    nella stessa cella da' un plaid, alternarle a scacchiera da' un
    intreccio a canestro. La spina vuole COLONNE: ogni colonna ha le sue
    righe tutte nello stesso verso, la colonna accanto le ha nel verso
    opposto e sfalsate di mezza riga, cosi' le punte si incontrano.
    """
    def cella(d, cx, cy, px, py, i, j):
        verso = 1 if i % 2 == 0 else -1
        sp = max(2, int(px * .13))
        x0, y0 = cx - px / 2, cy - py / 2
        sfasa = 0 if verso > 0 else sp
        k = -int(py) - sfasa
        alt = 0
        while k < px + py:
            c = pal.chiaro if alt % 2 == 0 else pal.tratto
            if verso > 0:
                d.line([(x0 + k, y0), (x0 + k + py, y0 + py)], fill=c, width=sp)
            else:
                d.line([(x0 + k, y0 + py), (x0 + k + py, y0)], fill=c, width=sp)
            k += sp * 2
            alt += 1
    # colonne strette e alte: e' la proporzione che fa leggere la spina
    return _piastrella(W, H, passo / 2, passo, cella, pal.fondo)


# --- 4. TRELLIS A OGIVA ---------------------------------------------------
def trellis(W, H, passo, pal):
    """Grata a ogiva con rosetta al centro: la prima versione disegnava
    cerchi perche' usava due archi non raccordati."""
    def cella(d, cx, cy, px, py, i, j):
        sp = max(2, int(px * .022))
        d.polygon(_ogiva(cx, cy, px, py), outline=pal.tratto, width=sp)
        d.polygon(_ogiva(cx, cy, px * .78, py * .78), outline=pal.accento, width=max(1, sp // 2))
        r = px * .055
        for a in range(0, 360, 60):
            fx = cx + r * 1.5 * math.cos(math.radians(a))
            fy = cy + r * 1.5 * math.sin(math.radians(a))
            d.ellipse([fx - r, fy - r, fx + r, fy + r], fill=pal.accento)
        d.ellipse([cx - r * .8, cy - r * .8, cx + r * .8, cy + r * .8], fill=pal.chiaro)
    return _piastrella(W, H, passo, passo, cella, pal.fondo, mezzo_salto=True)


# --- 5. ONDE --------------------------------------------------------------
def onde(W, H, passo, pal):
    """Onde larghe in due toni piu' un filo d'oro.

    Disegnate come FASCE PIENE fra due sinusoidi. Con line(width=...) i
    gomiti uscivano a denti di sega: una linea spessa e' una sequenza di
    segmenti, e su una curva larga i giunti si vedono.
    """
    def onda(cx, base, px, py, amp, n=64):
        return [(cx - px / 2 + px * (q / n),
                 base + math.sin((q / n) * 2 * math.pi) * amp) for q in range(n + 1)]

    def cella(d, cx, cy, px, py, i, j):
        amp = py * .22
        for k, (c, alt) in enumerate(((pal.scuro, .46), (pal.fondo, .46))):
            base = cy - py / 2 + k * py * .5
            sopra = onda(cx, base, px, py, amp)
            sotto = onda(cx, base + py * alt, px, py, amp)
            d.polygon(sopra + sotto[::-1], fill=c)
        base = cy - py / 2 + py * .5
        d.line(onda(cx, base, px, py, amp), fill=pal.tratto,
               width=max(2, int(py * .045)), joint="curve")
    return _piastrella(W, H, passo, passo, cella, pal.fondo)


# --- 6. RETICOLO GEOMETRICO ----------------------------------------------
def tribale(W, H, passo, pal):
    """Rombi con rosetta agli incroci: il reticolo teal, l'unico dei
    geometrici attuali che gia' funzionava."""
    def cella(d, cx, cy, px, py, i, j):
        r = px / 2
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                  fill=pal.scuro, outline=pal.chiaro, width=max(2, int(px * .03)))
        r2 = r * .55
        d.polygon([(cx, cy - r2), (cx + r2, cy), (cx, cy + r2), (cx - r2, cy)], fill=pal.tratto)
        r3 = r * .22
        d.polygon([(cx, cy - r3), (cx + r3, cy), (cx, cy + r3), (cx - r3, cy)], fill=pal.chiaro)
        f = px * .045
        for dx, dy in ((0, -r), (r, 0), (0, r), (-r, 0)):
            d.ellipse([cx + dx - f, cy + dy - f, cx + dx + f, cy + dy + f], fill=pal.chiaro)
    return _piastrella(W, H, passo, passo, cella, pal.fondo)


GEOMETRICI = {"Rombi": rombi, "Chevron": chevron, "Spinato": spinato,
              "Trellis": trellis, "Onde": onde, "Tribale": tribale}

MOTIVI = {"Tartan": tartan, "Marinara": righe, "Terracotta": terracotta, "Lino": minimal}

if __name__ == "__main__":
    import os
    os.makedirs("motivi", exist_ok=True)
    lato, riga = 300, []
    for nome, fn in MOTIVI.items():
        im = fn(1200, 1200, 3.2) if nome != "Marinara" else fn(1200, 1200, 6)
        riga.append((nome, tessitura(im)))
    tinte = ["grigio", "teal", "navy", "porpora", "bordeaux", "teal"]
    for (nome, fn), tinta in zip(GEOMETRICI.items(), tinte):
        riga.append((nome, tessitura(fn(1200, 1200, 300, PALETTE[tinta]))))

    prev = Image.new("RGB", (5 * lato, ((len(riga) + 4) // 5) * lato), "white")
    for i, (nome, im) in enumerate(riga):
        prev.paste(im.resize((lato, lato), Image.LANCZOS), ((i % 5) * lato, (i // 5) * lato))
        print(nome, "ok")
    prev.save("motivi/anteprima.png")
    print("%d motivi in motivi/anteprima.png" % len(riga))
