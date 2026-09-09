#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La catena che porta un prodotto ad avere l'editor di personalizzazione.

PERCHE' ESISTE
La titolare ha chiesto di verificare che l'editor vada bene per TUTTI i
prodotti. Guardandolo, la catena e' risultata lunga e con quattro punti dove
un prodotto puo' cadere fuori senza che nessuno se ne accorga -- e in tre di
quei punti c'era gia' qualcuno caduto. Qui c'e' la logica che decide, separata
da chi la stampa, cosi' e' misurabile con un test invece che a occhio sul
negozio vero.

LA CATENA, LETTA DAL TEMA PUBBLICATO
1. `is_custom` (sections/main-product.liquid): il prodotto ha il tag
   'personalizzabile', 'POD' o 'custom'. Senza, il blocco dell'editor non
   viene proprio renderizzato -- il prodotto si vende e basta.
2. `photo_type` (snippets/perla-print-areas.liquid): la PRIMA riga della
   tabella il cui tag combacia coi tag del prodotto. Se non combacia niente,
   photo_type resta vuoto: la tela prende un rapporto di ripiego e il pulsante
   "Salva anteprima" manda product_type="" al server, che rifiuta. E' il
   difetto ROUND 16e, gia' costato una volta.
3. `is_blank_design`: il tag 'tipo-neutro'. Sui neutri lo sfondo non si mostra
   di proposito, quindi li' il metafield non serve.
4. lo sfondo: il metafield `custom.editor_pattern_image`, che DEVE essere la
   stessa immagine che verra' stampata. Se i due divergono, il cliente disegna
   su un motivo e ne riceve un altro.

IL QUARTO CONTROLLO E' QUELLO CHE MANCAVA, ED E' IL PIU' IMPORTANTE
Sui 66 prodotti EU metafield e file di stampa oggi coincidono, ed e' il motivo
per cui caricare i motivi corretti senza toccare il metafield romperebbe
l'editor su tutta la linea. Sui ~24 prodotti USA invece divergono GIA': il
metafield punta all'artwork caricato prima che i file di stampa venissero
ricostruiti. Verificato su Bandana "Aurora": metafield db113652..., file di
stampa 6ba526d2....

DA DOVE ARRIVANO I DATI
Non da Shopify direttamente: in config/printify.local.env non c'e' un token
Admin, e non ce ne deve essere uno solo per un controllo di lettura. Si legge
un'istantanea, generated-designs/editor-shopify.json, scritta a parte -- lo
stesso modo in cui taglie-eu.json alimenta il controllo delle taglie. La
tabella dei tipi sta dentro l'istantanea come testo grezzo, copiata dal tema
PUBBLICATO: parsarla qui e non fidarsi di una copia nel repository e' voluto,
perche' il repository ne contiene 14 file su centinaia e puo' divergere.
"""
import json
import os

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ISTANTANEA = os.path.join(RADICE, "generated-designs", "editor-shopify.json")
PRODOTTI_EU = os.path.join(QUI, "perla-eu-prodotti.json")

# I tag che accendono l'editor, come li legge sections/main-product.liquid.
TAG_PERSONALIZZABILE = ("personalizzabile", "POD", "custom")
TAG_NEUTRO = "tipo-neutro"


def righe_tipi(tabella):
    """Le righe di perla-print-areas.liquid.

    Formato: chiave|tag1,tag2|rapporto|etichetta|left|top|right|height|radius
    Si tiene l'ORDINE, perche' il tema prende la prima riga che combacia e si
    ferma li': due righe che combaciano sullo stesso prodotto non sono un
    pareggio, vince quella scritta prima.
    """
    fuori = []
    for riga in (tabella or "").strip().split("#"):
        colonne = riga.strip().split("|")
        if len(colonne) < 4 or not colonne[0].strip():
            continue
        fuori.append({
            "chiave": colonne[0].strip(),
            "tag": [t.strip() for t in colonne[1].split(",") if t.strip()],
            "rapporto": colonne[2].strip(),
            "etichetta": colonne[3].strip(),
        })
    return fuori


def tipo_del_prodotto(tag_prodotto, righe):
    """La riga che il tema sceglierebbe, o None."""
    presenti = set(tag_prodotto or ())
    for riga in righe:
        if presenti.intersection(riga["tag"]):
            return riga
    return None


def personalizzabile(tag_prodotto):
    return bool(set(tag_prodotto or ()).intersection(TAG_PERSONALIZZABILE))


def neutro(tag_prodotto):
    return TAG_NEUTRO in set(tag_prodotto or ())


def stampe_correnti(prodotto_printify):
    """Le URL dei file che questo prodotto Printify stampa oggi.

    Sono piu' di una: dopo la correzione delle aree per variante ogni gruppo di
    misure ha il suo file, di dimensioni diverse. Quindi il confronto giusto
    non e' "il metafield e' UGUALE al file di stampa" ma "il metafield e' UNO
    dei file di stampa": se non lo e', punta a qualcosa che non si stampa piu'.
    """
    fuori = set()
    for area in (prodotto_printify or {}).get("print_areas", []) or []:
        for segnaposto in area.get("placeholders", []) or []:
            for immagine in segnaposto.get("images", []) or []:
                if immagine.get("src"):
                    fuori.add(immagine["src"])
    return fuori


def _senza_query(url):
    """Le URL Printify su S3 portano un ?v=1 che non fa parte dell'identita'."""
    return (url or "").split("?", 1)[0]


def esamina(voce, righe, motivi_eu, stampe_us):
    """I guai di UN prodotto. Lista vuota = l'editor va bene.

    `motivi_eu` e' {handle: url del motivo}, `stampe_us` e' {id printify: set
    di url}. Le due linee si controllano con la stessa regola, cambia solo da
    dove arriva "il file che si stampa".
    """
    guai = []
    if voce.get("status") != "ACTIVE":
        return guai

    riga = tipo_del_prodotto(voce.get("tags"), righe)
    if not riga:
        guai.append("nessun tag combacia con la tabella dei tipi: photo_type "
                    "resta vuoto e l'anteprima viene rifiutata dal server")
    if not personalizzabile(voce.get("tags")):
        guai.append("manca il tag 'personalizzabile': l'editor non compare")

    if neutro(voce.get("tags")):
        # Sui neutri lo sfondo e' nascosto di proposito: la featured_image e'
        # una foto lifestyle del fornitore, fuorviante dietro una tela vuota.
        return guai

    sfondo = voce.get("editor")
    if not sfondo:
        guai.append("manca custom.editor_pattern_image: l'editor ripiega sulla "
                    "foto del prodotto, che ora e' un mockup fotografico")
        return guai

    handle = voce.get("handle")
    if handle in motivi_eu:
        if _senza_query(sfondo) != _senza_query(motivi_eu[handle]):
            guai.append("lo sfondo dell'editor non e' il motivo che si stampa "
                        "(editor %s, stampa %s)"
                        % (_coda(sfondo), _coda(motivi_eu[handle])))
        return guai

    printify = voce.get("printify")
    if printify and printify in stampe_us:
        correnti = {_senza_query(u) for u in stampe_us[printify]}
        if correnti and _senza_query(sfondo) not in correnti:
            guai.append("lo sfondo dell'editor non e' fra i %d file di stampa "
                        "correnti (editor %s)" % (len(correnti), _coda(sfondo)))
    return guai


def _coda(url):
    """L'ultimo pezzo di una URL: quanto basta per riconoscerla in un elenco."""
    pezzo = _senza_query(url).rsplit("/", 1)[-1]
    return pezzo[:40] if pezzo else url


def sfondo_giusto(voce, motivi_eu, stampe_us):
    """Che cosa DOVREBBE esserci nel metafield di questo prodotto.

    Sulla linea USA i file di stampa sono piu' di uno, uno per gruppo di
    misure, e per lo sfondo dell'editor vanno bene tutti: e' la stessa
    texture a risoluzioni diverse. Si prende il primo in ordine alfabetico
    perche' serve una scelta DETERMINISTICA -- altrimenti due esecuzioni
    scriverebbero valori diversi e il controllo oscillerebbe fra pulito e
    sporco senza che sia cambiato niente.
    """
    handle = voce.get("handle")
    if handle in motivi_eu:
        return motivi_eu[handle]
    printify = voce.get("printify")
    correnti = stampe_us.get(printify) if printify else None
    return sorted(correnti)[0] if correnti else None


def carica_istantanea(percorso=None):
    percorso = percorso or ISTANTANEA
    if not os.path.exists(percorso):
        return None
    with open(percorso) as fh:
        return json.load(fh)


def motivi_per_handle(percorso=None):
    with open(percorso or PRODOTTI_EU) as fh:
        return {v["handle"]: v["pattern"] for v in json.load(fh) if v.get("handle")}


def verifica(istantanea, stampe_us, motivi_eu):
    """Il verdetto su tutti i prodotti dell'istantanea."""
    righe = righe_tipi(istantanea.get("tabella_tipi"))
    fuori = {"righe": len(righe), "esaminati": 0, "prodotti": []}
    for voce in istantanea.get("prodotti", []):
        if voce.get("status") != "ACTIVE":
            continue
        fuori["esaminati"] += 1
        guai = esamina(voce, righe, motivi_eu, stampe_us)
        if guai:
            fuori["prodotti"].append({
                "titolo": voce.get("title"), "handle": voce.get("handle"),
                "guai": guai,
                "atteso": sfondo_giusto(voce, motivi_eu, stampe_us)})
    return fuori
