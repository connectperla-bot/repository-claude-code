#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara le immagini dei motivi Perla nella proporzione di un prodotto.

PERCHE' ESISTE
Quasi tutti i fornitori di stampa su ordinazione vogliono, per ogni prodotto,
un'immagine gia' nella proporzione giusta, da caricare a mano nel loro studio.
Questo script la ricava dai motivi che vendiamo gia', alla massima risoluzione
possibile, senza inventare pixel.

Non dipende da nessun fornitore in particolare: si dichiara la proporzione
che serve e lo script produce il ritaglio piu' grande che quella proporzione
consente.

DA DOVE ARRIVANO I MOTIVI
Dai 66 pattern nativi su Cloudinary elencati in perla-eu-prodotti.json, gli
stessi file usati per la stampa reale sui prodotti EU. Ogni motivo esiste in
una o piu' forme, con proporzioni molto diverse:

    bandana      4125 x 4125    quadrata
    collare      7169 x  315    striscia 22:1
    ciotola      6496 x  803    fascia 8:1
    guinzaglio  12389 x  219    nastro 56:1

NON usare generated-designs/*.jpg: quelle sono le bozze AI a bassa
risoluzione (1280x720, 1248x832), non i file di stampa.

COME, E PERCHE' COSI'
Si RITAGLIA, non si affianca. Le due alternative sono state provate su
Bandana "Barocco" e scartate per motivi concreti:

  * AFFIANCARE SPECCHIANDO (il metodo di perla-build-eu-print-files.py, giusto
    per ciotola e guinzaglio) qui non va: questi motivi contengono la scritta
    "PERLA ITALIA" e il monogramma PI, e lo specchiamento li stampa
    rovesciati. Su un prodotto di lusso e' un difetto, non una texture.
  * AFFIANCARE DRITTO tiene il testo dritto ma lascia una cucitura visibile:
    gli originali non sono disegnati per combaciare ai bordi (misurato: lo
    stacco ai margini e' pari alla variazione interna del motivo). A piena
    risoluzione si vede una riga scura netta.

Il ritaglio centrato non ha nessuno di questi due problemi: niente giunzioni
perche' non c'e' nessuna giunzione, niente testo rovesciato, e il motivo resta
alla scala con cui e' stato disegnato. Il prezzo da pagare e' che si usa solo
una parte dell'originale, e che la risoluzione non puo' superare quella del
file di partenza -- riportata in chiaro nella tabella finale, cosi' si vede
subito per quali prodotti basta.

Per ogni proporzione richiesta si sceglie l'originale che produce il ritaglio
piu' grande in pixel, non quello di un tipo prodotto prestabilito: per una
cuccia quasi quadrata vince la bandana, per un nastro lungo vince il
guinzaglio.

USO
    python3 scripts/perla-file-stampa-motivi.py                  # motivi del nucleo
    python3 scripts/perla-file-stampa-motivi.py --tutti          # tutti i motivi
    python3 scripts/perla-file-stampa-motivi.py --motivo Barocco --motivo Onda
    python3 scripts/perla-file-stampa-motivi.py --elenco         # cosa esiste, senza scaricare

Richiede Pillow. Scrive in generated-designs/motivi-stampa/.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

from PIL import Image

# Gli originali sono grandi: senza questo Pillow rifiuta di aprirli
# ("DecompressionBombWarning"). Sono file nostri, non contenuto di terzi.
Image.MAX_IMAGE_PIXELS = None

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODOTTI = os.path.join(RADICE, "scripts", "perla-eu-prodotti.json")
CACHE = os.path.join(RADICE, "generated-designs", "motivi-stampa", "_originali")
USCITA = os.path.join(RADICE, "generated-designs", "motivi-stampa")

# I sette motivi presenti su tre o piu' tipi di prodotto: il nucleo gia'
# collaudato del catalogo EU.
NUCLEO = ["Barocco", "Damasco", "Floreale", "Geometrico", "Medaglioni", "Onda", "Paisley"]

# Proporzioni da produrre, una per famiglia di prodotti. Non si insegue una
# dimensione in pixel: i fornitori raramente pubblicano le misure esatte delle
# aree di stampa, e comunque il loro studio scala l'immagine. Si produce quindi
# il ritaglio piu' grande che ogni proporzione consente, e la tabella finale
# dice fino a che dimensione fisica regge.
#
# I rapporti NON sono arrotondamenti comodi: devono combaciare con l'area di
# stampa vera, altrimenti il fornitore adatta il file da solo e il motivo esce
# deformato. Per cuccia e tappetino il numero di riferimento e' quello scritto
# in snippets/perla-print-areas.liquid nel tema, che a sua volta e' stato
# ricavato dai dati reali del catalogo Printify (vedi ROUND 16 in quel file:
# la cuccia era impostata a 1.24 contro un'area reale di 8850x5850 = 1.51, e
# i design dei clienti venivano stampati schiacciati).
FORME = {
    "quadrato":  (1, 1),      # bandana, coperta
    "cuccia":    (151, 100),  # 1.51 - area reale 8850x5850 della variante 28"x18"
    "tappetino": (36, 25),    # 1.44 - stesso valore della riga tappetino nel tema
    "fascia":    (8, 1),      # ciotola
    "nastro":    (40, 1),     # guinzaglio
}

MOCKUP_LATO_LUNGO = 1600

# Solo un controllo di sanita': sotto questa soglia il ritaglio e' degenere.
# NON e' una soglia di qualita' -- quella la dice la tabella finale, in
# pollici. Tenerla bassa e' voluto: il nastro del guinzaglio e' alto 219 px ed
# e' proprio l'originale giusto per un guinzaglio, non uno da scartare.
MIN_LATO_CORTO = 64

# Sotto questa misura del lato lungo a 150 dpi il file non regge un prodotto
# di dimensioni reali: la riga viene marcata come scarsa nella tabella.
POLLICI_MINIMI = 12.0


def carica_indice():
    """motivo -> {tipo prodotto: url del pattern nativo}"""
    with open(PRODOTTI) as fh:
        dati = json.load(fh)
    indice = {}
    for voce in dati:
        m = re.match(r'(\w+)\s+"(.+)"', voce.get("title", ""))
        if not m:
            continue
        tipo, motivo = m.group(1), m.group(2)
        # "Crea il Tuo Design" e' la base neutra dello studio di
        # personalizzazione, non un motivo: qui non serve.
        if motivo == "Crea il Tuo Design":
            continue
        indice.setdefault(motivo, {})[tipo] = voce["pattern"]
    return indice


def scarica(url, motivo, tipo):
    os.makedirs(CACHE, exist_ok=True)
    nome = "%s-%s.jpg" % (tipo.lower(), motivo.lower().replace(" ", "-").replace("'", ""))
    percorso = os.path.join(CACHE, nome)
    if not os.path.exists(percorso):
        urllib.request.urlretrieve(url, percorso)
    return percorso


def ritaglio_massimo(dimensioni, proporzione):
    """Il piu' grande ritaglio con quella proporzione dentro l'immagine.

    Restituisce (larghezza, altezza) in pixel, senza mai ingrandire.
    """
    sw, sh = dimensioni
    rw, rh = proporzione
    r = rw / rh
    if sw / sh > r:
        h = sh
        w = int(round(sh * r))
    else:
        w = sw
        h = int(round(sw / r))
    return w, h


def scegli_originale(candidati, proporzione):
    """Fra gli originali disponibili sceglie quello che rende il ritaglio piu'
    grande. Restituisce (tipo, percorso, (w, h) del ritaglio)."""
    migliore = None
    for tipo, percorso in candidati.items():
        with Image.open(percorso) as im:
            w, h = ritaglio_massimo(im.size, proporzione)
        if min(w, h) < MIN_LATO_CORTO:
            continue
        if migliore is None or w * h > migliore[2][0] * migliore[2][1]:
            migliore = (tipo, percorso, (w, h))
    return migliore


def ritaglia_centrato(percorso, larghezza, altezza):
    im = Image.open(percorso).convert("RGB")
    sw, sh = im.size
    sx = (sw - larghezza) // 2
    sy = (sh - altezza) // 2
    return im.crop((sx, sy, sx + larghezza, sy + altezza))


def pollici_a(dpi, pixel):
    return pixel / float(dpi)


def main():
    p = argparse.ArgumentParser(description="Immagini dei motivi Perla nella proporzione di un prodotto.")
    p.add_argument("--motivo", action="append", default=[],
                   help="nome del motivo (ripetibile). Senza, usa i sette del nucleo.")
    p.add_argument("--tutti", action="store_true", help="tutti i motivi disponibili")
    p.add_argument("--elenco", action="store_true", help="mostra cosa esiste e esce, senza scaricare")
    p.add_argument("--forma", action="append", default=[],
                   help="limita alle forme indicate: " + ", ".join(FORME))
    args = p.parse_args()

    indice = carica_indice()

    if args.elenco:
        print("%d motivi disponibili:\n" % len(indice))
        for motivo in sorted(indice):
            nel_nucleo = " (nucleo)" if motivo in NUCLEO else ""
            print("  %-22s %s%s" % (motivo, ", ".join(sorted(indice[motivo])), nel_nucleo))
        return

    if args.tutti:
        motivi = sorted(indice)
    elif args.motivo:
        motivi = args.motivo
    else:
        motivi = NUCLEO

    sconosciuti = [m for m in motivi if m not in indice]
    if sconosciuti:
        print("Motivi non trovati: %s" % ", ".join(sconosciuti), file=sys.stderr)
        print("Usa --elenco per vedere i nomi esatti.", file=sys.stderr)
        return 1

    forme = {k: v for k, v in FORME.items() if not args.forma or k in args.forma}
    if not forme:
        print("Nessuna forma valida. Disponibili: %s" % ", ".join(FORME), file=sys.stderr)
        return 1

    os.makedirs(USCITA, exist_ok=True)
    righe = []
    manifesto = []

    for motivo in motivi:
        # Si scaricano solo gli originali di questo motivo, una volta sola.
        candidati = {}
        for tipo, url in indice[motivo].items():
            try:
                candidati[tipo] = scarica(url, motivo, tipo)
            except Exception as err:
                print("  originale non scaricabile (%s / %s): %s" % (motivo, tipo, err), file=sys.stderr)

        if not candidati:
            print("  %s: nessun originale disponibile, saltato" % motivo, file=sys.stderr)
            continue

        for forma, proporzione in forme.items():
            scelta = scegli_originale(candidati, proporzione)
            if scelta is None:
                righe.append((motivo, forma, "-", 0, 0, "nessun originale adatto"))
                continue
            tipo, percorso, (w, h) = scelta
            immagine = ritaglia_centrato(percorso, w, h)

            base = os.path.join(USCITA, "%s-%s" % (
                forma, motivo.lower().replace(" ", "-").replace("'", "")))
            immagine.save(base + ".jpg", quality=95, subsampling=0)

            lato = MOCKUP_LATO_LUNGO
            if w >= h:
                anteprima = (lato, max(1, round(h * lato / w)))
            else:
                anteprima = (max(1, round(w * lato / h)), lato)
            immagine.resize(anteprima, Image.LANCZOS).save(
                base + "-anteprima.jpg", quality=90)

            manifesto.append({
                "forma": forma,
                "motivo": motivo,
                "file": os.path.basename(base + ".jpg"),
                "anteprima": os.path.basename(base + "-anteprima.jpg"),
                "originale": tipo,
                "larghezza": w,
                "altezza": h,
                # il giudizio viaggia col file: chi lo consuma non deve
                # rifare il conto dei pollici per sapere se e' usabile
                "esito": "ok" if pollici_a(150, max(w, h)) >= POLLICI_MINIMI else "scarso",
            })
            righe.append((motivo, forma, tipo, w, h, ""))

    # Il manifesto e' il ponte verso chi carica i file (scripts/
    # perla-crea-tappetini.js): porta dimensioni ed esito, cosi' nessuno
    # ricarica per sbaglio un ritaglio marcato scarso. Stessa convenzione di
    # perla-build-eu-print-files.py, che scrive anche lui un files.json.
    with open(os.path.join(USCITA, "files.json"), "w") as fh:
        json.dump(manifesto, fh, indent=1, ensure_ascii=False)

    # Tabella finale. La colonna in pollici e' la cosa da guardare: dice fino
    # a che dimensione fisica il file regge una stampa di qualita'.
    print("\n%-18s %-9s %-11s %11s %9s %9s  %s" % (
        "motivo", "forma", "originale", "pixel", "a 300dpi", "a 150dpi", "esito"))
    print("-" * 84)
    scarsi = 0
    for motivo, forma, tipo, w, h, nota in righe:
        if nota:
            print("%-18s %-9s %s" % (motivo, forma, nota))
            continue
        a150 = pollici_a(150, max(w, h))
        if a150 < POLLICI_MINIMI:
            esito = "SCARSO, non caricare"
            scarsi += 1
        else:
            esito = "ok"
        print("%-18s %-9s %-11s %5d x%5d %8.1f\" %8.1f\"  %s" % (
            motivo, forma, tipo, w, h,
            pollici_a(300, max(w, h)), a150, esito))

    buoni = len([r for r in righe if not r[5]]) - scarsi
    print("\n%d immagini scritte in %s (%d buone, %d scarse)." % (
        len([r for r in righe if not r[5]]) * 2,
        os.path.relpath(USCITA, RADICE), buoni, scarsi))
    print("Le colonne in pollici sono il lato lungo stampabile a quella densita'.")
    print("Una riga SCARSO vuol dire che per quella forma non esiste un originale")
    print("abbastanza grande: quel motivo va rigenerato, non caricato cosi'.")
    print("Confronta questi numeri con l'area di stampa reale del prodotto,")
    print("nello studio del fornitore, prima di caricare.")


if __name__ == "__main__":
    sys.exit(main() or 0)
