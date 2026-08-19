#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ricostruisce i file di stampa delle bandane EU dai motivi nativi dei collari.

PERCHE' ESISTE
Le venti bandane in vendita hanno tre difetti, trovati controllando i file veri
scaricati da Cloudinary:

  * sei sono FOTOGRAFIE di un foulard gia' cucito -- angolo ripiegato, ombra,
    fondo bianco dello studio, e su "Onde" perfino una targhetta smaltata
    fotografata al posto del marchio. Stampandole, la piega finta finisce sul
    tessuto.
  * tutte e venti hanno un quinto della risoluzione che serve. L'area di stampa
    e' 4125x4125 ma il dettaglio vero si ferma a 1200: misurato riducendo ogni
    file a 1200px e riportandolo su, la perdita e' ~1,0 RMS su 255, cioe' il
    rumore del JPEG. Le altre tre famiglie perdono da 5 a 26 gia' dimezzandole.
  * cinque non hanno nessun marchio, e quattro ne hanno uno solo, grande, al
    centro: la bandana si piega in triangolo, e un marchio centrato finisce
    sulla piega o sulla meta' nascosta.

DA DOVE ARRIVA LA SOLUZIONE
Le strisce dei collari (7169x315) sono a risoluzione NATIVA vera -- stessa
misura, perdono 17-26 RMS a meta'. Il tassellatore di
perla-build-eu-print-files.py sa riempire un'area qualsiasi ripetendole senza
specchiare e allineando le giunzioni al periodo del motivo. Portato su
4125x4125 da' una bandana con dettaglio reale, marchio dritto e ripetuto.

LA SCALA
La striscia viene ingrandita INGRANDIMENTO volte prima di tassellare. Il motivo
del collare e' disegnato per una fascia da 2,5 cm: riportato tale e quale su una
bandana si ripeterebbe quattordici volte, troppo fitto. Misurato sui tre valori
provati, col dettaglio vero che resta (contro ~1,0 di oggi):

    1x   motivo alto  287px, 14,4 ripetizioni, dettaglio 13,6  -- troppo fitto
    2x   motivo alto  602px,  6,9 ripetizioni, dettaglio  7,6  -- scelto
    3x   motivo alto  917px,  4,5 ripetizioni, dettaglio  3,5  -- si svuota

A 2x il marchio "PERLA ITALIA" e' pienamente leggibile e il passo e' quello di
una micro-stampa di seta.

L'ABBINAMENTO
Scelto sui colori scritti negli handle dei prodotti, che usano lo stesso
vocabolario degli asset dei collari (bandana-eu-barocco-navy-oro accanto a
collare-src-barocco-navy-oro), e controllato guardando i motivi. Dove il
gemello esatto non c'era si e' preso il parente piu' vicino per famiglia e
colore, evitando SEMPRE i collari a tinta quasi unita (Chevron, Onda, Minimal,
Astratto, Onde Geometriche, Damasco Verde): su una bandana lascerebbero il
campo vuoto e il marchio invisibile, che e' il difetto da togliere.

"Crea il Tuo Design" resta fuori: e' la base neutra su cui disegna il cliente,
ed e' quasi bianca di proposito.

USO
    python3 scripts/perla-bandane-da-collari.py SORGENTI USCITA

SORGENTI e' una cartella con i file di stampa dei collari, uno per motivo,
chiamati Collare__<Motivo>.jpg. USCITA riceve i bandana-eu-*.jpg.

Richiede Pillow.
"""
import importlib.util
import json
import os
import sys

from PIL import Image, ImageChops, ImageStat

Image.MAX_IMAGE_PIXELS = None

AREA = (4125, 4125)
INGRANDIMENTO = 2

# Il marchio su campo bianco, gia' nel repository a piena risoluzione.
MARCHIO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "generated-designs", "bandana_eu-neutro-perla.png")

# Motivi su cui il marchio va sovrapposto, perche' tassellare non lo fa
# comparire. Due gruppi, trovati guardando il primo giro:
#   * il collare gemello non ha il marchio (Lino, Tartan, Terracotta, Marinara)
#   * il motivo e' cosi' scuro e a basso contrasto che, ingrandito su una
#     bandana, il marchio che pure c'e' sparisce (Art Deco Rosa, Diamanti,
#     Onde Dorate, Paisley Cammeo)
SENZA_MARCHIO = {"Lino", "Tartan", "Terracotta", "Marinara",
                 "Art Deco Rosa", "Diamanti", "Onde Dorate", "Paisley Cammeo"}

# UN marchio solo, in basso a destra, rientrato dal bordo.
#
# I due tentativi precedenti sono stati bocciati e per lo stesso motivo: erano
# elementi appiccicati sopra al tessuto invece che parte del disegno. Prima una
# griglia di rettangoli bianchi, poi una griglia di cammei ovali -- piu' bella,
# ma sempre ripetuta e sempre "incollata".
#
# Un solo marchio discreto in un angolo e' come firma un foulard vero.
# Rientrato dell'11% perche' il bordo viene orlato in produzione: e' esattamente
# li' che il marchio delle medagliette viene tranciato via, e qui si evita.
MARCHIO_LARGHEZZA = 0.13     # frazione del lato: si legge da vicino, non domina
MARCHIO_MARGINE = 0.11       # rientro da destra e dal basso
CREMA = (238, 232, 218)      # per "Italia" quando il fondo e' scuro

# bandana -> motivo del collare da cui prenderla
ABBINAMENTI = {
    "Barocco": "Barocco",                        # gemello esatto (navy e oro)
    "Ramo d'Ulivo": "Ramo-dUlivo",               # gemello esatto (crema e verde)
    "Paisley Rosa": "Paisley",                   # gemello esatto (avorio e rosa)
    "Tartan": "Tartan",                          # gemello esatto
    "Marinara": "Marinara",                      # gemello esatto
    "Terracotta": "Terracotta",                  # gemello esatto
    "Lino": "Lino",                              # gemello esatto
    "Ulivo": "Ulivo",                            # gemello esatto
    "Damasco Diamante": "Damasco",               # damascato bordeaux e oro
    "Damasco Reale": "Damasco-Classico",         # damascato bordeaux, variante
    "Art Deco Rosa": "Geometrico",               # nero e oro rosa
    "Erbario": "Floreale",                       # botanico verde smeraldo
    "Ulivo Nuovo": "Foglia-di-Salvia",           # fogliame verde salvia
    "Floreale Elegante": "Barocco-Floreale",     # floreale ricco su fondo scuro
    "Ghirigori": "Medaglioni",                   # volute fitte, oro su scuro
    "Diamanti": "Geometrico-Minimal",            # losanghe su antracite
    "Onde": "Toile",                             # smeraldo con wordmark
    # Damasco-Verde sembrava adatto a occhio, ma ha il 61,67% di bianco: la
    # bandana sarebbe uscita quasi vuota. Astratto e' la sorgente libera piu'
    # ricca fra i 24 collari (dettaglio 16,82, zero bianco).
    "Onde Dorate": "Astratto",                   # losanghe fitte su antracite
    # Toile era gia' di "Onde": due bandane con la stessa identica stampa.
    "Paisley Cammeo": "Minimal",                 # trama fine su antracite, col marchio sopra
}

# quelli che restano come sono
ESCLUSI = {"Crea il Tuo Design"}


def carica_tassellatore():
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "perla-build-eu-print-files.py")
    spec = importlib.util.spec_from_file_location("costruttore", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def ritaglia_marchio():
    """Isola il marchio dal file neutro, con trasparenza al posto del bianco."""
    intero = Image.open(MARCHIO).convert("RGB")
    grigio = intero.convert("L")
    # bianco -> trasparente, tutto il resto opaco, con una rampa stretta per
    # non lasciare il bordo seghettato
    alpha = grigio.point(lambda v: 0 if v > 246 else (255 if v < 232 else (246 - v) * 255 // 14))
    logo = intero.copy()
    logo.putalpha(alpha)
    return logo.crop(alpha.getbbox())


def applica_marchio(motivo, logo):
    """Compone UN marchio in basso a destra, direttamente sul tessuto.

    Niente pannello e niente ripetizione: i due tentativi precedenti mettevano
    una griglia di etichette sovrapposte, e su un foulard si leggevano come
    adesivi appiccicati sopra al disegno invece che come una firma.

    Su fondo scuro la scritta "Italia", che nel file originale e' nera,
    sparirebbe: si misura la luminanza del riquadro dove cade il marchio e, se
    e' scuro, i pixel quasi neri passano a crema. Il medaglione dorato e la
    scritta "Perla" restano come sono, perche' funzionano su entrambi i fondi.
    """
    larghezza, altezza = motivo.size
    scala = (larghezza * MARCHIO_LARGHEZZA) / logo.width
    marchio = logo.resize((max(1, round(logo.width * scala)),
                           max(1, round(logo.height * scala))), Image.LANCZOS)

    x = larghezza - marchio.width - round(larghezza * MARCHIO_MARGINE)
    y = altezza - marchio.height - round(altezza * MARCHIO_MARGINE)

    riquadro = motivo.crop((x, y, x + marchio.width, y + marchio.height))
    if ImageStat.Stat(riquadro.convert("L")).mean[0] < 110:
        canali = marchio.split()
        alpha = canali[3]
        # solo i pixel scuri E opachi: la trasparenza intorno alle lettere non
        # va colorata, o si vedrebbe un alone crema attorno al medaglione
        scuri = marchio.convert("L").point(lambda v: 255 if v < 90 else 0)
        scuri = ImageChops.multiply(scuri, alpha)
        tinta = Image.new("RGBA", marchio.size, CREMA + (255,))
        marchio = Image.composite(tinta, marchio, scuri)
        marchio.putalpha(alpha)

    fuori = motivo.convert("RGBA")
    fuori.alpha_composite(marchio, (x, y))
    return fuori.convert("RGB")


def dettaglio_vero(im, riferimento=1200):
    """Quanto si perde riducendo a `riferimento` e riportando su.

    E' la misura che ha bocciato le bandane attuali: se non si perde niente,
    quel dettaglio non c'era. Sulle attuali da' ~1,0 su una scala 0-255.
    """
    ridotta = im.resize((riferimento, riferimento), Image.LANCZOS)
    return ImageStat.Stat(ImageChops.difference(im, ridotta.resize(im.size, Image.LANCZOS))).rms[0]


def bianco_angoli(im):
    """Percentuale di pixel quasi bianchi nei quattro angoli.

    Sulle bandane-fotografia e' lo sfondo dello studio: 50% su "Damasco
    Diamante", 22% su "Ghirigori", 18% su "Onde". Su un disegno vero e' 0.
    """
    larghezza, altezza = im.size
    lato = max(40, min(larghezza, altezza) // 12)
    totali = bianchi = 0
    for x, y in ((0, 0), (larghezza - lato, 0), (0, altezza - lato), (larghezza - lato, altezza - lato)):
        angolo = im.crop((x, y, x + lato, y + lato)).convert("RGB").resize((60, 60))
        pixel = list(angolo.getdata())
        totali += len(pixel)
        bianchi += sum(1 for r, g, b in pixel if r > 238 and g > 238 and b > 238)
    return 100.0 * bianchi / totali


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip().splitlines()[-6])
        return 2
    sorgenti, uscita = sys.argv[1], sys.argv[2]
    os.makedirs(uscita, exist_ok=True)
    costruttore = carica_tassellatore()

    logo = ritaglia_marchio()
    indice = {}
    print("%-20s %-19s %8s %8s %8s %7s" % (
        "bandana", "dal collare", "dettagl", "sorgente", "rapporto", "bianco%"))
    for bandana, motivo in sorted(ABBINAMENTI.items()):
        percorso = os.path.join(sorgenti, "Collare__%s.jpg" % motivo)
        if not os.path.exists(percorso):
            print("  MANCA la sorgente %s" % percorso)
            continue

        originale = Image.open(percorso).convert("RGB")
        # quanto dettaglio ha la sorgente, misurato allo stesso modo: e' il
        # metro con cui si giudica il risultato
        meta = originale.resize((originale.width // 2, originale.height // 2), Image.LANCZOS)
        dett_sorgente = ImageStat.Stat(ImageChops.difference(
            originale, meta.resize(originale.size, Image.LANCZOS))).rms[0]

        striscia = originale
        if INGRANDIMENTO > 1:
            striscia = originale.resize(
                (originale.width * INGRANDIMENTO, originale.height * INGRANDIMENTO), Image.LANCZOS)
        temporaneo = os.path.join(uscita, ".striscia-scalata.jpg")
        striscia.save(temporaneo, quality=97, subsampling=0)

        grande = costruttore.costruisci(temporaneo, AREA[0], AREA[1])
        if bandana in SENZA_MARCHIO:
            grande = applica_marchio(grande, logo)

        nome = "bandana_eu-%s.jpg" % bandana.lower().replace(" ", "-").replace("'", "")
        grande.save(os.path.join(uscita, nome), quality=94, subsampling=0)

        dettaglio = dettaglio_vero(grande)
        bianco = bianco_angoli(grande)
        # Il rapporto sulla sorgente, non una soglia assoluta: un tartan e'
        # fatto di campiture piatte e prende un punteggio basso anche perfetto.
        # L'ingrandimento costa una frazione costante, misurata fra 0,69 e 0,79.
        rapporto = dettaglio / dett_sorgente if dett_sorgente else 0
        esito = "ok" if rapporto >= 0.6 and bianco < 1 else "scarso"
        indice[bandana] = {"file": nome, "dal_collare": motivo,
                           "dettaglio": round(dettaglio, 2),
                           "dettaglio_sorgente": round(dett_sorgente, 2),
                           "rapporto": round(rapporto, 2),
                           "bianco_angoli": round(bianco, 2),
                           "marchio_sovrapposto": bandana in SENZA_MARCHIO,
                           "esito": esito}
        print("%-20s %-19s %8.2f %8.2f %8.2f %7.2f  %s" % (
            bandana, motivo, dettaglio, dett_sorgente, rapporto, bianco,
            "" if esito == "ok" else "<-- " + esito))

    if os.path.exists(os.path.join(uscita, ".striscia-scalata.jpg")):
        os.remove(os.path.join(uscita, ".striscia-scalata.jpg"))

    with open(os.path.join(uscita, "bandane.json"), "w") as fh:
        json.dump(indice, fh, indent=1, ensure_ascii=False)

    scarsi = [b for b, v in indice.items() if v["esito"] != "ok"]
    print("\n%d bandane in %s" % (len(indice), uscita))
    if scarsi:
        print("DA RIVEDERE: " + ", ".join(scarsi))
    print("Fuori dal giro (base neutra): " + ", ".join(sorted(ESCLUSI)))
    return 1 if scarsi else 0


if __name__ == "__main__":
    sys.exit(main())
