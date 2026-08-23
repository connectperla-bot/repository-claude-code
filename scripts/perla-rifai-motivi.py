#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rifa' i file di stampa dei prodotti col motivo ornato, a misura giusta.

COSA RIFA' E COSA NO
Tocca solo i prodotti il cui motivo veniva da un'immagine fissa: damasco,
medaglioni, barocco, floreale, ulivo, paisley, toile, ghirigori, erbario.

NON tocca:
  * i dieci motivi gia' disegnati a codice (tartan, marinara, terracotta,
    lino, rombi, chevron, spinato, trellis, onde, tribale). Quelli escono
    gia' corretti su ogni pezzo, e infatti sui fogli di contatto sono gli
    unici senza difetti. Rifarli sarebbe cambiarli senza motivo.
  * i "crea il tuo design", che sono neutri per definizione: il disegno lo
    mette il cliente.

DA DOVE VIENE LA SCELTA
Dal nome del prodotto, non da una tabella scritta a mano. Un collare che si
chiama `collare-eu-damasco-bordeaux-oro-fornitore-europeo` vuole il damasco
nella colorazione bordeaux, e lo dice da solo. Cosi' un prodotto nuovo entra
nel giro senza che nessuno si ricordi di aggiungerlo, e -- soprattutto -- non
si puo' sbagliare l'abbinamento fra nome e disegno, che e' uno dei difetti
gia' trovati in catalogo (una bandana chiamata "Rubino" che stampava verde).

Quando il nome non basta, il prodotto viene ELENCATO E SALTATO, non indovinato.

LA MISURA
Da perla-scala-stampa.py: il passo si sceglie in centimetri, uguale per tutti
i prodotti della stessa famiglia, e diventa pixel diversi su ogni pezzo. E'
il contrario di quello che si faceva prima, ed e' il motivo per cui il
medaglione usciva gigante sul collare.

USO
    python3 scripts/perla-rifai-motivi.py            # elenca il piano
    python3 scripts/perla-rifai-motivi.py --genera   # scrive i file in out/
"""
import importlib.util
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
USCITA = os.path.join(RADICE, "generated-designs", "motivi-rifatti")


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ornati = _modulo("perla_motivi_ornati", os.path.join(QUI, "perla-motivi-ornati.py"))
scala = _modulo("perla_scala_stampa", os.path.join(QUI, "perla-scala-stampa.py"))

# Parola nel nome -> famiglia di motivo. L'ordine conta: le voci piu'
# specifiche stanno prima, cosi' "barocco-floreale" prende il barocco e non
# il floreale.
MOTIVO_DA_NOME = (
    ("barocco", "barocco"), ("baroque", "barocco"),
    ("medaglioni", "medaglioni"), ("medallion", "medaglioni"),
    ("damasco", "damasco"), ("damask", "damasco"),
    ("ghirigori", "ghirigori"), ("scroll", "ghirigori"), ("vortice", "ghirigori"),
    ("erbario", "erbario"), ("botanic", "erbario"), ("botanico", "erbario"),
    ("ramo-dulivo", "ulivo"), ("ulivo", "ulivo"), ("olive", "ulivo"),
    ("foglia-di-salvia", "ulivo"), ("laurel", "ulivo"), ("alloro", "ulivo"),
    ("paisley", "paisley"), ("cachemire", "paisley"),
    ("foglia", "ulivo"), ("erba", "erbario"),
    ("toile", "toile"),
    ("floreale", "floreale"), ("floral", "floreale"),
    ("fiorita", "floreale"), ("giardino", "floreale"), ("fiordaliso", "floreale"),
    ("stemma", "medaglioni"), ("emblema", "medaglioni"), ("nobile", "damasco"),
    ("reticolo", "ghirigori"), ("aurora", "floreale"), ("ornata", "barocco"),
    ("violetta", "damasco"), ("regale", "medaglioni"), ("traliccio", "ghirigori"),
    ("cobalto", "medaglioni"), ("cammeo", "paisley"),
)

# Parola nel nome -> colorazione. Stessa logica: si legge il nome, non si
# sceglie a occhio. Le palette sono quelle di perla-motivi-nuovi.py.
PALETTE_DA_NOME = (
    ("bordeaux", "bordeaux"), ("burgundy", "bordeaux"), ("rubino", "bordeaux"),
    ("navy", "navy"), ("blu-notte", "navy"), ("cobalto", "navy"),
    ("smeraldo", "smeraldo"), ("emerald", "smeraldo"),
    ("verde", "smeraldo"), ("salvia", "smeraldo"), ("sage", "smeraldo"),
    ("petrolio", "teal"), ("teal", "teal"),
    ("viola", "porpora"), ("purple", "porpora"), ("porpora", "porpora"),
    ("avorio", "avorio"), ("ivory", "avorio"), ("crema", "avorio"),
    ("cipria", "avorio"), ("rosa", "avorio"),
    ("antracite", "grigio"), ("charcoal", "grigio"), ("argento", "grigio"),
    ("silver", "grigio"), ("grigio", "grigio"),
    ("nero", "nero"), ("black", "nero"), ("oro", "navy"),
)

# "Crema e oro" deve uscire crema E ORO. La palette avorio ha il tratto
# rosa cipria, che e' giusto per "avorio rosa" e sbagliato per "crema oro":
# sul primo giro il Collare "Ulivo Crema Oro" e' uscito con le foglie rosa.
# Il nome lo diceva, bastava ascoltarlo.
PALETTE_EXTRA = {
    "crema-oro": ornati.Palette((243, 236, 226), (208, 190, 168),
                                (176, 138, 62), (200, 160, 74), (255, 252, 248)),
}
ornati.PALETTE.update(PALETTE_EXTRA)

# Prodotti diversi con lo stesso motivo e lo stesso colore uscirebbero
# identici: tre bandane verdi -- "Ulivo", "Foglia", "Smeraldo" -- sono finite
# indistinguibili al primo giro. Non e' un difetto del disegno ma del fatto
# che la scelta e' automatica, e va compensato. La densita' varia di un passo
# fisso ricavato dal nome: sempre la stessa per lo stesso prodotto, diversa
# fra prodotti vicini, come le varianti di una collezione vera.
VARIAZIONI = (0.82, 1.0, 1.22)


def variazione(handle):
    return VARIAZIONI[sum(ord(c) for c in handle) % len(VARIAZIONI)]


# Il passo, in centimetri, per famiglia di motivo. Scelto perche' la
# ripetizione abbia una misura fisica sensata addosso al cane: un damasco da
# 8 cm su una bandana e' un damasco, uno da 30 e' un poster.
PASSO_CM = {
    "damasco": 8.0, "medaglioni": 7.0, "barocco": 8.5, "floreale": 6.0,
    "ulivo": 7.5, "paisley": 7.0, "toile": 9.0, "ghirigori": 6.5,
    "erbario": 6.5,
}

# I motivi gia' disegnati a codice: si lasciano stare.
GIA_A_CODICE = ("tartan", "marinara", "terracotta", "lino", "rombi", "chevron",
                "spinato", "trellis", "onda", "onde", "geometric", "geometrico",
                "diamant", "minimal", "astratto", "tribale", "herringbone",
                "artdeco", "art-deco", "wave", "quadretti")

NEUTRI = ("crea-il-tuo-design", "neutro", "personalizza")


def famiglia(handle):
    """collare-eu-damasco-... -> 'collare-eu'; i prodotti USA per prefisso."""
    for tipo in scala.AREE:
        radice = tipo.split("-")[0]
        if handle.startswith(radice + "-eu-") and tipo.endswith("-eu"):
            return tipo
    for parola, tipo in (("cuccia", "cuccia-usa"), ("bed", "cuccia-usa"),
                         ("bandana", "bandana-usa"), ("tag", "medaglietta-usa"),
                         ("medaglietta", "medaglietta-usa"),
                         ("collar", "collare-usa"), ("ciotola", "ciotola-usa")):
        if parola in handle:
            return tipo
    return None


def _prima(coppie, testo):
    for parola, valore in coppie:
        if parola in testo:
            return valore
    return None


def piano(handle, titolo=""):
    """Cosa fare di questo prodotto. Torna (esito, dettagli).

    IL TITOLO COMANDA, NON L'HANDLE, e non e' un dettaglio.
    Sulla linea americana i due dicono cose diverse: l'handle
    `perla-italia-bandana-damask-navy` porta il titolo Bandana "Paisley", e
    `perla-italia-cuccia-baroque-navy` si chiama Cuccia "Geometrica". L'handle
    descrive il disegno con cui il prodotto era nato; il titolo e' quello che
    e' stato deciso dopo, ed e' l'unica delle due cose che il cliente legge.
    Se il titolo promette un paisley, il prodotto deve mostrare un paisley --
    altrimenti si ripete il difetto gia' trovato in catalogo con la bandana
    chiamata "Rubino" che stampava verde.

    L'handle resta come ripiego, perche' porta l'informazione sul colore che
    quasi nessun titolo contiene.
    """
    h = handle.lower()
    t = titolo.lower()
    if any(p in h for p in NEUTRI) or "crea il tuo" in t:
        return "neutro", None
    motivo = _prima(MOTIVO_DA_NOME, t) or _prima(MOTIVO_DA_NOME, h)
    if motivo is None:
        if any(p in t for p in GIA_A_CODICE) or any(p in h for p in GIA_A_CODICE):
            return "gia-a-codice", None
        return "non-riconosciuto", None
    tipo = famiglia(h)
    if tipo is None:
        return "tipo-ignoto", None
    pal = _prima(PALETTE_DA_NOME, t) or _prima(PALETTE_DA_NOME, h) or "navy"
    if pal == "avorio" and "oro" in (t + " " + h):
        pal = "crema-oro"
    return "rifare", (tipo, motivo, pal, PASSO_CM[motivo] * variazione(handle))


def elenco_prodotti():
    """I 66 EU dal manifest, i restanti dal file dei prodotti USA se c'e'."""
    voci = []
    eu = os.path.join(QUI, "perla-eu-prodotti.json")
    if os.path.exists(eu):
        for v in json.load(open(eu, encoding="utf-8")):
            voci.append((v["handle"], v.get("title", ""), v.get("id", ""), "eu"))
    usa = os.path.join(QUI, "perla-usa-prodotti.json")
    if os.path.exists(usa):
        for v in json.load(open(usa, encoding="utf-8")):
            voci.append((v["handle"], v.get("title", ""), v.get("id", ""), "usa"))
    return voci


def genera(tipo, motivo, pal, passo_cm, percorso):
    a = scala.AREE[tipo]
    passo = scala.passo_sicuro(tipo, scala.passo_px(tipo, passo_cm))
    im = ornati.tessitura(ornati.MOTIVI[motivo](a.px_w, a.px_h, passo,
                                                ornati.PALETTE[pal]))
    marchi = ornati.marchi_interi(im, tipo)
    im.save(percorso, quality=94)
    return passo, marchi


def main(argv):
    scrivi = "--genera" in argv
    if scrivi:
        os.makedirs(USCITA, exist_ok=True)
    conteggio = {}
    print("%-52s %-14s %-11s %-9s %s" % ("prodotto", "area", "motivo", "colore", "passo"))
    for handle, titolo, _id, linea in elenco_prodotti():
        esito, dett = piano(handle, titolo)
        conteggio[esito] = conteggio.get(esito, 0) + 1
        if esito != "rifare":
            print("%-52s %s" % (handle[:52], esito))
            continue
        tipo, motivo, pal, passo_cm = dett
        nota = "%.1f cm" % passo_cm
        if scrivi:
            percorso = os.path.join(USCITA, handle + ".jpg")
            passo, marchi = genera(tipo, motivo, pal, passo_cm, percorso)
            nota = "%.1f cm -> %.0f px, %d marchi" % (passo_cm, passo, marchi)
        print("%-52s %-14s %-11s %-9s %s" % (handle[:52], tipo, motivo, pal, nota))
    print()
    for k in sorted(conteggio):
        print("  %-18s %d" % (k, conteggio[k]))
    if not scrivi:
        print("\n(solo elenco: --genera per scrivere i file in %s)" % USCITA)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
