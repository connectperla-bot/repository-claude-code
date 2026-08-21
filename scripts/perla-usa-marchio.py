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

FUORI DALLE CUCCE NON BASTA CAMBIARE IL FILE
Provato con --tutti su una bandana e guardato il mockup: il marchio nuovo,
alto il doppio a parita' di larghezza, finisce oltre la punta del triangolo e
viene tagliato. Guardato il retro per escludere che fosse una piega: e' bianco,
la stoffa finisce li' davvero. E guardando la foto di prima si scopre che era
tagliato anche quello vecchio: la posizione era gia' sbagliata.

Ma il motivo vero e' un altro, ed e' venuto fuori elencando i livelli. Il
disegno di fondo di OGNI bandana e OGNI medaglietta si chiama "...-perla.jpg":
il marchio e' gia' dentro l'artwork. Quello sovrapposto e' un SECONDO marchio,
e per giunta non e' sempre lo stesso file -- in giro ce ne sono quattro
("LOGO PERLA - Copia.PNG", "v2-01-logo-centrale.png",
"v3-square-coaster-logo.png", "perla-combined-logo.png"), e due prodotti non ne
hanno nessuno.

Quindi qui non c'e' un file da sostituire: c'e' da decidere se il marchio
sovrapposto ci deve stare. La bandana di prova e' stata rimessa com'era
(LOGO PERLA - Copia.PNG, x=0.500 y=0.863 scale=0.0447). Sulle cucce il lavoro
resta valido: li' il marchio era davvero sotto risoluzione e non ce n'e' un
altro nell'artwork.

USO
    python3 scripts/perla-usa-marchio.py            # elenca e basta
    python3 scripts/perla-usa-marchio.py --applica
    python3 scripts/perla-usa-marchio.py --tutti --solo "Ocean Wave" --applica
    python3 scripts/perla-usa-marchio.py --rimuovi              # elenca
    python3 scripts/perla-usa-marchio.py --rimuovi --applica    # toglie
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
# Due nomi per lo stesso difetto: la cuccia "Geometric Tribal" usa un terzo
# file di marchio, logo-full.png, 600x507, che sta a 0,23 di copertura.
VECCHIO = ("LOGO PERLA - Copia.PNG", "logo-full.png")
# Dopo il primo giro il marchio vecchio non c'e' piu' su quei prodotti: per
# correggere la posizione si riconosce quello nuovo messo male.
DA_CORREGGERE = "perla-combined-logo.png"
# Per RIMUOVERE il marchio sovrapposto servono tutti i nomi, non i due che
# bastavano a sostituirlo: nel catalogo ne girano cinque, uno diverso quasi per
# ogni ondata di prodotti.
MARCHI = VECCHIO + (DA_CORREGGERE, "v2-01-logo-centrale.png",
                    "v3-square-coaster-logo.png")


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


def vendibile(p):
    """Vero se cambiare il marchio a questo prodotto serve a qualcuno.

    Due modi di non servire a niente, e li abbiamo incontrati entrambi:

    - il prodotto non ha `external.id`, cioe' su Shopify non esiste. Sono i
      quattro "Copy of" rimasti solo dentro Printify.
    - nessuna variante e' insieme abilitata e disponibile. Sono i 18 collari:
      il fornitore ha tutte e 288 le varianti a is_available: false, il PUT
      risponde 500 su qualunque cosa, e su Shopify stanno in bozza. Scriverci
      sopra vuol dire soltanto raccogliere errori.

    La regola guarda i dati, non l'elenco dei nomi: se un giorno i collari
    tornano producibili, rientrano da soli senza toccare il codice.
    """
    if not (p.get("external") or {}).get("id"):
        return False
    return any(v.get("is_enabled") and v.get("is_available")
               for v in p.get("variants", []))


def togli(da_fare, bersaglio, shop, token):
    """Toglie il marchio sovrapposto, lasciando l'artwork.

    MAI SVUOTARE UN'AREA DI STAMPA
    Due prodotti -- "Pet Bandana - Plain White Triangle" e "Blank Round Pet ID
    Tag" -- hanno SOLO il logo e nessun disegno di fondo: sono i "Crea il Tuo
    Design", dove il cliente porta lui l'immagine. Togliere il livello li
    lascerebbe con niente da stampare. Quindi il logo si rimuove solo se nel
    placeholder resta almeno un'altra immagine: i due si escludono da soli, e
    non c'e' nessun elenco di nomi da tenere aggiornato.
    """
    fatti = saltati = 0
    for p in da_fare:
        aree = json.loads(json.dumps(p["print_areas"]))
        tolti = 0
        for pa in aree:
            for ph in pa.get("placeholders", []):
                immagini = ph.get("images", [])
                restano = [im for im in immagini if im.get("name") not in bersaglio]
                if not restano:
                    continue          # qui il marchio E' il disegno: si lascia
                tolti += len(immagini) - len(restano)
                ph["images"] = restano
            pa["placeholders"] = [x for x in pa.get("placeholders", []) if x.get("images")]
        if not tolti:
            print("  %-52s solo marchio, lasciato com'e'" % p["title"][:52])
            saltati += 1
            continue
        r = api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                token=token, corpo={"print_areas": aree})
        if r.get("id") != p["id"]:
            print("  ERRORE %-44s %s" % (p["title"][:44], json.dumps(r)[:140]))
            continue
        print("  %-52s -%d marchi" % (p["title"][:52], tolti))
        fatti += 1
    print("\n%d prodotti ripuliti%s" % (fatti, ", %d lasciati intatti" % saltati if saltati else ""))


def main():
    env = chiavi()
    token, shop = env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"]
    applica = "--applica" in sys.argv
    rimuovi = "--rimuovi" in sys.argv
    # Il marchio piccolo sta su 49 prodotti, ma SOTTO RISOLUZIONE solo sulle
    # cucce: li' l'area e' 15600 px e il marchio viene stampato a 1350, mentre
    # su una bandana da 4275 sta a 370 e i 554 px bastano. Cambiarlo altrove
    # non e' una riparazione, e' una scelta di immagine -- e cambia la
    # dicitura da "PERLA" a "Perla Italia". Con --tutti si estende a tutti.
    #
    # La rimozione invece riguarda per definizione bandane e medagliette, dove
    # il marchio e' gia' dentro l'artwork: limitarla alle cucce non vorrebbe
    # dire niente, quindi --rimuovi vale su tutto.
    solo_cucce = "--tutti" not in sys.argv and not rimuovi

    prodotti, pagina = [], 1
    while True:
        d = api("GET", "/v1/shops/%s/products.json?limit=50&page=%d" % (shop, pagina), token=token)
        prodotti += d["data"]
        if pagina >= d["last_page"]:
            break
        pagina += 1

    if rimuovi:
        bersaglio = MARCHI
    elif "--correggi" in sys.argv:
        bersaglio = (DA_CORREGGERE,)
    else:
        bersaglio = VECCHIO

    def in_gioco(p):
        # La rimozione riguarda SOLO bandane (562) e medagliette (566): sono
        # quelle il cui artwork porta gia' il marchio, quindi quello
        # sovrapposto e' un doppione. Sulle cucce (419) il marchio e' uno solo
        # ed e' quello che abbiamo appena portato ad alta risoluzione: toglierlo
        # vorrebbe dire cancellare il lavoro fatto.
        if rimuovi:
            return p["blueprint_id"] in (562, 566)
        return not solo_cucce or p["blueprint_id"] == 419

    col_marchio = [p for p in prodotti if in_gioco(p) and any(
        im.get("name") in bersaglio
        for pa in p.get("print_areas", [])
        for ph in pa.get("placeholders", [])
        for im in ph.get("images", []))]
    da_fare = [p for p in col_marchio if vendibile(p)]
    scartati = len(col_marchio) - len(da_fare)
    # La regola "stessa larghezza" e' stata tarata guardando un mockup di
    # cuccia, area 15600x12600. Su una bandana (4275x2325) e su una
    # medaglietta (810x900) le proporzioni sono altre: prima di applicarla a
    # venti prodotti se ne fa uno per tipo e lo si guarda.
    if "--solo" in sys.argv:
        pezzi = [s for s in sys.argv[sys.argv.index("--solo") + 1].split(",") if s]
        da_fare = [p for p in da_fare if any(s.lower() in p["title"].lower() for s in pezzi)]
        if not da_fare:
            raise SystemExit("--solo non ha selezionato niente: controlla le sottostringhe")
    print("%d prodotti hanno il marchio piccolo, %d in vendita%s"
          % (len(col_marchio), len(da_fare),
             " (%d saltati: fuori vendita o non su Shopify)" % scartati if scartati else ""))
    if not applica:
        for p in da_fare:
            print("  " + p["title"][:64])
        print("\n(elenco soltanto: aggiungi --applica" +
              ("; --tutti per estendere oltre le cucce)" if solo_cucce else ")"))
        return

    if rimuovi:
        togli(da_fare, bersaglio, shop, token)
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
                    if im.get("name") not in bersaglio:
                        nuove.append(im)
                        continue
                    prop_vecchia = im["height"] / float(im["width"])
                    larghezza_area, altezza_area = AREE[p["blueprint_id"]]
                    largo = im["scale"] * larghezza_area
                    alto_prima = largo * prop_vecchia
                    alto_dopo = largo * prop_nuova
                    # Se il marchio era stato messo piu' largo di quanto il
                    # file nuovo consenta, si riduce fino alla sua risoluzione
                    # vera invece di ingrandirlo di nuovo. Succede sulla cuccia
                    # "Geometric Tribal", dove il marchio stava a 2621 px e il
                    # file ne ha 1600: lasciandolo com'era sarebbe rimasto
                    # l'unico livello sgranato di tutto il catalogo.
                    scala = im["scale"]
                    massima = caricato["width"] / float(larghezza_area)
                    if scala > massima:
                        scala = massima
                        largo = scala * larghezza_area
                        alto_dopo = largo * prop_nuova
                    y = im["y"] - (alto_dopo - alto_prima) / 2.0 / altezza_area
                    nuove.append({
                        "id": caricato["id"], "name": caricato["file_name"],
                        "type": caricato.get("mime_type", "image/png"),
                        "height": caricato["height"], "width": caricato["width"],
                        "x": im["x"], "y": round(max(0.02, min(0.98, y)), 6),
                        "angle": im.get("angle", 0), "scale": round(scala, 6),
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
