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
    python3 scripts/perla-usa-file-stampa.py --rifai    # rifa' anche i gia' fatti
    python3 scripts/perla-usa-file-stampa.py --collari  # include i collari (fermi)

Da ROUND 47 esce UN FILE PER MISURA DI VARIANTE, non uno per prodotto: il
nome porta il suffisso <larghezza>x<altezza>. Il perche' e' scritto sopra
TIPI, qui sotto.

I file finiscono in generated-designs/usa-print-files/ (ignorata da git:
sono centinaia di MB rigenerabili con un comando).
"""
import importlib.util
import json
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
aree = _modulo("aree_stampa", os.path.join(QUI, "aree-stampa.py"))
marchio = _modulo("marchio", os.path.join(QUI, "marchio.py"))

# ROUND 47 -- "un file che basta alla variante grande basta anche alle altre"
# era FALSO, ed e' costato l'intero catalogo.
#
# Qui c'era un dizionario AREE con UNA misura per tipo, sempre la piu' grande
# del blueprint. Il ragionamento sembra solido e non lo e': su Printify
# `scale` e' la larghezza come frazione dell'AREA, quindi lo stesso file su
# un'area di proporzioni diverse non si adatta, sfora o lascia vuoto. E le
# varianti hanno proporzioni diverse davvero:
#
#     collare S 5764x229 (25,2:1) contro XL 9519x338 (28,2:1)
#     cuccia 28"x18" 8850x5850 (1,51:1) contro 50"x40" 15600x12600 (1,24:1)
#
# Misurato con aree-stampa.py sui prodotti veri: il file XL sul collare M
# lascia il 24% di fettuccia BIANCA, il file 50"x40" sulla cuccia 28"x18"
# TAGLIA il 18% del disegno. Nessuno dei due si vede sulla variante per cui il
# file era stato costruito, ed e' per questo che sono rimasti in catalogo.
#
# Ora si costruisce UN FILE PER MISURA, e print_areas di Printify ne prende
# una voce per gruppo di varianti (vedi perla-usa-carica-stampe.py).
#
# blueprint e print provider sono gli stessi di render.yaml e di
# config/printify.env.example: le misure si leggono da printify-blueprints/,
# non si scrivono a mano.
TIPI = {
    "cuccia":      (419, 10),
    "collare":     (784, 93),
    "bandana":     (562, 70),
    "ciotola":     (570, 70),
    "medaglietta": (566, 70),
    "tappetino":   (855, 70),
}

_MISURE = {}


def misure(tipo, token=None):
    """Le misure di stampa distinte di questo tipo di prodotto, dalla piu'
    grande alla piu' piccola. Una per file da costruire."""
    if tipo not in _MISURE:
        bp, pr = TIPI[tipo]
        _MISURE[tipo] = [g["misura"] for g in aree.gruppi(aree.varianti(bp, pr, token))]
    return _MISURE[tipo]


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

# Il prefisso funziona per i file nati in questo progetto. Qualcuno pero' e'
# arrivato da fuori e non segue nessuna convenzione: si dichiara qui, invece
# di piegare la regola generale su un caso singolo.
TIPO_ESPLICITO = {"PINATA DOLIVO.jpg": "bandana"}


def tipo_di(sorgente):
    if sorgente in TIPO_ESPLICITO:
        return TIPO_ESPLICITO[sorgente]
    for pre, tipo in PREFISSO_TIPO.items():
        if sorgente.startswith(pre):
            return tipo
    return None


def nome_uscita(sorgente, misura=None):
    """Il nome del file costruito per questa sorgente e questa misura.

    La misura entra nel nome perche' da ROUND 47 ce n'e' uno per ogni
    proporzione di variante: senza il suffisso, il file della cuccia 28"x18"
    sovrascriverebbe quello della 50"x40" e si tornerebbe al difetto di prima
    senza accorgersene.
    """
    base = "%s-da-%s" % (tipo_di(sorgente), os.path.splitext(sorgente)[0])
    return base if misura is None else "%s-%dx%d" % (base, misura[0], misura[1])


def nome_catalogo(titolo, misura=None):
    """Come nome_uscita(), ma per le voci del CATALOGO (chiave = titolo)."""
    nome = titolo.lower().replace(" ", "-").replace("'", "").replace("\u2014", "")
    nome = "-".join(p for p in nome.split("-") if p)[:60]
    return nome if misura is None else "%s-%dx%d" % (nome, misura[0], misura[1])


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
    # ROUND 47 -- "Olive Branch Pet Bandana" stampava PINATA DOLIVO.jpg a
    # scale 0,22 e y=0,74: un decoro singolo su bandana bianca, con il 91%
    # dell'area vuoto e nessun marchio. Era rimasta fuori da tutte le tornate
    # precedenti perche' il suo livello non somigliava a niente di conosciuto.
    # bandana-ulivo-nuovo e' foglie d'ulivo tenui su crema, cioe' il nativo
    # che corrisponde davvero al nome del prodotto, ed e' fra i tre senza
    # marchio: quindi glielo compone marchio.py.
    "PINATA DOLIVO.jpg":                           "bandana-ulivo-nuovo.jpg",

    # --- medagliette: area 810x900, il nativo si riduce e si ritaglia ------
    "tag-paisley-burgundy-perla.jpg":              "bandana-paisley-cammeo.jpg",
    "tag-geometric-silver-perla.jpg":              "bandana-diamanti.jpg",
    "tag-geometric-emerald-perla.jpg":             "bandana-damasco-diamante.jpg",
    "tag-floral-emerald-perla.jpg":                "bandana-erbario.jpg",
    "tag-damask-purple-perla.jpg":                 ("bandana-onde-dorate.jpg", None, (0, 0, 4125, 1850)),
    "tag-perla-only.jpg":                          "bandana-barocco.jpg",
}


# ==========================================================================
# GLI ARTWORK CHE NON VANNO SOSTITUITI, SOLO RIMESSI IN SQUADRA
# ==========================================================================
# Otto medagliette stampano ancora il loro artwork originale, quadrato a
# 1024x1024, su un'area 810x900. Il file copre la larghezza e lascia il 10%
# di altezza vuota: e' la "fascia vuota" che l'audit conta su otto prodotti.
#
# Qui NON serve cambiare disegno. L'artwork e' gia' quello scelto, porta gia'
# il marchio dentro (sono tutti "-perla.jpg", la convenzione descritta in
# perla-usa-marchio.py) e 1024 px bastano per un'area di 810x900: si RITAGLIA
# alla proporzione giusta e si riduce. Nessun ingrandimento, nessuna scelta di
# immagine presa al posto della titolare.
#
# La medaglietta e' tonda e il ritaglio e' centrato: quello che si perde sono
# i bordi, che sul prodotto finito sono fuori dal cerchio comunque.
DA_ARTWORK = {
    "tag-baroque-purple-perla.jpg":        "medaglietta",
    "tag-border-rose-perla.jpg":           "medaglietta",
    "tag-central-rose-perla.jpg":          "medaglietta",
    "tag-damask-burgundy-perla.jpg":       "medaglietta",
    "tag-floral-burgundy-perla.jpg":       "medaglietta",
    "tag-geometric-navy-silver-perla.jpg": "medaglietta",
    "tag-medallion-emerald-perla.jpg":     "medaglietta",
    "tag-olive-sage-perla.jpg":            "medaglietta",
}


# ==========================================================================
# COSTRUZIONE
# ==========================================================================

def _sorgente_eu(nome, ritocco, ritaglio, temporanei):
    """Percorso del nativo EU, gia' ritagliato e ritinto se serve."""
    percorso = os.path.join(NATIVI, nome)
    if not os.path.exists(percorso):
        raise SystemExit("nativo mancante: " + percorso)

    # Quattro nativi hanno UN SOLO medaglione "Perla Italia", sempre a
    # x=0,81 y=0,75. Affiancati o ritagliati, quel medaglione finisce dove
    # capita -- sulla medaglietta "Green Geometric" e' arrivato sul bordo ed e'
    # stato tagliato dal tondo, lasciando una falce d'oro senza senso. Si
    # ritaglia via, e il marchio lo compone marchio.py dove deve stare.
    if os.path.basename(nome) in marchio.NATIVI_CON_MEDAGLIONE:
        with Image.open(percorso) as _im:
            dimensioni = _im.size
        if not marchio.esclude_il_medaglione(ritaglio, dimensioni):
            s0, a0, d0, b0 = marchio.RITAGLIO_SENZA_MEDAGLIONE
            nuovo = (round(s0 * dimensioni[0]), round(a0 * dimensioni[1]),
                     round(d0 * dimensioni[0]), round(b0 * dimensioni[1]))
            # se c'era gia' un ritaglio esplicito si intersecano, cosi' non si
            # perde la ragione per cui era stato messo
            ritaglio = nuovo if not ritaglio else (
                max(ritaglio[0], nuovo[0]), max(ritaglio[1], nuovo[1]),
                min(ritaglio[2], nuovo[2]), min(ritaglio[3], nuovo[3]))

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


def _da_artwork(nome, misura):
    """Riporta un artwork esistente alla proporzione dell'area, ritagliando.

    Solo riduzione: se l'artwork non ha abbastanza pixel ci si ferma, perche'
    ingrandire e' esattamente il difetto che questo file esiste per togliere.
    """
    percorso = os.path.join(SORGENTI, nome)
    if not os.path.exists(percorso):
        raise SystemExit("artwork mancante: " + percorso)
    im = Image.open(percorso).convert("RGB")
    larghezza, altezza = misura
    w, h = im.size
    if w < larghezza or h < altezza:
        raise SystemExit(
            "%s e' %dx%d, l'area e' %dx%d: ingrandirlo sarebbe rifare il "
            "difetto. Serve un artwork piu' grande." % (nome, w, h, larghezza, altezza))
    proporzione = larghezza / float(altezza)
    if w / float(h) > proporzione:
        nw, nh = int(round(h * proporzione)), h
    else:
        nw, nh = w, int(round(w / proporzione))
    im = im.crop(((w - nw) // 2, (h - nh) // 2, (w - nw) // 2 + nw, (h - nh) // 2 + nh))
    return im.resize((larghezza, altezza), Image.LANCZOS)


def costruisci(voce, tipo, misura, temporanei, passo_px=None):
    """Un file di stampa alla misura esatta dell'area, senza ingrandire nulla.

    `misura` e' quella del GRUPPO di varianti, non del tipo: lo stesso motivo
    produce piu' file, uno per ogni proporzione che il blueprint ha davvero.

    `passo_px` (solo motivi geometrici) e' il periodo in pixel calcolato una
    volta sulla misura piu' grande e poi riusato uguale su tutte. Ricavarlo
    ogni volta da `larghezza / ripetizioni` darebbe lo stesso NUMERO di
    ripetizioni su una cuccia da 50 pollici e su una da 28, cioe' due scale
    fisiche diverse dello stesso disegno: due prodotti diversi venduti con lo
    stesso nome.
    """
    larghezza, altezza = misura
    if voce[0] == "artwork":
        im = _da_artwork(voce[1], misura)
        # gli artwork "-perla.jpg" hanno il marchio dentro per convenzione
        nativo = None if "-perla" not in voce[1] else voce[1]
    elif voce[0] == "eu":
        _, nome, ritocco, ritaglio = voce
        percorso = _sorgente_eu(nome, ritocco, ritaglio, temporanei)
        percorso = _taglia_margini(percorso, temporanei)
        percorso = _riquadro_pulito(percorso, temporanei)
        percorso = _porta_all_altezza(percorso, altezza, temporanei)
        # eu.costruisci() affianca i tasselli dritti (mai specchiati: questi
        # motivi contengono la scritta "PERLA ITALIA") e dissolve le
        # giunzioni. E' la stessa funzione che produce la linea EU.
        im = eu.costruisci(percorso, larghezza, altezza, trim=6, feather=180)
        nativo = nome
    else:
        _, funzione, tinta, ripetizioni = voce
        passo = passo_px or int(round(larghezza / float(ripetizioni)))
        fn = motivi.GEOMETRICI[funzione.capitalize()]
        im = motivi.tessitura(fn(larghezza, altezza, passo, motivi.PALETTE[tinta]))
        nativo = None      # disegnato: il marchio non c'e' mai

    # Il file deve combaciare con l'area al pixel: e' quello che permette di
    # caricarlo a scale=1 senza tagli ne' fasce vuote. Se non combacia,
    # meglio fermarsi che scoprirlo dal mockup.
    if im.size != (larghezza, altezza):
        raise SystemExit("costruito %dx%d invece di %dx%d per %s"
                         % (im.size[0], im.size[1], larghezza, altezza, tipo))

    if marchio.serve(nativo):
        im, _ = marchio.componi(im, tipo)
        return im, "composto"
    return im, "nel motivo"


def main():
    provino = "--provino" in sys.argv
    rifai = "--rifai" in sys.argv
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    temporanei = os.path.join(USCITA, "_ritinti")
    os.makedirs(USCITA, exist_ok=True)

    fatti = []
    # Il manifesto dice, per ogni file costruito, se il marchio ci sta perche'
    # era gia' nel motivo o perche' l'abbiamo composto. Serve all'audit: da
    # ROUND 47 il marchio non e' piu' un LIVELLO su Printify, quindi contare i
    # livelli direbbe "senza marchio" su tutto il catalogo riparato.
    percorso_manifesto = os.path.join(USCITA, "_marchio.json")
    manifesto = {}
    if os.path.exists(percorso_manifesto):
        with open(percorso_manifesto) as fh:
            manifesto = json.load(fh)

    def scrivi(voce, tipo, chiave, nome_base, passo_px=None):
        """Costruisce e salva un file per OGNI misura di quel tipo."""
        # Da dove viene il marchio si sa dalla voce, senza dover ricostruire:
        # cosi' il manifesto si compila anche sui file gia' presenti, e non
        # resta vuoto quando la costruzione non ha niente da fare.
        nativo = voce[1] if voce[0] in ("eu", "artwork") else None
        if voce[0] == "artwork" and "-perla" not in (nativo or ""):
            nativo = None
        come = "composto" if marchio.serve(nativo) else "nel motivo"
        for misura in misure(tipo):
            fuori = os.path.join(USCITA, nome_base(misura) + ".jpg")
            manifesto[os.path.basename(fuori)] = {
                "tipo": tipo, "misura": list(misura), "marchio": come,
                "sorgente": chiave}
            if os.path.exists(fuori) and not rifai:
                fatti.append((chiave, fuori, Image.open(fuori).size, voce[0], misura))
                continue
            im, _ = costruisci(voce, tipo, misura, temporanei, passo_px)
            im.save(fuori, quality=92, subsampling=0)
            fatti.append((chiave, fuori, im.size, voce[0], misura))
            print("%-44s %5dx%-5d %-11s %.1f MB" % (
                chiave[:44], im.size[0], im.size[1], tipo,
                os.path.getsize(fuori) / 1e6))

    for sorgente, nativo in PER_SORGENTE.items():
        if solo and not any(x.lower() in sorgente.lower() for x in solo):
            continue
        tipo = tipo_di(sorgente)
        # I collari hanno tutte le varianti disabilitate E non disponibili sul
        # fornitore (verificato con perla-verifica-prodotti.py: 18 prodotti,
        # 16 varianti ciascuno, is_enabled false). Costruire i loro file
        # sarebbe mezz'ora di CPU e 300 MB per prodotti che non si possono
        # vendere. Si riattivano da soli il giorno che il fornitore torna
        # disponibile: basta togliere questa riga.
        if tipo == "collare" and "--collari" not in sys.argv:
            continue
        ritocco = ritaglio = None
        voce_nativo = nativo
        if isinstance(nativo, tuple):
            if len(nativo) == 2:
                voce_nativo, ritaglio = nativo
            else:
                voce_nativo, ritocco, ritaglio = nativo
        scrivi(("eu", voce_nativo, ritocco, ritaglio), tipo, sorgente,
               lambda m, s=sorgente: nome_uscita(s, m))

    for sorgente, tipo in DA_ARTWORK.items():
        if solo and not any(x.lower() in sorgente.lower() for x in solo):
            continue
        scrivi(("artwork", sorgente), tipo, sorgente,
               lambda m, s=sorgente: nome_uscita(s, m))

    for titolo, voce in CATALOGO.items():
        if solo and not any(s.lower() in titolo.lower() for s in solo):
            continue
        tipo = "cuccia"      # per ora il catalogo copre le cucce
        # Il periodo dei motivi geometrici si fissa UNA volta sulla misura piu'
        # grande e vale per tutte: vedi la docstring di costruisci().
        passo_px = None
        if voce[0] == "codice":
            larghezza_max = misure(tipo)[0][0]
            passo_px = int(round(larghezza_max / float(voce[3])))
        scrivi(voce, tipo, titolo, lambda m, t=titolo: "%s-%s" % (tipo, nome_catalogo(t, m)),
               passo_px)

    if provino and fatti:
        lato = 420
        colonne = 4
        righe = (len(fatti) + colonne - 1) // colonne
        sheet = Image.new("RGB", (colonne * lato, righe * (lato + 18)), "white")
        from PIL import ImageDraw
        d = ImageDraw.Draw(sheet)
        for i, (titolo, f, dim, via, misura) in enumerate(fatti):
            im = Image.open(f).convert("RGB")
            h = round(lato * dim[1] / dim[0])
            x, y = (i % colonne) * lato, (i // colonne) * (lato + 18)
            sheet.paste(im.resize((lato, max(1, h)), Image.LANCZOS), (x, y))
            d.text((x + 4, y + max(1, h) + 2),
                   ("%s %dx%d" % (titolo, misura[0], misura[1]))[:56], fill="black")
        sheet.save(os.path.join(USCITA, "_provino.jpg"), quality=90)
        print("\nprovino in", os.path.join(USCITA, "_provino.jpg"))

    with open(percorso_manifesto, "w") as fh:
        json.dump(manifesto, fh, indent=1, ensure_ascii=False)

    print("\n%d file di stampa in %s" % (len(fatti), USCITA))


if __name__ == "__main__":
    main()
