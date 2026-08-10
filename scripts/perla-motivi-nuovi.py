#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quattro motivi nuovi per il catalogo Perla, disegnati a codice.

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

USO
    from perla_motivi_nuovi import tartan, righe, terracotta, minimal, tessitura
    im = tessitura(tartan(4125, 4125, 11))

Eseguito direttamente scrive un'anteprima dei quattro motivi.
"""
from PIL import Image, ImageDraw, ImageFilter
import random

INK   = (19, 42, 74)      # --color-ink
GOLD  = (200, 134, 43)    # --color-gold
TAN   = (185, 152, 106)   # --color-gold-deep
CREAM = (243, 233, 218)   # --color-cream
TERRA = (226, 109, 92)    # --color-terra
BOSCO = (30, 61, 47)      # verde bosco, in famiglia con gli smeraldi gia' in catalogo
COTTO = (150, 62, 48)

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

MOTIVI = {"Tartan": tartan, "Marinara": righe, "Terracotta": terracotta, "Lino": minimal}

if __name__ == "__main__":
    prev = Image.new("RGB", (4*300, 300), "white")
    for i, (nome, fn) in enumerate(MOTIVI.items()):
        im = fn(1200, 1200, 3.2) if nome != "Marinara" else fn(1200, 1200, 6)
        im = tessitura(im)
        im.resize((300, 300), Image.LANCZOS)
        prev.paste(im.resize((300, 300), Image.LANCZOS), (i*300, 0))
        print(nome, "ok")
    prev.save("motivi/anteprima.png")
