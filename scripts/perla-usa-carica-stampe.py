#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porta i file di stampa rifatti su Printify e li mette sui prodotti.

COSA FA, IN ORDINE
1. carica il file su Printify (POST /v1/uploads/images.json, base64);
2. sostituisce nel prodotto SOLO il livello del motivo, lasciando dov'e' il
   livello del logo -- che e' un'immagine diversa e sta a coordinate sue;
3. rilegge il prodotto e scarica il mockup nuovo, cosi' si puo' GUARDARE
   invece che fidarsi.

DUE COSE CHE NON SI POSSONO SBAGLIARE

`scale` e' la larghezza dell'immagine come frazione della larghezza
dell'area. I file vecchi stavano a 1,1-1,5 perche' erano piccoli e venivano
allargati oltre l'area per coprirla. I nuovi sono esattamente della misura
dell'area, quindi scale=1 e centro a (0,5, 0,5). Lasciare la vecchia scala
significherebbe ingrandire di nuovo un file che era gia' giusto.

Il PUT del prodotto vuole `print_areas` INTERO: quello che non si rimanda
viene perso. Per questo si parte sempre dal prodotto appena riletto e si
cambia una voce sola.

USO
    python3 scripts/perla-usa-carica-stampe.py --prova "Baroque Royal"
    python3 scripts/perla-usa-carica-stampe.py --tutti
Senza --tutti non tocca niente: elenca e basta.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
STAMPE = os.path.join(RADICE, "generated-designs", "usa-print-files")
ENV = os.path.join(RADICE, "config", "printify.local.env")

# I livelli che NON sono il motivo: si riconoscono dal nome e vanno lasciati
# stare. Sono il marchio, e stanno a una scala e a coordinate loro.
LOGHI = ("logo", "LOGO", "perla-combined", "v2-01-logo")


def chiavi():
    valori = {}
    with open(ENV) as fh:
        for riga in fh:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip()
    return valori


def api(metodo, percorso, corpo=None, token=None):
    """Chiamata all'API Printify. Passa da curl e non da urllib perche' in
    questo ambiente urllib esce dal proxy con un 403."""
    cmd = ["curl", "-s", "-X", metodo,
           "-H", "Authorization: Bearer " + token,
           "-H", "Content-Type: application/json",
           "https://api.printify.com" + percorso]
    tmp = None
    if corpo is not None:
        # il corpo puo' pesare decine di MB (base64 di un file 15600x12600):
        # su riga di comando non ci sta, quindi passa da un file
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(corpo, tmp)
        tmp.close()
        cmd[1:1] = ["--data-binary", "@" + tmp.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    finally:
        if tmp:
            os.unlink(tmp.name)
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError("risposta non JSON da %s: %s" % (percorso, out[:300]))


def carica_immagine(percorso, token):
    with open(percorso, "rb") as fh:
        contenuto = base64.b64encode(fh.read()).decode("ascii")
    risposta = api("POST", "/v1/uploads/images.json", token=token, corpo={
        "file_name": os.path.basename(percorso), "contents": contenuto})
    if "id" not in risposta:
        raise RuntimeError("caricamento fallito: " + json.dumps(risposta)[:300])
    return risposta


def sostituisci_motivo(prodotto, nuova):
    """Rimpiazza il livello del motivo in ogni area di stampa.

    Torna anche quante voci ha toccato: se e' zero il prodotto non aveva un
    motivo da sostituire ed e' meglio saperlo che aggiornare a vuoto.
    """
    toccate = 0
    aree = json.loads(json.dumps(prodotto["print_areas"]))  # copia
    for pa in aree:
        for ph in pa.get("placeholders", []):
            nuove = []
            for im in ph.get("images", []):
                if any(l in (im.get("name") or "") for l in LOGHI):
                    nuove.append(im)
                    continue
                nuove.append({
                    "id": nuova["id"],
                    "name": nuova["file_name"],
                    "type": nuova.get("mime_type", "image/jpeg"),
                    "height": nuova["height"],
                    "width": nuova["width"],
                    "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0,
                })
                toccate += 1
            # il motivo sta sotto, il marchio sopra: l'ordine e' quello della
            # lista e si conserva perche' si riscrive nella stessa posizione
            ph["images"] = nuove
    return aree, toccate


def _catalogo():
    """Il catalogo sta in perla-usa-file-stampa.py e non va duplicato qui:
    se le due liste divergono si carica il file sbagliato sul prodotto
    sbagliato, ed e' un errore che non si vede finche' non arriva stampato."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "perla_usa_file_stampa", os.path.join(QUI, "perla-usa-file-stampa.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CATALOGO


def file_per(titolo, catalogo):
    """Il file costruito per questo prodotto.

    La chiave del catalogo e' l'INIZIO del titolo Printify, non il titolo
    intero: i titoli sono lunghi e cambiano in coda ("...for Dogs & Cats").
    Il nome del file lo genera perla-usa-file-stampa.py dalla chiave, quindi
    qui si parte dalla chiave e non dal titolo, altrimenti non si trova
    niente -- e' esattamente lo sbaglio fatto la prima volta.

    Fra due chiavi che combaciano entrambe (per esempio "Perla Italy..." e
    "Copy of Perla Italy...") vince la piu' lunga, che e' la piu' precisa.
    """
    chiavi_ok = [k for k in catalogo if titolo.startswith(k)]
    if not chiavi_ok:
        return None
    chiave = max(chiavi_ok, key=len)
    nome = chiave.lower().replace(" ", "-").replace("'", "").replace("\u2014", "")
    nome = "-".join(p for p in nome.split("-") if p)[:60]
    for tipo in ("cuccia", "collare", "bandana", "ciotola", "medaglietta"):
        f = os.path.join(STAMPE, "%s-%s.jpg" % (tipo, nome))
        if os.path.exists(f):
            return f
    return None


def main():
    env = chiavi()
    catalogo = _catalogo()
    token, shop = env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"]
    tutti = "--tutti" in sys.argv
    filtro = None
    if "--prova" in sys.argv:
        filtro = sys.argv[sys.argv.index("--prova") + 1]

    prodotti = []
    pagina = 1
    while True:
        d = api("GET", "/v1/shops/%s/products.json?limit=50&page=%d" % (shop, pagina), token=token)
        prodotti += d["data"]
        if pagina >= d["last_page"]:
            break
        pagina += 1

    mockup = os.path.join(STAMPE, "_mockup")
    os.makedirs(mockup, exist_ok=True)
    fatti = 0
    for p in prodotti:
        if filtro and filtro.lower() not in p["title"].lower():
            continue
        f = file_per(p["title"], catalogo)
        if not f:
            continue
        if not (tutti or filtro):
            print("da fare  %-52s %s" % (p["title"][:52], os.path.basename(f)))
            continue

        print("carico   %-52s %.1f MB" % (p["title"][:52], os.path.getsize(f) / 1e6))
        nuova = carica_immagine(f, token)
        aree, toccate = sostituisci_motivo(p, nuova)
        if not toccate:
            print("  saltato: nessun livello motivo da sostituire")
            continue
        r = api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                token=token, corpo={"print_areas": aree})
        if r.get("id") != p["id"]:
            print("  ERRORE aggiornamento: " + json.dumps(r)[:200])
            continue

        # rileggi e prendi il mockup nuovo: e' l'unica prova che il file e'
        # finito dove doveva, e va guardato
        d = api("GET", "/v1/shops/%s/products/%s.json" % (shop, p["id"]), token=token)
        img = next((i for i in d.get("images", []) if i.get("is_default")), None) \
            or (d.get("images") or [None])[0]
        if img:
            dove = os.path.join(mockup, os.path.basename(f).replace(".jpg", "-mockup.jpg"))
            subprocess.run(["curl", "-s", "-o", dove, img["src"]], check=True)
            print("  ok, %d livelli sostituiti, mockup in %s" % (toccate, os.path.basename(dove)))
        fatti += 1

    print("\n%d prodotti aggiornati" % fatti)
    if not (tutti or filtro):
        print("(elenco soltanto: aggiungi --tutti per applicare)")


if __name__ == "__main__":
    main()
