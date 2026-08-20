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
# COSTRUZIONE
# ==========================================================================

def _sorgente_eu(nome, ritocco, ritaglio, temporanei):
    """Percorso del nativo EU, gia' ritagliato e ritinto se serve."""
    percorso = os.path.join(NATIVI, nome)
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


def costruisci(voce, tipo, temporanei):
    """Un file di stampa alla misura esatta dell'area, senza ingrandire nulla."""
    larghezza, altezza = AREE[tipo]
    if voce[0] == "eu":
        _, nome, ritocco, ritaglio = voce
        percorso = _sorgente_eu(nome, ritocco, ritaglio, temporanei)
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
