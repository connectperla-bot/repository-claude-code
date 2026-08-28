#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dice, prodotto per prodotto, cosa c'e' che non va. Non tocca niente.

PERCHE' ESISTE
Tre tornate di riparazioni sono state fatte a occhio, su un prodotto alla
volta, e ogni volta il difetto e' ricomparso da un'altra parte: i file di
stampa sono stati rifatti alla risoluzione vera, ma nessuno ha verificato che
la scala fosse giusta su TUTTE le varianti; il marchio e' stato sostituito,
ma nessuno ha verificato che restasse dentro l'area. Questo script trasforma
"guarda se e' a posto" in un numero.

I QUATTRO DIFETTI CHE CERCA

  sgranato       il file viene stampato piu' grande di quanto sia
  fascia vuota   l'immagine non copre l'area: striscia bianca sul prodotto
  tagliato       l'immagine esce dall'area: disegno mozzato
  senza marchio  nessun livello marchio dentro l'area (o e' fuori dal bordo)

piu' due guasti di manutenzione che fanno fallire gli aggiornamenti:

  riferimento morto   livello senza nome, residuo di una duplicazione
  non producibile     varianti abilitate che il fornitore non sa fare

LA COSA CHE NESSUNO GUARDAVA
`print_areas` di Printify accetta piu' voci, ognuna con i suoi `variant_ids`.
Oggi i prodotti ne hanno UNA per tutte le varianti, ma le varianti hanno
misure diverse: sul collare M un file costruito per la XL lascia il 24% di
fettuccia bianca. Questo script controlla ogni immagine contro OGNI variante
che quella voce copre, non contro la piu' grande.

USO
    python3 scripts/perla-verifica-prodotti.py                # tutto
    python3 scripts/perla-verifica-prodotti.py --solo cuccia  # filtra sul titolo
    python3 scripts/perla-verifica-prodotti.py --mockup       # scarica i mockup
    python3 scripts/perla-verifica-prodotti.py --printful     # anche i due store EU

Uscita leggibile a schermo e generated-designs/audit-prodotti.json per il
confronto prima/dopo.
"""
import importlib.util
import json
import os
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ENV = os.path.join(RADICE, "config", "printify.local.env")
USCITA = os.path.join(RADICE, "generated-designs")


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aree = _modulo("aree_stampa", os.path.join(QUI, "aree-stampa.py"))
marchio = _modulo("marchio", os.path.join(QUI, "marchio.py"))

# Sotto queste soglie il difetto non si vede sul prodotto finito e segnalarlo
# sarebbe solo rumore che nasconde i difetti veri.
SOGLIA_VUOTO = 0.01      # 1% di area scoperta
SOGLIA_TAGLIO = 0.02     # 2% di immagine fuori
SOGLIA_INGRANDIMENTO = 1.05   # 5% di stiramento

# Un difetto si racconta per esteso ("tagliato fino al 18%") ma si conta per
# categoria, altrimenti il riepilogo elenca una riga per ogni sfumatura di
# percentuale e non si capisce piu' quanti prodotti sono davvero rotti.
CATEGORIE = (
    ("fascia vuota", "fascia vuota (striscia bianca sul prodotto)"),
    ("tagliato", "tagliato (disegno mozzato su qualche misura)"),
    ("sgranato", "sgranato (file stampato piu' grande di quanto sia)"),
    ("marchio fuori", "marchio fuori dall'area di stampa"),
    ("senza marchio", "senza marchio"),
    ("una sola area", "una sola area di stampa per misure diverse"),
    ("nessuna variante abilitata", "nessuna variante abilitata (prodotto morto)"),
    ("riferimento morto", "riferimento morto (livello senza nome)"),
    ("non producibile", "non producibile (nessuna variante disponibile)"),
    ("non pubblicato", "non pubblicato su Shopify"),
    ("misure blueprint", "misure del blueprint non disponibili"),
)


# ==========================================================================
# CIO' CHE E' GIA' STATO DECISO, E NON E' PIU' UN DIFETTO
# ==========================================================================
# Un audit che elenca ogni volta cose gia' viste e gia' decise smette di
# essere letto, e il giorno che compare un difetto vero nessuno se ne
# accorge. Queste due situazioni sono note e volute, quindi si contano a
# parte invece che fra i difetti.
#
# Le regole guardano i DATI, non un elenco di titoli da tenere aggiornato a
# mano: se domani il fornitore riabilita i collari, o se qualcuno mette un
# disegno sul prodotto neutro, rientrano da soli fra i prodotti normali.

def noto(prodotto, difetti):
    """Perche' questo prodotto e' cosi' di proposito, o None."""
    if not aree.abilitate(prodotto):
        # I 18 collari: blueprint 784, fornitore 93, tutte le varianti
        # is_enabled false E is_available false. Archiviati su Shopify il
        # 2026-08-28 d'accordo con la titolare: non si vende una cosa che il
        # fornitore non produce piu'.
        return "archiviato: il fornitore non lo produce piu'"

    # I quattro "Crea il Tuo Design" (medaglietta, ciotola, bandana e cuccia
    # neutre) hanno SOLO il livello del marchio, perche' l'immagine la porta
    # il cliente dallo studio di personalizzazione. Un prodotto senza disegno
    # di fondo qui e' giusto, non rotto.
    livelli = [im.get("name")
               for pa in prodotto.get("print_areas", [])
               for ph in pa.get("placeholders", [])
               for im in ph.get("images", [])]
    if livelli and all(n in marchio.LIVELLI_OBSOLETI for n in livelli if n):
        return "neutro: il disegno lo porta il cliente"
    return None


def categoria(difetto):
    for prefisso, etichetta in CATEGORIE:
        if difetto.startswith(prefisso):
            return etichetta
    return difetto


MANIFESTO = os.path.join(USCITA, "usa-print-files", "_marchio.json")


def marchio_nei_file():
    """I file di stampa che il marchio ce l'hanno DENTRO.

    Da ROUND 47 il marchio non e' piu' un livello separato su Printify: e'
    composto nel file (marchio.py). Contare i livelli direbbe "senza marchio"
    su tutto il catalogo appena riparato, che e' il contrario della verita'.

    Due fonti, tutte e due verificabili:
      * il manifesto scritto da perla-usa-file-stampa.py, che per ogni file
        costruito dice se il marchio era gia' nel motivo o se e' stato composto;
      * la convenzione "-perla.jpg" sugli artwork originali, descritta in
        perla-usa-marchio.py: quei file il marchio ce l'hanno dentro (verificato
        aprendoli: cartella "PERLA" al centro della bandana, "Perla Italia"
        ripetuto sul collare).
    """
    fuori = {}
    if os.path.exists(MANIFESTO):
        with open(MANIFESTO) as fh:
            for nome, voce in json.load(fh).items():
                fuori[nome] = voce.get("marchio", "si")
    return fuori


def chiavi():
    valori = {}
    with open(ENV) as fh:
        for riga in fh:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip()
    return valori


def api(url, token, intestazioni=()):
    """Da curl e non da urllib: in questo ambiente urllib esce dal proxy con
    un 403 (stessa nota in perla-usa-carica-stampe.py)."""
    cmd = ["curl", "-s", "-H", "Authorization: Bearer " + token]
    for h in intestazioni:
        cmd += ["-H", h]
    out = subprocess.run(cmd + [url], capture_output=True, text=True, check=True).stdout
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError("risposta non JSON da %s: %s" % (url, out[:200]))


# ==========================================================================
# PRINTIFY
# ==========================================================================

def prodotti_printify(token, shop):
    fuori, pagina = [], 1
    while True:
        d = api("https://api.printify.com/v1/shops/%s/products.json?limit=50&page=%d"
                % (shop, pagina), token)
        fuori += d["data"]
        if pagina >= d.get("last_page", 1):
            break
        pagina += 1
    return fuori


def esamina(p, token, cache, manifesto=None):
    """I difetti di un prodotto. Torna (elenco_difetti, dettaglio)."""
    manifesto = manifesto or {}
    difetti = []
    chiave = (p["blueprint_id"], p["print_provider_id"])
    if chiave not in cache:
        try:
            cache[chiave] = aree.varianti(chiave[0], chiave[1], token)
        except RuntimeError as err:
            cache[chiave] = err
    geometria = cache[chiave]
    if isinstance(geometria, RuntimeError):
        return ["misure blueprint non disponibili: %s" % geometria], {}

    per_id = {v["id"]: v for v in geometria}
    abilitate = aree.abilitate(p)
    vendibili = aree.vendibili(p)
    # Un prodotto senza NESSUNA variante abilitata non stampa niente: qualunque
    # verdetto su copertura o marchio sarebbe calcolato su zero varianti e
    # quindi inventato. E' il caso dei 18 collari, che hanno tutte e 16 le
    # varianti a is_enabled false E is_available false.
    if not abilitate:
        difetti.append("nessuna variante abilitata: il prodotto non e' vendibile")
    elif not vendibili:
        difetti.append("non producibile: %d varianti abilitate, nessuna disponibile"
                       % len(abilitate))
    if not (p.get("external") or {}).get("id"):
        difetti.append("non pubblicato su Shopify")

    dettaglio = {"aree": [], "gruppi_attesi": len(aree.gruppi(geometria, solo_varianti=abilitate))}
    peggio = {"vuoto": 0.0, "taglio": 0.0, "ingrandimento": 1.0}
    marchi_dentro = 0
    marchi_totali = 0
    varianti_esaminate = 0
    marchio_nel_motivo = 0

    for pa in p.get("print_areas", []):
        ids = [i for i in pa.get("variant_ids", []) if i in abilitate]
        misure = sorted({per_id[i]["placeholders"].get("front")
                         for i in ids if i in per_id} - {None})
        if len(misure) > 1:
            difetti.append("una sola area di stampa per %d misure diverse (%s)"
                           % (len(misure), " / ".join("%dx%d" % m for m in misure)))
        for ph in pa.get("placeholders", []):
            posizione = ph.get("position", "front")
            for im in ph.get("images", []):
                nome = im.get("name")
                if not nome:
                    difetti.append("riferimento morto (livello senza nome, id %s)"
                                   % im.get("id"))
                    continue
                e_marchio = nome in marchio.LIVELLI_OBSOLETI
                if e_marchio:
                    marchi_totali += 1
                elif nome in manifesto or nome.endswith("-perla.jpg"):
                    marchio_nel_motivo += 1
                for vid in ids:
                    misura = per_id.get(vid, {}).get("placeholders", {}).get(posizione)
                    if not misura:
                        continue
                    varianti_esaminate += 1
                    c = aree.copertura(misura, (im["width"], im["height"]),
                                       im.get("x", 0.5), im.get("y", 0.5),
                                       im.get("scale", 1.0))
                    if e_marchio:
                        # per il marchio non conta la copertura dell'area: conta
                        # che sia dentro. taglio 1,0 = interamente fuori bordo.
                        if c["taglio"] < 0.5:
                            marchi_dentro += 1
                        continue
                    peggio["vuoto"] = max(peggio["vuoto"], c["vuoto"])
                    peggio["taglio"] = max(peggio["taglio"], c["taglio"])
                    peggio["ingrandimento"] = max(peggio["ingrandimento"], c["ingrandimento"])
                    dettaglio["aree"].append({
                        "variante": vid, "posizione": posizione, "file": nome,
                        "area": list(misura), "immagine": [im["width"], im["height"]],
                        "vuoto": round(c["vuoto"], 4), "taglio": round(c["taglio"], 4),
                        "ingrandimento": round(c["ingrandimento"], 3),
                    })

    if peggio["vuoto"] > SOGLIA_VUOTO:
        difetti.append("fascia vuota fino al %.0f%% dell'area" % (peggio["vuoto"] * 100))
    if peggio["taglio"] > SOGLIA_TAGLIO:
        difetti.append("tagliato fino al %.0f%% del disegno" % (peggio["taglio"] * 100))
    if peggio["ingrandimento"] > SOGLIA_INGRANDIMENTO:
        difetti.append("sgranato: ingrandito %.1f volte" % peggio["ingrandimento"])
    # Solo se c'e' stata almeno una variante da misurare: senza, non si sa
    # dove cada il marchio e dirlo comunque sarebbe un falso positivo.
    if varianti_esaminate and not marchio_nel_motivo:
        if marchi_totali and not marchi_dentro:
            difetti.append("marchio fuori dall'area di stampa (c'e' il livello, non si stampa)")
        elif not marchi_totali:
            difetti.append("senza marchio (ne' nel motivo ne' come livello)")

    dettaglio["peggio"] = {k: round(v, 4) for k, v in peggio.items()}
    dettaglio["marchi"] = {"livelli": marchi_totali, "livelli_dentro": marchi_dentro,
                           "nel_motivo": marchio_nel_motivo}
    return difetti, dettaglio


def scarica_mockup(p, cartella):
    img = next((i for i in p.get("images", []) if i.get("is_default")), None) \
        or (p.get("images") or [None])[0]
    if not img:
        return None
    nome = "".join(c for c in p["title"][:44].lower().replace(" ", "-")
                   if c.isalnum() or c == "-") + ".jpg"
    os.makedirs(cartella, exist_ok=True)
    subprocess.run(["curl", "-s", "-o", os.path.join(cartella, nome), img["src"]], check=True)
    return nome


# ==========================================================================
# PRINTFUL
# ==========================================================================

def verifica_printful(env):
    """I due store, e a cosa serve ognuno.

    Va detto per esteso perche' e' la fonte del malinteso "l'account non ha
    prodotti": gli store sono DUE e mostrano cose diverse.
    """
    token = env.get("PRINTFUL_API_KEY")
    if not token:
        print("PRINTFUL_API_KEY mancante: salto.")
        return {}
    fuori = {"store": [], "varianti": []}
    d = api("https://api.printful.com/stores", token)
    for s in (d.get("result") or []):
        voce = {"id": s.get("id"), "nome": s.get("name"), "tipo": s.get("type")}
        if s.get("type") == "native":
            r = api("https://api.printful.com/store/products?limit=1", token,
                    ["X-PF-Store-Id: %s" % s["id"]])
            voce["prodotti"] = (r.get("paging") or {}).get("total")
            voce["nota"] = ("store degli ordini API: zero prodotti e' NORMALE, "
                            "providers/printful-client.js ordina sul catalogo")
        else:
            r = api("https://api.printful.com/sync/products?limit=100", token,
                    ["X-PF-Store-Id: %s" % s["id"]])
            elenco = r.get("result") or []
            voce["prodotti"] = (r.get("paging") or {}).get("total")
            voce["collegati"] = sum(1 for x in elenco if x.get("synced"))
            voce["nota"] = ("store Shopify: i prodotti si vedono ma %d/%d hanno "
                            "zero varianti collegate al catalogo Printful"
                            % (len(elenco) - voce["collegati"], len(elenco)))
        fuori["store"].append(voce)

    # le quattro varianti EU configurate esistono ancora?
    for tipo in ("COLLARE", "BANDANA", "CIOTOLA", "GUINZAGLIO"):
        vid = env.get("PRINTFUL_%s_EU_VARIANT_ID" % tipo)
        if not vid:
            fuori["varianti"].append({"tipo": tipo, "esito": "non configurata"})
            continue
        r = api("https://api.printful.com/products/variant/%s" % vid, token)
        res = (r.get("result") or {}).get("variant") or {}
        fuori["varianti"].append({
            "tipo": tipo, "id": vid, "esito": "ok" if res else "NON TROVATA",
            "nome": res.get("name"), "prodotto": (r.get("result") or {}).get("product", {}).get("id"),
        })
    return fuori


# ==========================================================================

def main():
    env = chiavi()
    solo = None
    if "--solo" in sys.argv:
        solo = sys.argv[sys.argv.index("--solo") + 1].lower()
    token, shop = env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"]

    prodotti = prodotti_printify(token, shop)
    if solo:
        prodotti = [p for p in prodotti if solo in p["title"].lower()]
    print("%d prodotti su Printify\n" % len(prodotti))

    manifesto = marchio_nei_file()
    if manifesto:
        print("(%d file di stampa nel manifesto del marchio)\n" % len(manifesto))
    cache, rapporto, conteggio, noti = {}, [], {}, []
    for p in sorted(prodotti, key=lambda x: x["title"]):
        difetti, dettaglio = esamina(p, token, cache, manifesto)
        perche = noto(p, difetti) if difetti else None
        if perche:
            noti.append((p["title"], perche))
            difetti = []
        for d in difetti:
            c = categoria(d)
            conteggio[c] = conteggio.get(c, 0) + 1
        voce = {"id": p["id"], "titolo": p["title"], "blueprint": p["blueprint_id"],
                "provider": p["print_provider_id"],
                "shopify": (p.get("external") or {}).get("id"),
                "difetti": difetti, "noto": perche, "dettaglio": dettaglio}
        if "--mockup" in sys.argv:
            voce["mockup"] = scarica_mockup(p, os.path.join(USCITA, "audit-mockup"))
        rapporto.append(voce)
        segno = "OK " if not difetti else "   "
        print("%s%-54s bp%s" % (segno, p["title"][:54], p["blueprint_id"]))
        for d in difetti:
            print("      - " + d)

    print("\n" + "=" * 72)
    print("RIEPILOGO")
    for d, n in sorted(conteggio.items(), key=lambda kv: -kv[1]):
        print("  %3d prodotti  %s" % (n, d))
    sani = sum(1 for v in rapporto if not v["difetti"] and not v.get("noto"))
    print("  %3d prodotti  senza difetti" % sani)
    if noti:
        print("\n  gia' deciso, non sono difetti:")
        per_motivo = {}
        for _, perche in noti:
            per_motivo[perche] = per_motivo.get(perche, 0) + 1
        for perche, n in sorted(per_motivo.items(), key=lambda kv: -kv[1]):
            print("  %3d prodotti  %s" % (n, perche))

    if "--printful" in sys.argv:
        print("\n" + "=" * 72)
        print("PRINTFUL")
        pf = verifica_printful(env)
        for s in pf.get("store", []):
            print("  store %-10s %-18s tipo %-8s prodotti %s"
                  % (s["id"], (s["nome"] or "")[:18], s["tipo"], s.get("prodotti")))
            print("        %s" % s.get("nota", ""))
        for v in pf.get("varianti", []):
            print("  variante %-11s %-8s %s" % (v["tipo"], v.get("id", "-"),
                                                v["esito"] + " " + str(v.get("nome") or "")))
        rapporto = {"printify": rapporto, "printful": pf}

    os.makedirs(USCITA, exist_ok=True)
    percorso = os.path.join(USCITA, "audit-prodotti.json")
    with open(percorso, "w") as fh:
        json.dump(rapporto, fh, indent=1, ensure_ascii=False)
    print("\ndettaglio completo in %s" % percorso)


if __name__ == "__main__":
    main()
