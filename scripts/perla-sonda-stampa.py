#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manda a Printify due sonde e riscarica i mockup: tinta piatta e scacchiera.

PERCHE' ESISTE
Per mettere un tipo nuovo nell'editor servono tre numeri che il fornitore NON
dichiara:

  - la SAGOMA vera del pezzo (che il tappetino a osso non e' un rettangolo);
  - dove cade l'area di stampa RISPETTO al pezzo, cioe' quanto deborda e viene
    tagliato;
  - la FINESTRA, dove il fornitore stampa a pieno contrasto.

Il catalogo dichiara solo "front 3150x2400". Che poi quei 3150x2400 finiscano
sul pezzo bordo a bordo, oppure debordino dell'8%, cambia dove il cliente vede
il proprio nome -- e la prima volta l'ho scoperto a mano, con due prodotti
sonda creati e cancellati a colpi di curl. La seconda volta serviva il
tappetino grande, e rifare tutto a mano era la strada per sbagliare un numero.

LE DUE SONDE, E PERCHE' DUE
  tinta piatta  Riempie l'area dichiarata di un colore solo. Sul mockup
                l'unica cosa scura e' il pezzo, il resto e' il fondo bianco
                dello studio: quel contorno E' la sagoma.
  scacchiera    Riempie la stessa area di caselle di passo noto. Le caselle si
                vedono anche dove il pezzo le taglia, quindi il loro passo in
                pixel dice quanto e' grande sul mockup una casella dell'AREA,
                e da li' l'area intera anche fuori dal pezzo. Senza la
                scacchiera la sagoma esce giusta di forma e sbagliata di
                posto.

CHE COSA LASCIA IN GIRO
Niente. I due prodotti sono bozze con un titolo che comincia per 'ZZ sonda' e
vengono cancellati alla fine, anche se qualcosa va storto (--tieni per
tenerli). Le immagini caricate restano nella libreria Printify: sono due, e
non danno fastidio a nessuno.

DOPO
    python3 scripts/perla-ricalca-sagoma.py <cartella>/piatto-73845-front.jpg \\
        --nome tappetino-osso-grande \\
        --scacchiera <cartella>/scacchiera-73845-front.jpg --griglia 10x8

USO
    python3 scripts/perla-sonda-stampa.py --blueprint 623 --provider 10 \\
        --varianti 73845 --cartella scratchpad/sonda-tappetino
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request

API = "https://api.printify.com/v1"
PAUSA = 1.0
COLONNE, RIGHE = 10, 8
CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "printify.local.env")


def config():
    """Le credenziali stanno solo nel file locale, che e' fuori da git."""
    if not os.path.exists(CONFIG):
        sys.exit("Manca %s" % CONFIG)
    testo = open(CONFIG, encoding="utf-8").read()

    def campo(nome):
        m = re.search(r"^%s=([^\r\n]*)" % nome, testo, re.M)
        return (m.group(1).strip() if m else "")

    chiave, negozio = campo("PRINTIFY_API_KEY"), campo("PRINTIFY_SHOP_ID")
    if not chiave or not negozio:
        sys.exit("PRINTIFY_API_KEY o PRINTIFY_SHOP_ID mancanti in %s" % CONFIG)
    return chiave, negozio


def chiama(chiave, metodo, percorso, corpo=None):
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(API + percorso, data=dati, method=metodo, headers={
        "Authorization": "Bearer " + chiave,
        "Content-Type": "application/json",
        "User-Agent": "perla-sonda-stampa/1.0",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        grezzo = r.read()
    return json.loads(grezzo) if grezzo else {}


def scarica(url, dove):
    """La CDN dei mockup risponde 403 a chi non si presenta come un browser."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; perla-sonda-stampa/1.0)",
        "Accept": "image/jpeg,image/*;q=0.8,*/*;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=120) as r, open(dove, "wb") as f:
        f.write(r.read())


def disegni(larghezza, altezza):
    """Le due sonde, generate qui: nessun file da tenere aggiornato a mano."""
    from PIL import Image, ImageDraw
    piatto = Image.new("RGB", (larghezza, altezza), (24, 26, 38))
    scacchiera = Image.new("RGB", (larghezza, altezza), (255, 255, 255))
    d = ImageDraw.Draw(scacchiera)
    passo_x, passo_y = larghezza / float(COLONNE), altezza / float(RIGHE)
    for r in range(RIGHE):
        for c in range(COLONNE):
            if (r + c) % 2 == 0:
                d.rectangle([c * passo_x, r * passo_y, (c + 1) * passo_x, (r + 1) * passo_y],
                            fill=(198, 32, 32))
    return {"piatto": piatto, "scacchiera": scacchiera}


def carica(chiave, immagine, nome, cartella):
    percorso = os.path.join(cartella, nome)
    immagine.save(percorso, quality=95)
    contenuto = base64.b64encode(open(percorso, "rb").read()).decode()
    return chiama(chiave, "POST", "/uploads/images.json",
                  {"file_name": nome, "contents": contenuto})["id"]


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--blueprint", type=int, required=True)
    a.add_argument("--provider", type=int, required=True)
    a.add_argument("--varianti", required=True, help="id separati da virgola")
    a.add_argument("--cartella", default="scratchpad/sonda")
    a.add_argument("--tieni", action="store_true", help="non cancellare le bozze")
    opz = a.parse_args()

    chiave, negozio = config()
    varianti = [int(v) for v in opz.varianti.split(",")]
    os.makedirs(opz.cartella, exist_ok=True)

    catalogo = chiama(chiave, "GET", "/catalog/blueprints/%d/print_providers/%d/variants.json"
                      % (opz.blueprint, opz.provider))
    misure = {}
    for v in catalogo.get("variants", []):
        if v["id"] in varianti:
            fronte = [p for p in v.get("placeholders", []) if p["position"] == "front"]
            if not fronte:
                sys.exit("La variante %d non ha un fronte." % v["id"])
            misure[v["id"]] = (fronte[0]["width"], fronte[0]["height"], v["title"])
    mancanti = [v for v in varianti if v not in misure]
    if mancanti:
        sys.exit("Varianti non trovate nel blueprint: %s" % mancanti)

    # Le varianti con la stessa area condividono una sonda sola: una chiamata
    # in meno e, soprattutto, un file in meno da confondere.
    gruppi = {}
    for vid, (w, h, titolo) in misure.items():
        gruppi.setdefault((w, h), []).append(vid)
    for (w, h), ids in sorted(gruppi.items()):
        print("area %dx%d (rapporto %.4f) -> varianti %s" % (w, h, w / float(h), ids))

    creati, esito = [], 0
    try:
        for tipo in ("piatto", "scacchiera"):
            aree = []
            for (w, h), ids in sorted(gruppi.items()):
                img = disegni(w, h)[tipo]
                nome = "%s-%dx%d.jpg" % (tipo, w, h)
                iid = carica(chiave, img, nome, opz.cartella)
                print("  caricato %s -> %s" % (nome, iid))
                time.sleep(PAUSA)
                aree.append({"variant_ids": ids, "placeholders": [
                    {"position": "front",
                     "images": [{"id": iid, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}]}]})
            prodotto = chiama(chiave, "POST", "/shops/%s/products.json" % negozio, {
                "title": "ZZ sonda %s (temporaneo)" % tipo,
                "description": "Sonda tecnica. Si cancella da sola.",
                "blueprint_id": opz.blueprint,
                "print_provider_id": opz.provider,
                "variants": [{"id": v, "price": 999, "is_enabled": True} for v in varianti],
                "print_areas": aree,
            })
            creati.append(prodotto["id"])
            print("  sonda %s creata: %s" % (tipo, prodotto["id"]))
            time.sleep(PAUSA)

            # I mockup non sono pronti appena il prodotto esiste: il fornitore
            # li rende, e la prima lettura torna spesso senza immagini.
            immagini = []
            for tentativo in range(10):
                p = chiama(chiave, "GET", "/shops/%s/products/%s.json" % (negozio, prodotto["id"]))
                immagini = p.get("images", [])
                if immagini:
                    break
                time.sleep(4)
            if not immagini:
                print("  ! nessun mockup dopo 40 secondi per %s" % tipo)
                esito = 1
                continue
            for im in immagini:
                if "front" not in (im.get("src") or ""):
                    continue
                for vid in im.get("variant_ids", []):
                    if vid not in varianti:
                        continue
                    nome = os.path.join(opz.cartella, "%s-%d-front.jpg" % (tipo, vid))
                    scarica(im["src"], nome)
                    print("  scaricato %s" % nome)
    finally:
        if opz.tieni:
            print("--tieni: le bozze %s restano su Printify." % creati)
        else:
            for pid in creati:
                try:
                    chiama(chiave, "DELETE", "/shops/%s/products/%s.json" % (negozio, pid))
                    print("  cancellata la sonda %s" % pid)
                except Exception as e:
                    print("  ! sonda %s NON cancellata, toglila a mano: %s" % (pid, e))
                    esito = 1
                time.sleep(PAUSA)
    return esito


if __name__ == "__main__":
    sys.exit(main())
