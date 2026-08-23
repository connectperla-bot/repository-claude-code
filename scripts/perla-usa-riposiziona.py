#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rimette al centro gli artwork che su Printify sono piazzati fuori dall'area.

IL DIFETTO, MISURATO
Su Printify ogni livello di stampa ha una posizione (x, y), una scala e un
angolo, in frazioni dell'area. Un artwork che copre tutto il prodotto sta a
x=0,5 y=0,5 scala=1,0 angolo=0. Sessantadue livelli su ottantuno sono cosi'.

Gli altri diciannove no, e non di poco:

    Perla Italia Pinstripe Dog Collar   y=-0,49  ruotato 90  scala 0,17
    Navy & Gold Baroque Dog Collar      y= 2,98  ruotato 90  scala 0,20
    Perla Italia Burgundy Damask Collar y= 2,46              scala 0,63
    Teal Chevron Dog Collar             y= 1,14              scala 0,23

y=2,98 vuol dire che il disegno sta tre aree piu' in basso: sul prodotto non
si vede affatto. y=-0,49 vuol dire meta' fuori dal bordo superiore. E una
scala di 0,17 su un collare lascia l'83% del nastro vuoto.

E' questo che la titolare vedeva e chiamava "tagliati, ripetuti male e
decentrati". Non era il disegno: era dove il disegno era stato messo. Undici
collari, quattro medagliette, una bandana.

COSA FA
Riporta i livelli di FONDO a x=0,5 y=0,5 scala=1,0 angolo=0 -- centrati e a
coprire, come i sessantadue che sono gia' giusti -- e toglie le copie
doppie dello stesso artwork nello stesso riquadro.

COSA NON TOCCA, E PERCHE'
  * i marchi sovrapposti (scala sotto 0,15). Sulle cucce quel livello E' il
    marchio, e sui prodotti neutri -- "Blank Round Pet ID Tag", "Plain White
    Triangle", "Plush White Pet Bed" -- e' l'unico contenuto: centrarlo a
    coprire lo stamperebbe grande come il letto.
  * i livelli gia' a posto. Si riscrive solo cio' che e' fuori tolleranza,
    cosi' un giro a vuoto non cambia niente e si puo' rieseguire senza paura.

USO
    python3 scripts/perla-usa-riposiziona.py                    # elenca
    python3 scripts/perla-usa-riposiziona.py --solo "Pinstripe" --applica
    python3 scripts/perla-usa-riposiziona.py --applica          # tutti
"""
import json
import os
import sys
import urllib.error
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)

# I file che sono MARCHI, non disegni di fondo: non si centrano e non si
# ingrandiscono mai.
MARCHI = ("logo perla - copia.png", "perla-combined-logo.png",
          "v2-01-logo-centrale.png", "v3-square-coaster-logo.png",
          "logo-full.png")

# Sotto questa scala un livello e' un marchio o una firma, non il disegno.
SCALA_FONDO = 0.15
# Quanto puo' scostarsi dal centro prima di essere considerato fuori posto.
# 0,15 e' largo apposta: alcuni disegni sono volutamente decentrati di poco e
# non vanno raddrizzati per pignoleria.
TOLLERANZA = 0.15
# LA SCALA RIDOTTA NON E' UN DIFETTO, e questa e' la lezione piu' cara di
# tutto il lavoro. Prima stesura: "sotto 0,90 il disegno lascia scoperta
# troppa area". Applicata alla medaglietta "Blue & Gold" (scala 0,66) e
# guardato il mockup vero prima e dopo: il PRIMA era giusto. Su un tondo il
# disegno quadrato deve stare DENTRO il cerchio, e portandolo a coprire la
# cornice esce dal tondo e la scritta tocca il bordo. Il prodotto e' stato
# rimesso com'era.
#
# Restano difetti solo le due cose che non possono mai essere volute:
# il disegno piazzato FUORI dall'area, e il disegno ruotato di traverso.


def chiavi():
    valori = {}
    with open(os.path.join(RADICE, "config", "printify.local.env")) as fh:
        for riga in fh:
            if "=" in riga and not riga.strip().startswith("#"):
                k, v = riga.strip().split("=", 1)
                valori[k] = v
    return valori["PRINTIFY_API_KEY"], valori["PRINTIFY_SHOP_ID"]


def api(metodo, percorso, token, corpo=None):
    req = urllib.request.Request(
        "https://api.printify.com" + percorso, method=metodo,
        headers={"Authorization": "Bearer " + token, "User-Agent": "perla",
                 "Content-Type": "application/json"},
        data=json.dumps(corpo).encode() if corpo is not None else None)
    with urllib.request.urlopen(req, timeout=120) as r:
        testo = r.read().decode()
    return json.loads(testo) if testo.strip() else {}


def e_marchio(nome):
    return (nome or "").lower() in MARCHI


def fuori_posto(im):
    """Perche' questo livello e' sbagliato. Lista vuota = va bene com'e'."""
    perche = []
    if abs(im.get("x", 0.5) - 0.5) > TOLLERANZA:
        perche.append("x=%.2f" % im.get("x", 0.5))
    if abs(im.get("y", 0.5) - 0.5) > TOLLERANZA:
        perche.append("y=%.2f" % im.get("y", 0.5))
    if im.get("angle", 0) not in (0, 180):
        perche.append("ruotato %s" % im.get("angle"))
    return perche


def sistema(prodotto):
    """Il prodotto corretto e l'elenco di cosa e' cambiato, o (None, [])."""
    cambi = []
    aree = json.loads(json.dumps(prodotto.get("print_areas", [])))
    for area in aree:
        # Un riquadro senza immagini -- il RETRO di una medaglietta, che spesso
        # e' vuoto -- va omesso, non mandato con la lista vuota: Printify
        # risponde "images field is required" e rifiuta tutto il salvataggio.
        area["placeholders"] = [q for q in area.get("placeholders", [])
                                if q.get("images")]
        for posto in area.get("placeholders", []):
            tenute, viste = [], set()
            for im in posto.get("images", []):
                nome = im.get("name") or ""
                if e_marchio(nome) or im.get("scale", 1.0) < SCALA_FONDO:
                    tenute.append(im)               # marchi: non si toccano
                    continue
                if nome in viste:
                    cambi.append("tolta copia doppia di %s" % nome[:30])
                    continue                        # doppione dello stesso file
                viste.add(nome)
                perche = fuori_posto(im)
                if perche:
                    # Si rimette al centro e si raddrizza, ma LA SCALA NON SI
                    # TOCCA: e' una scelta di disegno, non un difetto.
                    cambi.append("%s: %s -> rimesso al centro, dritto"
                                 % (nome[:30], ", ".join(perche)))
                    im["x"], im["y"] = 0.5, 0.5
                    im["angle"] = 0
                tenute.append(im)
            # Printify accetta SOLO questi campi nel salvataggio: rimandarle
            # l'immagine com'e' arrivata -- con name, src, width, height --
            # fa rispondere 500 senza dire quale campo dia fastidio.
            posto["images"] = [
                {"id": im["id"], "x": im.get("x", 0.5), "y": im.get("y", 0.5),
                 "scale": im.get("scale", 1.0), "angle": im.get("angle", 0)}
                for im in tenute]
    return (aree, cambi) if cambi else (None, [])


def main(argv):
    applica = "--applica" in argv
    solo = None
    if "--solo" in argv:
        solo = argv[argv.index("--solo") + 1].lower()

    token, shop = chiavi()
    prodotti, pagina = [], 1
    while True:
        d = api("GET", "/v1/shops/%s/products.json?limit=50&page=%d" % (shop, pagina), token)
        prodotti += d.get("data", [])
        if pagina >= d.get("last_page", 1):
            break
        pagina += 1

    toccati = saltati = 0
    for p in prodotti:
        ext = p.get("external", {}) or {}
        if not (p.get("visible") and ext.get("id")):
            continue
        if solo and solo not in p["title"].lower():
            continue
        aree, cambi = sistema(p)
        if not cambi:
            saltati += 1
            continue
        toccati += 1
        print("\n%s" % p["title"][:70])
        for c in cambi:
            print("    %s" % c)
        if applica:
            try:
                api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                    token, {"print_areas": aree})
                print("    -> salvato")
            except urllib.error.HTTPError as err:
                print("    -> ERRORE %s: %s" % (err.code, err.read().decode()[:200]))

    print("\n%d prodotti da correggere, %d gia' a posto." % (toccati, saltati))
    if not applica:
        print("(elenco soltanto: aggiungi --applica)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
