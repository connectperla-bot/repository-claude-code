#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porta i file di stampa rifatti su Printify e li mette sui prodotti.

COSA FA, IN ORDINE
1. carica il file su Printify (POST /v1/uploads/images.json, base64);
2. sostituisce nel prodotto SOLO il livello del motivo, lasciando dov'e' il
   livello del logo -- che e' un'immagine diversa e sta a coordinate sue;
3. rilegge il prodotto e scarica il mockup nuovo, cosi' si puo' GUARDARE
   invece che fidarsi.

TRE COSE CHE NON SI POSSONO SBAGLIARE

`scale` e' la larghezza dell'immagine come frazione della larghezza
dell'area. I file vecchi stavano a 1,1-1,5 perche' erano piccoli e venivano
allargati oltre l'area per coprirla. I nuovi sono esattamente della misura
dell'area, quindi scale=1 e centro a (0,5, 0,5). Lasciare la vecchia scala
significherebbe ingrandire di nuovo un file che era gia' giusto.

UNA VOCE print_areas PER GRUPPO DI VARIANTI. E' la correzione di ROUND 47.
Fino a ieri si scriveva UNA voce con dentro tutte le varianti, e siccome
scale e' relativa all'AREA, lo stesso file su varianti di proporzioni
diverse sforava o lasciava vuoto: sul collare M il 24% di fettuccia bianca,
sulla cuccia 28"x18" il 18% di disegno tagliato. Printify accetta piu' voci,
ognuna con i suoi `variant_ids`: una per misura, ognuna col suo file.

Il PUT del prodotto vuole `print_areas` INTERO: quello che non si rimanda
viene perso. Per questo si riscrive tutto, partendo dal prodotto appena
riletto.

USO
    python3 scripts/perla-usa-carica-stampe.py --prova "Baroque Royal"
    python3 scripts/perla-usa-carica-stampe.py --tutti
    python3 scripts/perla-usa-carica-stampe.py --tutti --riprendi
Senza --tutti non tocca niente: elenca e basta. Con --riprendi salta i
prodotti che portano gia' i file giusti, per riprendere un giro interrotto
senza ricaricare centinaia di MB.
"""
import base64
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
STAMPE = os.path.join(RADICE, "generated-designs", "usa-print-files")
ENV = os.path.join(RADICE, "config", "printify.local.env")

def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aree = _modulo("aree_stampa", os.path.join(QUI, "aree-stampa.py"))
marchio = _modulo("marchio", os.path.join(QUI, "marchio.py"))
costruttore = _modulo("perla_usa_file_stampa", os.path.join(QUI, "perla-usa-file-stampa.py"))

# I livelli che NON sono il motivo: sono il marchio.
#
# ROUND 47 -- prima venivano LASCIATI STARE, perche' il marchio viveva li'.
# Ora il marchio e' composto dentro il file di stampa (marchio.py), quindi
# questi livelli sono doppioni: si tolgono. Erano anche la fonte del difetto
# "senza marchio": su diversi prodotti stavano fuori dal bordo dell'area
# (misurato: x=-0,084 y=1,044 sulla cuccia "Geometric Tribal"), cioe' c'erano
# ma non si stampavano.
LOGHI = marchio.LIVELLI_OBSOLETI

TIPO_DI_BLUEPRINT = {419: "cuccia", 562: "bandana", 566: "medaglietta",
                     784: "collare", 570: "ciotola", 855: "tappetino"}


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
    # ROUND 47 -- la scala si fermava a 58 e poi caricava LO STESSO il file
    # troppo grande, che Printify rifiuta con "The POST data is too large".
    # Successo davvero sulla cuccia "Luxury Paisley": 85,6 MB di partenza, a
    # qualita' 58 ancora 32,7 MB, sopra il limite, e il prodotto e' rimasto
    # indietro senza che il giro se ne accorgesse.
    #
    # Scendere piu' in basso non costa niente di visibile: affiancati a
    # grandezza 1:1, su quel paisley fitto oro su blu, qualita' 92, 58, 40 e 32
    # sono indistinguibili e la scritta "Perla Italia" resta nitida a tutte e
    # quattro. Guardato, non supposto.
    for sotto, qualita in ((2, 92), (2, 88), (2, 82), (2, 76), (2, 68),
                           (2, 58), (2, 50), (2, 42), (2, 34), (2, 28)):
        fuori = percorso.replace(".jpg", "-s%dq%d.jpg" % (sotto, qualita))
        im.save(fuori, quality=qualita, subsampling=sotto, optimize=True)
        if os.path.getsize(fuori) <= LIMITE_MB * 1e6:
            return fuori, True
    # Meglio fermarsi che caricare qualcosa che verra' rifiutato: un prodotto
    # saltato con un motivo chiaro si rifa', uno saltato in silenzio no.
    raise RuntimeError(
        "%s resta %.1f MB anche a qualita' 28: non si puo' caricare senza "
        "ridurre i pixel, che sarebbe rifare il difetto. Serve un motivo meno "
        "fitto per questa misura."
        % (os.path.basename(percorso), os.path.getsize(fuori) / 1e6))


def carica_immagine(percorso, token):
    with open(percorso, "rb") as fh:
        contenuto = base64.b64encode(fh.read()).decode("ascii")
    risposta = api("POST", "/v1/uploads/images.json", token=token, corpo={
        "file_name": os.path.basename(percorso), "contents": contenuto})
    if "id" not in risposta:
        raise RuntimeError("caricamento fallito: " + json.dumps(risposta)[:300])
    return risposta


def sorgente_del_livello(nome):
    """Dal file che il prodotto stampa OGGI alla chiave di PER_SORGENTE.

    Tre forme possibili, perche' il catalogo ha stratificato tre tornate:
        bandana-damask-navy-perla.jpg                    artwork originale
        bandana-da-bandana-damask-navy-perla.jpg         gia' ricostruito
        bandana-da-bandana-damask-navy-perla-4275x2325.jpg  ricostruito per misura
    Tutte e tre riportano alla stessa chiave: bandana-damask-navy-perla.jpg.
    """
    nome = nome or ""
    m = re.match(r"^(?:collare|bandana|medaglietta|ciotola|cuccia|tappetino)"
                 r"-da-(.+?)(?:-\d+x\d+)?\.jpg$", nome)
    if m:
        return m.group(1) + ".jpg"
    if nome in costruttore.PER_SORGENTE or nome in costruttore.DA_ARTWORK:
        return nome
    return None


def chiave_catalogo(titolo):
    """La voce di CATALOGO per questo titolo Printify.

    La chiave e' l'INIZIO del titolo, non il titolo intero: i titoli sono
    lunghi e cambiano in coda ("...for Dogs & Cats"). Fra due che combaciano
    entrambe ("Perla Italy..." e "Copy of Perla Italy...") vince la piu'
    lunga, che e' la piu' precisa.
    """
    ok = [k for k in costruttore.CATALOGO if titolo.startswith(k)]
    return max(ok, key=len) if ok else None


def file_costruito(tipo, identita, misura, da_catalogo):
    """Il file costruito per questa identita' E QUESTA MISURA, o None."""
    if da_catalogo:
        nome = "%s-%s" % (tipo, costruttore.nome_catalogo(identita, misura))
    else:
        nome = costruttore.nome_uscita(identita, misura)
    percorso = os.path.join(STAMPE, nome + ".jpg")
    return percorso if os.path.exists(percorso) else None


def identifica(prodotto, tipo):
    """Cosa stampa questo prodotto: (identita', da_catalogo) oppure (None, motivo).

    Sulle CUCCE si va per titolo, perche' quattro di loro stampano motivi
    geometrici disegnati che non hanno una sorgente. Su tutto il resto si va
    per FILE STAMPATO, perche' i titoli mentono: "Maroon Damask Dog Collar"
    stampa collar-olive-perla-only.jpg. E' la stessa regola gia' scritta in
    perla-usa-file-stampa.py.
    """
    if tipo == "cuccia":
        chiave = chiave_catalogo(prodotto["title"])
        return (chiave, True) if chiave else (None, "titolo non nel CATALOGO")

    for pa in prodotto.get("print_areas", []):
        for ph in pa.get("placeholders", []):
            for im in ph.get("images", []):
                nome = im.get("name")
                if not nome or nome in LOGHI:
                    continue
                sorgente = sorgente_del_livello(nome)
                if sorgente and (sorgente in costruttore.PER_SORGENTE
                                 or sorgente in costruttore.DA_ARTWORK):
                    return sorgente, False
    return None, "nessun livello motivo riconosciuto"


def gia_aggiornato(prodotto, tipo, identita, da_catalogo, token):
    """Vero se il prodotto porta gia' i file giusti, uno per gruppo.

    Serve a riprendere un giro interrotto senza ricaricare centinaia di MB
    per prodotti gia' a posto. Il confronto e' sui NOMI dei file attesi: se
    il contenuto di un file cambia a parita' di nome (per esempio dopo un
    --rifai) questo controllo NON se ne accorge, quindi in quel caso si usa
    --prova sul titolo, che salta la ripresa.
    """
    try:
        geometria = aree.per_prodotto(prodotto, token)
    except RuntimeError:
        return False
    per_id = {v["id"]: v for v in geometria}
    abilitate = aree.abilitate(prodotto)
    if not abilitate:
        return False
    presenti = {im.get("name")
                for pa in prodotto.get("print_areas", [])
                for ph in pa.get("placeholders", [])
                for im in ph.get("images", [])}
    for gruppo in aree.gruppi(geometria, "front", solo_varianti=abilitate):
        misura = per_id[gruppo["variant_ids"][0]]["placeholders"].get("front")
        if not misura:
            continue
        percorso = file_costruito(tipo, identita, misura, da_catalogo)
        if not percorso or os.path.basename(percorso) not in presenti:
            return False
    return True


def aree_per_variante(prodotto, tipo, identita, da_catalogo, token, carica):
    """Le print_areas nuove: UNA VOCE PER GRUPPO DI VARIANTI.

    E' il cuore della correzione. Prima si scriveva una voce sola con dentro
    tutte le varianti, e siccome `scale` e' relativa all'area, sulle varianti
    di proporzioni diverse il file sforava o lasciava vuoto.

    `carica` e' la funzione che porta un file su Printify: la si passa da
    fuori cosi' questa funzione resta verificabile senza rete (vedi
    tests/aree-per-variante.test.py).
    """
    geometria = aree.per_prodotto(prodotto, token)
    per_id = {v["id"]: v for v in geometria}
    abilitate = aree.abilitate(prodotto)
    if not abilitate:
        return None, "nessuna variante abilitata"

    # PRINT_AREAS DEVE ELENCARE TUTTE LE VARIANTI DEL PRODOTTO, NON SOLO QUELLE
    # ABILITATE. Senza, Printify rifiuta l'intero aggiornamento con
    #   8251 "Variants do not match selected blueprint and print provider"
    # (incontrato sul primo caricamento di prova, bandana "Vintage Damask").
    #
    # E la differenza non e' solo "abilitate contro disabilitate": quel
    # prodotto porta la variante 70849 ('25" x 12"'), che il blueprint 562 NON
    # ELENCA PIU'. E' una misura ritirata dal fornitore e rimasta attaccata al
    # prodotto. Non ha una misura di stampa da nessuna parte, quindi non puo'
    # avere un gruppo suo: si aggrega al gruppo piu' grande. Siccome e'
    # disabilitata non e' ordinabile, e il file che le tocca non stampera' mai.
    tutte = [v["id"] for v in prodotto.get("variants", [])]

    # Le posizioni che oggi hanno davvero un'immagine. Il retro delle
    # medagliette e' dichiarato e vuoto: rimandarlo vuoto fa fallire il PUT
    # con "print_areas.N.placeholders.M.images: required".
    posizioni = []
    for pa in prodotto.get("print_areas", []):
        for ph in pa.get("placeholders", []):
            if ph.get("images") and ph.get("position") not in posizioni:
                posizioni.append(ph["position"])
    if not posizioni:
        return None, "nessun placeholder con immagini"

    nuove = []
    orfane = list(tutte)
    for gruppo in aree.gruppi(geometria, posizioni[0], solo_varianti=set(tutte)):
        segnaposto = []
        mancante = None
        for posizione in posizioni:
            misura = per_id[gruppo["variant_ids"][0]]["placeholders"].get(posizione)
            if not misura:
                continue
            percorso = file_costruito(tipo, identita, misura, da_catalogo)
            if not percorso:
                mancante = misura
                break
            caricata = carica(percorso)
            segnaposto.append({
                "position": posizione,
                "images": [{
                    "id": caricata["id"],
                    "name": caricata["file_name"],
                    "type": caricata.get("mime_type", "image/jpeg"),
                    "height": caricata["height"],
                    "width": caricata["width"],
                    # il file E' della misura dell'area: scale=1 e centro esatto
                    "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0,
                }],
            })
        if mancante:
            # Se il gruppo non ha nemmeno una variante VENDIBILE, il file
            # mancante non serve a nessuno: le sue varianti si aggregano al
            # gruppo piu' grande e si va avanti. Se invece qualcuno la vende,
            # fermarsi e' l'unica risposta onesta.
            if set(gruppo["variant_ids"]) & abilitate:
                return None, ("manca il file %dx%d: costruiscilo con "
                              "python3 scripts/perla-usa-file-stampa.py" % mancante)
            continue
        if segnaposto:
            nuove.append({"variant_ids": list(gruppo["variant_ids"]),
                          "placeholders": segnaposto})
            orfane = [v for v in orfane if v not in set(gruppo["variant_ids"])]

    if not nuove:
        return None, "nessun gruppo di varianti da scrivere"
    if orfane:
        # varianti ritirate dal blueprint, o rimaste senza file: al gruppo piu'
        # grande, che e' il primo (aree.gruppi ordina dal piu' grande)
        nuove[0]["variant_ids"] = sorted(set(nuove[0]["variant_ids"]) | set(orfane))
    return nuove, None


def main():
    env = chiavi()
    token, shop = env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"]
    tutti = "--tutti" in sys.argv
    riprendi = "--riprendi" in sys.argv
    gia = 0
    filtro = None
    if "--prova" in sys.argv:
        filtro = sys.argv[sys.argv.index("--prova") + 1]

    prodotti, pagina = [], 1
    while True:
        d = api("GET", "/v1/shops/%s/products.json?limit=50&page=%d" % (shop, pagina), token=token)
        prodotti += d["data"]
        if pagina >= d["last_page"]:
            break
        pagina += 1

    caricate = {}

    def carica(percorso):
        """Un file si carica UNA volta sola, anche se lo usano dieci prodotti.

        La chiave e' il percorso, che ora contiene la misura: due prodotti che
        condividono il motivo ma non la taglia sono due file diversi e vanno
        caricati tutti e due.
        """
        if percorso not in caricate:
            f, ridotto = alleggerisci(percorso)      # puo' sollevare RuntimeError
            caricate[percorso] = carica_immagine(f, token)
            print("    caricato %-46s %.1f MB%s" % (
                os.path.basename(f)[:46], os.path.getsize(f) / 1e6,
                " (ricompresso)" if ridotto else ""))
        return caricate[percorso]

    mockup = os.path.join(STAMPE, "_mockup")
    os.makedirs(mockup, exist_ok=True)
    fatti, saltati = 0, []

    for p in sorted(prodotti, key=lambda x: x["title"]):
        if filtro and filtro.lower() not in p["title"].lower():
            continue
        tipo = TIPO_DI_BLUEPRINT.get(p["blueprint_id"])
        if not tipo:
            continue
        identita, da_catalogo = identifica(p, tipo)
        if not identita:
            saltati.append((p["title"], da_catalogo))
            continue
        if not (tutti or filtro):
            print("da fare  %-52s %s" % (p["title"][:52], identita))
            continue
        # --riprendi vale solo senza filtro: se qualcuno nomina un prodotto,
        # lo vuole rifare comunque (e' il caso dopo un --rifai dei file)
        if riprendi and not filtro and gia_aggiornato(p, tipo, identita, da_catalogo, token):
            gia += 1
            continue

        print("%-54s" % p["title"][:54])
        try:
            nuove, errore = aree_per_variante(p, tipo, identita, da_catalogo, token, carica)
        except RuntimeError as err:
            saltati.append((p["title"], str(err)[:90]))
            continue
        if errore:
            print("    saltato: " + errore)
            saltati.append((p["title"], errore))
            continue

        r = api("PUT", "/v1/shops/%s/products/%s.json" % (shop, p["id"]),
                token=token, corpo={"print_areas": nuove})
        if r.get("id") != p["id"]:
            print("    ERRORE: " + json.dumps(r)[:200])
            saltati.append((p["title"], json.dumps(r)[:90]))
            continue

        # rileggi e prendi il mockup nuovo: e' l'unica prova che il file e'
        # finito dove doveva, e va guardato
        d = api("GET", "/v1/shops/%s/products/%s.json" % (shop, p["id"]), token=token)
        img = next((i for i in d.get("images", []) if i.get("is_default")), None) \
            or (d.get("images") or [None])[0]
        if img:
            nome_file = "".join(c for c in p["title"][:44].lower().replace(" ", "-")
                                if c.isalnum() or c == "-") + "-mockup.jpg"
            # SENZA check=True DI PROPOSITO. Il mockup serve a noi per
            # guardare, il prodotto e' gia' aggiornato quando arriviamo qui.
            # Con check=True un errore SSL passeggero di curl (visto: exit 35)
            # fa cadere l'intero giro e i prodotti rimasti restano indietro --
            # e' successo davvero, al quarantunesimo su settanta.
            esito = subprocess.run(["curl", "-s", "-o", os.path.join(mockup, nome_file),
                                    img["src"]])
            if esito.returncode:
                print("    (mockup non scaricato, curl %d: il prodotto e' comunque "
                      "aggiornato)" % esito.returncode)
        print("    ok: %d gruppi di varianti, mockup in %s"
              % (len(nuove), os.path.basename(mockup)))
        fatti += 1

    print("\n%d prodotti aggiornati%s" % (
        fatti, ", %d gia' a posto" % gia if gia else ""))
    for titolo, motivo in saltati:
        print("  saltato  %-46s %s" % (titolo[:46], motivo))
    if not (tutti or filtro):
        print("(elenco soltanto: aggiungi --tutti per applicare)")


if __name__ == "__main__":
    main()
