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
                      blueprint, profilo degli STATI UNITI -- che e' l'unico
                      paese fuori dalla UE in cui il negozio spedisce, e la
                      linea Printify ai clienti UE non si vede nemmeno
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

# L'IVA CHE NON SI SA, E PERCHE' VA DETTO INVECE DI TACERLO
#
# Su Printful l'IVA e' un numero letto: l'ordine 169833807, stato "fulfilled",
# porta 43,50 di prodotto + 9,29 di spedizione + 11,59 di IVA, cioe' il 22,0%
# esatto. Il negozio non ha partita IVA, quindi la paga e non la recupera: fa
# parte del costo, ed e' contata.
#
# Su Printify l'ordine da cui leggerla non c'e' ancora: l'unico mai passato di
# li' e' ANNULLATO e ha total_price, total_shipping e total_tax tutti a zero.
# Per due tornate questo script ha percio' mostrato DUE colonne, con e senza,
# dicendo che la seconda era un'ipotesi.
#
# Il 4 settembre la proprietaria l'ha chiusa lei: "considera che io pago l'IVA
# sia su printful che printify". Non e' piu' un'ipotesi, e' un dato di chi
# riceve le fatture. Quindi il costo Printify e' prodotto + spedizione + IVA,
# una colonna sola, e i prezzi si fanno su quello.
#
# iva_da_un_ordine_printify() resta e ha la precedenza: il giorno del primo
# ordine vero il numero si legge invece di darlo per buono, e se fosse diverso
# dal 22% lo si scopre da solo.
IVA_PRINTIFY = 0.22

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

    # SPEDIZIONE: IL PROFILO DEGLI STATI UNITI, E QUI PRIMA C'ERA UN ERRORE MIO.
    #
    # Fino al 3 settembre si prendeva il profilo che contiene l'ITALIA, e
    # sembrava la scelta prudente: il caso piu' caro. Ma non e' il caso piu'
    # caro, e' un caso che NON SUCCEDE MAI. La linea Printify e' nascosta ai
    # visitatori europei -- lo fa snippets/perla-region-hidden.liquid, e la
    # regola e' netta: "visitatore UE vede SOLO prodotti con un tag *-eu,
    # visitatore non UE vede SOLO prodotti senza". Un cliente italiano non puo'
    # comprare una cuccia Printify nemmeno volendo.
    #
    # E fuori dalla UE il negozio spedisce in un paese solo. L'informativa
    # sulle spedizioni elenca Italia, UE, Regno Unito, Monaco, San Marino,
    # Montenegro, Ucraina e Stati Uniti -- e i primi sette stanno tutti dentro
    # perla_eu_countries, cioe' vedono la linea europea. Resta l'America.
    #
    # Quanto pesava l'errore, misurato sui profili veri:
    #
    #                    verso gli USA      verso la UE
    #     bandana            5,69              15,09
    #     cuccia          27,29-51,99       73,49-88,49
    #
    # Su una cuccia significava caricare fino a 37 dollari di spedizione che
    # nessun cliente paga: il margine risultava schiacciato e il rimedio
    # sarebbe stato alzare un prezzo che invece va bene.
    #
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
            if "US" not in prof.get("countries", []):
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


def iva_da_un_ordine_printify():
    """L'IVA vera, se un ordine Printify l'ha mai pagata. Altrimenti None.

    Il giorno che un ordine vero passa di qui, questo numero smette di essere
    un'ipotesi. Fino ad allora torna None e la tabella lo dice.
    """
    k = os.environ.get("PRINTIFY_API_KEY")
    shop = os.environ.get("PRINTIFY_SHOP_ID")
    if not (k and shop):
        return None
    try:
        d = chiedi("https://api.printify.com/v1/shops/%s/orders.json?limit=20" % shop,
                   {"Authorization": "Bearer " + k})
    except Exception:
        return None
    for o in d.get("data", []):
        if o.get("status") == "canceled":
            continue
        imponibile = (o.get("total_price") or 0) + (o.get("total_shipping") or 0)
        imposta = o.get("total_tax") or 0
        if imponibile and imposta:
            return imposta / float(imponibile)
    return None


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
    iva_vera = iva_da_un_ordine_printify()
    iva_pf = iva_vera if iva_vera is not None else IVA_PRINTIFY

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
            # L'IVA e' dentro tutti e due i costi, per strade diverse: su
            # Printful la da' gia' il preventivo, su Printify si aggiunge qui.
            # La paga il negozio e non la recupera, quindi e' costo.
            printify = t in PRINTIFY.values()
            c_iva = c * (1 + iva_pf) if printify else c
            righe.append({"prodotto": p["title"], "taglia": v["title"], "prezzo": prezzo,
                          "fornitore": "Printify" if printify else "Printful",
                          "costo_senza_iva": round(c, 2),
                          "costo": round(c_iva, 2),
                          "margine": round(100 * (prezzo - c_iva) / prezzo, 1)})

    righe.sort(key=lambda r: r["margine"])
    print("%-28s %-15s %-9s %8s %8s %8s" % (
        "prodotto", "taglia", "fornitore", "prezzo", "costo", "margine"))
    print("-" * 82)
    for r in righe[:25]:
        print("%-28s %-15s %-9s %8.2f %8.2f %7.1f%%" % (
            r["prodotto"][:28], r["taglia"][:15], r["fornitore"],
            r["prezzo"], r["costo"], r["margine"]))
    if len(righe) > 25:
        print("  … e altre %d varianti, tutte con margine piu' alto" % (len(righe) - 25))

    sotto = [r for r in righe if r["margine"] < opz.soglia]
    print("\n%d varianti misurate. Sotto il %.0f%%: %d" % (len(righe), opz.soglia, len(sotto)))
    print("Il costo comprende sempre spedizione e IVA: e' quello che il negozio")
    print("paga davvero, e la spedizione al cliente e' gratuita per informativa.")
    if iva_vera is not None:
        print("IVA Printify LETTA da un ordine vero: %.1f%%." % (100 * iva_vera))
    else:
        print("IVA Printify al %.0f%%, come dichiarato dalla proprietaria: nessun"
              % (100 * iva_pf))
        print("ordine vero da cui leggerla, ma le fatture le riceve lei.")
    if senza:
        print("Senza costo noto (%d): %s" % (len(senza), ", ".join(
            "%s %s" % s for s in senza[:5])))
    if opz.json:
        json.dump({"cambio": tasso, "aggiornato": quando, "righe": righe},
                  open(opz.json, "w"), ensure_ascii=False, indent=1)
    return 1 if sotto else 0


if __name__ == "__main__":
    sys.exit(main())
