#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Misura un file di stampa con lo stesso metro usato per la diagnosi.

Due numeri, due difetti diversi:

  NITIDEZZA   deviazione standard del filtro dei bordi su un ritaglio centrale
              a risoluzione piena. Bassa = ingrandito da un originale piccolo.
              Bersaglio: >= 50,9, la mediana dei file nativi del catalogo
              (collari 7169x315, ciotole 6496x803, guinzagli 12389x219).
              Le bandane ingrandite stavano a 10,4.

  GIUNTA      rapporto fra il salto massimo e il salto medio da una colonna
              alla successiva. Dove due moduli si accostano male c'e' un
              gradino, e il massimo schizza sopra la media.
              Bersaglio: < 2x. Le prove di affiancamento fallite stavano a
              3,1x; la fascia EU buona a 1,6x.

Un avvertimento, imparato sbagliando: questi numeri NON vedono un marchio
specchiato. La ripetizione a specchio segnava 69,5 di nitidezza e giunta
perfetta, e la scritta si leggeva "AIJATI AA ITALIA". Le immagini vanno
guardate, sempre.

    python3 tests/perla-misura-stampa.py file.png [altri.png ...]
"""
import os
import sys

from PIL import Image, ImageChops, ImageFilter, ImageStat

NITIDEZZA_MINIMA = 50.9
GIUNTA_MASSIMA = 2.0


def nitidezza(im):
    lato = min(700, im.width, im.height)
    c = im.crop((im.width // 2 - lato // 2, im.height // 2 - lato // 2,
                 im.width // 2 + lato // 2, im.height // 2 + lato // 2)).convert("L")
    return round(ImageStat.Stat(c.filter(ImageFilter.FIND_EDGES)).stddev[0], 1)


def giunta(im):
    g = im.convert("L")
    if g.width < 3:
        return 0.0
    sx = g.crop((0, 0, g.width - 1, g.height))
    dx = g.crop((1, 0, g.width, g.height))
    diff = ImageChops.difference(sx, dx)
    passo = max(1, diff.width // 900)
    col = [ImageStat.Stat(diff.crop((i, 0, i + 1, diff.height))).mean[0]
           for i in range(0, diff.width, passo)]
    media = sum(col) / len(col)
    return round(max(col) / media, 1) if media > 0.01 else 0.0


def main():
    ko = 0
    print("%-42s %10s %8s  %s" % ("FILE", "nitidezza", "giunta", "esito"))
    for p in sys.argv[1:]:
        im = Image.open(p).convert("RGB")
        n, s = nitidezza(im), giunta(im)
        buono = n >= NITIDEZZA_MINIMA and s < GIUNTA_MASSIMA
        if not buono:
            ko += 1
        motivo = "" if buono else (" molle" if n < NITIDEZZA_MINIMA else "") + \
                                  (" giunta" if s >= GIUNTA_MASSIMA else "")
        print("%-42s %10.1f %8.1f  %s%s" % (
            os.path.basename(p)[:42], n, s, "OK" if buono else "NO", motivo))
    print("\n%d su %d passano (nitidezza >= %.1f, giunta < %.1f)" %
          (len(sys.argv) - 1 - ko, len(sys.argv) - 1, NITIDEZZA_MINIMA, GIUNTA_MASSIMA))
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
