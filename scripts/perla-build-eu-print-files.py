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
  * le file e le colonne alterne sono specchiate, cosi' i bordi combaciano
    invece di ripetersi con uno stacco.
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


def costruisci(path, larghezza, altezza, trim=14, feather=90):
    """Riempie l'area di stampa ripetendo la striscia, senza ingrandirla."""
    intera = Image.open(path).convert("RGB")
    src = intera.crop((0, trim, intera.width, intera.height - trim))
    if src.height > altezza:
        # solo riduzione, mai il contrario
        src = src.resize((round(src.width * altezza / src.height), altezza), Image.LANCZOS)

    sw, sh = src.size
    feather = min(feather, max(1, sh // 3))
    passo = max(1, sh - feather)
    sfumatura = Image.linear_gradient("L").resize((larghezza, feather))
    tela = Image.new("RGB", (larghezza, altezza + sh))

    y = riga = 0
    while y < altezza:
        tassello = src if riga % 2 == 0 else src.transpose(Image.FLIP_TOP_BOTTOM)
        fascia = Image.new("RGB", (larghezza, sh))
        x = colonna = 0
        while x < larghezza:
            pezzo = tassello if colonna % 2 == 0 else tassello.transpose(Image.FLIP_LEFT_RIGHT)
            fascia.paste(pezzo, (x, 0))
            x += sw
            colonna += 1
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
