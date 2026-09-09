#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La geometria delle aree di stampa Printify, variante per variante.

IL DIFETTO CHE QUESTO MODULO ESISTE PER CHIUDERE

Su Printify `scale` e' la larghezza dell'immagine come frazione della larghezza
dell'area, e `x`/`y` sono il centro, anch'essi in frazione. Il file di stampa
pero' viene scritto UNA volta e applicato a TUTTE le varianti del prodotto --
mentre le varianti dello stesso blueprint hanno proporzioni diverse:

    collare 784     5764x229   7257x338   8318x338   9519x338
                      25,2:1     21,5:1     24,6:1     28,2:1
    cuccia  419    15600x12600  12750x9750  8850x5850
                     1,238:1     1,308:1    1,513:1
    bandana 562     3150x1691   4275x2325
                     1,863:1     1,839:1

Un file costruito per la variante piu' grande e messo a scale=1 copre, sul
collare M, 258 px di 338: il 24% della fettuccia resta BIANCO. Sulla cuccia
28"x18" lo stesso file perde il 18% in altezza, TAGLIATO. Nessuno dei due
difetti si vede sulla variante per cui il file era stato costruito, ed e'
esattamente il motivo per cui e' rimasto in catalogo cosi' a lungo.

La cura non e' scegliere una scala furba: e' che `print_areas` di Printify
accetta PIU' VOCI, ognuna con i suoi `variant_ids`. Un file per gruppo di
varianti che condividono la misura, e ogni gruppo combacia esatto.

DA DOVE ARRIVANO LE MISURE
Da printify-blueprints/<blueprint>_<provider>.json, gia' nel repository. Se il
file non c'e' (ciotola 570, tappetino 855) e c'e' una chiave, si scarica e si
salva li' -- cosi' la volta dopo funziona anche offline, e i test girano senza
rete.
"""
import json
import os
import subprocess

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
BLUEPRINT = os.path.join(RADICE, "printify-blueprints")


# ==========================================================================
# LETTURA DELLE MISURE
# ==========================================================================

def _percorso(blueprint_id, provider_id):
    return os.path.join(BLUEPRINT, "%s_%s.json" % (blueprint_id, provider_id))


def _scarica(blueprint_id, provider_id, token):
    """Chiede a Printify le varianti del blueprint e le salva nel repository.

    Passa da curl e non da urllib per la stessa ragione scritta in
    perla-usa-carica-stampe.py: in questo ambiente urllib esce dal proxy con
    un 403.
    """
    url = ("https://api.printify.com/v1/catalog/blueprints/%s"
           "/print_providers/%s/variants.json" % (blueprint_id, provider_id))
    out = subprocess.run(
        ["curl", "-s", "-H", "Authorization: Bearer " + token, url],
        capture_output=True, text=True, check=True).stdout
    try:
        dati = json.loads(out)
    except ValueError:
        raise RuntimeError("risposta non JSON dal catalogo %s/%s: %s"
                           % (blueprint_id, provider_id, out[:200]))
    if "variants" not in dati:
        raise RuntimeError("catalogo %s/%s senza varianti: %s"
                           % (blueprint_id, provider_id, json.dumps(dati)[:200]))
    # stessa forma dei file gia' versionati, cosi' i due percorsi di lettura
    # non divergono mai
    salvato = {"fetchedAt": None, "blueprint": {"id": blueprint_id},
               "providers": [{"id": provider_id}], "printProviderDetail": None,
               "variants": dati["variants"]}
    os.makedirs(BLUEPRINT, exist_ok=True)
    with open(_percorso(blueprint_id, provider_id), "w") as fh:
        json.dump(salvato, fh, indent=1)
    return salvato


def varianti(blueprint_id, provider_id, token=None):
    """Le varianti con le loro misure di stampa, dal repository o dall'API.

    Torna [{id, title, placeholders: {posizione: (larghezza, altezza)}}].
    """
    percorso = _percorso(blueprint_id, provider_id)
    dati = None
    if os.path.exists(percorso):
        with open(percorso) as fh:
            dati = json.load(fh)
        # 254_70.json e' salvato con zero varianti: c'e' il file ma non serve a
        # niente, e trattarlo come valido significherebbe non raggruppare
        # nessuna variante e scrivere un print_areas vuoto.
        if not dati.get("variants"):
            dati = None
    if dati is None:
        if not token:
            raise RuntimeError(
                "misure mancanti per il blueprint %s/%s. Scaricale con:\n"
                "  node scripts/fetch-printify-blueprint.js -b %s -p %s --save"
                % (blueprint_id, provider_id, blueprint_id, provider_id))
        dati = _scarica(blueprint_id, provider_id, token)

    fuori = []
    for v in dati["variants"]:
        misure = {}
        for ph in v.get("placeholders", []):
            if ph.get("width") and ph.get("height"):
                misure[ph["position"]] = (int(ph["width"]), int(ph["height"]))
        if misure:
            fuori.append({"id": v["id"], "title": v.get("title", ""),
                          "placeholders": misure})
    if not fuori:
        raise RuntimeError("nessuna variante con misure per %s/%s"
                           % (blueprint_id, provider_id))
    return fuori


def gruppi(elenco, posizione="front", solo_varianti=None):
    """Raggruppa le varianti per misura IDENTICA dell'area di stampa.

    Un gruppo = un file di stampa. Si raggruppa sulla misura esatta e non su
    una tolleranza di proporzione: due varianti larghe uguale ma alte diverso
    (collare L 8318x338 e XL 9519x338 hanno la stessa altezza e larghezza
    diversa) vogliono comunque due file diversi, e una tolleranza sarebbe solo
    un modo elegante di rimettere dentro il difetto che stiamo togliendo.

    solo_varianti: se passato, tiene solo quelle (sono le varianti che il
    prodotto ha davvero abilitate -- il blueprint ne elenca sempre di piu').
    """
    per_misura = {}
    for v in elenco:
        if solo_varianti is not None and v["id"] not in solo_varianti:
            continue
        misura = v["placeholders"].get(posizione)
        if not misura:
            continue
        per_misura.setdefault(misura, []).append(v)
    fuori = []
    # dal piu' grande al piu' piccolo: il primo gruppo e' quello che detta la
    # risoluzione della sorgente, ed e' comodo vederlo per primo nei log
    for misura in sorted(per_misura, key=lambda m: -m[0] * m[1]):
        voci = per_misura[misura]
        fuori.append({
            "misura": misura,
            "variant_ids": sorted(v["id"] for v in voci),
            "titoli": [v["title"] for v in voci],
        })
    return fuori


def posizioni(elenco):
    """Tutte le posizioni di stampa presenti (front, back, ...)."""
    viste = []
    for v in elenco:
        for p in v["placeholders"]:
            if p not in viste:
                viste.append(p)
    return viste


# ==========================================================================
# QUANTO SI VEDE DAVVERO
# ==========================================================================

def copertura(area, immagine, x=0.5, y=0.5, scala=1.0):
    """Cosa succede davvero a un'immagine messa a (x, y, scala) su un'area.

    Printify disegna l'immagine larga `scala` volte la larghezza dell'area,
    alta di conseguenza (le proporzioni non si deformano mai), centrata in
    (x, y) espressi in frazione dell'area. Da qui escono le due misure che
    contano, e sono cose diverse:

        vuoto   quanta AREA resta scoperta -> fascia bianca sul prodotto
        taglio  quanta IMMAGINE finisce fuori -> disegno mozzato

    Un file giusto ha tutti e due a zero. Il difetto del collare M e' vuoto
    0,24; quello della cuccia 28"x18" e' taglio 0,18.

    `ingrandimento` e' quante volte i pixel della sorgente vengono stirati:
    sopra 1,0 e' il difetto "sgranato", ed e' la stessa grandezza misurata in
    testa a perla-usa-file-stampa.py.
    """
    aw, ah = float(area[0]), float(area[1])
    iw, ih = float(immagine[0]), float(immagine[1])
    if aw <= 0 or ah <= 0 or iw <= 0 or ih <= 0:
        raise ValueError("misure non valide: area=%s immagine=%s" % (area, immagine))

    dis_w = scala * aw
    dis_h = dis_w * ih / iw
    cx, cy = x * aw, y * ah
    sinistra, destra = cx - dis_w / 2.0, cx + dis_w / 2.0
    alto, basso = cy - dis_h / 2.0, cy + dis_h / 2.0

    sov_w = max(0.0, min(destra, aw) - max(sinistra, 0.0))
    sov_h = max(0.0, min(basso, ah) - max(alto, 0.0))
    sovrapposta = sov_w * sov_h

    return {
        "vuoto": 1.0 - sovrapposta / (aw * ah),
        "taglio": 1.0 - sovrapposta / (dis_w * dis_h),
        # le due fasce vuote separate: sono quelle che si VEDONO come strisce
        # bianche, e dirle per asse fa capire subito da che parte sbaglia
        "vuoto_orizzontale": 1.0 - min(sov_w / aw, 1.0),
        "vuoto_verticale": 1.0 - min(sov_h / ah, 1.0),
        "ingrandimento": dis_w / iw,
        "disegnata": (round(dis_w), round(dis_h)),
    }


def scala_per_coprire(area, immagine):
    """La scala minima perche' l'immagine copra l'area senza lasciare vuoti.

    Non e' la strada che questo progetto prende -- si costruisce un file per
    ogni misura, cosi' scala resta 1 e non si taglia niente -- ma serve
    all'audit per dire di quanto e' sbagliato il valore che c'e' adesso.
    """
    aw, ah = float(area[0]), float(area[1])
    iw, ih = float(immagine[0]), float(immagine[1])
    return max(1.0, (ah / aw) * (iw / ih))


def esatta(area, immagine, tolleranza=0.005):
    """Vero se l'immagine ha esattamente le proporzioni dell'area.

    La tolleranza e' mezzo punto percentuale: sotto, la differenza sparisce
    nell'arrotondamento dei pixel e non produce nessuna striscia visibile.
    """
    return abs((immagine[0] / float(immagine[1])) /
               (area[0] / float(area[1])) - 1.0) <= tolleranza


# ==========================================================================
# DAL PRODOTTO ALLE MISURE
# ==========================================================================

def per_prodotto(prodotto, token=None):
    """Le misure di stampa di un prodotto Printify gia' letto dall'API.

    Il prodotto porta con se' blueprint_id e print_provider_id, quindi non
    serve nessuna tabella da tenere aggiornata a mano: si va a leggere il
    catalogo di QUEL blueprint e di QUEL fornitore.
    """
    return varianti(prodotto["blueprint_id"], prodotto["print_provider_id"], token)


def abilitate(prodotto):
    """Gli id delle varianti che il prodotto vende davvero.

    Il blueprint elenca tutte le varianti possibili (il collare ne ha 288); il
    prodotto ne abilita una parte. Costruire un file per una misura che il
    prodotto non vende e' lavoro buttato e MB caricati per niente.
    """
    return {v["id"] for v in prodotto.get("variants", []) if v.get("is_enabled")}


def vendibili(prodotto):
    """Come abilitate(), ma solo quelle che il fornitore sa davvero produrre.

    La distinzione conta: i collari hanno tutte le varianti abilitate e
    NESSUNA disponibile, il PUT risponde 500 e su Shopify stanno in bozza.
    E' la stessa regola gia' scritta in perla-usa-marchio.py::vendibile().
    """
    return {v["id"] for v in prodotto.get("variants", [])
            if v.get("is_enabled") and v.get("is_available")}
