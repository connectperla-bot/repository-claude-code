#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera i mockup dei prodotti EU con l'API Printful, senza collegare niente.

PERCHE' NON SI COLLEGA NIENTE
Sull'account Printful i 133 prodotti Shopify risultano importati con ZERO
varianti collegate al catalogo. Collegarle darebbe i mockup automatici, ma
farebbe evadere gli ordini all'app Printful invece che al nostro webhook -- e
l'app stampa il disegno GENERICO del prodotto sincronizzato, non l'immagine
che il cliente ha composto nello studio di personalizzazione. Chi ordina un
collare col nome del cane riceverebbe un collare senza nome.

I mockup pero' si ottengono lo stesso: il Mockup Generator lavora sul
CATALOGO, non sui prodotti sincronizzati. Stessa filosofia con cui
providers/printful-client.js evade gli ordini.

DA DOVE VENGONO I DATI
catalogId, placement e misure sono gli stessi di PRINTFUL_MOCKUP_CONFIG in
perla-upload-endpoint.js, verificati contro l'account vero. La sottigliezza
del placement e' scritta li' e vale anche qui: e' il files[].TYPE di
GET /products/<catalogId>, non il files[].id. Sui quattro cataloghi l'id e'
sempre "default"; il type e' "front" su collare, bandana e guinzaglio,
"default" sulla ciotola. Sbagliarlo fa rispondere
"File type default is not allowed for this product".

I 66 motivi con le loro URL Cloudinary stanno gia' in perla-eu-prodotti.json.

LA RISOLUZIONE DA DARE AL GENERATORE
Nel repository c'erano due note che si contraddicevano: perla-build-eu-print-files.py
diceva che sopra una certa misura il mockup torna impastato,
perla-upload-endpoint.js diceva che la risoluzione di partenza non conta.

Provate tutte e due sullo stesso collare ("Barocco", motivo navy e oro) e
guardati i risultati affiancati: il nativo 7169x315 e il ridotto a 1600x70
danno la STESSA immagine, 1000x1000 in tutti e due i casi, indistinguibili.
Quindi si manda il nativo e --riduci resta li' solo per rifare il confronto
il giorno che Printful cambia qualcosa.

USO
    python3 scripts/perla-eu-mockup.py --prova Collare        # un solo tipo
    python3 scripts/perla-eu-mockup.py --prova Collare --riduci 1600
    python3 scripts/perla-eu-mockup.py --tutti                # tutti e 66

Printful limita la frequenza: --tutti puo' metterci mezz'ora e si riprende da
solo se lo si rilancia, perche' i mockup gia' scaricati li salta.

I mockup finiscono in generated-designs/eu-mockup/ con un indice JSON che
associa ogni file al prodotto Shopify, pronto per il caricamento.
"""
import json
import os
import re
import subprocess
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ENV = os.path.join(RADICE, "config", "printify.local.env")
PRODOTTI = os.path.join(QUI, "perla-eu-prodotti.json")
USCITA = os.path.join(RADICE, "generated-designs", "eu-mockup")

# Stessi valori di PRINTFUL_MOCKUP_CONFIG in perla-upload-endpoint.js.
CONFIG = {
    "Collare":    {"catalogo": 749, "variante": "PRINTFUL_COLLARE_EU_VARIANT_ID",
                   "placement": "front",   "w": 7169,  "h": 315},
    "Bandana":    {"catalogo": 630, "variante": "PRINTFUL_BANDANA_EU_VARIANT_ID",
                   "placement": "front",   "w": 4125,  "h": 4125},
    "Ciotola":    {"catalogo": 678, "variante": "PRINTFUL_CIOTOLA_EU_VARIANT_ID",
                   "placement": "default", "w": 6496,  "h": 803},
    "Guinzaglio": {"catalogo": 745, "variante": "PRINTFUL_GUINZAGLIO_EU_VARIANT_ID",
                   "placement": "front",   "w": 12389, "h": 219},
}

TENTATIVI = 20
ATTESA = 3

# Printful limita la frequenza del Mockup Generator, e stretto: lanciati i 66
# di fila, tredici sono passati e cinquantatre sono tornati
# 429 "TooManyRequests". Non e' un errore da ritentare subito: e' una finestra
# da aspettare. Si ritenta con pause crescenti, e i mockup gia' scaricati si
# saltano, cosi' un giro interrotto riprende invece di ricominciare.
RITENTATIVI_429 = 6
ATTESA_429 = 65


def chiavi():
    valori = {}
    with open(ENV) as fh:
        for riga in fh:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip()
    return valori


def api(metodo, percorso, token, store, corpo=None):
    """Da curl e non da urllib: in questo ambiente urllib esce dal proxy con
    un 403 (stessa nota in perla-usa-carica-stampe.py)."""
    cmd = ["curl", "-s", "-X", metodo,
           "-H", "Authorization: Bearer " + token,
           "-H", "X-PF-Store-Id: " + str(store)]
    if corpo is not None:
        cmd += ["-H", "Content-Type: application/json",
                "--data-binary", json.dumps(corpo)]
    out = subprocess.run(cmd + ["https://api.printful.com" + percorso],
                         capture_output=True, text=True, check=True).stdout
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError("risposta non JSON da %s: %s" % (percorso, out[:200]))


def url_ridotta(url, lato):
    """La stessa immagine Cloudinary, rimpicciolita, senza ricaricare niente.

    Si infila una trasformazione nel percorso: Cloudinary la applica al volo e
    la serve dalla sua cache. Nessun file locale, nessun secondo upload.
    """
    if not lato or "/image/upload/" not in url:
        return url
    return url.replace("/image/upload/", "/image/upload/w_%d,c_limit/" % lato, 1)


def tipo_di(titolo):
    """Da 'Collare "Barocco"' al tipo. I titoli EU seguono tutti questa forma."""
    m = re.match(r'(\w+)\s+"', titolo or "")
    return m.group(1) if m and m.group(1) in CONFIG else None


def genera(voce, env, lato):
    """Un mockup. Torna (percorso locale, url del mockup) o solleva."""
    tipo = tipo_di(voce["title"])
    if not tipo:
        raise RuntimeError("tipo non riconosciuto dal titolo: " + voce["title"])
    c = CONFIG[tipo]
    variante = env.get(c["variante"])
    if not variante:
        raise RuntimeError("variante non configurata: " + c["variante"])

    token, store = env["PRINTFUL_API_KEY"], env["PRINTFUL_STORE_ID"]
    # Lo store degli ordini API, non quello Shopify: e' l'unico su cui questa
    # chiave puo' creare task, ed e' lo stesso che usa printful-client.js.
    if str(store) != "18346388":
        store = "18346388"

    corpo = {
        "variant_ids": [int(variante)],
        "format": "jpg",
        "files": [{
            "placement": c["placement"],
            "image_url": url_ridotta(voce["pattern"], lato),
            # il motivo riempie l'intera area di stampa, come il composito in
            # perla-upload-endpoint.js
            "position": {"area_width": c["w"], "area_height": c["h"],
                         "width": c["w"], "height": c["h"],
                         "top": 0, "left": 0},
        }],
    }
    for tentativo in range(RITENTATIVI_429 + 1):
        r = api("POST", "/mockup-generator/create-task/%d" % c["catalogo"],
                token, store, corpo)
        if r.get("code") != 429:
            break
        if tentativo == RITENTATIVI_429:
            raise RuntimeError("429 anche dopo %d attese" % RITENTATIVI_429)
        attesa = ATTESA_429 * (tentativo + 1)
        print("      limite di frequenza, aspetto %ds..." % attesa)
        time.sleep(attesa)
    if r.get("code") != 200:
        raise RuntimeError("create-task %s: %s" % (r.get("code"), str(r.get("error"))[:200]))
    chiave = r["result"]["task_key"]

    for _ in range(TENTATIVI):
        time.sleep(ATTESA)
        t = api("GET", "/mockup-generator/task?task_key=" + chiave, token, store)
        res = t.get("result") or {}
        if res.get("status") == "completed":
            mock = (res.get("mockups") or [None])[0]
            if not mock:
                raise RuntimeError("task completato senza mockup")
            os.makedirs(USCITA, exist_ok=True)
            nome = "%s%s.jpg" % (voce["handle"][:60], "-r%d" % lato if lato else "")
            dove = os.path.join(USCITA, nome)
            subprocess.run(["curl", "-s", "-o", dove, mock["mockup_url"]], check=True)
            return dove, mock["mockup_url"]
        if res.get("status") == "failed":
            raise RuntimeError("task fallito: " + str(res.get("error"))[:200])
    raise RuntimeError("task non completato dopo %d tentativi" % TENTATIVI)


def main():
    env = chiavi()
    lato = 0
    if "--riduci" in sys.argv:
        lato = int(sys.argv[sys.argv.index("--riduci") + 1])
    prova = None
    if "--prova" in sys.argv:
        prova = sys.argv[sys.argv.index("--prova") + 1]

    with open(PRODOTTI) as fh:
        prodotti = json.load(fh)

    if prova:
        # uno solo per tipo, che e' il modo giusto di cominciare
        scelti, visti = [], set()
        for v in prodotti:
            t = tipo_di(v["title"])
            if t and prova.lower() in t.lower() and t not in visti:
                visti.add(t)
                scelti.append(v)
        prodotti = scelti
    elif "--tutti" not in sys.argv:
        for v in prodotti:
            print("da fare  %-46s %s" % (v["title"][:46], tipo_di(v["title"])))
        print("\n(elenco soltanto: --prova <tipo> per uno, --tutti per tutti)")
        return

    indice = {}
    percorso_indice = os.path.join(USCITA, "indice.json")
    if os.path.exists(percorso_indice):
        with open(percorso_indice) as fh:
            indice = json.load(fh)
    for v in prodotti:
        # ripresa: un mockup gia' scaricato non si rifa'
        gia = indice.get(v["id"])
        if gia and os.path.exists(gia.get("mockup", "")):
            print("  %-46s gia' fatto" % v["title"][:46])
            continue
        try:
            dove, url = genera(v, env, lato)
            indice[v["id"]] = {"titolo": v["title"], "handle": v["handle"],
                               "mockup": dove, "url": url}
            print("  %-46s %.0f KB" % (v["title"][:46], os.path.getsize(dove) / 1e3))
        except (RuntimeError, subprocess.CalledProcessError) as err:
            print("  %-46s FALLITO: %s" % (v["title"][:46], str(err)[:90]))

    if indice:
        os.makedirs(USCITA, exist_ok=True)
        with open(os.path.join(USCITA, "indice.json"), "w") as fh:
            json.dump(indice, fh, indent=1, ensure_ascii=False)
        print("\n%d mockup in %s" % (len(indice), USCITA))


if __name__ == "__main__":
    main()
