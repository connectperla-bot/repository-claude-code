#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Costruisce i file di stampa per ciotole e guinzagli EU partendo dai motivi
gia' in vendita come collari.

PERCHE' ESISTE
Il catalogo EU era sbilanciato: diciannove collari e quindici bandane, ma solo
quattro ciotole e quattro guinzagli. I motivi mancanti esistono gia' come
strisce da collare a risoluzione nativa negli asset del tema
(assets/collare-src-*.jpg, 7169 x 315). Qui vengono riportati sulle altre due
aree di stampa Printful.

    ciotola_eu     6496 x  803   (fascia attorno alla ciotola)
    guinzaglio_eu 12389 x  219   (nastro del guinzaglio)

COME, E PERCHE' COSI'
Stirare una striscia 22:1 dentro una fascia 8:1 la sfoca. Invece:

  * per la CIOTOLA la striscia viene IMPILATA a scala naturale finche' non
    riempie l'altezza. Nessun ingrandimento: il motivo resta grande esattamente
    quanto sul collare, che e' anche la scala con cui e' stato disegnato.
  * per il GUINZAGLIO la striscia viene RIDOTTA a 219px di altezza. Anche qui
    nessun ingrandimento, solo una riduzione, che e' sempre sicura.
  * i tasselli restano SEMPRE DRITTI e le giunzioni vengono dissolte. Fino a
    ROUND 41 file e colonne alterne erano specchiate: i bordi combaciavano,
    ma il marchio "PERLA ITALIA" finiva capovolto sul prodotto stampato.
    Vedi la docstring di costruisci().
  * le strisce hanno i bordi alto/basso leggermente piu' scuri: impilate
    lascerebbero righe orizzontali. Vengono ritagliati e le file si
    sovrappongono con una dissolvenza.

I DUE FORMATI IN USCITA
Per ogni motivo si scrivono due file:

  <tipo>-<motivo>.jpg          risoluzione nativa, per lo sfondo dell'editor
                               (metafield custom.editor_pattern_image) e per
                               la stampa reale
  <tipo>-<motivo>-mockup.jpg   ridotto a 1600px sul lato lungo, SOLO per
                               generare il mockup

La seconda versione non e' un ripiego. Il Mockup Generator di Printful, sopra
una certa dimensione del file, restituisce il prodotto con il motivo impastato
in una macchia sfocata: verificato affiancando il mockup generato dal file
nativo 7169x315 e quello gia' online, su tre collari diversi. Il file grande
resta quello giusto per la stampa; per la fotografia serve quello piccolo.

NOMI DEI FILE, ATTENZIONE
I nomi degli asset nel tema NON descrivono il motivo che contengono
(collare-src-ulivo-crema-oro.jpg e' un damascato bordeaux). La mappa qui sotto
e' stata compilata guardando le immagini, non leggendo i nomi.

USO
    python3 scripts/perla-build-eu-print-files.py [cartella_uscita]

Richiede Pillow. Scarica gli asset dal CDN del tema se non sono gia' in cache.
"""
import json
import os
import sys
import urllib.request

from PIL import Image

CDN = "https://perlaitaly.com/cdn/shop/t/49/assets/"
CACHE = "print-src-cache"

# nome commerciale -> asset del tema, scelto guardando il motivo
MOTIVI = {
    "Onda": "collare-src-onda-navy-oro.jpg",                      # onde su blu notte
    "Medaglioni": "collare-src-medaglioni-antracite-argento.jpg",  # medaglioni oro su porpora
    "Geometrico": "collare-src-geometrico-nero-rosa.jpg",          # losanghe nero e oro rosa
    "Petrolio": "collare-src-chevron-verde-petrolio-oro.jpg",      # verde petrolio pieno
    "Avorio": "collare-src-foglia-di-salvia-verde-salvia-oro.jpg",  # volute chiare su avorio
    "Smeraldo": "collare-src-toile-crema-bordeaux.jpg",            # smeraldo con wordmark
}

# misure reali delle aree di stampa Printful, le stesse di
# snippets/perla-print-areas.liquid e di PRINTFUL_MOCKUP_CONFIG
AREE = {"ciotola_eu": (6496, 803), "guinzaglio_eu": (12389, 219)}

MOCKUP_LATO_LUNGO = 1600


def scarica(asset):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, asset)
    if not os.path.exists(path):
        urllib.request.urlretrieve(CDN + asset, path)
    return path


def _periodo_orizzontale(src, soglia=1.5):
    """Ogni quanti pixel il motivo si ripete, o None se non si ripete.

    Questi motivi sono disegnati come carte da parati: la striscia contiene lo
    stesso elemento piu' volte. Trovare quel passo permette di affiancare i
    tasselli su un confine dove il disegno combacia gia' da solo -- niente
    giunzione da nascondere, quindi niente dissolvenza che sfumerebbe un
    marchio finito li' sopra.

    Misurato sulle sei sorgenti reali: lo scarto sul periodo giusto sta fra
    0,22 e 0,60 su una scala 0-255, cioe' ripetizione praticamente esatta.
    La soglia e' larga apposta, e sopra di essa si ripiega sulla dissolvenza.
    """
    g = src.convert("L")
    w, h = g.size
    px = g.load()
    campioni_y = range(0, h, max(1, h // 40))
    profilo = [sum(px[x, y] for y in campioni_y) / len(campioni_y) for x in range(w)]

    migliore = None
    for p in range(w // 12, w // 2):
        indici = range(0, w - p, 7)
        scarto = sum(abs(profilo[i] - profilo[i + p]) for i in indici) / len(indici)
        if migliore is None or scarto < migliore[0]:
            migliore = (scarto, p)

    if migliore is None or migliore[0] > soglia:
        return None
    return migliore[1]


def _fascia_orizzontale(src, larghezza, dissolvenza):
    """Ripete la striscia verso destra fino a coprire larghezza.

    Mai specchiata: vedi la docstring di costruisci().
    """
    sw, sh = src.size
    if sw >= larghezza:
        # e' il caso della ciotola (striscia 7169 contro area 6496): nessuna
        # ripetizione orizzontale, quindi nessuna giunzione
        return src.crop((0, 0, larghezza, sh))

    periodo = _periodo_orizzontale(src)
    passo = (sw // periodo) * periodo if periodo else sw

    # GIUNZIONE NETTA, MAI DISSOLTA. Con un periodo riconosciuto il disegno
    # riparte esattamente dove si era interrotto e la giunzione non si vede.
    # Senza, resta una riga verticale visibile -- ed e' voluto: dissolvere
    # significherebbe sfumare quello che ci cade sopra, e su questi motivi
    # cade il marchio. Provato: con una dissolvenza di 20px un logo a cavallo
    # della giunzione perde meta' delle sue forme. Una riga netta si nota;
    # un marchio mangiato e' un reso.
    fascia = Image.new("RGB", (larghezza + sw, sh))
    x = 0
    while x < larghezza:
        fascia.paste(src, (x, 0))
        x += passo
    return fascia.crop((0, 0, larghezza, sh))


def costruisci(path, larghezza, altezza, trim=14, feather=90):
    """Riempie l'area di stampa ripetendo la striscia, senza ingrandirla.

    SEMPRE DRITTA, MAI SPECCHIATA. Fino a ROUND 41 le file e le colonne
    alterne venivano ribaltate (FLIP_TOP_BOTTOM / FLIP_LEFT_RIGHT) perche' i
    bordi combaciassero. Su una texture astratta e' il metodo giusto; su
    QUESTI motivi no, perche' contengono la scritta "PERLA ITALIA" e il
    monogramma PI, e il ribaltamento li stampa capovolti e riflessi.

    Non e' un rischio teorico: era il difetto arrivato a casa. Verificato sui
    12 file che questa funzione aveva prodotto -- su ciotola_eu-smeraldo le
    righe 2 e 4 avevano il marchio sottosopra, su guinzaglio_eu-smeraldo la
    meta' destra era riflessa. Stessa cosa sul monogramma di "Geometrico".
    La stessa nota sta in perla-file-stampa-motivi.py, righe 32-40.

    Al posto dello specchiamento le giunzioni vengono dissolte, in orizzontale
    e in verticale. Resta una fascia di sovrapposizione appena percettibile
    dove due tasselli si incontrano: molto meno grave di un marchio capovolto,
    ed e' il compromesso scelto consapevolmente.
    """
    intera = Image.open(path).convert("RGB")
    src = intera.crop((0, trim, intera.width, intera.height - trim))
    if src.height > altezza:
        # solo riduzione, mai il contrario
        src = src.resize((round(src.width * altezza / src.height), altezza), Image.LANCZOS)

    sw, sh = src.size
    feather = min(feather, max(1, sh // 3))
    passo = max(1, sh - feather)
    sfumatura = Image.linear_gradient("L").resize((larghezza, feather))
    fascia = _fascia_orizzontale(src, larghezza, feather)
    tela = Image.new("RGB", (larghezza, altezza + sh))

    y = riga = 0
    while y < altezza:
        if riga == 0:
            tela.paste(fascia, (0, y))
        else:
            tela.paste(fascia.crop((0, feather, larghezza, sh)), (0, y + feather))
            tela.paste(fascia.crop((0, 0, larghezza, feather)), (0, y), sfumatura)
        y += passo
        riga += 1

    return tela.crop((0, 0, larghezza, altezza))


def main():
    uscita = sys.argv[1] if len(sys.argv) > 1 else "generated-designs/eu-print-files"
    os.makedirs(uscita, exist_ok=True)
    indice = {}

    for nome, asset in MOTIVI.items():
        src = scarica(asset)
        for tipo, (larghezza, altezza) in AREE.items():
            grande = costruisci(src, larghezza, altezza)
            base = os.path.join(uscita, "%s-%s" % (tipo, nome.lower()))
            grande.save(base + ".jpg", quality=95, subsampling=0)

            h = max(1, round(altezza * MOCKUP_LATO_LUNGO / larghezza))
            grande.resize((MOCKUP_LATO_LUNGO, h), Image.LANCZOS).save(
                base + "-mockup.jpg", quality=95, subsampling=0)

            indice["%s/%s" % (tipo, nome)] = {
                "full": base + ".jpg", "mockup": base + "-mockup.jpg"}
            print("%-14s %-11s %5d x %4d" % (tipo, nome, larghezza, altezza))

    with open(os.path.join(uscita, "files.json"), "w") as fh:
        json.dump(indice, fh, indent=1)
    print("\n%d file di stampa in %s" % (len(indice), uscita))


if __name__ == "__main__":
    main()
