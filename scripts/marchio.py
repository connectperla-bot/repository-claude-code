#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mette il marchio DENTRO il file di stampa, non sopra come livello a parte.

PERCHE' NON E' PIU' UN LIVELLO SEPARATO

Fino a ROUND 46 il marchio viveva come seconda immagine dentro il placeholder
Printify, con coordinate sue. Due difetti nascevano da li', e sono arrivati
tutti e due in catalogo:

1. SPARIVA. perla-usa-marchio.py --rimuovi toglieva il livello sovrapposto da
   bandane e medagliette perche' "il marchio e' gia' dentro l'artwork" -- vero
   quando fu scritto. Ma perla-usa-carica-stampe.py aveva nel frattempo
   sostituito quell'artwork con i nativi europei, che sono motivo e basta.
   Due operazioni giuste da sole lasciano il prodotto senza nessun marchio.
2. ERA SGRANATO O TAGLIATO. In catalogo giravano CINQUE file di marchio
   diversi ("LOGO PERLA - Copia.PNG" 554x408, "logo-full.png" 600x507,
   "v2-01-logo-centrale.png", "v3-square-coaster-logo.png",
   "perla-combined-logo.png"), a scale copiate da un prodotto all'altro. Sulla
   cuccia il piu' piccolo veniva stampato largo 1350 px: ingrandito 2,4 volte.

Composto qui, il marchio nasce alla risoluzione del file di stampa, non puo'
essere rimosso per sbaglio, e non c'e' piu' nessuna scala da mantenere
allineata a mano fra prodotti diversi.

QUANTO GRANDE: FRAZIONE DEL LATO CORTO, NON PIXEL
La misura e' espressa come frazione del LATO CORTO dell'area. E' l'unica che
resta coerente fra varianti di misura fisica diversa: il collare S e' una
fettuccia da 1 pollice (229 px), il collare M da 1,5 (338 px), e un marchio
alto "il 72% della fettuccia" si vede uguale su tutti e due, mentre un marchio
"alto 240 px" sul primo sarebbe fuori misura.

DOVE: DENTRO LA FORMA VERA DEL PRODOTTO
L'area di stampa e' sempre un rettangolo, il prodotto quasi mai. La bandana e'
un TRIANGOLO e la medaglietta un CERCHIO: un marchio centrato nel rettangolo
puo' cadere benissimo fuori dal tessuto. Non e' teoria -- e' il difetto
descritto in perla-usa-marchio.py, dove il marchio a y=0,863 finiva oltre la
punta della bandana e veniva tagliato. area_sicura() modella la forma vera e
componi() si rifiuta di uscirne.

MAI INGRANDITO
Il file del marchio e' 1600 px di larghezza. Se la misura richiesta chiede piu'
di tanto, si scende a 1600 e lo si dice: rimetterlo sgranato sarebbe rifare da
capo il difetto che questo modulo esiste per togliere.
"""
import os

from PIL import Image, ImageDraw

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
MARCHIO = os.path.join(RADICE, "generated-designs", "perla-combined-logo.png")

# Il nome con cui il marchio si riconosce nei file gia' costruiti, e i nomi dei
# livelli-marchio che questo modulo rende obsoleti su Printify.
NOME = "perla-combined-logo.png"

# ==========================================================================
# QUALI MOTIVI IL MARCHIO CE L'HANNO GIA'
# ==========================================================================
# Aggiungere il marchio a un motivo che lo contiene gia' non e' un dettaglio:
# e' il difetto "marchio doppio" gia' corretto una volta su bandane e
# medagliette (commit 962ade7). Quindi si compone SOLO dove manca davvero.
#
# La classificazione e' stata fatta GUARDANDO i quindici nativi europei a
# risoluzione piena -- provino d'insieme e poi zoom centrale a 1240 px sui
# dubbi -- e non leggendo i nomi, che su questo progetto mentono
# regolarmente: bandana-damasco-reale.jpg non e' un damasco, e' un ramo
# d'ulivo su crema senza un filo di marchio.
#
# Tre modi in cui un nativo porta gia' il marchio, tutti e tre validi:
#   medaglione singolo   art-deco-rosa, diamanti, onde-dorate, paisley-cammeo
#   scritta ripetuta     barocco, damasco-diamante, erbario, floreale-elegante,
#                        ghirigori, onde, paisley-rosa, ramo-dulivo
#
# Chi rivede questa tabella rifaccia lo stesso: guardi le immagini.
# ==========================================================================
# I NATIVI CON UN MEDAGLIONE SOLO: il marchio c'e', ma non si puo' contarci
# ==========================================================================
# Quattro nativi portano UN SOLO medaglione "Perla Italia", sempre nello
# stesso punto: centro a x=0,81 y=0,75 (misurato su tutti e quattro cercando
# la finestra a saturazione massima -- il picco sta a 7-40 volte la media, non
# e' un'interpretazione).
#
# "Il nativo ha il marchio" e' vero per il nativo INTERO e falso per un suo
# ritaglio. Sulla medaglietta "Green Geometric" (area 810x900, ritagliata da
# bandana-diamanti) quel medaglione e' finito sul bordo ed e' stato tagliato
# dal tondo: si vedeva una falce d'oro a destra e nient'altro. Guardato il
# mockup vero, non dedotto. Affiancando il nativo il medaglione si ripete a
# caso e a volte cade sulla punta della bandana, dove viene mozzato.
#
# Quindi: si RITAGLIA via il medaglione dal nativo, e il marchio lo si compone
# noi dove deve stare. Il ritaglio tiene i due terzi sinistri a piena altezza,
# che e' la porzione piu' grande che lo esclude di sicuro.
NATIVI_CON_MEDAGLIONE = {
    "bandana-art-deco-rosa.jpg",
    "bandana-diamanti.jpg",
    "bandana-onde-dorate.jpg",
    "bandana-paisley-cammeo.jpg",
}

# Il medaglione, in frazione del nativo: centro (0,81 - 0,75), largo circa 0,18.
MEDAGLIONE = (0.72, 0.66, 0.90, 0.84)
# Il ritaglio che lo esclude, in frazione del nativo (sinistra, alto, destra, basso).
RITAGLIO_SENZA_MEDAGLIONE = (0.0, 0.0, 0.66, 1.0)


def esclude_il_medaglione(ritaglio, dimensioni):
    """Vero se questo ritaglio (in pixel) lascia gia' fuori il medaglione.

    Serve per non ritagliare due volte: bandana-onde-dorate ha gia' un
    ritaglio esplicito a (0, 0, 4125, 1850) messo in una tornata precedente,
    e 1850 sta ben sopra il medaglione, che comincia a 0,66 di 4125 = 2722.
    """
    if not ritaglio:
        return False
    w, h = dimensioni
    _, _, destra, basso = ritaglio
    return destra <= MEDAGLIONE[0] * w or basso <= MEDAGLIONE[1] * h


NATIVI_SENZA_MARCHIO = {
    "bandana-damasco-reale.jpg",   # rami d'ulivo verdi su crema, niente scritte
    "bandana-ulivo-nuovo.jpg",     # foglie tenui su crema, niente scritte
    "bandana-ulivo.jpg",           # damasco bordeaux e oro pieno, niente scritte
}


def serve(nativo):
    """Vero se a questo motivo il marchio va aggiunto.

    I motivi GEOMETRICI sono disegnati da perla-motivi-nuovi.py e non hanno
    marchio per costruzione: si passa None e la risposta e' sempre si'.
    """
    if not nativo:
        return True
    base = os.path.basename(nativo)
    # I quattro col medaglione singolo contano come "senza marchio": il loro
    # viene ritagliato via, perche' su un ritaglio non ci si puo' contare.
    return base in NATIVI_SENZA_MARCHIO or base in NATIVI_CON_MEDAGLIONE

LIVELLI_OBSOLETI = ("LOGO PERLA - Copia.PNG", "logo-full.png",
                    "perla-combined-logo.png", "v2-01-logo-centrale.png",
                    "v3-square-coaster-logo.png")


# ==========================================================================
# GEOMETRIA PER TIPO DI PRODOTTO
# ==========================================================================
# altezza:   quanto e' alto il marchio, in frazione del LATO CORTO dell'area
# centro:    dove sta il suo centro, in frazione dell'area (solo se ripeti=0)
# ripeti:    quante volte lungo la lunghezza; 0 = una volta sola, al centro.
#            Serve sui prodotti a nastro (collare, guinzaglio, fascia della
#            ciotola), dove un marchio solo su un metro di fettuccia non si
#            vedrebbe mai -- ed e' anche come era disegnato l'artwork
#            originale, che sul collare ripeteva la cartella quattro volte.
# forma:     come e' fatto il prodotto davvero, per l'area sicura.
#
# I NUMERI VANNO GUARDATI, NON CREDUTI. Sono la prima proposta, tarata sulle
# proporzioni dell'artwork originale (sulla bandana la cartella occupava circa
# un sesto del lato; sul collare si ripeteva quattro volte per riga). Prima di
# applicarli a settanta prodotti se ne fa UNO per tipo e si guarda il mockup:
# e' la stessa regola scritta in perla-usa-carica-stampe.py.
GEOMETRIA = {
    "collare":     {"altezza": 0.72, "ripeti": 8,  "forma": "rettangolo"},
    "guinzaglio":  {"altezza": 0.72, "ripeti": 12, "forma": "rettangolo"},
    "ciotola":     {"altezza": 0.55, "ripeti": 6,  "forma": "rettangolo"},
    "bandana":     {"altezza": 0.34, "ripeti": 0, "centro": (0.50, 0.42),
                    "forma": "triangolo"},
    "medaglietta": {"altezza": 0.62, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "cerchio"},
    "cuccia":      {"altezza": 0.22, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "rettangolo"},
    "tappetino":   {"altezza": 0.22, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "rettangolo"},
}

# Quanto bordo dell'area non e' tessuto visibile. Sulla cuccia il bordo si
# arrotola sotto (e' la ragione per cui il marchio vecchio finiva nella parte
# nascosta, vedi perla-usa-marchio.py); sugli altri e' margine di taglio.
MARGINE = {"cuccia": 0.10, "tappetino": 0.06}
MARGINE_PREDEFINITO = 0.04


def _marchio(percorso=None):
    im = Image.open(percorso or MARCHIO)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    # Il file ha 120 px di trasparente per lato: ritagliarlo significa che
    # "altezza 0,72" e' 0,72 di marchio VISIBILE e non di aria intorno.
    riquadro = im.getchannel("A").getbbox()
    return im.crop(riquadro) if riquadro else im


def area_sicura(tipo, area):
    """Il rettangolo dentro cui il marchio si vede davvero, in pixel.

    Torna (sinistra, alto, destra, basso). Per triangolo e cerchio e' il piu'
    grande rettangolo utile inscritto nella forma, non il rettangolo di stampa.
    """
    aw, ah = area
    forma = GEOMETRIA.get(tipo, {}).get("forma", "rettangolo")
    m = MARGINE.get(tipo, MARGINE_PREDEFINITO)

    if forma == "cerchio":
        # cerchio inscritto, poi il quadrato inscritto nel cerchio: e' il
        # riquadro dentro cui qualunque cosa resta sulla medaglietta
        r = min(aw, ah) / 2.0 * (1 - m)
        lato = r * 1.41421356 / 2.0
        return (aw / 2.0 - lato, ah / 2.0 - lato, aw / 2.0 + lato, ah / 2.0 + lato)

    if forma == "triangolo":
        # Bandana: base in alto, punta in basso. A quota y la stoffa e' larga
        # (1 - y) della base. Si prende la fascia alta 20%-60%, dove il
        # triangolo e' ancora largo piu' di meta' -- sotto, la punta stringe in
        # fretta ed e' li' che il marchio vecchio veniva tagliato.
        y0, y1 = 0.20 * ah, 0.60 * ah
        largo = (1 - 0.60) * aw * (1 - m)   # larghezza alla quota piu' stretta
        return (aw / 2.0 - largo / 2.0, y0, aw / 2.0 + largo / 2.0, y1)

    return (aw * m, ah * m, aw * (1 - m), ah * (1 - m))


def riquadri(tipo, area, marchio_wh):
    """Dove va disegnato il marchio: una lista di (sinistra, alto, larghezza, altezza).

    Solleva ValueError se non ci sta nell'area sicura: meglio fermarsi qui che
    scoprire dal cliente che il marchio e' mozzato.
    """
    if tipo not in GEOMETRIA:
        raise ValueError("tipo senza geometria del marchio: %r (previsti: %s)"
                         % (tipo, ", ".join(sorted(GEOMETRIA))))
    g = GEOMETRIA[tipo]
    aw, ah = area
    mw, mh = marchio_wh

    alto_px = g["altezza"] * min(aw, ah)
    largo_px = alto_px * mw / float(mh)
    # mai ingrandito oltre la sua risoluzione vera
    if largo_px > mw:
        largo_px = float(mw)
        alto_px = largo_px * mh / float(mw)

    s, a, d, b = area_sicura(tipo, area)
    if largo_px > (d - s) or alto_px > (b - a):
        raise ValueError(
            "il marchio (%dx%d px) non entra nell'area sicura di %s "
            "(%dx%d px su un'area %dx%d): abbassa GEOMETRIA[%r]['altezza']."
            % (largo_px, alto_px, tipo, d - s, b - a, aw, ah, tipo))

    if not g.get("ripeti"):
        cx, cy = g.get("centro", (0.5, 0.5))
        cx, cy = cx * aw, cy * ah
        # riportato dentro l'area sicura se il centro chiesto lo porterebbe fuori
        cx = min(max(cx, s + largo_px / 2), d - largo_px / 2)
        cy = min(max(cy, a + alto_px / 2), b - alto_px / 2)
        return [(cx - largo_px / 2, cy - alto_px / 2, largo_px, alto_px)]

    n = int(g["ripeti"])
    cy = (a + b) / 2.0
    passo = (d - s) / float(n)
    fuori = []
    for i in range(n):
        cx = s + passo * (i + 0.5)
        fuori.append((cx - largo_px / 2, cy - alto_px / 2, largo_px, alto_px))
    return fuori


# Oro del marchio: serve per decidere se sul fondo si vedrebbe o no.
ORO = (214, 178, 96)
# Sotto questo scarto di luminosita' fra marchio e fondo, il marchio sparisce.
# Misurato sul caso che ha fatto nascere questa funzione: la bandana
# "laurel navy" ha fondo senape (luminosita' 176) e l'oro sta a 178 -- scarto
# 2 su 255, e infatti della scritta "Perla" non si vedeva niente, restava solo
# la parola "Italia" scura che sembrava capitata li' per sbaglio.
CONTRASTO_MINIMO = 60


def _luminosita(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _cartella(base, riquadro, margine=0.14, raggio=0.10):
    """Disegna dietro il marchio una cartella che lo renda leggibile.

    PERCHE'
    Il file del marchio e' oro su trasparente: nato per fondi scuri. Su un
    fondo chiaro o dorato -- e ce ne sono, il damasco ritinto in senape e' uno
    -- l'oro sull'oro non si vede, e del marchio resta solo la parola scura in
    basso. Non e' un difetto del file: e' che manca il supporto.

    NON E' UN'INVENZIONE STILISTICA. I motivi originali di questo catalogo
    mettono gia' il marchio dentro una cartella: ovale su paisley-rosa, tonda
    su ghirigori, rettangolare con bordo dorato sulla bandana damascata. Qui
    si fa la stessa cosa, prendendo il colore dal fondo che c'e' davvero
    sotto, cosi' la cartella appartiene al disegno invece di esserci appoggiata.

    Si disegna SOLO quando serve: su fondo gia' scuro il marchio si legge da
    solo e una cartella sarebbe una toppa.
    """
    s, a, largo, alto = riquadro
    px, py = largo * margine, alto * margine * 0.5
    box = (s - px, a - py, s + largo + px, a + alto + py)
    ritaglio = base.crop(tuple(round(v) for v in box)).convert("RGB")
    piccolo = ritaglio.resize((16, 16), Image.LANCZOS)
    n = 16 * 16
    medio = tuple(sum(p[i] for p in piccolo.getdata()) // n for i in range(3))

    if _luminosita(medio) < _luminosita(ORO) - CONTRASTO_MINIMO:
        return None      # fondo gia' scuro: il marchio d'oro si legge da solo

    # cartella scura ricavata dal fondo: stessa tinta, molto piu' cupa, cosi'
    # non e' un rettangolo nero appiccicato ma un'ombra dello stesso tessuto
    fondo = tuple(max(0, min(255, round(c * 0.22))) for c in medio)
    strato = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(strato)
    r = round(min(box[2] - box[0], box[3] - box[1]) * raggio)
    d.rounded_rectangle([round(v) for v in box], radius=r,
                        fill=fondo + (238,), outline=ORO + (255,),
                        width=max(2, round(largo * 0.012)))
    return strato


def componi(immagine, tipo, percorso_marchio=None):
    """Disegna il marchio sul file di stampa gia' costruito.

    Torna (immagine, riquadri_usati). I riquadri servono ai test e all'audit
    per verificare che il marchio ci sia davvero e stia dove deve, senza
    doverlo cercare a occhio dentro un file da 15600 px.
    """
    base = immagine.convert("RGBA") if immagine.mode != "RGBA" else immagine.copy()
    logo = _marchio(percorso_marchio)
    box = riquadri(tipo, base.size, logo.size)

    for s, a, largo, alto in box:
        largo, alto = max(1, round(largo)), max(1, round(alto))
        cartella = _cartella(base, (s, a, largo, alto))
        if cartella is not None:
            base.alpha_composite(cartella, (0, 0))
        # solo riduzione: riquadri() ha gia' impedito il caso contrario
        pezzo = logo.resize((largo, alto), Image.LANCZOS)
        base.alpha_composite(pezzo, (round(s), round(a)))

    return base.convert("RGB"), box


def presente(immagine, box, percorso_marchio=None, soglia=18.0):
    """Vero se nei riquadri indicati c'e' davvero il marchio.

    Confronta i pixel del file finito con il marchio ridisegnato sul fondo che
    quel file ha in quel punto. Serve al test: "il marchio c'e'" deve essere
    una misura, non una speranza -- e' esattamente il controllo che mancava
    quando bandane e medagliette sono rimaste senza.
    """
    if not box:
        return False
    logo = _marchio(percorso_marchio)
    rgb = immagine.convert("RGB")
    for s, a, largo, alto in box:
        largo, alto = max(1, round(largo)), max(1, round(alto))
        ritaglio = rgb.crop((round(s), round(a), round(s) + largo, round(a) + alto))
        pezzo = logo.resize((largo, alto), Image.LANCZOS)
        # dove il marchio e' opaco, il file finito deve somigliare al marchio
        maschera = pezzo.getchannel("A").point(lambda v: 255 if v > 200 else 0)
        if not maschera.getbbox():
            continue
        atteso = pezzo.convert("RGB")
        punti = [(p, q) for p, q, m in zip(
            ritaglio.getdata(), atteso.getdata(), maschera.getdata()) if m]
        if not punti:
            continue
        scarto = sum(abs(p[i] - q[i]) for p, q in punti for i in range(3)) / (3.0 * len(punti))
        if scarto > soglia:
            return False
    return True
