#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porta i file di stampa dei prodotti EU alla risoluzione dell'area di stampa.

PERCHE'
custom.editor_pattern_image e' due cose insieme: lo sfondo dell'area di stampa
nello studio, e la base su cui composeAndUpload disegna il nome del cliente
prima di mandarlo in produzione. Su 19 collari puntava a una striscia
1200 x 53 px che Printful poi porta a 7169 x 315: sei volte di ingrandimento
sul prodotto che arriva a casa. Su 12 prodotti non puntava a niente, e lo
studio ripiegava sulla FOTO del prodotto.

COSA FA, PER GRUPPO

  collari (19)   l'asset nativo del tema, 7169 x 315. L'abbinamento
                 prodotto -> asset e' stato fatto confrontando le IMMAGINI
                 (il file 1200 x 53 e' la riduzione dello stesso disegno),
                 non i nomi: 19 prodotti su 19 asset distinti, distanza ~1
                 contro >=11 del secondo candidato.

  ciotole e
  guinzagli (8)  gli asset nativi ciotola_eu-* e guinzaglio_eu-* che erano gia'
                 nel tema, 6496 x 803 e 12389 x 219, e che nessuno usava.

  neutri (4)     i file gia' committati in generated-designs/.

  bandane (15)   ingrandimento Lanczos + maschera di contrasto da 1200 a 4125.
                 NON ricostruite dalla striscia del collare: verificato che un
                 gemello non esiste (vedi sotto). L'ingrandimento non aggiunge
                 dettaglio, ma lo fa con un algoritmo decente invece di
                 lasciarlo al RIP di Printful.

PERCHE' LE BANDANE NO
Confronto per istogramma fra ognuna delle 15 e i 19 collari nativi: il miglior
candidato e' sempre sbagliato (Bandana "Barocco" -> medaglioni antracite) e il
margine sul secondo e' nullo (3148 contro 3223). Nel test dei collari, dove il
gemello c'era davvero, il rapporto era 1 contro 11. Le bandane hanno un disegno
proprio: ricostruirle dal collare non le migliorerebbe, le sostituirebbe -- e
cinque finirebbero sullo stesso motivo.

USO
    python3 pipeline.py build     costruisce i file in out/
    python3 pipeline.py upload    li carica e scrive out/uploads.json
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageFilter

QUI = os.path.dirname(os.path.abspath(__file__))


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


marchio = _modulo("marchio", os.path.join(QUI, "marchio.py"))

SRC_COLLARI = "src"
SRC_ALTRI = "src2"
NEUTRI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated-designs")
OUT = "out"
ENDPOINT = "https://perla-upload-endpoint-yizy.onrender.com/upload"

AREE = {"collare-eu": (7169, 315), "bandana-eu": (4125, 4125),
        "ciotola-eu": (6496, 803), "guinzaglio-eu": (12389, 219)}

# prodotto -> asset nativo, stabilito confrontando le immagini (vedi docstring)
COLLARI = {
    'Collare "Astratto"': "astratto-antracite-argento",
    'Collare "Barocco Floreale"': "barocco-floreale-navy",
    'Collare "Barocco"': "barocco-navy-oro",
    'Collare "Chevron"': "chevron-verde-petrolio-oro",
    'Collare "Damasco Classico"': "damasco-classico-bordeaux",
    'Collare "Damasco Verde"': "damasco-verde-salvia-oro",
    'Collare "Damasco"': "damasco-bordeaux-oro",
    'Collare "Floreale"': "floreale-verde-smeraldo-oro",
    'Collare "Foglia di Salvia"': "foglia-di-salvia-verde-salvia-oro",
    'Collare "Geometrico Minimal"': "geometrico-minimal-antracite",
    'Collare "Geometrico"': "geometrico-nero-rosa",
    'Collare "Medaglioni"': "medaglioni-antracite-argento",
    'Collare "Minimal"': "minimal-antracite-argento",
    'Collare "Onda"': "onda-navy-oro",
    'Collare "Onde Geometriche"': "onde-geometriche-antracite-rosa",
    'Collare "Paisley"': "paisley-avorio-rosa",
    "Collare \"Ramo d'Ulivo\"": "ramo-dulivo-crema",
    'Collare "Toile"': "toile-crema-bordeaux",
    'Collare "Ulivo"': "ulivo-crema-oro",
}

# i quattro motivi che avevano gia' l'asset nativo nel tema e nessun metafield
ALTRI = {
    ('ciotola-eu', 'Barocco'): "ciotola_eu-baroque-navy-gold",
    ('ciotola-eu', 'Damasco'): "ciotola_eu-damasco-bordeaux-oro",
    ('ciotola-eu', 'Floreale'): "ciotola_eu-floreale-smeraldo-oro",
    ('ciotola-eu', 'Paisley'): "ciotola_eu-paisley-avorio-rosa",
    ('guinzaglio-eu', 'Barocco'): "guinzaglio_eu-baroque-navy-gold",
    ('guinzaglio-eu', 'Damasco'): "guinzaglio_eu-damasco-bordeaux-oro",
    ('guinzaglio-eu', 'Floreale'): "guinzaglio_eu-floreale-smeraldo-oro",
    ('guinzaglio-eu', 'Paisley'): "guinzaglio_eu-paisley-avorio-rosa",
}

NEUTRO_FILE = {"collare-eu": "collare_eu-neutro-perla.png",
               "bandana-eu": "bandana_eu-neutro-perla.png",
               "ciotola-eu": "ciotola_eu-neutro-perla.png",
               "guinzaglio-eu": "guinzaglio_eu-neutro-perla.png"}

MOCKUP_LATO_LUNGO = 1600   # vedi perla-build-eu-print-files.py: sopra una certa
                           # dimensione il generatore Printful impasta il motivo


def lavori():
    """[(handle, tipo, sorgente_su_disco, motivo)] per ogni prodotto da toccare."""
    idx = json.load(open("eu-index.json"))
    fuori = []
    for o in idx:
        tipo, titolo = o["tipo"], o["title"]
        neutro = "Crea il Tuo Design" in titolo
        if neutro:
            yield o, os.path.join(NEUTRI, NEUTRO_FILE[tipo]), "neutro"
            continue
        if tipo == "collare-eu" and titolo in COLLARI:
            yield o, "%s/collare-src-%s.jpg" % (SRC_COLLARI, COLLARI[titolo]), "nativo"
            continue
        motivo = titolo.split('"')[1] if '"' in titolo else ""
        if (tipo, motivo) in ALTRI:
            yield o, "%s/%s.jpg" % (SRC_ALTRI, ALTRI[(tipo, motivo)]), "nativo"
            continue
        if tipo == "bandana-eu" and o["mf"]:
            p = "pat/%s.img" % o["handle"][:70]
            if os.path.exists(p) and Image.open(p).size == (1200, 1200):
                yield o, p, "ingrandito"
                continue
        fuori.append((tipo, titolo))
    if fuori:
        print("\nnon toccati (hanno gia' il file nativo): %d" % len(fuori))


def costruisci():
    os.makedirs(OUT, exist_ok=True)
    piano = []
    for o, src, motivo in lavori():
        larg, alt = AREE[o["tipo"]]
        base = os.path.join(OUT, o["handle"][:70])
        pieno, mock = base + ".jpg", base + "-mockup.jpg"
        im = Image.open(src).convert("RGB")

        if im.size != (larg, alt):
            if motivo != "ingrandito":
                raise SystemExit("misura inattesa %s %s" % (src, im.size))
            # Lanczos, poi una maschera di contrasto leggera per recuperare il
            # microcontrasto che l'ingrandimento appiattisce. Niente di piu':
            # spingere oltre creerebbe aloni sui bordi dorati.
            im = im.resize((larg, alt), Image.LANCZOS).filter(
                ImageFilter.UnsharpMask(radius=2.0, percent=70, threshold=3))
        im.save(pieno, quality=95, subsampling=0)

        h = max(1, round(alt * MOCKUP_LATO_LUNGO / larg))
        im.resize((MOCKUP_LATO_LUNGO, h), Image.LANCZOS).save(
            mock, quality=95, subsampling=0)

        piano.append({"id": o["id"], "handle": o["handle"], "title": o["title"],
                      "tipo": o["tipo"], "motivo": motivo,
                      "pieno": pieno, "mockup": mock,
                      "mf_vecchio": o["mf"]})
        print("%-13s %-11s %-32s %5dx%-5d" % (o["tipo"], motivo, o["title"][:32], larg, alt))
    json.dump(piano, open(os.path.join(OUT, "piano.json"), "w"), indent=1)
    print("\n%d file in %s" % (len(piano), OUT))


def neutri():
    """Ricostruisce i file di stampa dei prodotti "Crea il Tuo Design".

    UNO SOLO ALLA VOLTA, E DI PROPOSITO
    Si passa il tipo sulla riga di comando. I quattro file neutri sono in
    catalogo da mesi e sono diversi fra loro -- il collare porta il
    medaglione ripetuto dieci volte lungo la fettuccia, la ciotola sei volte
    attorno al cilindro -- e ricostruirli tutti insieme cambierebbe prodotti
    che nessuno ha chiesto di cambiare. Si rifa' quello che va rifatto.

    PERCHE' NON ERANO GIA' QUI
    Erano quattro PNG committati a mano, senza il codice che li aveva fatti:
    per correggerne uno bisognava riaprire un editor di immagini e indovinare
    la misura del marchio. Adesso il marchio lo mette marchio.componi(), lo
    stesso che lo mette su tutto il resto del catalogo -- quindi inchiostro,
    alone e area sicura sono quelli di tutti gli altri prodotti, e non una
    seconda regola che nessuno ricorda di aggiornare.

        python3 scripts/perla-eu-print-files.py neutri ciotola-eu
    """
    tipi = sys.argv[2:]
    if not tipi:
        raise SystemExit("uso: ... neutri <tipo> [tipo ...]  fra: %s"
                         % ", ".join(sorted(NEUTRO_FILE)))
    for tipo in tipi:
        if tipo not in NEUTRO_FILE:
            raise SystemExit("tipo sconosciuto: %s" % tipo)
        larg, alt = AREE[tipo]
        # Il fondo e' bianco perche' il prodotto neutro E' bianco: quello che
        # il cliente disegna ci va sopra, e il marchio deve stare sul bianco
        # esattamente come ci starebbe sul prodotto finito.
        base = Image.new("RGB", (larg, alt), (255, 255, 255))
        chiave = tipo.replace("-", "_")
        fuori, box = marchio.componi(base, chiave)
        percorso = os.path.join(NEUTRI, NEUTRO_FILE[tipo])
        fuori.save(percorso)
        print("%-14s %5dx%-5d  %d marchio/i  %s"
              % (tipo, larg, alt, len(box), os.path.basename(percorso)))
        for s_, a_, w_, h_ in box:
            print("      a (%d, %d) grande %dx%d px" % (round(s_), round(a_), round(w_), round(h_)))


def carica():
    piano = json.load(open(os.path.join(OUT, "piano.json")))
    fatto = {}
    p_out = os.path.join(OUT, "uploads.json")
    if os.path.exists(p_out):
        fatto = json.load(open(p_out))
    for i, v in enumerate(piano, 1):
        if v["handle"] in fatto:
            continue
        for tentativo in range(3):
            r = subprocess.run(
                ["curl", "-s", "-m", "300", "-X", "POST", ENDPOINT,
                 "-F", "photo=@" + v["pieno"]], capture_output=True, text=True)
            try:
                d = json.loads(r.stdout)
            except Exception:
                d = {}
            if d.get("url"):
                fatto[v["handle"]] = {"url": d["url"], "printify_id": d.get("id")}
                print("%2d/%d  %-34s %s" % (i, len(piano), v["title"][:34], d["url"]))
                break
            print("%2d/%d  %-34s tentativo %d fallito: %s"
                  % (i, len(piano), v["title"][:34], tentativo + 1, r.stdout[:120]))
            time.sleep(5 * (tentativo + 1))
        json.dump(fatto, open(p_out, "w"), indent=1)
    print("\n%d/%d caricati" % (len(fatto), len(piano)))


if __name__ == "__main__":
    {"build": costruisci, "upload": carica, "neutri": neutri}[sys.argv[1]]()
