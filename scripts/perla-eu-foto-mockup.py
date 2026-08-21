#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rigenera le foto dei prodotti EU dal file di stampa vero.

PERCHE'
Le foto sul sito erano state generate quando custom.editor_pattern_image
puntava a una riduzione a 1200px del disegno: non erano la fotografia del
prodotto che parte davvero. Ora il metafield punta al file nativo (7169x315 per
un collare) e /generate-mockup lo manda a Printful a piena risoluzione -- vedi
il commento ROUND 23 in perla-upload-endpoint.js.

LA NITIDEZZA
Il mockup esce sempre 1000x1000: create-task non ha un parametro di larghezza.
Il motivo viene quindi ridotto di circa dodici volte, e una maschera di
contrasto applicata PRIMA della riduzione recupera cio' che la riduzione
appiattisce. Misurato sul collare "Barocco", gradiente sulla cinghia:

    foto che c'era sul sito          15,24
    rigenerata senza nitidezza       15,25
    rigenerata con w_2400,e_sharpen  16,10

Si applica infilando la trasformazione nella URL Cloudinary che il prodotto ha
gia': nessun file nuovo da caricare, e resta una URL res.cloudinary.com, cioe'
passa la validazione di urlCompositoValida sul server.

IL FONDO BIANCO
Printful restituisce un PNG col fondo trasparente, su una URL sotto /tmp/ che
scade. Va comunque riscaricato e riospitato; nel farlo si appiattisce su bianco,
come il resto del catalogo.

IL RITMO
Printful risponde 429 dopo quattro richieste ravvicinate, dicendo lui stesso
quanti secondi aspettare. Da qui la pausa e il rispetto di quel numero.

RIPRESA
Il contenitore di lavoro si riavvia spesso e si porta via il disco. Il
segnaposto vero non e' qui: e' su Shopify, dove i prodotti gia' sistemati hanno
featuredMedia.image.altText che finisce con "— Perla Italia" (campo gia_fatta
nel manifest), e su Cloudinary, che tiene le URL per sempre. out-foto/ e' solo
un'area di transito.

RIFARE UNA FOTO GIA' FATTA
Il segnaposto gia_fatta serve a non ripetere il lavoro dopo un riavvio, ma
diventa un ostacolo quando il DISEGNO cambia: e' successo alle venti bandane,
sostituite con i file ricavati dai motivi nativi dei collari
(perla-bandane-da-collari.py). Le foto sul sito continuavano a mostrare il
disegno vecchio -- su nove delle diciannove nemmeno il colore corrispondeva --
mentre in stampa partiva quello nuovo: il cliente vedeva una cosa e ne
riceveva un'altra. Con --rifai il segnaposto viene ignorato e la foto si
rigenera dal pattern che c'e' adesso nel manifest.

--solo restringe a handle precisi (per sottostringa), cosi' si rigenerano le
poche foto rimaste indietro invece di tutta la famiglia: dei ventidue fra
ciotole e guinzagli, solo dodici hanno il file di stampa piu' recente della
foto, e le altre dieci sarebbero mezz'ora di chiamate a Printful per riavere
la stessa immagine.

    python3 scripts/perla-eu-foto-mockup.py [--tipi collare_eu,bandana_eu] [--max 8]
    python3 scripts/perla-eu-foto-mockup.py --tipi bandana_eu --rifai
    python3 scripts/perla-eu-foto-mockup.py --tipi ciotola_eu --rifai --solo onda,smeraldo
"""
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image

MOCKUP = "https://perla-upload-endpoint-yizy.onrender.com/generate-mockup"
UPLOAD = "https://perla-upload-endpoint-yizy.onrender.com/upload"
OUT = "out-foto"
PAUSA = 45
TRASF = "w_2400,e_sharpen:100"
# id inesistente di proposito: la rotta esige composite_image_id ma non lo
# guarda quando la URL e' valida. Se la validazione della URL smettesse di
# passare, questo fa fallire la chiamata invece di produrre in silenzio la foto
# di un altro prodotto.
ID_FINTO = "solo-url"
QUI = os.path.dirname(os.path.abspath(__file__))


def tipo_di(handle):
    for t in ("collare-eu", "bandana-eu", "ciotola-eu", "guinzaglio-eu"):
        if handle.startswith(t):
            return t.replace("-", "_")
    raise SystemExit("tipo sconosciuto: " + handle)


def url_nitida(url):
    marca = "/image/upload/"
    testa, coda = url.split(marca, 1)
    return testa + marca + TRASF + "/" + coda


def posta(url, dati=None, file=None, timeout="300"):
    cmd = ["curl", "-s", "-m", timeout, "-X", "POST", url]
    if dati is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(dati)]
    if file:
        cmd += ["-F", "photo=@" + file]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": "risposta illeggibile", "detail": r.stdout[:200]}


def attesa_429(d):
    testo = json.dumps(d)
    if "429" not in testo:
        return None
    m = re.search(r"try again after (\d+) second", testo)
    return int(m.group(1)) + 5 if m else 65


def bianco(sorgente, dest):
    im = Image.open(sorgente)
    if im.mode in ("RGBA", "LA"):
        fondo = Image.new("RGB", im.size, "white")
        fondo.paste(im, mask=im.split()[-1])
        im = fondo
    im = im.convert("RGB")
    im.save(dest, quality=95, subsampling=0)
    return im.size


def main():
    args = sys.argv[1:]
    tipi = None
    massimo = 999
    rifai = "--rifai" in args
    solo = None
    if "--solo" in args:
        solo = [s for s in args[args.index("--solo") + 1].split(",") if s]
    if "--tipi" in args:
        tipi = set(args[args.index("--tipi") + 1].split(","))
    if "--max" in args:
        massimo = int(args[args.index("--max") + 1])
    if rifai and tipi is None:
        raise SystemExit("--rifai va usato insieme a --tipi: rifare tutto il "
                         "catalogo per sbaglio costa un'ora di chiamate a Printful")

    os.makedirs(OUT, exist_ok=True)
    prodotti = json.load(open(os.path.join(QUI, "perla-eu-prodotti.json")))
    p_out = os.path.join(OUT, "ospitate.json")
    ospitate = json.load(open(p_out)) if os.path.exists(p_out) else {}

    coda = [p for p in prodotti
            if (rifai or (not p["gia_fatta"] and p["handle"] not in ospitate))
            and (tipi is None or tipo_di(p["handle"]) in tipi)
            and (solo is None or any(s in p["handle"] for s in solo))][:massimo]
    if solo is not None and not coda:
        raise SystemExit("--solo non ha selezionato niente: controlla le sottostringhe")
    print("%d da fare adesso (%d gia' ospitate, %d gia' live)%s\n"
          % (len(coda), len(ospitate), sum(1 for p in prodotti if p["gia_fatta"]),
             "  [--rifai: si rigenera anche cio' che risultava gia' fatto]" if rifai else ""))

    for i, p in enumerate(coda, 1):
        tipo = tipo_di(p["handle"])
        d = None
        for _ in range(4):
            d = posta(MOCKUP, {"product_type": tipo, "composite_image_id": ID_FINTO,
                               "composite_image_url": url_nitida(p["pattern"])})
            if d.get("images"):
                break
            att = attesa_429(d)
            if att:
                print("   429, aspetto %ds" % att)
                time.sleep(att)
                continue
            print("%2d/%d  %-32s MOCKUP FALLITO: %s" % (i, len(coda), p["title"][:32], str(d)[:150]))
            d = None
            break
        if not d or not d.get("images"):
            time.sleep(PAUSA)
            continue

        # TUTTE le inquadrature, non solo la prima.
        # /generate-mockup ne restituisce fino a quattro -- la principale piu'
        # gli extra[] di Printful (piegato, indossato, di lato): il lavoro lato
        # server e' gia' fatto, vedi perla-upload-endpoint.js righe 505-533.
        # Qui se ne prendeva una sola, ed e' per questo che i 66 prodotti EU
        # avevano una foto contro le otto dei Printify.
        indirizzi = []
        for n, sorgente in enumerate(d["images"], 1):
            base = "%s-%d" % (p["handle"][:66], n)
            grezzo = os.path.join(OUT, base + ".png")
            finito = os.path.join(OUT, base + ".jpg")
            subprocess.run(["curl", "-s", "-m", "180", "-o", grezzo, sorgente])
            if not os.path.exists(grezzo) or os.path.getsize(grezzo) < 5000:
                print("%2d/%d  %-32s scarico fallito (%d)" % (i, len(coda), p["title"][:32], n))
                continue
            misura = bianco(grezzo, finito)
            os.remove(grezzo)
            u = posta(UPLOAD, file=finito)
            if not u.get("url"):
                print("%2d/%d  %-32s upload fallito (%d): %s"
                      % (i, len(coda), p["title"][:32], n, str(u)[:100]))
                continue
            indirizzi.append(u["url"])

        if not indirizzi:
            time.sleep(PAUSA)
            continue

        # La chiave resta il handle, ma il valore ora e' un ELENCO. Le voci
        # vecchie sono stringhe singole: chi legge questo file deve accettare
        # entrambe le forme finche' non sono state rifatte tutte.
        ospitate[p["handle"]] = indirizzi
        json.dump(ospitate, open(p_out, "w"), indent=1)
        print("%2d/%d  %-32s %s  %d foto" % (i, len(coda), p["title"][:32], misura, len(indirizzi)))
        time.sleep(PAUSA)

    print("\n%d ospitate in totale" % len(ospitate))


if __name__ == "__main__":
    main()
