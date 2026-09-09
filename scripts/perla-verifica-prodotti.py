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
    python3 scripts/perla-verifica-prodotti.py --eu           # i 66 prodotti EU

Per il controllo delle taglie EU serve generated-designs/taglie-eu.json, una
fotografia dei titoli delle varianti su Shopify. Va rifatta quando i prodotti
cambiano, con questa query (gli id sono quelli di perla-eu-prodotti.json):

    query($ids:[ID!]!){ nodes(ids:$ids){ ... on Product {
        id variants(first:10){ nodes{ title } } } } }

e salvando {id prodotto: [titoli delle varianti]}. Senza quel file l'audit
controlla solo le misure dei motivi, e lo dice invece di tacere.

Uscita leggibile a schermo e generated-designs/audit-prodotti.json per il
confronto prima/dopo.
"""
import importlib.util
import json
import os
import re
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

# UN FILE CHE FINISCE PER "-perla" HA IL MARCHIO GIA' DENTRO
#
# Prima qui c'era nome.endswith("-perla.jpg"), e ha smesso di bastare il 4
# settembre: i file dei tre prodotti americani nuovi si chiamano
# collare-pelle-neutro-perla-1650x150.png -- PNG perche' l'incisione vuole la
# trasparenza, e con la misura nel nome perche' se ne costruisce uno per ogni
# area di stampa. Con la vecchia regola l'audit li dichiarava "senza marchio"
# pur avendocelo composto dentro: un falso allarme su tre prodotti buoni
# nasconde i difetti veri quanto un difetto non visto.
#
# La convenzione vera e' il suffisso "-perla", non l'estensione: la misura
# facoltativa e l'estensione stanno dopo.
MARCHIO_DENTRO = re.compile(r"-perla(-\d+x\d+)?\.(jpe?g|png)$", re.I)

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
                # SPECCHIATO O RUOTATO. Chiesto esplicitamente ("il fatto di
                # aver tagli, cose specchiate o incongruenze") e costa niente:
                # Printify lo dice nel placeholder, non serve scaricare il
                # file. Oggi sono zero su 89 immagini, ed e' proprio per questo
                # che il controllo va messo adesso: un giorno che qualcuno
                # trascina un livello nell'editor di Printify, un motivo
                # specchiato non si distingue a occhio dall'originale -- ma la
                # scritta del marchio dentro il motivo si', e si stampa al
                # contrario.
                if im.get("flipX"):
                    difetti.append("%s e' specchiata in orizzontale" % nome)
                if im.get("flipY"):
                    difetti.append("%s e' specchiata in verticale" % nome)
                giro = im.get("angle") or 0
                if giro % 360:
                    difetti.append("%s e' ruotata di %s gradi" % (nome, giro))
                e_marchio = nome in marchio.LIVELLI_OBSOLETI
                if e_marchio:
                    marchi_totali += 1
                elif nome in manifesto or MARCHIO_DENTRO.search(nome or ""):
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
# LA LINEA EU
# ==========================================================================
# Fino a ROUND 47 questo audit guardava SOLO Printify, e la linea europea non
# era mai passata sotto lo stesso controllo. Rifatto a mano su tutti e 66 i
# prodotti: erano a posto. Ma "erano a posto quel giorno" non serve a niente
# se domani nessuno puo' rifarlo, e i due controlli che contano costano poco.
#
# 1. LA MISURA DEL MOTIVO. Il file EU va a Printful cosi' com'e', senza
#    passare da un print_areas: se non ha la misura dell'area di stampa,
#    Printful lo adatta da solo e il motivo esce deformato. E' lo stesso
#    difetto del catalogo americano, in una forma dove non lo vedremmo.
# 2. IL TITOLO DELLA TAGLIA. varianti-fornitore.js traduce il titolo scelto
#    dal cliente nell'id della variante da ordinare, e se non lo riconosce
#    SOLLEVA -- di proposito, perche' spedire la taglia sbagliata e' un reso.
#    Un titolo cambiato su Shopify ferma quegli ordini, in silenzio finche'
#    qualcuno non guarda i log.
#
# Le misure sono le stesse di PRINTFUL_MOCKUP_CONFIG in
# perla-upload-endpoint.js, verificate contro
# GET /mockup-generator/printfiles/<catalogo>.
AREE_EU = {"Collare": (7169, 315), "Bandana": (4125, 4125),
           "Ciotola": (6496, 803), "Guinzaglio": (12389, 219)}

# Il tipo prodotto come lo conosce varianti-fornitore.js.
TIPO_EU = {"Collare": "collare_eu", "Bandana": "bandana_eu",
           "Ciotola": "ciotola_eu", "Guinzaglio": "guinzaglio_eu"}

# I titoli EU hanno la forma 'Collare "Barocco"', con le virgolette dritte
# oppure "a sesto": la titolare rinomina i prodotti dal pannello Shopify, che
# le mette curve da solo. Sedici prodotti su 66 ce le hanno, e finche' qui si
# chiedevano solo quelle dritte l'audit li saltava in silenzio: diceva "66
# motivi alla misura giusta" dopo averne guardati cinquanta.
import re as _re  # noqa: E402  (qui, accanto a cio' che serve)
TITOLO_EU = _re.compile(u'(\\w+)\\s+[\u201c"\u00ab]')
MOTIVO_EU = _re.compile(u'\\w+\\s+[\u201c"\u00ab](.+)[\u201d"\u00bb]\\s*$')


def _misura_remota(url):
    """La misura di un JPEG senza scaricarlo tutto: bastano i primi 64 KB."""
    import struct
    dati = subprocess.run(["curl", "-s", "-r", "0-65535", url],
                          capture_output=True).stdout
    i = 2
    while i < len(dati) - 9:
        if dati[i] != 0xFF:
            i += 1
            continue
        m = dati[i + 1]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", dati[i + 5:i + 9])
            return (w, h)
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        if i + 4 > len(dati):
            break
        i += 2 + struct.unpack(">H", dati[i + 2:i + 4])[0]
    return None


def _scarica_ridotta(url, larghezza=900):
    """L'immagine pubblicata, rimpicciolita da Cloudinary invece che da noi.

    Un nativo pesa fino a 8 MB e per controllare il marchio ne bastano 900 px:
    inserendo w_900 nella URL e' Cloudinary a ridurlo, e ne arrivano un
    centinaio di KB. Su URL non Cloudinary si scarica l'originale.
    """
    from PIL import Image
    import io as _io
    if "/image/upload/" in url:
        url = url.replace("/image/upload/", "/image/upload/w_%d/" % larghezza, 1)
    dati = subprocess.run(["curl", "-sL", url], capture_output=True).stdout
    if not dati:
        return None
    try:
        return Image.open(_io.BytesIO(dati)).convert("RGB")
    except Exception:
        return None


def _controlla_marchio(tipo, motivo, url):
    """Il marchio composto c'e' davvero, e la firma vecchia non c'e' piu'.

    E' il controllo che mancava. Fino a qui --eu misurava solo le DIMENSIONI
    del motivo, e per questo diceva "66 motivi alla misura giusta" mentre la
    bandana antracite aveva il logo semitrasparente col puntino nero e la
    bandana cammei cipria era decentrata: nessuna delle due sbagliava misura.

    Torna None se non c'e' niente da dire, altrimenti la ragione.
    """
    import marchio
    nome = "%s-%s.jpg" % (tipo.lower(),
                          motivo.lower().replace(" ", "-").replace("'", ""))
    if tipo != "Bandana" or not marchio.serve(nome):
        # collari, ciotole e guinzagli portano il monogramma dentro il motivo
        return None
    im = _scarica_ridotta(url)
    if im is None:
        return "immagine non scaricabile"
    riquadri = marchio.riquadri("bandana_eu", im.size, (1360, 2288))
    if not marchio.presente(im, riquadri, soglia=34.0):
        return "il marchio non c'e' dove dovrebbe stare"
    if nome in marchio.NATIVI_CON_MEDAGLIONE:
        s, a, d, b = marchio.MEDAGLIONE
        w, h = im.size
        vecchia = im.crop((int(s * w), int(a * h), int(d * w), int(b * h)))
        oro = sum(1 for p in vecchia.getdata()
                  if p[0] > 150 and p[1] > 110 and p[2] < 110)
        if oro > 0.06 * vecchia.width * vecchia.height:
            return "la firma vecchia e' ancora li' (%d%% d'oro nel suo riquadro)" % (
                100 * oro // max(1, vecchia.width * vecchia.height))
    return None


def verifica_eu(taglie_shopify=None):
    """I 66 prodotti EU: misura del motivo e titoli di taglia.

    `taglie_shopify` e' {id prodotto: [titoli delle varianti]}, che si legge da
    Shopify. Se non c'e', si controlla solo la misura dei motivi -- meta'
    verifica e' meglio di nessuna, ma va detto.
    """
    import re
    percorso = os.path.join(QUI, "perla-eu-prodotti.json")
    with open(percorso) as fh:
        prodotti = json.load(fh)

    varianti_note = {}
    js = os.path.join(QUI, "varianti-fornitore.js")
    if os.path.exists(js):
        with open(js) as fh:
            testo = fh.read()
        for tipo in TIPO_EU.values():
            m = re.search(r"\b%s:\s*\{(.*?)\n  \}" % tipo, testo, re.S)
            if m:
                varianti_note[tipo] = set(
                    re.findall(r"'([^']+)':", m.group(1)))

    fuori = {"motivi": [], "taglie": [], "marchi": []}
    for v in prodotti:
        m = TITOLO_EU.match(v.get("title", ""))
        tipo = m.group(1) if m else None
        if tipo not in AREE_EU:
            continue
        attesa = AREE_EU[tipo]
        avuta = _misura_remota(v["pattern"])
        if avuta != attesa:
            fuori["motivi"].append({
                "titolo": v["title"], "attesa": list(attesa),
                "avuta": list(avuta) if avuta else None})
        motivo = MOTIVO_EU.match(v["title"])
        guaio = _controlla_marchio(tipo, motivo.group(1), v["pattern"]) if motivo else None
        if guaio:
            fuori["marchi"].append({"titolo": v["title"], "guaio": guaio})

        titoli = (taglie_shopify or {}).get(v["id"])
        note = varianti_note.get(TIPO_EU[tipo])
        if titoli is None or note is None:
            continue
        # guinzaglio_eu resta fuori dalla mappa di proposito: Printful lo fa
        # in una misura sola, quindi vale la variante configurata
        if not note:
            continue
        sconosciuti = [t for t in titoli if t not in note]
        if sconosciuti:
            fuori["taglie"].append({"titolo": v["title"], "tipo": TIPO_EU[tipo],
                                    "sconosciuti": sconosciuti})
    fuori["esaminati"] = sum(
        1 for v in prodotti
        if TITOLO_EU.match(v.get("title", ""))
        and TITOLO_EU.match(v["title"]).group(1) in AREE_EU)
    fuori["taglie_controllate"] = taglie_shopify is not None
    return fuori


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

def verifica_toppe(prodotti, cartella):
    """La cartella crema c'e' ancora, dentro i pixel dei file di stampa?

    PERCHE' E' A RICHIESTA E NON SEMPRE
    Va scaricato il file di stampa vero: sono 317 MB per i 48 prodotti attivi.
    Farlo a ogni giro trasformerebbe un controllo di trenta secondi in uno di
    dieci minuti, e un controllo che nessuno lancia non controlla niente. Qui
    si scarica una volta e si tiene in cache.

    Uso:  python3 scripts/perla-verifica-prodotti.py --toppe
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs(cartella, exist_ok=True)
    logo = marchio._marchio()
    tipi = {419: "cuccia", 562: "bandana", 566: "medaglietta", 570: "ciotola"}
    sporchi = []
    guardati = 0
    for p in sorted(prodotti, key=lambda x: x["title"]):
        tipo = tipi.get(p["blueprint_id"])
        if tipo is None:
            continue
        immagine = next((im for pa in p.get("print_areas", [])
                         for ph in pa.get("placeholders", [])
                         for im in ph.get("images", [])), None)
        if not immagine:
            continue
        dove = os.path.join(cartella, "%s-%s.img" % (tipo, p["id"]))
        if not (os.path.exists(dove) and os.path.getsize(dove)):
            subprocess.run(["curl", "-sL", "--max-time", "180",
                            immagine["src"], "-o", dove], check=False)
        try:
            im = Image.open(dove)
            esiti = marchio.toppa(im, marchio.riquadri(tipo, im.size, logo.size))
        except Exception as err:
            print("   %-52s non misurabile: %s" % (p["title"][:52], err))
            continue
        guardati += 1
        peggio = max(esiti, key=lambda e: e["dentro"] - e["intorno"]) if esiti else None
        if peggio and peggio["toppa"]:
            sporchi.append((p["title"], peggio))
            print("   CARTELLA  %-44s dentro %.2f intorno %.2f bordo %.2f"
                  % (p["title"][:44], peggio["dentro"], peggio["intorno"], peggio["bordo"]))
    print("\n%d file di stampa guardati, %d con la cartella incollata dietro al marchio"
          % (guardati, len(sporchi)))
    return sporchi


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

    if "--toppe" in sys.argv:
        print("Cerco la cartella crema dentro i file di stampa veri...\n")
        verifica_toppe(prodotti, os.path.join(USCITA, "stampe-scaricate"))
        return 0

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

    if "--eu" in sys.argv:
        print("\n" + "=" * 72)
        print("LINEA EU (Printful)")
        taglie = None
        percorso_taglie = os.path.join(USCITA, "taglie-eu.json")
        if os.path.exists(percorso_taglie):
            with open(percorso_taglie) as fh:
                taglie = json.load(fh)
        eu = verifica_eu(taglie)
        print("  %d motivi controllati contro l'area di stampa Printful"
              % eu["esaminati"])
        if eu["motivi"]:
            for x in eu["motivi"]:
                print("    MISURA SBAGLIATA %-34s attesa %s, e' %s"
                      % (x["titolo"][:34], x["attesa"], x["avuta"]))
        else:
            print("    tutti alla misura giusta")
        if eu.get("marchi"):
            for x in eu["marchi"]:
                print("    MARCHIO          %-34s %s"
                      % (x["titolo"][:34], x["guaio"]))
        else:
            print("    il marchio c'e' su tutte le bandane che devono averlo, "
                  "e la firma vecchia non c'e' piu'")
        if not eu["taglie_controllate"]:
            print("  titoli di taglia NON controllati: manca %s"
                  % os.path.basename(percorso_taglie))
            print("    (si scrive da Shopify: {id prodotto: [titoli varianti]})")
        elif eu["taglie"]:
            for x in eu["taglie"]:
                print("    TAGLIA SCONOSCIUTA %-30s %s -> %s"
                      % (x["titolo"][:30], x["tipo"], x["sconosciuti"]))
        else:
            print("    tutti i titoli di taglia sono riconosciuti da varianti-fornitore.js")
        rapporto = rapporto if isinstance(rapporto, dict) else {"printify": rapporto}
        rapporto["eu"] = eu

    if "--editor" in sys.argv:
        print("\n" + "=" * 72)
        print("L'EDITOR DI PERSONALIZZAZIONE")
        catena = _modulo("editor_catena", os.path.join(QUI, "editor-catena.py"))
        istantanea = catena.carica_istantanea()
        if not istantanea:
            print("  NON controllato: manca %s"
                  % os.path.relpath(catena.ISTANTANEA, RADICE))
            print("    (si scrive da Shopify: tabella_tipi = il testo di")
            print("     snippets/perla-print-areas.liquid del tema PUBBLICATO,")
            print("     prodotti = [{id, title, handle, status, tags, editor,")
            print("     printify}] con editor = custom.editor_pattern_image)")
        else:
            stampe = {p["id"]: catena.stampe_correnti(p) for p in prodotti}
            ed = catena.verifica(istantanea, stampe, catena.motivi_per_handle())
            print("  %d prodotti attivi contro %d righe della tabella dei tipi"
                  % (ed["esaminati"], ed["righe"]))
            for x in ed["prodotti"]:
                print("    %-38s" % x["titolo"][:38])
                for g in x["guai"]:
                    print("      - " + g)
                if x.get("atteso"):
                    print("      dovrebbe essere: %s" % x["atteso"])
            if not ed["prodotti"]:
                print("    l'editor c'e' su tutti, e lo sfondo su cui il cliente "
                      "disegna e' il file che si stampa")
            else:
                print("  %d prodotti da sistemare (li allinea "
                      "perla-editor-allinea.py)" % len(ed["prodotti"]))
            rapporto = rapporto if isinstance(rapporto, dict) else {"printify": rapporto}
            rapporto["editor"] = ed

    os.makedirs(USCITA, exist_ok=True)
    percorso = os.path.join(USCITA, "audit-prodotti.json")
    with open(percorso, "w") as fh:
        json.dump(rapporto, fh, indent=1, ensure_ascii=False)
    print("\ndettaglio completo in %s" % percorso)


if __name__ == "__main__":
    main()
