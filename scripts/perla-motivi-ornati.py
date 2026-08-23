#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le famiglie ornate del catalogo Perla, disegnate a codice.

PERCHE' ESISTE
perla-motivi-nuovi.py aveva coperto i motivi geometrici -- tartan, righe,
rombi, chevron, spinato, trellis, onde, tribale -- e li aveva risolti bene,
perche' una griglia di bande e' una griglia di bande a qualunque misura.
Restavano fuori le famiglie ornate: damasco, medaglioni, barocco, floreale,
ulivo, paisley, toile, ghirigori, erbario. Quelle arrivavano ancora da
immagini generate una volta sola, e portavano con se' tre difetti che sul
negozio si vedono a occhio nudo (fogli di contatto del 23 agosto):

  la scritta "PERLA ITALIA" tagliata a meta' dal bordo -- si legge "erla",
  "Italia" mozzato -- su una decina di bandane americane, sui collari EU
  "Toile" e "Medaglioni", sulla ciotola "Smeraldo";

  il motivo gigante sul pezzo stretto: il medaglione disegnato per una
  bandana da 53 cm, ritagliato per un collare alto 2,5 cm, resta grande
  com'era e si vede una fetta di due medaglioni invece di un disegno;

  la cucitura visibile a meta' bandana ("Damask Navy", "Green Floral"), dove
  due copie erano state affiancate e gli originali non combaciano ai bordi.

Non erano tre difetti: era uno. Quelle immagini non sono piastrelle, e la
scritta e' cotta dentro. perla-file-stampa-motivi.py lo aveva gia' scritto:
affiancarle specchiando stampa il testo rovesciato, affiancarle dritte lascia
una cucitura misurabile. Il ritaglio centrato era la meno peggio delle tre,
non una soluzione.

Qui la piastrella nasce piastrella. `_piastrella` disegna anche le celle oltre
il bordo, quindi la ripetizione e' esatta per costruzione e non c'e' niente da
far combaciare. E il passo arriva da perla-scala-stampa.py in CENTIMETRI, non
in pixel: lo stesso damasco esce della stessa misura fisica sulla bandana e
sul guinzaglio, che e' esattamente cio' che oggi non succede.

IL MARCHIO
La titolare ha scelto di tenerlo nel motivo, piccolo e mai tagliato.
`marchi_interi` lo stampa su una griglia SALTANDO ogni posizione il cui
riquadro uscirebbe dalla tela. "Mai tagliato" non e' quindi una speranza
riposta in una misura fortunata: e' una proprieta' costruttiva, e
tests/motivi-ornati.test.py la verifica su tutte le aree di stampa.

USO
    from perla_motivi_ornati import damasco, MOTIVI, marchi_interi
    from perla_scala_stampa import AREE, passo_px, passo_sicuro
    a = AREE["collare-eu"]
    p = passo_sicuro("collare-eu", passo_px("collare-eu", 2.2))
    im = damasco(a.px_w, a.px_h, p, PALETTE["navy"])
    marchi_interi(im, "collare-eu")

Eseguito direttamente scrive un foglio di anteprima di tutti i motivi.
"""
import importlib.util
import math
import os

from PIL import Image, ImageDraw, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))


def _modulo(nome, percorso):
    """I file di questo repository hanno il trattino nel nome e non si possono
    importare con `import`. Stesso espediente di perla-usa-file-stampa.py."""
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_geo = _modulo("perla_motivi_nuovi", os.path.join(QUI, "perla-motivi-nuovi.py"))
_scala = _modulo("perla_scala_stampa", os.path.join(QUI, "perla-scala-stampa.py"))

# Si riusa tutto quello che c'e' gia': palette dai token del tema, la
# piastrella con supercampionamento e mezzo salto, l'ogiva (che il file
# chiama "l'impalcatura di mezzo catalogo", ed e' vero: damasco, medaglioni
# e barocco partono tutti da li'), la tessitura contro i campi piatti.
PALETTE = _geo.PALETTE
Palette = _geo.Palette
mix = _geo.mix
tessitura = _geo.tessitura
_ogiva = _geo._ogiva
_passo_intero = _scala.passo_intero


def _piastrella(W, H, px, py, cella, fondo, mezzo_salto=False, ss=2):
    """Come `_geo._piastrella`, ma il passo viene prima portato a dividere la
    tela un numero intero di volte.

    La prova tests/motivi-ornati.test.py ha trovato cosi' una cucitura vera sul
    barocco: stacco 43,9 al bordo contro 2,1 dentro il motivo. Non era un
    difetto del disegno -- era il passo (220 px) che non stava un numero intero
    di volte nell'altezza (600), quindi il bordo cadeva a meta' cella. E' lo
    stesso motivo per cui sul negozio si vedono motivi interi da un lato e
    mozzi dall'altro."""
    return _geo._piastrella(W, H, _passo_intero(W, px), _passo_intero(H, py),
                            cella, fondo, mezzo_salto, ss)

# Serif largamente disponibile, in famiglia con il Playfair del tema. Se manca
# si scende di grado invece di fallire: un marchio con un altro carattere e'
# un difetto piccolo, un file di stampa che non esce e' un prodotto in meno.
CARATTERI = (
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
)


def _carattere(dim):
    for percorso in CARATTERI:
        if os.path.exists(percorso):
            try:
                return ImageFont.truetype(percorso, int(dim))
            except Exception:
                pass
    return ImageFont.load_default()


# ---- primitive condivise --------------------------------------------------

def _ruota(punti, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * c - (y - cy) * s,
             cy + (x - cx) * s + (y - cy) * c) for x, y in punti]


def _foglia(d, cx, cy, lung, larg, ang, colore, bordo=None):
    """La foglia a mandorla: due archi che si incontrano a punta. Serve a
    ulivo, erbario, floreale e alle volute del barocco."""
    punti = []
    for t in range(0, 21):
        u = t / 20.0
        x = cx - lung / 2 + lung * u
        y = cy - larg / 2 * math.sin(math.pi * u)
        punti.append((x, y))
    for t in range(20, -1, -1):
        u = t / 20.0
        x = cx - lung / 2 + lung * u
        y = cy + larg / 2 * math.sin(math.pi * u)
        punti.append((x, y))
    d.polygon(_ruota(punti, cx, cy, ang), fill=colore,
              outline=bordo if bordo else None)


def _spirale(d, cx, cy, raggio, giri, colore, spessore, ang=0.0, verso=1):
    """La voluta: il segno di barocco e ghirigori."""
    punti = []
    passi = max(24, int(giri * 28))
    for i in range(passi + 1):
        u = i / float(passi)
        a = ang + verso * u * giri * 2 * math.pi
        r = raggio * (1 - 0.86 * u)
        punti.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.line(punti, fill=colore, width=max(1, int(spessore)), joint="curve")


def _rosetta(d, cx, cy, raggio, petali, colore, riempi=None):
    for k in range(petali):
        a = 2 * math.pi * k / petali
        _foglia(d, cx + raggio * 0.52 * math.cos(a), cy + raggio * 0.52 * math.sin(a),
                raggio * 0.9, raggio * 0.42, a, riempi or colore)
    d.ellipse([cx - raggio * 0.2, cy - raggio * 0.2,
               cx + raggio * 0.2, cy + raggio * 0.2], fill=colore)


def _boteh(n=60, w0=0.32, pot=0.55):
    """Il profilo del boteh, in coordinate proprie.

    DUE ERRORI PRIMA DI ARRIVARCI, ed entrambi si vedevano solo guardando.
    Il primo: una goccia che derivava di lato: era una mandorla appuntita, non
    un paisley -- mancava la punta arricciata, che e' l'unica cosa che rende
    un paisley riconoscibile.
    Il secondo, piu' insidioso: preso l'arco come spina, avevo scostato i due
    fianchi lungo la TANGENTE invece che lungo la normale. Lo spessore correva
    quindi lungo la curva anziche' attraverso, il poligono si intrecciava e ne
    usciva un disco con la coda. La normale di un arco e' la radiale: e' quella
    riga, `nx, ny = cos(a), sin(a)`, tutta la differenza.

    La ruota di -90 gradi in fondo mette la parte grossa in basso e la punta
    che si piega in alto, come si guarda un paisley.
    """
    a0, a1 = math.radians(150), math.radians(-30)
    est, dentro = [], []
    for i in range(n + 1):
        u = i / float(n)
        a = a0 + (a1 - a0) * u
        w = w0 * (1 - u) ** pot
        nx, ny = math.cos(a), math.sin(a)
        est.append((nx * (1 + w), ny * (1 + w)))
        dentro.append((nx * (1 - w), ny * (1 - w)))
    # calotta tonda sull'estremita' grossa: senza, il boteh finisce di netto
    sx, sy = math.cos(a0), math.sin(a0)
    calotta = []
    for k in range(1, 16):
        b = a0 + math.pi - math.pi * k / 16.0
        calotta.append((sx + math.cos(b) * w0, sy + math.sin(b) * w0))
    punti = est + dentro[::-1] + calotta
    return _ruota(punti, 0.0, 0.0, math.radians(-90))


_BOTEH = _boteh()


def _goccia(d, cx, cy, alt, colore, bordo=None, ang=0.0, sp=2):
    xs = [p[0] for p in _BOTEH]
    ys = [p[1] for p in _BOTEH]
    h = max(ys) - min(ys)
    k = alt / h
    mx = (max(xs) + min(xs)) / 2.0
    my = (max(ys) + min(ys)) / 2.0
    punti = [(cx + (x - mx) * k, cy + (y - my) * k) for x, y in _BOTEH]
    punti = _ruota(punti, cx, cy, ang)
    d.polygon(punti, fill=colore)
    if bordo:
        d.line(punti + [punti[0]], fill=bordo, width=max(1, int(sp)), joint="curve")


def _tralcio(d, punti, colore, spessore):
    """Un ramo curvo invece di una riga dritta. Il primo ulivo aveva il
    tralcio disegnato con d.line fra due punti: sul motivo si vedeva una riga
    orizzontale netta che tagliava le foglie, e sembrava un errore di stampa."""
    d.line(punti, fill=colore, width=max(1, int(spessore)), joint="curve")


def _curva(p0, p1, p2, n=24):
    """Quadratica di Bezier: la spina di ulivo, erbario e toile."""
    out = []
    for i in range(n + 1):
        t = i / float(n)
        m = 1 - t
        out.append((m * m * p0[0] + 2 * m * t * p1[0] + t * t * p2[0],
                    m * m * p0[1] + 2 * m * t * p1[1] + t * t * p2[1]))
    return out


# ---- le nove famiglie -----------------------------------------------------
# Firma comune: (W, H, passo, pal) come le sei funzioni nuove di
# perla-motivi-nuovi.py. `passo` e' la ripetizione in pixel, che chi chiama
# ricava dai centimetri con perla-scala-stampa.passo_px.

def damasco(W, H, passo, pal):
    """L'ogiva con il fiore dentro, a mezzo salto: il damascato classico."""
    def cella(d, cx, cy, px, py, i, j):
        w, h = px * 0.78, py * 0.88
        d.polygon(_ogiva(cx, cy, w, h), outline=pal.tratto, width=max(1, int(px * 0.035)))
        _rosetta(d, cx, cy, h * 0.20, 6, pal.accento, mix(pal.accento, pal.fondo, 0.35))
        for segno in (-1, 1):
            _foglia(d, cx + segno * w * 0.26, cy - h * 0.24, h * 0.20, h * 0.085,
                    segno * 0.9, pal.tratto)
            _foglia(d, cx + segno * w * 0.26, cy + h * 0.24, h * 0.20, h * 0.085,
                    -segno * 0.9, pal.tratto)
    return _piastrella(W, H, passo, passo * 1.28, cella, pal.fondo, mezzo_salto=True)


def medaglioni(W, H, passo, pal):
    """Il medaglione tondo entro una cornice: il motivo che sul collare usciva
    tagliato, ed e' il motivo per cui esiste questo file."""
    def cella(d, cx, cy, px, py, i, j):
        r = min(px, py) * 0.40
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=pal.tratto,
                  width=max(1, int(r * 0.10)))
        d.ellipse([cx - r * 0.80, cy - r * 0.80, cx + r * 0.80, cy + r * 0.80],
                  outline=pal.accento, width=max(1, int(r * 0.055)))
        _rosetta(d, cx, cy, r * 0.46, 8, pal.accento, mix(pal.accento, pal.chiaro, 0.4))
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            _foglia(d, cx + r * 1.28 * math.cos(a), cy + r * 1.28 * math.sin(a),
                    r * 0.40, r * 0.17, a, pal.tratto)
    return _piastrella(W, H, passo, passo, cella, pal.fondo, mezzo_salto=True)


def barocco(W, H, passo, pal):
    """Volute d'acanto affrontate."""
    def cella(d, cx, cy, px, py, i, j):
        r = min(px, py) * 0.30
        sp = max(1, int(r * 0.14))
        for verso in (1, -1):
            _spirale(d, cx + verso * px * 0.20, cy, r, 1.35, pal.tratto, sp,
                     ang=math.pi / 2 if verso > 0 else -math.pi / 2, verso=verso)
            _foglia(d, cx + verso * px * 0.20, cy + py * 0.28, r * 1.1, r * 0.42,
                    verso * 0.5, pal.accento)
        _rosetta(d, cx, cy - py * 0.26, r * 0.42, 5, pal.accento)
    return _piastrella(W, H, passo, passo * 1.1, cella, pal.fondo, mezzo_salto=True)


def floreale(W, H, passo, pal):
    """Fiorellino con due foglie, a mezzo salto: il registro leggero."""
    def cella(d, cx, cy, px, py, i, j):
        r = min(px, py) * 0.19
        _foglia(d, cx - px * 0.20, cy + py * 0.16, r * 1.7, r * 0.62, -0.7, pal.tratto)
        _foglia(d, cx + px * 0.20, cy + py * 0.16, r * 1.7, r * 0.62, 0.7, pal.tratto)
        d.line([(cx, cy + py * 0.30), (cx, cy - py * 0.02)], fill=pal.tratto,
               width=max(1, int(r * 0.16)))
        _rosetta(d, cx, cy - py * 0.10, r, 6, pal.accento, pal.chiaro)
    return _piastrella(W, H, passo, passo * 1.15, cella, pal.fondo, mezzo_salto=True)


def ulivo(W, H, passo, pal):
    """Il ramo d'ulivo. Prima stesura: tralcio dritto con d.line, foglie a
    mandorla larga, drupe da 3 px. All'anteprima si vedeva una riga
    orizzontale netta che tagliava le foglie -- sembrava un errore di stampa,
    non un ramo. Ora il tralcio e' una curva, le foglie sono strette e rivolte
    verso la punta come su un ulivo vero, e le olive si vedono."""
    def cella(d, cx, cy, px, py, i, j):
        verso = -1 if (j % 2) else 1
        x0, x1 = cx - px * 0.42, cx + px * 0.42
        spina = _curva((x0, cy + verso * py * 0.10),
                       (cx, cy - verso * py * 0.20),
                       (x1, cy + verso * py * 0.10))
        _tralcio(d, spina, pal.tratto, py * 0.020)
        for k in range(1, len(spina) - 1, 3):
            sx, sy = spina[k]
            prec, succ = spina[k - 1], spina[k + 1]
            dir_ang = math.atan2(succ[1] - prec[1], succ[0] - prec[0])
            for s in (-1, 1):
                a = dir_ang + s * 1.05
                lung = px * 0.17
                _foglia(d, sx + math.cos(a) * lung * 0.5,
                        sy + math.sin(a) * lung * 0.5,
                        lung, py * 0.055, a, pal.tratto)
        for k in (len(spina) // 3, 2 * len(spina) // 3):
            sx, sy = spina[k]
            rr = py * 0.045
            d.ellipse([sx - rr, sy - verso * py * 0.11 - rr,
                       sx + rr, sy - verso * py * 0.11 + rr], fill=pal.accento)
    return _piastrella(W, H, passo, passo * 0.66, cella, pal.fondo, mezzo_salto=True)



def paisley(W, H, passo, pal):
    """Il boteh, alternato di verso."""
    def cella(d, cx, cy, px, py, i, j):
        alt = py * 0.66
        ang = math.pi if (i + j) % 2 else 0.0
        # Il riempimento va staccato dal fondo, se no il boteh si legge come
        # un contorno vuoto: alla prima anteprima era mix(fondo, scuro), cioe'
        # piu' scuro del fondo su una palette gia' scura, e spariva.
        _goccia(d, cx, cy, alt, mix(pal.fondo, pal.tratto, 0.34), pal.tratto, ang,
                sp=max(1, int(py * 0.016)))
        _rosetta(d, cx + (alt * 0.06 if not ang else -alt * 0.06),
                 cy + (alt * 0.10 if not ang else -alt * 0.10),
                 alt * 0.13, 5, pal.accento)
    return _piastrella(W, H, passo, passo * 1.25, cella, pal.fondo, mezzo_salto=True)


def toile(W, H, passo, pal):
    """Rada e disegnata a penna: un mazzetto di tre steli curvi con i fiori in
    cima. La prima stesura faceva convergere tre rette in un punto in basso e
    all'anteprima sembrava un paracadute. Steli che si APRONO invece di
    chiudersi, e il mazzetto torna un mazzetto."""
    def cella(d, cx, cy, px, py, i, j):
        sp = max(1, int(py * 0.013))
        piede = (cx, cy + py * 0.30)
        for k, incl in enumerate((-0.42, 0.0, 0.42)):
            cima = (cx + math.sin(incl) * px * 0.30,
                    cy - py * 0.28 + abs(incl) * py * 0.10)
            stelo = _curva(piede, (cx + math.sin(incl) * px * 0.06, cy), cima)
            _tralcio(d, stelo, pal.tratto, sp)
            _rosetta(d, cima[0], cima[1], py * 0.062, 5, pal.accento, pal.chiaro)
            meta = stelo[len(stelo) // 2]
            lato = 1 if incl >= 0 else -1
            _foglia(d, meta[0] + lato * px * 0.06, meta[1],
                    px * 0.14, py * 0.050, incl + lato * 1.1, pal.tratto)
        # reticolo rado agli angoli: tiene insieme il campo vuoto
        for dx, dy in ((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)):
            d.ellipse([cx + dx * px - sp, cy + dy * py - sp,
                       cx + dx * px + sp, cy + dy * py + sp], fill=pal.tratto)
    return _piastrella(W, H, passo, passo, cella, pal.fondo)



def ghirigori(W, H, passo, pal):
    """Volute libere che si rincorrono: il piu' fitto della famiglia."""
    def cella(d, cx, cy, px, py, i, j):
        r = min(px, py) * 0.26
        sp = max(1, int(r * 0.16))
        for k, (dx, dy, verso) in enumerate(
                ((-0.24, -0.20, 1), (0.24, 0.20, -1), (0.26, -0.24, -1), (-0.26, 0.24, 1))):
            _spirale(d, cx + dx * px, cy + dy * py, r, 1.15,
                     pal.tratto if k % 2 else pal.accento, sp,
                     ang=k * math.pi / 2, verso=verso)
    return _piastrella(W, H, passo, passo, cella, pal.fondo, mezzo_salto=True)


def erbario(W, H, passo, pal):
    """La fronda: foglioline appaiate lungo una nervatura curva, sempre piu'
    piccole verso la punta. La prima stesura metteva quattro coppie uguali su
    un gambo dritto e all'anteprima sembravano frecce, non erbe."""
    def cella(d, cx, cy, px, py, i, j):
        piega = 0.22 if (i % 2) else -0.22
        base = (cx - px * piega, cy + py * 0.40)
        cima = (cx + px * piega, cy - py * 0.40)
        spina = _curva(base, (cx + px * piega * 2.2, cy), cima)
        _tralcio(d, spina, pal.tratto, py * 0.016)
        n = len(spina)
        for k in range(2, n - 2, 2):
            u = k / float(n - 1)
            prec, succ = spina[k - 1], spina[k + 1]
            dir_ang = math.atan2(succ[1] - prec[1], succ[0] - prec[0])
            lung = px * 0.20 * (1.0 - 0.62 * u)      # si accorciano salendo
            for s in (-1, 1):
                a = dir_ang + s * 1.15
                _foglia(d, spina[k][0] + math.cos(a) * lung * 0.5,
                        spina[k][1] + math.sin(a) * lung * 0.5,
                        lung, lung * 0.34, a, pal.tratto)
        _rosetta(d, cima[0], cima[1], py * 0.042, 5, pal.accento)
    return _piastrella(W, H, passo, passo * 0.92, cella, pal.fondo, mezzo_salto=True)


MOTIVI = {
    "damasco": damasco,
    "medaglioni": medaglioni,
    "barocco": barocco,
    "floreale": floreale,
    "ulivo": ulivo,
    "paisley": paisley,
    "toile": toile,
    "ghirigori": ghirigori,
    "erbario": erbario,
}


# ---- il marchio, piccolo e mai tagliato -----------------------------------

# Altezza del riquadro del marchio, in centimetri di prodotto finito. Nove
# millimetri: si legge da vicino su una bandana e resta discreto su un
# collare, dove l'area e' alta 2,5 cm.
MARCHIO_CM = 0.9
# Ogni quanto si ripete, in centimetri. Rado di proposito: il marchio
# accompagna il motivo, non lo sostituisce.
MARCHIO_PASSO_CM = 16.0


def marchi_interi(im, tipo, testo="PERLA ITALIA", colore=None, opacita=0.62,
                  passo_cm=MARCHIO_PASSO_CM, altezza_cm=MARCHIO_CM):
    """Stampa il marchio su una griglia, saltando quelli che uscirebbero.

    LA REGOLA
    Si calcola il riquadro di ogni marchio PRIMA di disegnarlo e lo si scarta
    se tocca un bordo. Cosi' "mai tagliato" e' garantito dalla costruzione e
    non dalla fortuna della misura: su un guinzaglio alto 219 px o su una
    medaglietta da 810, dove nessun margine e' scontato, il marchio o ci sta
    intero o non c'e'.

    Torna il numero di marchi stampati -- zero e' un esito legittimo: su un
    pezzo troppo stretto il motivo resta nudo, che e' meglio di una scritta
    monca. Chi chiama puo' guardarlo e decidere.
    """
    a = _scala.AREE[tipo]
    ppc = _scala.px_per_cm(tipo)
    alt = max(8.0, altezza_cm * ppc)
    passo = max(alt * 2.4, passo_cm * ppc)

    font = _carattere(alt * 0.62)
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, y1 = d.textbbox((0, 0), testo, font=font)
    tw, th = x1 - x0, y1 - y0
    # Il riquadro e' il testo piu' un respiro attorno: e' quello che non deve
    # toccare il bordo, non le lettere nude.
    mw, mh = tw + alt * 0.9, max(th + alt * 0.55, alt)

    if colore is None:
        colore = (255, 255, 255)
    rgba = tuple(colore) + (int(255 * opacita),)

    W, H = im.size
    stampati = 0
    # Si parte da mezzo passo, cosi' la griglia e' centrata sulla tela e i
    # margini avanzano uguali ai due lati invece che tutti da una parte --
    # l'altra meta' del difetto "decentrato".
    ncol = max(1, int(round(W / passo)))
    nrig = max(1, int(round(H / passo)))
    for i in range(ncol):
        for j in range(nrig):
            cx = W * (i + 0.5) / ncol
            cy = H * (j + 0.5) / nrig
            if (i + j) % 2:
                continue          # a scacchiera: piu' rado, meno insistente
            l, t = cx - mw / 2, cy - mh / 2
            if l < 0 or t < 0 or l + mw > W or t + mh > H:
                continue          # uscirebbe: si salta, non si taglia
            d.text((cx - tw / 2 - x0, cy - th / 2 - y0), testo, font=font, fill=rgba)
            stampati += 1
    return stampati


def _anteprima(percorso="anteprima-motivi-ornati.png", lato=420):
    pal = PALETTE["navy"]
    nomi = sorted(MOTIVI)
    cols = 3
    rows = (len(nomi) + cols - 1) // cols
    foglio = Image.new("RGB", (cols * lato, rows * (lato + 26)), (250, 248, 244))
    d = ImageDraw.Draw(foglio)
    font = _carattere(18)
    for k, nome in enumerate(nomi):
        r, c = divmod(k, cols)
        im = tessitura(MOTIVI[nome](lato, lato, lato / 4.0, pal))
        foglio.paste(im, (c * lato, r * (lato + 26)))
        d.text((c * lato + 6, r * (lato + 26) + lato + 4), nome, fill=(40, 40, 40), font=font)
    foglio.save(percorso)
    return percorso


if __name__ == "__main__":
    print("scritto", _anteprima())
