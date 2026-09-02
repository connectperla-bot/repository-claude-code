#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ogni variante in vendita copre il suo costo, spedizione compresa?

PERCHE' ESISTE
Il 2 settembre 2026 un controllo a mano ha trovato che 109 varianti su 253
stavano sotto il 20% di margine e TRE si vendevano IN PERDITA: la cuccia
28x18 a 71,90 EUR costava 89,12 (-17,22 a copia), la 40x30 -9,2%, e la
ciotola EU a 36,90 ne costava 41,24. Nessuno se n'era accorto perche' il
prezzo di listino non dice niente da solo: il costo vero e' prodotto +
spedizione + IVA, e la spedizione dagli Stati Uniti verso l'Italia su una
cuccia vale 73-88 dollari, piu' del prodotto stesso.

I prezzi si spostano da soli: i fornitori li ritoccano, il cambio si muove,
le fasce di spedizione cambiano. Questo script rimisura tutto dal vivo, cosi'
la prossima volta la scoperta arriva prima di una vendita in perdita e non
dopo.

DA DOVE VENGONO I NUMERI, TUTTI MISURATI E NESSUNO SCRITTO A MANO
  prezzi di vendita   perlaitaly.com/products.json -- la vetrina pubblica,
                      nessun token: e' esattamente cio' che vede il cliente
  costo Printify      API prodotti (costo per variante) + API spedizione del
                      blueprint, profilo che contiene l'Italia
  costo Printful      /orders/estimate-costs verso un indirizzo italiano vero:
                      e' l'unico numero che comprende gia' spedizione E IVA,
                      e l'IVA qui si paga davvero perche' il negozio non ha
                      partita IVA e non la puo' recuperare
  cambio              open.er-api.com, con la data di aggiornamento stampata

USO
    python3 scripts/perla-verifica-margini.py                 # tabella
    python3 scripts/perla-verifica-margini.py --soglia 25     # altra asticella
    python3 scripts/perla-verifica-margini.py --json esito.json

Esce 1 se qualcosa sta sotto la soglia, cosi' si puo' mettere in un controllo
automatico. Non tocca niente: sola lettura, su Shopify e sui fornitori.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ENV = os.path.join(RADICE, "config", "printify.local.env")

VETRINA = "https://perlaitaly.com/products.json?limit=250"
CAMBIO = "https://open.er-api.com/v6/latest/USD"

# Le varianti Printful che il negozio vende davvero, per tipo. Gli id sono gli
# stessi di scripts/varianti-fornitore.js: se li' cambiano, vanno cambiati qui.
PRINTFUL = {
    "collare-eu":    [("S", 19186, {}), ("M", 19187, {}), ("L", 19188, {})],
    "guinzaglio-eu": [("unica", 19126, {})],
    "bandana-eu":    [("S", 16031, {"stitch_color": "white"}),
                      ("M", 16032, {"stitch_color": "white"}),
                      ("L", 16033, {"stitch_color": "white"})],
    "ciotola-eu":    [("530 ml", 16785, {}), ("950 ml", 16786, {})],
}
# I blueprint Printify in vendita, con il tipo che compare nel titolo Shopify.
PRINTIFY = {419: "cuccia", 562: "bandana", 566: "medaglietta", 570: "ciotola"}

INDIRIZZO = {"address1": "Via della Beata Colomba 1", "city": "Perugia",
             "country_code": "IT", "zip": "06132"}


def ambiente():
    if not os.path.exists(ENV):
        sys.exit("manca %s: senza le chiavi dei fornitori non si misura niente" % ENV)
    for riga in open(ENV, encoding="utf-8"):
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def chiedi(url, intestazioni=None, corpo=None):
    dati = json.dumps(corpo).encode() if corpo is not None else None
    testa = {"User-Agent": "perla-verifica-margini"}
    testa.update(intestazioni or {})
    if corpo is not None:
        testa["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=dati, headers=testa)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def cambio_usd_eur():
    d = chiedi(CAMBIO)
    tasso = d.get("rates", {}).get("EUR")
    if not tasso:
        sys.exit("il cambio non risponde: meglio fermarsi che inventare un numero")
    return tasso, d.get("time_last_update_utc", "?")


def costi_printful():
    """Costo sbarcato in euro per ogni variante EU, spedizione e IVA comprese."""
    k = os.environ["PRINTFUL_API_KEY"]
    store = os.environ["PRINTFUL_STORE_ID"]
    testa = {"Authorization": "Bearer " + k, "X-PF-Store-Id": store}
    fuori = {}
    for tipo, varianti in PRINTFUL.items():
        for etichetta, vid, opzioni in varianti:
            corpo = {"recipient": INDIRIZZO,
                     "items": [{"variant_id": vid, "quantity": 1, "options": opzioni}]}
            try:
                r = chiedi("https://api.printful.com/orders/estimate-costs", testa, corpo)
                fuori[(tipo, etichetta)] = float(r["result"]["costs"]["total"])
            except Exception as e:
                print("  Printful non quota %s %s: %s" % (tipo, etichetta, e), file=sys.stderr)
    return fuori


def costi_printify(tasso):
    """Costo sbarcato in euro per (tipo, titolo variante). Costo + spedizione."""
    k = os.environ["PRINTIFY_API_KEY"]
    shop = os.environ["PRINTIFY_SHOP_ID"]
    testa = {"Authorization": "Bearer " + k}
    costo = {}          # (blueprint, titolo variante) -> costo massimo in $
    blueprint = {}      # blueprint -> provider
    pagina = 1
    while True:
        d = chiedi("https://api.printify.com/v1/shops/%s/products.json?limit=50&page=%d"
                   % (shop, pagina), testa)
        for p in d.get("data", []):
            blueprint[p["blueprint_id"]] = p["print_provider_id"]
            for v in p["variants"]:
                if not v.get("is_enabled"):
                    continue
                ch = (p["blueprint_id"], v["title"])
                costo[ch] = max(costo.get(ch, 0), v["cost"] / 100.0)
        if not d.get("next_page_url"):
            break
        pagina += 1

    # spedizione: il profilo che contiene l'Italia, per variante.
    # Solo per i blueprint che vendiamo davvero: sul negozio Printify ne
    # restano altri (il vecchio collare 784) i cui prodotti su Shopify sono
    # archiviati, e chiederne la spedizione risponde 404 -- un allarme per
    # una cosa che non e' in vendita e' peggio di nessun allarme.
    spedizione = {}
    for bp, pp in blueprint.items():
        if bp not in PRINTIFY:
            continue
        try:
            d = chiedi("https://api.printify.com/v1/catalog/blueprints/%d/print_providers/%d/shipping.json"
                       % (bp, pp), testa)
        except Exception as e:
            print("  spedizione Printify non leggibile per il blueprint %d: %s" % (bp, e),
                  file=sys.stderr)
            continue
        for prof in d.get("profiles", []):
            if "IT" not in prof.get("countries", []):
                continue
            for vid in prof.get("variant_ids", []):
                spedizione[(bp, vid)] = prof["first_item"]["cost"] / 100.0

    # id variante -> titolo, per accostare spedizione e costo
    titolo_di = {}
    pagina = 1
    while True:
        d = chiedi("https://api.printify.com/v1/shops/%s/products.json?limit=50&page=%d"
                   % (shop, pagina), testa)
        for p in d.get("data", []):
            for v in p["variants"]:
                titolo_di[(p["blueprint_id"], v["id"])] = v["title"]
        if not d.get("next_page_url"):
            break
        pagina += 1

    sped_per_titolo = {}
    for (bp, vid), c in spedizione.items():
        t = titolo_di.get((bp, vid))
        if t is not None:
            sped_per_titolo[(bp, t)] = c

    fuori = {}
    for (bp, titolo), c in costo.items():
        tipo = PRINTIFY.get(bp)
        if tipo is None:
            continue
        s = sped_per_titolo.get((bp, titolo))
        if s is None:
            print("  nessuna spedizione verso l'Italia per %s %s" % (tipo, titolo), file=sys.stderr)
            continue
        fuori[(tipo, titolo)] = (c + s) * tasso
    return fuori


def tipo_di(prodotto):
    h = prodotto["handle"]
    for t in PRINTFUL:
        if h.startswith(t):
            return t
    return prodotto["title"].split()[0].lower().strip(u"“\"")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--soglia", type=float, default=20.0, help="margine minimo in percento")
    a.add_argument("--json", help="dove scrivere l'esito")
    opz = a.parse_args()

    ambiente()
    tasso, quando = cambio_usd_eur()
    print("cambio 1 USD = %.4f EUR (%s)\n" % (tasso, quando))

    print("Chiedo i costi ai fornitori...", file=sys.stderr)
    costo = {}
    for (tipo, etichetta), c in costi_printful().items():
        costo[(tipo, etichetta)] = c
    for k, c in costi_printify(tasso).items():
        costo[k] = c

    prodotti = chiedi(VETRINA)["products"]
    righe, senza = [], []
    for p in prodotti:
        t = tipo_di(p)
        for v in p["variants"]:
            c = costo.get((t, v["title"]))
            if c is None and t in PRINTFUL:
                # le taglie EU costano uguale: si accetta una etichetta qualunque
                candidati = [x for (tt, _), x in costo.items() if tt == t]
                c = max(candidati) if candidati else None
            if c is None:
                senza.append((p["title"], v["title"]))
                continue
            prezzo = float(v["price"])
            righe.append({"prodotto": p["title"], "taglia": v["title"], "prezzo": prezzo,
                          "costo": round(c, 2), "margine": round(100 * (prezzo - c) / prezzo, 1)})

    righe.sort(key=lambda r: r["margine"])
    print("%-30s %-18s %8s %8s %8s" % ("prodotto", "taglia", "prezzo", "costo", "margine"))
    print("-" * 78)
    for r in righe[:25]:
        print("%-30s %-18s %8.2f %8.2f %7.1f%%" % (
            r["prodotto"][:30], r["taglia"][:18], r["prezzo"], r["costo"], r["margine"]))
    if len(righe) > 25:
        print("  … e altre %d varianti, tutte con margine piu' alto" % (len(righe) - 25))

    sotto = [r for r in righe if r["margine"] < opz.soglia]
    print("\n%d varianti misurate. Sotto il %.0f%%: %d" % (len(righe), opz.soglia, len(sotto)))
    if senza:
        print("Senza costo noto (%d): %s" % (len(senza), ", ".join(
            "%s %s" % s for s in senza[:5])))
    if opz.json:
        json.dump({"cambio": tasso, "aggiornato": quando, "righe": righe},
                  open(opz.json, "w"), ensure_ascii=False, indent=1)
    return 1 if sotto else 0


if __name__ == "__main__":
    sys.exit(main())
