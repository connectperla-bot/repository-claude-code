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
    # La 950 ml non si vende piu' dal 4 settembre -- vedi PREZZO_DECISO qui
    # sotto. L'id 16786 resta in varianti-fornitore.js, che e' la mappa degli
    # ORDINI: toglierlo di li' renderebbe irrisolvibile un ordine storico.
    # Qui invece si chiede un preventivo, e chiedere il prezzo di una misura
    # che non e' in vendita e' una chiamata sprecata.
    "ciotola-eu":    [("530 ml", 16785, {})],
}
# I blueprint Printify in vendita, con il tipo che compare nel titolo Shopify.
# Gli ultimi tre sono del 4 settembre: collare di pelle inciso, medaglietta
# incisa e giacchetto parka, scelti dalla proprietaria dal catalogo Printify.
PRINTIFY = {419: "cuccia", 562: "bandana", 566: "medaglietta", 570: "ciotola",
            10700: "collare-pelle", 10674: "medaglietta-incisa",
            10740: "giacchetto", 623: "tappetino"}

# IL TAPPETINO E' L'UNICO TIPO VENDUTO NELLO STESSO BLUEPRINT SU DUE MERCATI
#
# 623/10 (MWW On Demand) stampa e spedisce sia la scheda americana sia quella
# europea, e questo rompe due cose che fin qui erano costanti:
#
#   la SPEDIZIONE. Fin qui bastava leggere il profilo degli Stati Uniti,
#   perche' tutto il Printify andava li'. Il tappetino europeo va in Italia,
#   dove lo stesso pezzo costa 7,79 invece di 6,09 (e 7,79 invece di 7,29
#   sulla misura grande). Leggere il profilo sbagliato vuol dire misurare il
#   margine su una spedizione che nessuno paga.
#
#   l'IMPOSTA. Sul resto della linea Printify e' una RISERVA del 5% per la
#   sales tax americana, e non e' IVA italiana perche' quella merce in Europa
#   non entra mai. Il tappetino europeo invece in Europa ci entra: li' l'IVA
#   e' quella vera al 22%, la stessa che Printful dichiara nei preventivi.
#
# Da qui le due tabelle. La chiave e' il tipo, non il blueprint, perche' il
# blueprint e' lo stesso per tutti e due.
DESTINAZIONE = {"tappetino-eu": "IT"}      # il resto e' "US"
IMPOSTA_REALE = {"tappetino-eu": 0.22}     # il resto usa la riserva americana

# DUE TIPI DIVERSI CHE COMINCIANO CON LA STESSA PAROLA
#
# tipo_di() legge il tipo dalla PRIMA PAROLA del titolo, e da sola non basta
# piu': "Collare in Pelle" comincia come i collari, "Medaglietta Incisa" come
# le medagliette -- ma costano il doppio e la meta', e confonderli
# significherebbe misurare il margine di un prodotto sul costo di un altro.
# Qui il tipo si riconosce dall'handle, che e' piu' lungo e li distingue.
PRINTIFY_HANDLE = {"collare-in-pelle": "collare-pelle",
                   "medaglietta-incisa": "medaglietta-incisa",
                   "giacchetto-parka": "giacchetto"}

# IL TITOLO DEL FORNITORE E IL TITOLO DELLA SCHEDA NON SONO PIU' LO STESSO
#
# Il costo arriva da Printify indicizzato per titolo di variante, e per quasi
# tutto il catalogo basta, perche' le schede portano il titolo del fornitore
# tale e quale. Sul tappetino no: l'opzione e' stata rinominata in italiano
# ("Osso piccolo (48x36 cm)") e il "Color / White" del fornitore -- un'opzione
# con un valore solo -- e' stato tolto dalla scheda.
#
# Da quel momento l'accostamento per titolo non trova piu' niente e le
# TRENTASEI varianti dei tappetini escono dal foglio SENZA UN ERRORE: finiscono
# nell'elenco "senza costo noto" in fondo, che e' molto piu' facile da non
# leggere di una riga rossa. Il foglio continuava a dire "sotto il 20%: 0" ed
# era vero soltanto perche' quelle righe non le stava piu' guardando.
#
# Stessa medicina di scripts/varianti-fornitore.js, che per gli ORDINI gli
# alias inglesi ce li ha gia': qui servono nel verso opposto, dal titolo del
# fornitore a quello della scheda. Nel catalogo Printify le virgolette e il
# segno "per" sono scritti in due modi sulla stessa riga (" e ”, x e ×),
# quindi prima di confrontare si pareggiano.
ALIAS_VARIANTE = {
    623: {'bone shape (19 x 14) / white': 'Osso piccolo (48x36 cm)',
          'bone shape (30 x 18) / white': 'Osso grande (76x46 cm)',
          'fish shape (19 x 14) / white': 'Pesce (48x36 cm)'},
}


def _pareggia(titolo):
    """Virgolette e segno per uniformati, per confrontare due cataloghi."""
    for a, b in (('“', ''), ('”', ''), ('"', ''), ('″', ''),
                 ('×', 'x'), ("'", '')):
        titolo = titolo.replace(a, b)
    return " ".join(titolo.split()).lower()

# L'UNICA DEROGA AL 20%, DECISA DALLA PROPRIETARIA IL 4 SETTEMBRE
#
# La ciotola europea costa 41,24 (prodotto + spedizione + IVA): con la regola
# del 20% il prezzo minimo sarebbe 51,90, e le sembrava alto. Fra le tre strade
# proposte ha tolto la 950 ml e tenuto la 530; poi, guardando il prezzo in
# vetrina, l'ha voluto sotto i cinquanta -- 49,90, cioe' un margine del 17,4%.
#
# Sta scritta qui e non lasciata a mente per due motivi. Il primo: senza, il
# controllo tornerebbe rosso ogni volta su una riga che e' una decisione e non
# un errore, e un controllo che si sa gia' che fallisce smette di essere
# guardato. Il secondo: la soglia resta 20 per tutto il resto del catalogo --
# la regola non cambia, cambia il fatto che una deroga e' dichiarata, con la
# data e il motivo.
DEROGHE = {("ciotola-eu", "530 ml"): "decisa dalla proprietaria il 4 settembre"}

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
# IL 22% SU PRINTIFY ERA UN MIO ERRORE, E VA DETTO PER INTERO
#
# Il 4 settembre la proprietaria aveva chiuso la questione cosi': "considera
# che io pago l'IVA sia su printful che printify", e io ho messo il 22% su
# tutte e due le linee. Su Printful e' giusto -- merce stampata in Europa e
# consegnata in Italia, IVA italiana, e l'ordine 169833807 la mostra.
#
# Su Printify no, e a vederlo e' stata lei: "siccome siamo in America non penso
# si paghi l'IVA, o se si paga non al 22". Ha ragione, e la ragione e'
# geografica prima che fiscale: quella merce viene stampata negli Stati Uniti e
# consegnata a un indirizzo americano. In Europa non entra mai, quindi non c'e'
# nessuna importazione e nessuna IVA italiana da pagare. Quello che Printify
# puo' addebitare e' la SALES TAX americana, che dipende dallo stato di
# consegna e va da zero a circa il dieci per cento.
#
# QUINDI NON E' PIU' UN'IVA, E' UNA RISERVA. Il numero qui sotto non pretende
# di essere l'imposta vera: e' l'accantonamento che la proprietaria ha scelto
# -- "considera un 5% per pararci un po' il sedere sul primo ordine" -- per non
# trovarsi scoperta se al primo ordine la sales tax arriva davvero.
#
# iva_da_un_ordine_printify() resta e MANTIENE LA PRECEDENZA: il giorno del
# primo ordine vero l'imposta si legge dalla fattura invece di stimarla, e se
# fosse diversa dal 5% lo si scopre da solo, senza che nessuno debba
# ricordarsene.
RISERVA_IMPOSTA_USA = 0.05

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


def _printful_composto(testa, vid):
    """Il costo sbarcato ricomposto, quando il preventivo non si puo' chiedere.

    Prodotto dal listino v2, spedizione dalle tariffe vere verso l'indirizzo
    italiano, IVA al 22% su prodotto + spedizione. Non e' una stima: sulle tre
    varianti in cui il preventivo RISPONDE, l'IVA che dichiara Printful e'
    esattamente il 22% di (subtotal + shipping) -- collare 4,44 su 20,14,
    ciotola 7,44 su 33,80. La stessa aritmetica applicata dove il preventivo
    non risponde da' lo stesso numero che darebbe lui.
    """
    prezzo = None
    d = chiedi("https://api.printful.com/v2/catalog-variants/%d/prices?currency=EUR" % vid, testa)
    for t in (d.get("data", {}).get("variant", {}) or {}).get("techniques", []):
        prezzo = float(t.get("discounted_price") or t.get("price") or 0)
        break
    if not prezzo:
        raise RuntimeError("listino v2 senza prezzo per la variante %d" % vid)
    r = chiedi("https://api.printful.com/shipping/rates", testa,
               {"recipient": INDIRIZZO, "items": [{"variant_id": vid, "quantity": 1}],
                "currency": "EUR"})
    sped = min(float(t["rate"]) for t in r["result"])
    iva = round((prezzo + sped) * 0.22, 2)
    return {"prodotto": prezzo, "spedizione": sped, "imposta": iva,
            "totale": round(prezzo + sped + iva, 2), "composto": True}


def costi_printful():
    """Le PARTI del costo sbarcato, in euro, per ogni variante EU.

    Torna un dizionario per variante: prodotto, spedizione, imposta, totale.
    Prima tornava il solo totale, e bastava per dire se il margine reggeva.
    Non basta per il foglio dei margini che la proprietaria usa per decidere i
    prezzi: li' serve vedere QUANTO pesa la spedizione e quanto l'IVA, se no
    non si sa su cosa si puo' agire.

    DUE DIFETTI TROVATI MISURANDO, NON LEGGENDO (ROUND 59)

    1. L'IVA STAVA NEL CAMPO SBAGLIATO. Il preventivo tiene separati `tax` e
       `vat`, e su un ordine italiano `tax` e' 0,00 mentre l'IVA vera sta in
       `vat` -- 4,44 euro su un collare. Si leggeva solo `tax`, quindi la
       colonna IVA del foglio diceva zero su tutta la linea europea. Il
       margine invece era giusto: quello si calcola su `total`, che l'IVA la
       comprende.

    2. `options` FA CADERE IL PREVENTIVO. Mandare la chiave `options`, anche
       vuota, fa rispondere 500 su collare, guinzaglio e bandana; senza,
       rispondono. Provato tre volte per combinazione, e' una regola, non un
       capriccio. Ma la bandana SENZA options risponde 400 e chiede
       stitch_color: con options 500 e senza 400, per lei il preventivo non e'
       ottenibile in nessun modo, e li' si ricompone il costo (vedi
       _printful_composto).
    """
    k = os.environ["PRINTFUL_API_KEY"]
    store = os.environ["PRINTFUL_STORE_ID"]
    testa = {"Authorization": "Bearer " + k, "X-PF-Store-Id": store}
    fuori = {}
    for tipo, varianti in PRINTFUL.items():
        for etichetta, vid, opzioni in varianti:
            voce = {"variant_id": vid, "quantity": 1}
            if opzioni:
                voce["options"] = opzioni
            corpo = {"recipient": INDIRIZZO, "items": [voce]}
            try:
                r = chiedi("https://api.printful.com/orders/estimate-costs", testa, corpo)
                c = r["result"]["costs"]
                fuori[(tipo, etichetta)] = {
                    "prodotto": float(c.get("subtotal") or 0),
                    "spedizione": float(c.get("shipping") or 0),
                    # tax E vat: su un ordine italiano la prima e' zero e la
                    # seconda no, altrove puo' essere il contrario.
                    "imposta": float(c.get("tax") or 0) + float(c.get("vat") or 0),
                    "totale": float(c["total"]),
                }
            except Exception as e:
                try:
                    fuori[(tipo, etichetta)] = _printful_composto(testa, vid)
                    print("  Printful non quota %s %s (%s): costo ricomposto dal listino"
                          % (tipo, etichetta, e), file=sys.stderr)
                except Exception as e2:
                    print("  Printful non quota %s %s: %s / %s"
                          % (tipo, etichetta, e, e2), file=sys.stderr)
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
        # Un profilo per PAESE di destinazione, non piu' solo gli Stati Uniti:
        # lo stesso blueprint puo' servire due mercati (il tappetino), e li'
        # il costo cambia. La chiave porta il paese, e chi la legge sceglie.
        for prof in d.get("profiles", []):
            paesi = prof.get("countries", [])
            for paese in ("US", "IT"):
                if paese not in paesi:
                    continue
                for vid in prof.get("variant_ids", []):
                    spedizione[(bp, vid, paese)] = prof["first_item"]["cost"] / 100.0

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
    for (bp, vid, paese), c in spedizione.items():
        t = titolo_di.get((bp, vid))
        if t is not None:
            sped_per_titolo[(bp, t, paese)] = c

    fuori = {}
    for (bp, titolo), c in costo.items():
        tipo = PRINTIFY.get(bp)
        if tipo is None:
            continue
        # Un tipo puo' avere un gemello su un altro mercato: stesso blueprint,
        # stesso costo di produzione, spedizione diversa. Si emette una voce
        # per ognuno, ognuna con la spedizione verso il SUO paese.
        for t2 in [tipo] + [x for x, y in DESTINAZIONE.items() if x != tipo and x.startswith(tipo)]:
            paese = DESTINAZIONE.get(t2, "US")
            s = sped_per_titolo.get((bp, titolo, paese))
            if s is None:
                print("  nessuna spedizione verso %s per %s %s" % (paese, t2, titolo),
                      file=sys.stderr)
                continue
            voce = {
                "prodotto": c * tasso,
                "spedizione": s * tasso,
                # L'imposta NON si sa qui: dipende da dove va il pacco, e su
                # Printify quel numero e' una riserva scelta dalla proprietaria,
                # non un importo letto. La aggiunge main(), che sa se la riga e'
                # americana o europea.
                "imposta": 0.0,
                "totale": (c + s) * tasso,
            }
            fuori[(t2, titolo)] = voce
            # Lo stesso costo anche sotto il titolo che porta la SCHEDA, quando
            # non e' quello del fornitore: vedi ALIAS_VARIANTE piu' sopra.
            alias = ALIAS_VARIANTE.get(bp, {}).get(_pareggia(titolo))
            if alias:
                fuori[(t2, alias)] = voce
    return fuori


def costo_sbarcato(tipo, c, iva_pf):
    """Quanto ci costa davvero una variante: prodotto + spedizione + imposta.

    UNA FONTE SOLA, E QUI PRIMA CE N'ERANO DUE.

    Questo conto lo fanno due programmi: il controllo dei margini, che chiede
    «c'e' qualcosa sotto il venti per cento?», e perla-prezzi-margine.py, che
    propone i prezzi. Finche' il costo era un numero solo le due copie si
    somigliavano abbastanza da non dare fastidio. Quando il costo e' diventato
    un dizionario con le parti separate -- per il foglio dei margini -- qui e'
    stato aggiornato e li' no: il listino e' rimasto ROTTO per giorni, con un
    TypeError al primo prodotto Printify, e nessuno se n'e' accorto perche'
    nel frattempo nessuno ha rifatto i prezzi.

    Un programma che si pianta almeno lo dice. La copia silenziosamente
    sfasata sarebbe stata peggio: avrebbe proposto prezzi calcolati su
    un'imposta diversa da quella del controllo, e i due si sarebbero
    contraddetti senza che nessuno capisse quale credere.

    Le tre strade dell'imposta, che sono tre cose diverse e vanno tenute
    distinte:
      IMPOSTA_REALE  merce che entra davvero in Europa: IVA vera sul valore.
      Printify       riserva scelta dalla proprietaria per la sales tax
                     americana. E' una stima, non un importo letto.
      Printful       importo LETTO dal preventivo del fornitore.
    """
    printify = tipo in PRINTIFY.values() or tipo in DESTINAZIONE
    if tipo in IMPOSTA_REALE:
        imposta = (c["prodotto"] + c["spedizione"]) * IMPOSTA_REALE[tipo]
    elif printify:
        imposta = c["totale"] * iva_pf
    else:
        imposta = c["imposta"]
    return c["prodotto"] + c["spedizione"] + imposta, imposta, printify


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


def etichette(prodotto):
    """I tag del prodotto, sia che arrivino in lista sia in una stringa.

    /products.json li da' in lista, l'API Admin in una stringa separata da
    virgole: senza questo si leggerebbero le lettere una per una."""
    grezzi = prodotto.get("tags") or []
    if isinstance(grezzi, str):
        grezzi = grezzi.split(",")
    return [str(x).strip() for x in grezzi]


def tipo_di(prodotto):
    """Il tipo su cui e' quotato il costo: prima il TAG, poi l'handle.

    Gli europei si riconoscevano dall'handle, che cominciava per "collare-eu-".
    Da settembre gli handle sono corti (collare-barocco) e quel prefisso non
    c'e' piu': cercandolo ancora, tutti e 66 gli europei finirebbero senza
    costo e il controllo sul margine smetterebbe di guardare mezza vetrina
    senza dirlo. Il tag "collare-eu" invece e' rimasto, ed e' lo stesso nome
    che fa da chiave in PRINTFUL. L'handle resta come ripiego per le
    istantanee vecchie salvate su disco."""
    for e in etichette(prodotto):
        if e in PRINTFUL:
            return e
    h = prodotto["handle"]
    for t in PRINTFUL:
        if h.startswith(t):
            return t
    for prefisso, t in PRINTIFY_HANDLE.items():
        if h.startswith(prefisso):
            return t
    # Il tappetino europeo e quello globale hanno lo STESSO titolo e lo stesso
    # blueprint: a distinguerli c'e' solo il tag, e distinguerli serve perche'
    # cambiano spedizione e imposta.
    if "tappetino-eu" in etichette(prodotto):
        return "tappetino-eu"
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
    iva_pf = iva_vera if iva_vera is not None else RISERVA_IMPOSTA_USA

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
                c = max(candidati, key=lambda x: x["totale"]) if candidati else None
            if c is None:
                senza.append((p["title"], v["title"]))
                continue
            prezzo = float(v["price"])
            # L'IVA e' dentro tutti e due i costi, per strade diverse: vedi
            # costo_sbarcato(), che questo conto lo fa per tutti e due i
            # programmi che ne hanno bisogno.
            sbarcato, imposta, printify = costo_sbarcato(t, c, iva_pf)
            righe.append({"prodotto": p["title"], "taglia": v["title"], "prezzo": prezzo,
                          "fornitore": "Printify" if printify else "Printful",
                          "tipo": t,
                          "deroga": DEROGHE.get((t, v["title"])),
                          # Le tre parti separate: servono al foglio dei
                          # margini per dire su cosa si puo' agire.
                          "costo_prodotto": round(c["prodotto"], 2),
                          "spedizione": round(c["spedizione"], 2),
                          "imposta": round(imposta, 2),
                          "costo_senza_iva": round(c["prodotto"] + c["spedizione"], 2),
                          "costo": round(sbarcato, 2),
                          "guadagno": round(prezzo - sbarcato, 2),
                          "margine": round(100 * (prezzo - sbarcato) / prezzo, 1)})

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

    # Una riga sotto soglia CON una deroga dichiarata non e' un guasto: e' una
    # scelta di listino, e va detta invece di sparire dal conto.
    sotto = [r for r in righe if r["margine"] < opz.soglia and not r["deroga"]]
    derogate = [r for r in righe if r["margine"] < opz.soglia and r["deroga"]]
    print("\n%d varianti misurate. Sotto il %.0f%%: %d" % (len(righe), opz.soglia, len(sotto)))
    # Raggruppate: la deroga e' UNA decisione, non undici. Undici righe uguali
    # si smettono di leggere alla terza.
    gruppi = {}
    for r in derogate:
        gruppi.setdefault((r["taglia"], r["deroga"]), []).append(r["margine"])
    for (taglia, perche), margini_g in sorted(gruppi.items()):
        print("  %d varianti «%s» stanno al %.1f%%: deroga %s"
              % (len(margini_g), taglia, min(margini_g), perche))
    print("Il costo comprende sempre spedizione e IVA: e' quello che il negozio")
    print("paga davvero, e la spedizione al cliente e' gratuita per informativa.")
    if iva_vera is not None:
        print("IVA Printify LETTA da un ordine vero: %.1f%%." % (100 * iva_vera))
    else:
        print("Sulla linea Printify: riserva del %.0f%% per la sales tax\n"
              "americana. Non e' IVA italiana -- quella merce non entra mai in\n"
              "Europa -- ed e' una stima, non un numero letto: la chiude la\n"
              "prima fattura Printify vera." % (100 * iva_pf))
    if senza:
        print("Senza costo noto (%d): %s" % (len(senza), ", ".join(
            "%s %s" % s for s in senza[:5])))
    if opz.json:
        json.dump({"cambio": tasso, "aggiornato": quando, "righe": righe},
                  open(opz.json, "w"), ensure_ascii=False, indent=1)
    return 1 if sotto else 0


if __name__ == "__main__":
    sys.exit(main())
