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


# Printify rifiuta il POST oltre una certa misura ("The POST data is too
# large"). Misurato sul campo: un file da 30,6 MB passa, uno da 39,2 no --
# e il corpo e' base64, quindi un terzo in piu' del file. 24 MB sta largo.
LIMITE_MB = 24


def alleggerisci(percorso):
    """Riduce la QUALITA' JPEG, mai le dimensioni, finche' il file sta sotto
    il limite.

    Il caricamento passa per base64, che aggiunge un terzo: un file da 77 MB
    diventa un corpo da 103 MB. Ridurre i pixel sarebbe rifare il difetto che
    stiamo togliendo, quindi si toglie qualita' di compressione -- su un
    motivo fitto, fra qualita' 92 e 82 non si vede differenza nemmeno al 100%,
    e il file dimezza.
    """
    if os.path.getsize(percorso) <= LIMITE_MB * 1e6:
        return percorso, False
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(percorso).convert("RGB")
    # PRIMA il sottocampionamento del colore, POI la qualita'. I file
    # nascono a 4:4:4 (subsampling=0), che serve dove il colore ha bordi
    # netti -- una scritta, un logo. Qui il livello del marchio e' un'altra
    # immagine e questo file e' solo motivo, quindi 4:2:0 toglie il 40% del
    # peso senza che si veda, e vale molto piu' che scendere di qualita':
    # a qualita' 52 su un damasco fitto gli artefatti si vedono, a 4:2:0 e
    # qualita' 88 no.
    for sotto, qualita in ((2, 92), (2, 88), (2, 82), (2, 76), (2, 68), (2, 58)):
        fuori = percorso.replace(".jpg", "-s%dq%d.jpg" % (sotto, qualita))
        im.save(fuori, quality=qualita, subsampling=sotto, optimize=True)
        if os.path.getsize(fuori) <= LIMITE_MB * 1e6:
            return fuori, True
    return fuori, True


def carica_immagine(percorso, token):
    with open(percorso, "rb") as fh:
        contenuto = base64.b64encode(fh.read()).decode("ascii")
    risposta = api("POST", "/v1/uploads/images.json", token=token, corpo={
        "file_name": os.path.basename(percorso), "contents": contenuto})
    if "id" not in risposta:
        raise RuntimeError("caricamento fallito: " + json.dumps(risposta)[:300])
    return risposta


def sostituisci_per_sorgente(prodotto, nuove_per_nome):
    """Sostituisce OGNI livello con il file costruito per quella sorgente.

    Diverso da sostituisci_motivo(): li' un prodotto aveva un motivo solo e
    si rimpiazzava tutto con quello. Qui la chiave e' il nome del file che il
    livello sta usando adesso, perche' un prodotto puo' averne piu' d'uno e
    perche' i titoli non dicono cosa stampano davvero.
    """
    toccate = 0
    aree = json.loads(json.dumps(prodotto["print_areas"]))
    for pa in aree:
        for ph in pa.get("placeholders", []):
            nuove = []
            for im in ph.get("images", []):
                if not im.get("name"):
                    # Livello senza nome = riferimento morto. Su "Copy of
                    # Gingham Luxe" ce n'era uno da 566x147 il cui id, chiesto
                    # a /v1/uploads, risponde "Not found": e' un residuo della
                    # duplicazione del prodotto. Printify rifiutava l'intero
                    # aggiornamento con "Provided images do not exist" finche'
                    # glielo si rimandava. Ogni immagine vera ha un nome.
                    print("  tolto un livello con riferimento morto (id %s)" % im.get("id"))
                    continue
                nuova = nuove_per_nome.get(im.get("name"))
                if not nuova:
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
            ph["images"] = nuove
        # Un placeholder senza immagini fa fallire il PUT con
        # "print_areas.N.placeholders.M.images: ... required". Le medagliette
        # ce l'hanno tutte: hanno un retro dichiarato e vuoto. Toglierlo dal
        # payload non cancella niente -- era gia' vuoto -- e senza questo
        # nessuna delle quindici medagliette si aggiorna.
        pa["placeholders"] = [x for x in pa.get("placeholders", []) if x.get("images")]
    return aree, toccate


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
        pa["placeholders"] = [x for x in pa.get("placeholders", []) if x.get("images")]
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


def per_sorgente(prodotti, token, shop, catalogo_sorgenti, filtro):
    """Secondo giro: collari, bandane e medagliette, dove si va per file
    stampato e non per titolo del prodotto."""
    caricate = {}
    mockup = os.path.join(STAMPE, "_mockup")
    os.makedirs(mockup, exist_ok=True)
    fatti = 0
    for p in prodotti:
        da_fare = {}
        for pa in p.get("print_areas", []):
            for ph in pa.get("placeholders", []):
                for im in ph.get("images", []):
                    nome = im.get("name")
                    if nome not in catalogo_sorgenti:
                        continue
                    if filtro and filtro.lower() not in nome.lower():
                        continue
                    da_fare[nome] = True
        if not da_fare:
            continue

        nuove = {}
        saltato = False
        for nome in da_fare:
            if nome not in caricate:
                f = file_da_sorgente(nome)
                if not f:
                    print("  manca il file costruito per " + nome)
                    saltato = True
                    break
                f, ridotto = alleggerisci(f)
                try:
                    caricate[nome] = carica_immagine(f, token)
                except RuntimeError as err:
                    print("  NON CARICATO %s: %s" % (nome, err))
                    saltato = True
                    break
                print("caricato %-46s %.1f MB%s" % (
                    nome[:46], os.path.getsize(f) / 1e6, " (ricompresso)" if ridotto else ""))
            nuove[nome] = caricate[nome]
        if saltato:
            continue

        aree, toccate = sostituisci_per_sorgente(p, nuove)
        r = api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                token=token, corpo={"print_areas": aree})
        if r.get("id") != p["id"]:
            print("  ERRORE su %s: %s" % (p["title"][:40], json.dumps(r)[:160]))
            continue
        d = api("GET", "/v1/shops/%s/products/%s.json" % (shop, p["id"]), token=token)
        img = next((i for i in d.get("images", []) if i.get("is_default")), None) \
            or (d.get("images") or [None])[0]
        if img:
            nome_file = p["title"][:44].lower().replace(" ", "-").replace("/", "-")
            nome_file = "".join(c for c in nome_file if c.isalnum() or c == "-")
            subprocess.run(["curl", "-s", "-o",
                            os.path.join(mockup, nome_file + "-mockup.jpg"), img["src"]], check=True)
        print("  %-50s %d livelli" % (p["title"][:50], toccate))
        fatti += 1
    return fatti


def file_da_sorgente(sorgente):
    """Il file costruito per questa sorgente, qualunque tipo sia."""
    base = os.path.splitext(sorgente)[0]
    for tipo in ("collare", "bandana", "medaglietta", "ciotola", "cuccia"):
        f = os.path.join(STAMPE, "%s-da-%s.jpg" % (tipo, base))
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

    if "--sorgenti" in sys.argv:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pufs", os.path.join(QUI, "perla-usa-file-stampa.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        n = per_sorgente(prodotti, token, shop, mod.PER_SORGENTE, filtro)
        print("\n%d prodotti aggiornati" % n)
        return

    mockup = os.path.join(STAMPE, "_mockup")
    os.makedirs(mockup, exist_ok=True)
    fatti = 0
    mancati = []
    for p in prodotti:
        if filtro and filtro.lower() not in p["title"].lower():
            continue
        f = file_per(p["title"], catalogo)
        if not f:
            continue
        if not (tutti or filtro):
            print("da fare  %-52s %s" % (p["title"][:52], os.path.basename(f)))
            continue

        f, ridotto = alleggerisci(f)
        print("carico   %-52s %.1f MB%s" % (
            p["title"][:52], os.path.getsize(f) / 1e6, " (ricompresso)" if ridotto else ""))
        try:
            nuova = carica_immagine(f, token)
        except RuntimeError as err:
            # un prodotto che non passa non deve fermare gli altri undici:
            # si segnala e si va avanti, poi lo si rifa'
            print("  NON CARICATO: %s" % err)
            mancati.append(p["title"])
            continue
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
    for t in mancati:
        print("  DA RIFARE: " + t)
    if not (tutti or filtro):
        print("(elenco soltanto: aggiungi --tutti per applicare)")


if __name__ == "__main__":
    main()
