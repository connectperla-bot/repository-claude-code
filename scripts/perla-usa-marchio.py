#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sostituisce il marchio sgranato con quello grande, sui prodotti Printify.

IL DIFETTO
"LOGO PERLA - Copia.PNG" e' 554x408 e sulle cucce viene stampato largo circa
1350 px: ingrandito 2,4 volte. Era l'ultimo livello sotto risoluzione rimasto
dopo il rifacimento dei motivi. In magazzino c'e' gia' perla-combined-logo.png
a 1600x2528, nitido, e tre cucce lo usavano gia': il catalogo era incoerente
anche prima.

LARGHEZZA UGUALE, POSIZIONE CORRETTA
`scale` su Printify e' la larghezza dell'immagine come frazione della
larghezza dell'area. Il marchio vecchio e' 554x408, quello nuovo 1600x2528:
proporzioni diverse, quindi qualcosa cambia per forza.

Primo tentativo: pareggiare l'ALTEZZA, cioe' ridurre la scala di 0,466.
Sbagliato -- guardato il mockup, il marchio passava da 1357 a 383 px di
larghezza e sulla cuccia restava una perlina illeggibile. Su un marchio
quello che si vede e' la larghezza.

Quindi si tiene la scala com'era (stessa larghezza a video) e si ALZA il
marchio di meta' della differenza di altezza, cosi' il bordo inferiore
resta dov'era invece di finire nella parte che la cuccia arrotola sotto.

USO
    python3 scripts/perla-usa-marchio.py            # elenca e basta
    python3 scripts/perla-usa-marchio.py --applica
"""
import base64
import json
import os
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
NUOVO = os.path.join(RADICE, "generated-designs", "perla-combined-logo.png")
VECCHIO = "LOGO PERLA - Copia.PNG"
# Dopo il primo giro il marchio vecchio non c'e' piu' su quei prodotti: per
# correggere la posizione si riconosce quello nuovo messo male.
DA_CORREGGERE = "perla-combined-logo.png"


def chiavi():
    valori = {}
    with open(os.path.join(RADICE, "config", "printify.local.env")) as fh:
        for riga in fh:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip()
    return valori


def api(metodo, percorso, corpo=None, token=None):
    cmd = ["curl", "-s", "-X", metodo, "-H", "Authorization: Bearer " + token,
           "-H", "Content-Type: application/json", "https://api.printify.com" + percorso]
    tmp = None
    if corpo is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(corpo, tmp); tmp.close()
        cmd[1:1] = ["--data-binary", "@" + tmp.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    finally:
        if tmp:
            os.unlink(tmp.name)
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError("risposta non JSON: " + out[:200])


def main():
    env = chiavi()
    token, shop = env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"]
    applica = "--applica" in sys.argv
    # Il marchio piccolo sta su 49 prodotti, ma SOTTO RISOLUZIONE solo sulle
    # cucce: li' l'area e' 15600 px e il marchio viene stampato a 1350, mentre
    # su una bandana da 4275 sta a 370 e i 554 px bastano. Cambiarlo altrove
    # non e' una riparazione, e' una scelta di immagine -- e cambia la
    # dicitura da "PERLA" a "Perla Italia". Con --tutti si estende a tutti.
    solo_cucce = "--tutti" not in sys.argv

    prodotti, pagina = [], 1
    while True:
        d = api("GET", "/v1/shops/%s/products.json?limit=50&page=%d" % (shop, pagina), token=token)
        prodotti += d["data"]
        if pagina >= d["last_page"]:
            break
        pagina += 1

    bersaglio = DA_CORREGGERE if "--correggi" in sys.argv else VECCHIO
    da_fare = [p for p in prodotti if (not solo_cucce or p["blueprint_id"] == 419) and any(
        im.get("name") == bersaglio
        for pa in p.get("print_areas", [])
        for ph in pa.get("placeholders", [])
        for im in ph.get("images", []))]
    print("%d prodotti hanno il marchio piccolo" % len(da_fare))
    if not applica:
        for p in da_fare:
            print("  " + p["title"][:64])
        print("\n(elenco soltanto: aggiungi --applica" +
              ("; --tutti per estendere oltre le cucce)" if solo_cucce else ")"))
        return

    with open(NUOVO, "rb") as fh:
        contenuto = base64.b64encode(fh.read()).decode("ascii")
    caricato = api("POST", "/v1/uploads/images.json", token=token,
                   corpo={"file_name": os.path.basename(NUOVO), "contents": contenuto})
    if "id" not in caricato:
        raise SystemExit("caricamento marchio fallito: " + json.dumps(caricato)[:200])
    print("marchio caricato: %dx%d" % (caricato["width"], caricato["height"]))
    prop_nuova = caricato["height"] / float(caricato["width"])
    AREE = {419: (15600, 12600), 562: (4275, 2325), 566: (810, 900),
            570: (2760, 750), 784: (9519, 338)}

    fatti = 0
    for p in da_fare:
        aree = json.loads(json.dumps(p["print_areas"]))
        toccati = 0
        for pa in aree:
            for ph in pa.get("placeholders", []):
                nuove = []
                for im in ph.get("images", []):
                    if im.get("name") != bersaglio:
                        nuove.append(im)
                        continue
                    prop_vecchia = im["height"] / float(im["width"])
                    larghezza_area, altezza_area = AREE[p["blueprint_id"]]
                    largo = im["scale"] * larghezza_area
                    alto_prima = largo * prop_vecchia
                    alto_dopo = largo * prop_nuova
                    y = im["y"] - (alto_dopo - alto_prima) / 2.0 / altezza_area
                    nuove.append({
                        "id": caricato["id"], "name": caricato["file_name"],
                        "type": caricato.get("mime_type", "image/png"),
                        "height": caricato["height"], "width": caricato["width"],
                        "x": im["x"], "y": round(max(0.02, min(0.98, y)), 6),
                        "angle": im.get("angle", 0), "scale": im["scale"],
                    })
                    toccati += 1
                ph["images"] = nuove
            pa["placeholders"] = [x for x in pa.get("placeholders", []) if x.get("images")]
        r = api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                token=token, corpo={"print_areas": aree})
        if r.get("id") != p["id"]:
            print("  ERRORE %-44s %s" % (p["title"][:44], json.dumps(r)[:140]))
            continue
        print("  %-52s %d marchi" % (p["title"][:52], toccati))
        fatti += 1
    print("\n%d prodotti aggiornati" % fatti)


if __name__ == "__main__":
    main()
