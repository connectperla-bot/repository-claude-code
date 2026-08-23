#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rifa' i file di stampa della linea americana alla risoluzione vera.

IL DIFETTO
Sui 71 prodotti Printify, 99 immagini di stampa su 172 sono sotto
risoluzione. Le cucce sono il caso estremo: la sorgente e' un'immagine da
1248x832 e l'area di stampa e' 15600x12600, quindi il disegno viene
ingrandito dodici volte. A quel punto non ha piu' bordi -- sul mockup
ingrandito si vede il motivo impastato, e in stampa si vedrebbe di piu'.

    cuccia      15600 x 12600   copertura attuale 0,04-0,06
    collare      9519 x   338   copertura attuale 0,13
    bandana      4275 x  2325   copertura attuale 0,30
    ciotola      2760 x   750
    medaglietta   810 x   900

DA DOVE ARRIVA IL RIMEDIO
Da due posti, nessuno dei quali e' un generatore di immagini (non ce n'e'
uno collegato a questo progetto):

1. I NATIVI EU. La linea europea ha gli stessi disegni a 4125x4125 --
   stessa famiglia, stessa colorazione, spesso lo stesso identico motivo.
   Verificato affiancandoli: fra la bandana USA "damask navy" e la EU
   "paisley-cammeo" lo scarto medio e' 0,61 su 255, cioe' sono la stessa
   immagine; su "onde petrolio" e' 11,9; su "medaglioni porpora" 21. Non e'
   una sostituzione: e' lo stesso disegno alla risoluzione che avrebbe
   dovuto avere fin dall'inizio.

2. IL CODICE. Le famiglie geometriche si disegnano, e disegnate non hanno
   risoluzione propria: si chiede la misura dell'area e nascono li'. Le
   funzioni stanno in perla-motivi-nuovi.py.

LA SCALA NON SI SCEGLIE A OCCHIO
Un motivo giusto su una bandana e' invisibile su un collare largo 2,5 cm.
Per i motivi disegnati la scala si ricava MISURANDO il periodo della
sorgente attuale (periodo_relativo) e riportandolo in proporzione sull'area
nuova, cosi' il disegno rifatto ha la stessa grana di quello che sostituisce.

USO
    python3 scripts/perla-usa-file-stampa.py            # costruisce e basta
    python3 scripts/perla-usa-file-stampa.py --provino  # + provino da guardare

I file finiscono in generated-designs/usa-print-files/ (ignorata da git:
sono centinaia di MB rigenerabili con un comando).
"""
import importlib.util
import os
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
NATIVI = os.path.join(RADICE, "generated-designs", "motivi-stampa", "_originali")
SORGENTI = os.path.join(RADICE, "generated-designs")
USCITA = os.path.join(RADICE, "generated-designs", "usa-print-files")


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


motivi = _modulo("perla_motivi_nuovi", os.path.join(QUI, "perla-motivi-nuovi.py"))
eu = _modulo("perla_eu", os.path.join(QUI, "perla-build-eu-print-files.py"))

# Aree di stampa reali, prese dalle varianti Printify: sempre la piu' grande
# del blueprint, perche' un file che basta alla variante grande basta anche
# alle altre, mentre il contrario no.
AREE = {
    "cuccia":      (15600, 12600),
    "collare":     (9519, 338),
    "bandana":     (4275, 2325),
    "ciotola":     (2760, 750),
    "medaglietta": (810, 900),
}


def periodo_relativo(percorso, minimo=1 / 14.0):
    """Ogni quanta parte della larghezza si ripete il motivo della sorgente.

    Serve a non inventare la scala: se il disegno di adesso si ripete ogni
    quarto di larghezza, quello rifatto deve fare lo stesso, altrimenti e'
    un altro prodotto. Torna None quando la sorgente non e' periodica (per
    esempio quando e' la fotografia di un prodotto finito invece che un
    motivo) e allora la scala va decisa a mano.
    """
    im = Image.open(percorso).convert("L")
    w, _ = im.size
    piccola = im.resize((min(w, 900), 64), Image.LANCZOS)
    px = piccola.load()
    n = piccola.width
    profilo = [sum(px[x, y] for y in range(64)) / 64.0 for x in range(n)]
    media = sum(profilo) / n
    profilo = [v - media for v in profilo]

    migliore = None
    for p in range(max(2, int(n * minimo)), n // 2):
        campioni = range(0, n - p, 3)
        scarto = sum(abs(profilo[i] - profilo[i + p]) for i in campioni) / len(list(campioni))
        if migliore is None or scarto < migliore[0]:
            migliore = (scarto, p)
    # La soglia e' larga apposta: su questi motivi lo scarto sul periodo
    # giusto sta fra 0,4 e 7,1, e sotto 6 restavano fuori proprio i due
    # geometrici che servivano. Sopra 8 non e' piu' un periodo, e' rumore.
    if migliore is None or migliore[0] > 8.0:
        return None
    return migliore[1] / float(n)


def ritinta(im, nuovo_rgb, su_scuro=True, soglia=0.50, morbidezza=0.18):
    """Cambia la tinta del FONDO lasciando stare l'ornamento.

    Serve perche' i nativi EU coprono tutte le famiglie ma non tutte le
    colorazioni: il damasco fine esiste in bordeaux e oro, e sul catalogo
    americano lo stesso damasco serve anche in blu.

    La selezione e' sulla LUMINOSITA', non sulla tinta. Provato prima con una
    rotazione della tonalita': su questi disegni non funziona, perche' il
    bordeaux (350 gradi) e l'oro (40 gradi) distano solo cinquanta gradi e
    ruotando il fondo si ruota anche l'oro, che diventa verde.

    La SOGLIA va tarata sul disegno e non lasciata a meta'. Primo tentativo a
    0,50 sul damasco bordeaux: l'oro sta fra 0,32 e 0,68 di luminosita', e'
    finito dentro la fascia morbida, e il motivo e' uscito verde. A 0,32 con
    una fascia stretta cambia solo il fondo davvero scuro. Guardare il
    risultato e' l'unico modo di saperlo.
    """
    import colorsys
    hsv = im.convert("HSV")
    h, s, v = hsv.split()
    nh, ns, _ = colorsys.rgb_to_hsv(*[c / 255.0 for c in nuovo_rgb])
    nh, ns = int(nh * 255), int(ns * 255)

    lo, hi = (soglia - morbidezza) * 255, (soglia + morbidezza) * 255
    def peso(x):
        if x <= lo: return 255 if su_scuro else 0
        if x >= hi: return 0 if su_scuro else 255
        t = (x - lo) / (hi - lo)
        return int((1 - t) * 255) if su_scuro else int(t * 255)
    maschera = v.point([peso(x) for x in range(256)])

    h2 = Image.composite(Image.new("L", im.size, nh), h, maschera)
    s2 = Image.composite(Image.new("L", im.size, ns), s, maschera)
    return Image.merge("HSV", (h2, s2, v)).convert("RGB")


def duotono(im, fondo_rgb, motivo_rgb, taglio=2):
    """Ridisegna il motivo in due soli colori, seguendo la luminosita'.

    Serve quando la colorazione nuova non e' una variante di quella vecchia
    ma il suo rovescio -- il damasco EU e' fondo scuro con ornamento chiaro,
    la cuccia "Damasco Elegante" e' fondo crema con ornamento bordeaux -- e
    anche quando lo spostamento di tinta non riesce: sul damasco bordeaux il
    fondo e l'oro si sovrappongono come luminosita', e qualunque soglia
    provata lasciava il fondo bordeaux o tingeva di verde l'oro.

    L'AUTOCONTRASTO NON E' UN OPZIONALE. Senza, il fondo del damasco (0,25 di
    luminosita') e l'oro (0,60) finiscono a un quarto e a tre quinti della
    rampa: esce tutto slavato, provato e buttato. Allargando prima la scala a
    tutto l'intervallo, il fondo diventa fondo e il motivo diventa motivo.

    Si perde la sfumatura metallica dell'oro. E' il prezzo, ed e' accettato.
    """
    from PIL import ImageOps
    grigio = ImageOps.autocontrast(im.convert("L"), cutoff=taglio)
    tavola = []
    for canale in range(3):
        tavola += [round(fondo_rgb[canale] +
                         (motivo_rgb[canale] - fondo_rgb[canale]) * (x / 255.0))
                   for x in range(256)]
    return Image.merge("RGB", (grigio, grigio, grigio)).point(tavola)


# ==========================================================================
# IL CATALOGO
# ==========================================================================
# Una riga per prodotto Printify. La chiave e' l'inizio del titolo, perche'
# i titoli su Printify sono lunghi e cambiano in coda.
#
#   ("eu",     file, ritocco, ritaglio)  -> nativo europeo a 4125, affiancato
#   ("codice", funzione, tinta, ripetizioni_in_larghezza)
#
# ritocco:  None
#           ("scuro"|"chiaro", colore, soglia)  sposta la tinta del fondo
#           ("duotono", fondo, motivo)          ribalta il contrasto
# ritaglio: None, oppure (sinistra, alto, destra, basso) sul nativo.
#           Serve perche' alcuni nativi sono FOTOGRAFIE di una bandana
#           appoggiata: hanno pieghe, ombre e a volte un angolo di tavolo.
#           Affiancate senza ritagliare, la piega si ripete in griglia --
#           visto sulle prime due cucce a medaglioni, e si notava subito.
#
# "ripetizioni" e' quante volte il motivo entra nella larghezza dell'area:
# si legge dalla sorgente attuale con periodo_relativo(), non si sceglie.

CATALOGO = {
    # ---- CUCCE (area 15600x12600, oggi copertura 0,04-0,06) --------------
    "Baroque Royal Pet Bed":
        ("eu", "bandana-barocco.jpg", None, None),
    "Vintage Damask Pet Bed":
        ("eu", "bandana-damasco-reale.jpg", None, None),
    "Luxury Paisley Plush Pet Bed":
        ("eu", "bandana-floreale-elegante.jpg", None, None),
    "Ornate Medallion Pet Bed — Luxe Purple":
        ("eu", "bandana-onde-dorate.jpg", None, (0, 0, 4125, 1850)),
    "Ornate Medallion Pet Bed — Cozy":
        ("eu", "bandana-onde-dorate.jpg", ("scuro", (16, 74, 58), 0.55, 0.10), (0, 0, 4125, 1850)),
    "Luxurious Navy Damask Pet Bed":
        ("eu", "bandana-damasco-reale.jpg", ("duotono", (18, 34, 64), (214, 178, 96)), None),
    "Perla Italy Luxury - Cuccia Damasco Elegante":
        ("eu", "bandana-damasco-reale.jpg", ("duotono", (243, 236, 226), (108, 26, 38)), None),
    "Copy of Perla Italy Luxury - Cuccia Damasco Elegante":
        ("eu", "bandana-damasco-reale.jpg", ("duotono", (243, 236, 226), (108, 26, 38)), None),
    "Geometric Gray 'Perla Italia' Rectangle Pet Bed":
        ("codice", "rombi", "grigio", 3.6),
    "Geometric Tribal Pet Bed":
        ("codice", "rombi", "nero", 3.1),
    "Personalized Pet Bed — Teal Chevron":
        ("codice", "chevron", "teal", 9.7),
    "Teal Geometric Diamond Pet Bed":
        ("codice", "tribale", "teal", 6.7),
}


# ==========================================================================
# COLLARI, BANDANE E MEDAGLIETTE: si va per SORGENTE, non per titolo
# ==========================================================================
# Sulle cucce bastava il titolo. Sugli altri no, perche' i titoli non dicono
# la verita': "Maroon Damask Dog Collar" stampa collar-olive-perla-only.jpg,
# "Vintage Toile Dog Collar" stampa collar-floral-emerald-gold-perla.jpg,
# "Brown Paisley Pet Bandana" stampa bandana-damask-navy-perla.jpg. Anche i
# nomi dei file mentono: collar-botanical-olive-gold.jpg e' un damasco
# bordeaux e oro, senza un filo di verde.
#
# Quindi la chiave e' il FILE che il prodotto stampa oggi, e l'abbinamento
# l'ho fatto GUARDANDO le venti strisce americane accanto alle ventitre
# europee, non leggendo i nomi. Chi rivede questa tabella rifaccia lo stesso:
# scripts/perla-usa-file-stampa.py --strisce rigenera il confronto.

# Il tipo di prodotto si legge dal prefisso della sorgente.
PREFISSO_TIPO = {"collar-": "collare", "bandana-": "bandana", "tag-": "medaglietta"}


def tipo_di(sorgente):
    for pre, tipo in PREFISSO_TIPO.items():
        if sorgente.startswith(pre):
            return tipo
    return None


def nome_uscita(sorgente):
    return "%s-da-%s" % (tipo_di(sorgente), os.path.splitext(sorgente)[0])


PER_SORGENTE = {
    # --- collari: nativo EU 7169x315, area 9519x338 -----------------------
    "collar-baroque-navy-gold-perla.jpg":          "collare-barocco.jpg",
    "collar-baroque-perla-only.jpg":               "collare-barocco-floreale.jpg",
    "collar-botanical-olive-gold.jpg":             "collare-damasco.jpg",
    "collar-damask-burgundy-gold-perla.jpg":       "collare-damasco.jpg",
    "collar-damask-gold-burgundy.jpg":             "collare-damasco-classico.jpg",
    # collare-damasco-verde e' quasi tutto margine: la banda colorata sta
    # fra la riga 104 e la 218 di 315, e il taglio automatico non la trova
    # perche' li' il margine E' la maggioranza dell'immagine, quindi anche
    # la mediana e' chiara. Ritaglio a mano, misurato.
    "collar-damask-perla-only.jpg":                ("collare-damasco-verde.jpg", (0, 104, 7169, 219)),
    "collar-floral-emerald-gold-perla.jpg":        "collare-floreale.jpg",
    "collar-geometric-black-rose-perla.jpg":       "collare-geometrico-minimal.jpg",
    "collar-geometric-perla-only.jpg":             "collare-geometrico.jpg",
    "collar-herringbone-charcoal-silver-perla.jpg": "collare-medaglioni.jpg",
    "collar-medallion-purple-gold-perla.jpg":      "collare-astratto.jpg",
    "collar-modern-abstract-silver-perla.jpg":     "collare-onde-geometriche.jpg",
    "collar-modern-geometric-rose-perla.jpg":      "collare-minimal.jpg",
    "collar-modern-herringbone-teal-perla.jpg":    "collare-chevron.jpg",
    "collar-modern-minimal-charcoal-silver-perla.jpg": "collare-minimal.jpg",
    "collar-modern-wave-navy-gold-perla.jpg":      "collare-onda.jpg",
    "collar-olive-perla-only.jpg":                 "collare-ramo-dulivo.jpg",
    "collar-olive-sage-gold-perla.jpg":            "collare-foglia-di-salvia.jpg",
    "collar-paisley-ivory-rose-perla.jpg":         "collare-paisley.jpg",
    "collar-toile-cream-burgundy-perla.jpg":       "collare-toile.jpg",

    # --- bandane: nativo EU 4125x4125, area 4275x2325 ---------------------
    "bandana-baroque-navy-perla.jpg":              "bandana-barocco.jpg",
    "bandana-laurel-navy-perla.jpg":               ("bandana-damasco-reale.jpg",
                                                    ("duotono", (18, 34, 64), (214, 178, 96)), None),
    "bandana-botanical-emerald-new-perla.jpg":     "bandana-damasco-reale.jpg",
    "bandana-damask-burgundy-perla2.jpg":          "bandana-damasco-reale.jpg",
    "bandana-damask-burgundy-perla.jpg":           "bandana-ulivo-nuovo.jpg",
    "bandana-botanical-emerald-perla.jpg":         "bandana-erbario.jpg",
    "bandana-damask-burgundy-new-perla.jpg":       "bandana-damasco-diamante.jpg",
    "bandana-botanical-sage-perla.jpg":            "bandana-ulivo.jpg",
    "bandana-olive-sage-perla.jpg":                "bandana-ramo-dulivo.jpg",
    "bandana-damask-navy-perla.jpg":               "bandana-paisley-cammeo.jpg",
    "bandana-floral-emerald-perla.jpg":            "bandana-floreale-elegante.jpg",
    "bandana-paisley-ivory-perla.jpg":             "bandana-paisley-rosa.jpg",
    "bandana-geometric-black-rose-perla.jpg":      "bandana-art-deco-rosa.jpg",
    "bandana-geometric-scroll-perla.jpg":          "bandana-ghirigori.jpg",
    "bandana-geometric-silver-perla.jpg":          "bandana-diamanti.jpg",
    # stessa geometria a rombi dei "diamanti", ma oro su verde scuro invece
    # che argento su nero: senza il duotono uscirebbero due prodotti identici
    "bandana-artdeco-charcoal-perla.jpg":          ("bandana-diamanti.jpg",
                                                    ("duotono", (34, 36, 30), (196, 162, 92)), None),
    "bandana-medallion-purple-perla.jpg":          ("bandana-onde-dorate.jpg", None, (0, 0, 4125, 1850)),
    "bandana-wave-teal-perla.jpg":                 "bandana-onde.jpg",
    "bandana-paisley-ivory-rose-perla.jpg":        ("bandana-ulivo-nuovo.jpg",
                                                    ("duotono", (16, 54, 42), (206, 174, 104)), None),
    "bandana-perla-only.jpg":                      ("bandana-ulivo-nuovo.jpg",
                                                    ("duotono", (18, 48, 38), (198, 168, 100)), None),

    # --- medagliette: area 810x900, il nativo si riduce e si ritaglia ------
    "tag-paisley-burgundy-perla.jpg":              "bandana-paisley-cammeo.jpg",
    "tag-geometric-silver-perla.jpg":              "bandana-diamanti.jpg",
    "tag-geometric-emerald-perla.jpg":             "bandana-damasco-diamante.jpg",
    "tag-floral-emerald-perla.jpg":                "bandana-erbario.jpg",
    "tag-damask-purple-perla.jpg":                 ("bandana-onde-dorate.jpg", None, (0, 0, 4125, 1850)),
    "tag-perla-only.jpg":                          "bandana-barocco.jpg",
}


# ==========================================================================
# COSTRUZIONE
# ==========================================================================

def _sorgente_eu(nome, ritocco, ritaglio, temporanei):
    """Percorso del nativo EU, gia' ritagliato e ritinto se serve."""
    percorso = os.path.join(NATIVI, nome)
    if not os.path.exists(percorso):
        raise SystemExit("nativo mancante: " + percorso)
    if not ritocco and not ritaglio:
        return percorso

    os.makedirs(temporanei, exist_ok=True)
    firma = [os.path.splitext(nome)[0]]
    if ritaglio:
        firma.append("r" + "-".join(str(v) for v in ritaglio))
    if ritocco:
        firma.append("-".join(str(v) for v in ritocco[:1]) +
                     "-".join(str(c) for parte in ritocco[1:] for c in
                              (parte if isinstance(parte, tuple) else (parte,))))
    fuori = os.path.join(temporanei, "-".join(firma).replace(".", "_") + ".jpg")
    if os.path.exists(fuori):
        return fuori

    im = Image.open(percorso).convert("RGB")
    if ritaglio:
        im = im.crop(ritaglio)
    if ritocco:
        modo = ritocco[0]
        if modo == "duotono":
            im = duotono(im, ritocco[1], ritocco[2])
        else:
            soglia = ritocco[2] if len(ritocco) > 2 else 0.50
            morbidezza = ritocco[3] if len(ritocco) > 3 else 0.08
            im = ritinta(im, ritocco[1], su_scuro=(modo == "scuro"),
                         soglia=soglia, morbidezza=morbidezza)
    im.save(fuori, quality=96, subsampling=0)
    return fuori


def _taglia_margini(percorso, temporanei, salto=40):
    """Toglie le fasce di margine ai bordi della sorgente.

    Alcuni nativi EU sono stati esportati con un bordo: collare-damasco-
    verde.jpg ha una striscia chiara sopra e sotto. Affiancato cosi', il
    collare esce con due righe pallide per tutta la lunghezza -- non e' un
    difetto di risoluzione, e' un difetto e basta, e si vede in stampa.

    NON si puo' usare una soglia assoluta tipo "piu' chiaro di 245": quel
    margine sta a 241, e abbassando la soglia si mangerebbero i disegni su
    fondo crema (lino, paisley avorio), che sono chiari dappertutto. Il
    confronto giusto e' RELATIVO: si taglia una riga di bordo solo se e'
    piu' chiara della MEDIANA delle righe di almeno `salto`. Su un fondo
    crema uniforme la mediana e' chiara quanto il bordo e non si taglia
    niente; dove c'e' davvero un margine, lo scarto e' netto.
    """
    im = Image.open(percorso).convert("RGB")
    grigio = im.convert("L")
    w, h = grigio.size
    campione = grigio.resize((min(w, 600), min(h, 600)), Image.LANCZOS)
    px = campione.load()
    cw, ch = campione.size

    righe = [sum(px[x, y] for x in range(0, cw, 3)) / len(range(0, cw, 3)) for y in range(ch)]
    colonne = [sum(px[x, y] for y in range(0, ch, 3)) / len(range(0, ch, 3)) for x in range(cw)]
    mediana_r = sorted(righe)[ch // 2]
    mediana_c = sorted(colonne)[cw // 2]

    alto = 0
    while alto < ch // 4 and righe[alto] > mediana_r + salto: alto += 1
    basso = ch - 1
    while basso > ch * 3 // 4 and righe[basso] > mediana_r + salto: basso -= 1
    sinistra = 0
    while sinistra < cw // 4 and colonne[sinistra] > mediana_c + salto: sinistra += 1
    destra = cw - 1
    while destra > cw * 3 // 4 and colonne[destra] > mediana_c + salto: destra -= 1
    if (alto, sinistra) == (0, 0) and (basso, destra) == (ch - 1, cw - 1):
        return percorso

    box = (round(sinistra * w / cw), round(alto * h / ch),
           round((destra + 1) * w / cw), round((basso + 1) * h / ch))
    os.makedirs(temporanei, exist_ok=True)
    fuori = os.path.join(temporanei, "%s-tagliata.jpg" %
                         os.path.splitext(os.path.basename(percorso))[0])
    ritagliata = im.crop(box)
    if not os.path.exists(fuori):
        ritagliata.save(fuori, quality=96, subsampling=0)
    print("   margini tolti da %s: %s -> %s" % (
        os.path.basename(percorso), im.size, ritagliata.size))
    return fuori


def _riquadro_pulito(percorso, temporanei, quota=0.02, minimo=0.55):
    """Restringe il riquadro finche' sui bordi non c'e' piu' bianco.

    _taglia_margini() lavora per righe e colonne intere, quindi prende le
    fasce ma non gli ANGOLI. E diversi nativi EU sono fotografie di una
    bandana appoggiata storta: hanno un triangolo di tavolo bianco in un
    angolo. Affiancati, quel triangolo si ripete su tutta la cuccia -- si
    vedeva sulle olive verdi e sui ghirigori viola.

    Il bianco si riconosce in modo RELATIVO, come nell'altra funzione: piu'
    chiaro della mediana di 45 E sopra 235 in assoluto. Cosi' un disegno su
    fondo crema (lino sta a 234 di mediana) non viene toccato, perche' li'
    non c'e' niente che superi la mediana di 45.

    Non si scende sotto il 55% del lato: se per togliere il bianco bisogna
    buttare meta' immagine, il nativo e' sbagliato e va cambiato, non
    ritagliato.
    """
    im = Image.open(percorso).convert("RGB")
    w, h = im.size
    c = im.convert("L").resize((min(w, 400), min(h, 400)), Image.LANCZOS)
    px = c.load()
    cw, ch = c.size
    tutti = sorted(px[x, y] for x in range(0, cw, 2) for y in range(0, ch, 2))
    mediana = tutti[len(tutti) // 2]
    soglia = max(235, mediana + 45)

    x0, y0, x1, y1 = 0, 0, cw, ch
    for _ in range(cw):
        def frazione(punti):
            return sum(1 for v in punti if v > soglia) / max(1, len(punti))
        alto = frazione([px[x, y0] for x in range(x0, x1)])
        basso = frazione([px[x, y1 - 1] for x in range(x0, x1)])
        sin = frazione([px[x0, y] for y in range(y0, y1)])
        des = frazione([px[x1 - 1, y] for y in range(y0, y1)])
        peggio = max(alto, basso, sin, des)
        if peggio <= quota:
            break
        if (x1 - x0) < cw * minimo or (y1 - y0) < ch * minimo:
            break
        if peggio == alto: y0 += 1
        elif peggio == basso: y1 -= 1
        elif peggio == sin: x0 += 1
        else: x1 -= 1

    if (x0, y0, x1, y1) == (0, 0, cw, ch):
        return percorso
    box = (round(x0 * w / cw), round(y0 * h / ch), round(x1 * w / cw), round(y1 * h / ch))
    os.makedirs(temporanei, exist_ok=True)
    fuori = os.path.join(temporanei, "%s-pulita.jpg" %
                         os.path.splitext(os.path.basename(percorso))[0])
    dentro = im.crop(box)
    if not os.path.exists(fuori):
        dentro.save(fuori, quality=96, subsampling=0)
    print("   angoli tolti da %s: %s -> %s" % (
        os.path.basename(percorso), im.size, dentro.size))
    return fuori


def _porta_all_altezza(percorso, altezza, temporanei):
    """Se la sorgente e' poco piu' bassa dell'area, la si allunga fino a
    combaciare invece di affiancare un secondo giro.

    Sui collari il nativo EU e' alto 315 e l'area 338: costruisci() li
    affianca anche in verticale, e sul collare -- che e' alto 2,5 cm --
    resta una giunzione orizzontale a tre quarti d'altezza, con mezza fila
    di motivo sotto. Visto sul provino delle venti strisce. Portare la
    sorgente a 338 vuol dire ingrandirla del 7%: non e' niente, e la
    giunzione sparisce del tutto.

    Sotto l'80% dell'altezza non si fa: li' ingrandire tornerebbe a essere
    il difetto che stiamo togliendo, e conviene affiancare.
    """
    im = Image.open(percorso)
    if not (altezza * 0.80 <= im.height < altezza):
        return percorso
    os.makedirs(temporanei, exist_ok=True)
    fuori = os.path.join(temporanei, "%s-h%d.jpg" % (
        os.path.splitext(os.path.basename(percorso))[0], altezza))
    if not os.path.exists(fuori):
        larghezza = round(im.width * altezza / im.height)
        im.convert("RGB").resize((larghezza, altezza), Image.LANCZOS).save(
            fuori, quality=96, subsampling=0)
    return fuori


def costruisci(voce, tipo, temporanei):
    """Un file di stampa alla misura esatta dell'area, senza ingrandire nulla."""
    larghezza, altezza = AREE[tipo]
    if voce[0] == "eu":
        _, nome, ritocco, ritaglio = voce
        percorso = _sorgente_eu(nome, ritocco, ritaglio, temporanei)
        percorso = _taglia_margini(percorso, temporanei)
        percorso = _riquadro_pulito(percorso, temporanei)
        percorso = _porta_all_altezza(percorso, altezza, temporanei)
        # costruisci() affianca i tasselli dritti (mai specchiati: questi
        # motivi contengono la scritta "PERLA ITALIA") e dissolve le
        # giunzioni. E' la stessa funzione che produce la linea EU.
        return eu.costruisci(percorso, larghezza, altezza, trim=6, feather=180)

    _, funzione, tinta, ripetizioni = voce
    passo = int(round(larghezza / float(ripetizioni)))
    fn = motivi.GEOMETRICI[funzione.capitalize()]
    return motivi.tessitura(fn(larghezza, altezza, passo, motivi.PALETTE[tinta]))


def main():
    provino = "--provino" in sys.argv
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    temporanei = os.path.join(USCITA, "_ritinti")
    os.makedirs(USCITA, exist_ok=True)

    fatti = []
    for sorgente, nativo in PER_SORGENTE.items():
        if solo and not any(x.lower() in sorgente.lower() for x in solo):
            continue
        tipo = tipo_di(sorgente)
        ritocco = ritaglio = None
        if isinstance(nativo, tuple):
            if len(nativo) == 2:
                nativo, ritaglio = nativo
            else:
                nativo, ritocco, ritaglio = nativo
        fuori = os.path.join(USCITA, nome_uscita(sorgente) + ".jpg")
        if os.path.exists(fuori):
            fatti.append((sorgente, fuori, Image.open(fuori).size, "eu"))
            continue
        im = costruisci(("eu", nativo, ritocco, ritaglio), tipo, temporanei)
        im.save(fuori, quality=92, subsampling=0)
        fatti.append((sorgente, fuori, im.size, "eu"))
        print("%-52s %5dx%-5d %-7s %.1f MB" % (
            sorgente[:52], im.size[0], im.size[1], tipo, os.path.getsize(fuori) / 1e6))

    for titolo, voce in CATALOGO.items():
        if solo and not any(s.lower() in titolo.lower() for s in solo):
            continue
        tipo = "cuccia"      # per ora il catalogo copre le cucce
        im = costruisci(voce, tipo, temporanei)
        nome = titolo.lower().replace(" ", "-").replace("'", "").replace("—", "")
        nome = "-".join(p for p in nome.split("-") if p)[:60]
        fuori = os.path.join(USCITA, "%s-%s.jpg" % (tipo, nome))
        im.save(fuori, quality=92, subsampling=0)
        fatti.append((titolo, fuori, im.size, voce[0]))
        print("%-52s %5dx%-5d %-7s %.1f MB" % (
            titolo[:52], im.size[0], im.size[1], voce[0],
            os.path.getsize(fuori) / 1e6))

    if provino and fatti:
        lato = 420
        colonne = 4
        righe = (len(fatti) + colonne - 1) // colonne
        sheet = Image.new("RGB", (colonne * lato, righe * (lato + 18)), "white")
        from PIL import ImageDraw
        d = ImageDraw.Draw(sheet)
        for i, (titolo, f, dim, via) in enumerate(fatti):
            im = Image.open(f).convert("RGB")
            h = round(lato * dim[1] / dim[0])
            x, y = (i % colonne) * lato, (i // colonne) * (lato + 18)
            sheet.paste(im.resize((lato, h), Image.LANCZOS), (x, y))
            d.text((x + 4, y + h + 2), titolo[:56], fill="black")
        sheet.save(os.path.join(USCITA, "_provino.jpg"), quality=90)
        print("\nprovino in", os.path.join(USCITA, "_provino.jpg"))

    print("\n%d file di stampa in %s" % (len(fatti), USCITA))


if __name__ == "__main__":
    main()
