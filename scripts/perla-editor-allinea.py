#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara l'allineamento fra lo sfondo dell'editor e il file che si stampa.

PERCHE' ESISTE
Il controllo `perla-verifica-prodotti.py --editor` dice QUALI prodotti hanno
lo sfondo dell'editor diverso dal file che va davvero in stampa. Questo dice
CHE COSA scriverci, e lo mette in una forma che si puo' rileggere prima di
toccare il negozio.

PERCHE' NON SCRIVE DA SOLO
In config/printify.local.env non c'e' un token Admin di Shopify, e non ce ne
deve essere uno solo per questo: un token che puo' riscrivere i metafield di
tutto il catalogo e' molto piu' potere di quanto serva a un allineamento che
si fa una volta. Quindi qui si PREPARA l'input della mutation, e a scriverlo
e' chi ha gia' le credenziali in mano. E' lo stesso motivo per cui le taglie
passano da taglie-eu.json invece che da una chiamata diretta.

Il file in uscita e' fatto per essere letto prima di essere usato: per ogni
prodotto ci sono il titolo, il valore di adesso e quello nuovo. Se una riga
sembra sbagliata si vede li', non dopo.

CHE COSA CI VA, PER OGNI LINEA
  EU (Printful)   il campo `pattern` di perla-eu-prodotti.json, cioe' il
                  motivo che il fornitore stampa. Oggi metafield e pattern
                  coincidono su tutti e 66, ed e' esattamente il motivo per
                  cui caricare i motivi corretti senza rifare questo passaggio
                  romperebbe l'editor su tutta la linea: si disegnerebbe sul
                  motivo vecchio e si riceverebbe quello nuovo.
  USA (Printify)  uno dei file elencati in print_areas. Sono piu' d'uno --
                  uno per gruppo di misure -- e per lo sfondo vanno bene
                  tutti: e' la stessa texture a risoluzioni diverse.

USO
    python3 scripts/perla-editor-allinea.py            # tutte e due le linee
    python3 scripts/perla-editor-allinea.py --eu       # solo la linea europea
    python3 scripts/perla-editor-allinea.py --us       # solo l'americana
    python3 scripts/perla-editor-allinea.py --tag      # solo i tag mancanti
"""
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
sys.path.insert(0, QUI)

import importlib.util  # noqa: E402


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


catena = _modulo("editor_catena", os.path.join(QUI, "editor-catena.py"))
audit = _modulo("audit", os.path.join(QUI, "perla-verifica-prodotti.py"))

USCITA = os.path.join(RADICE, "generated-designs", "editor-da-scrivere.json")

# Il metafield e' dichiarato come URL sul negozio: scriverlo come stringa
# libera lo farebbe rifiutare dalla validazione.
TIPO_METAFIELD = "url"
NAMESPACE, CHIAVE = "custom", "editor_pattern_image"


def gid(id_numerico):
    return "gid://shopify/Product/%s" % id_numerico


def da_allineare(istantanea, stampe_us, motivi_eu, linee):
    """Le scritture da fare, gia' divise fra metafield e tag."""
    righe = catena.righe_tipi(istantanea.get("tabella_tipi"))
    metafield, tag = [], []
    for voce in istantanea.get("prodotti", []):
        if voce.get("status") != "ACTIVE":
            continue
        guai = catena.esamina(voce, righe, motivi_eu, stampe_us)
        if not guai:
            continue

        if any("personalizzabile" in g for g in guai) and "tag" in linee:
            tag.append({"id": gid(voce["id"]), "titolo": voce.get("title"),
                        "aggiungi": "personalizzabile"})

        if not any("sfondo" in g or "editor_pattern_image" in g for g in guai):
            continue
        eu = voce.get("handle") in motivi_eu
        if ("eu" if eu else "us") not in linee:
            continue
        nuovo = catena.sfondo_giusto(voce, motivi_eu, stampe_us)
        if not nuovo or nuovo == voce.get("editor"):
            continue
        metafield.append({
            "ownerId": gid(voce["id"]), "titolo": voce.get("title"),
            "linea": "EU" if eu else "USA",
            "adesso": voce.get("editor"), "nuovo": nuovo,
            "namespace": NAMESPACE, "key": CHIAVE, "type": TIPO_METAFIELD})
    return metafield, tag


def main():
    scelte = {a for a in sys.argv[1:] if a.startswith("--")}
    linee = {"eu", "us", "tag"} if not scelte else {
        a.lstrip("-") for a in scelte}

    istantanea = catena.carica_istantanea()
    if not istantanea:
        raise SystemExit(
            "manca %s: e' l'istantanea di Shopify da cui si parte "
            "(vedi editor-catena.py)" % os.path.relpath(catena.ISTANTANEA, RADICE))

    env = audit.chiavi()
    prodotti = audit.prodotti_printify(env["PRINTIFY_API_KEY"], env["PRINTIFY_SHOP_ID"])
    stampe = {p["id"]: catena.stampe_correnti(p) for p in prodotti}
    motivi = catena.motivi_per_handle()

    metafield, tag = da_allineare(istantanea, stampe, motivi, linee)

    for m in metafield:
        print("%-4s %-38s" % (m["linea"], (m["titolo"] or "")[:38]))
        print("      da  %s" % (m["adesso"] or "(niente)"))
        print("      a   %s" % m["nuovo"])
    for t in tag:
        print("TAG  %-38s + %s" % ((t["titolo"] or "")[:38], t["aggiungi"]))

    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with open(USCITA, "w") as fh:
        json.dump({"metafield": metafield, "tag": tag}, fh, indent=1,
                  ensure_ascii=False)
    print("\n%d metafield e %d tag da scrivere, in %s"
          % (len(metafield), len(tag), os.path.relpath(USCITA, RADICE)))
    if metafield or tag:
        print("Si scrivono con metafieldsSet e tagsAdd sull'Admin API, a blocchi "
              "da 25; poi si rilancia --editor, che deve tornare pulito.")


if __name__ == "__main__":
    main()
