#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cosa deve reggere in editor-catena.py.

Ognuno di questi controlli insegue un difetto TROVATO SUL NEGOZIO VERO
guardando i dati veri, non immaginato:

  * Cuccia "Tribale" era l'unico prodotto attivo senza il tag
    'personalizzabile': per il tema l'editor non esiste, e il prodotto si
    vendeva senza personalizzazione;
  * sui ~24 prodotti americani lo sfondo dell'editor punta all'artwork
    caricato PRIMA che i file di stampa venissero ricostruiti -- si disegna su
    un motivo e se ne riceve un altro;
  * sui 66 europei sfondo e stampa oggi coincidono, e caricare i motivi
    corretti senza toccare il metafield li separerebbe;
  * il difetto ROUND 16e, gia' costato una volta: nessun tag combacia con la
    tabella dei tipi, photo_type resta vuoto e il server rifiuta l'anteprima.
"""
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

catena = __import__("editor-catena")          # noqa: E402

superate = 0
fallite = []


def prova(titolo, funzione):
    global superate
    try:
        funzione()
        superate += 1
        print("  ok   " + titolo)
    except AssertionError as e:
        fallite.append((titolo, str(e)))
        print("  NO   %s\n       %s" % (titolo, e))


# La tabella vera del tema pubblicato, ridotta alle righe che servono qui.
# Le due righe 'bandana' e 'bandana_eu' ci sono tutte e due di proposito: e'
# la coppia su cui una collisione di tag farebbe piu' danno.
TABELLA = ("collare|tipo-collare,collar,collare|25.2|Collare|8|30|7|38|0"
           "#bandana|tipo-bandana,bandana|1.86|Bandana|8|37|8|44|0"
           "#cuccia|tipo-cuccia,bed,cuccia|1.51|Cuccia|6|20|5|56|0"
           "#collare_eu|tipo-collare_eu,collare-eu|22.76|Collare EU|8|30|7|38|0"
           "#bandana_eu|tipo-bandana_eu,bandana-eu|1.0|Bandana EU|8|37|8|44|0")

RIGHE = catena.righe_tipi(TABELLA)

MOTIVI_EU = {"bandana-eu-antracite": "https://res.cloudinary.com/x/image/upload/v9/nuovo.jpg"}
STAMPE_US = {"6a50d39f": {"https://s3.example/27496136/6ba526d2-aaa?v=1",
                          "https://s3.example/27496136/7cc1f0e3-bbb?v=1"}}


def prodotto(**campi):
    base = {"title": "Prova", "handle": "prova", "status": "ACTIVE",
            "tags": ["bandana", "personalizzabile"], "editor": None,
            "printify": None}
    base.update(campi)
    return base


# ==========================================================================

def la_tabella_si_legge():
    assert len(RIGHE) == 5, "%d righe invece di 5" % len(RIGHE)
    assert RIGHE[0]["chiave"] == "collare"
    assert "bandana-eu" in RIGHE[4]["tag"]
    assert RIGHE[4]["rapporto"] == "1.0"


def vince_la_prima_riga_che_combacia():
    """Il tema fa `break` alla prima: due righe che combaciano non pareggiano."""
    riga = catena.tipo_del_prodotto(["bandana", "bandana-eu"], RIGHE)
    assert riga["chiave"] == "bandana", (
        "ha scelto %r: il tema prenderebbe 'bandana', che sta prima" % riga["chiave"])


def i_tag_eu_non_pescano_la_riga_americana():
    """E' quello che tiene separate le due linee.

    Le bandane EU hanno 'pet bandana' e 'bandana ecologica' ma NON 'bandana'
    nudo: se un domani qualcuno aggiungesse quel tag, la bandana europea
    prenderebbe il rapporto 1.86 della bandana Printify invece di 1.0, e la
    tela dell'editor uscirebbe deformata.
    """
    riga = catena.tipo_del_prodotto(
        ["bandana ecologica", "bandana-eu", "pet bandana", "square bandana"], RIGHE)
    assert riga and riga["chiave"] == "bandana_eu", (
        "ha scelto %r" % (riga and riga["chiave"]))


def senza_tag_di_tipo_lo_dice():
    guai = catena.esamina(prodotto(tags=["personalizzabile", "pet gift"]),
                          RIGHE, MOTIVI_EU, STAMPE_US)
    assert any("photo_type" in g for g in guai), guai


def senza_personalizzabile_lo_dice():
    """Il difetto di Cuccia "Tribale"."""
    guai = catena.esamina(prodotto(tags=["cuccia", "luxury pet bed"]),
                          RIGHE, MOTIVI_EU, STAMPE_US)
    assert any("personalizzabile" in g for g in guai), guai


def i_tre_tag_accendono_tutti_l_editor():
    for tag in ("personalizzabile", "POD", "custom"):
        assert catena.personalizzabile(["bandana", tag]), tag
    assert not catena.personalizzabile(["bandana"])


def sul_neutro_lo_sfondo_non_serve():
    """Sui 'crea il tuo design' lo sfondo e' nascosto di proposito."""
    guai = catena.esamina(
        prodotto(tags=["bandana", "personalizzabile", "tipo-neutro"], editor=None),
        RIGHE, MOTIVI_EU, STAMPE_US)
    assert not guai, "un neutro senza sfondo non e' un difetto: %r" % guai


def senza_sfondo_lo_dice():
    guai = catena.esamina(prodotto(editor=None), RIGHE, MOTIVI_EU, STAMPE_US)
    assert any("editor_pattern_image" in g for g in guai), guai


def sulla_linea_eu_sfondo_e_stampa_devono_coincidere():
    """E' l'invariante che il caricamento dei motivi corretti romperebbe."""
    uguali = prodotto(handle="bandana-eu-antracite", tags=["bandana-eu", "personalizzabile"],
                      editor=MOTIVI_EU["bandana-eu-antracite"])
    assert not catena.esamina(uguali, RIGHE, MOTIVI_EU, STAMPE_US)

    diversi = dict(uguali, editor="https://res.cloudinary.com/x/image/upload/v1/vecchio.jpg")
    guai = catena.esamina(diversi, RIGHE, MOTIVI_EU, STAMPE_US)
    assert any("non e' il motivo che si stampa" in g for g in guai), guai


def sulla_linea_us_lo_sfondo_deve_essere_uno_dei_file_di_stampa():
    """UNO dei file, non IL file: ogni gruppo di misure ha il suo."""
    buono = prodotto(printify="6a50d39f",
                     editor="https://s3.example/27496136/7cc1f0e3-bbb?v=1")
    assert not catena.esamina(buono, RIGHE, MOTIVI_EU, STAMPE_US)

    vecchio = dict(buono, editor="https://s3.example/27496136/db113652-ccc?v=1")
    guai = catena.esamina(vecchio, RIGHE, MOTIVI_EU, STAMPE_US)
    assert any("file di stampa correnti" in g for g in guai), guai


def il_v1_di_printify_non_conta():
    """Le URL S3 di Printify portano un ?v=1 che non fa parte dell'identita'.

    Senza normalizzarlo ogni prodotto americano risulterebbe sbagliato, e un
    controllo che segnala tutto non serve a niente.
    """
    senza = prodotto(printify="6a50d39f",
                     editor="https://s3.example/27496136/6ba526d2-aaa")
    assert not catena.esamina(senza, RIGHE, MOTIVI_EU, STAMPE_US)


def i_prodotti_archiviati_non_si_contano():
    guai = catena.esamina(prodotto(status="ARCHIVED", tags=[], editor=None),
                          RIGHE, MOTIVI_EU, STAMPE_US)
    assert not guai, "un archiviato non e' un difetto: %r" % guai


def le_stampe_correnti_si_leggono_da_printify():
    prodotto_printify = {"print_areas": [
        {"placeholders": [{"position": "front", "images": [{"src": "a.jpg"}]},
                          {"position": "back", "images": []}]},
        {"placeholders": [{"images": [{"src": "b.jpg"}, {"src": "a.jpg"}]}]}]}
    assert catena.stampe_correnti(prodotto_printify) == {"a.jpg", "b.jpg"}
    assert catena.stampe_correnti({}) == set()


def sa_dire_cosa_ci_dovrebbe_essere():
    eu = prodotto(handle="bandana-eu-antracite")
    assert catena.sfondo_giusto(eu, MOTIVI_EU, STAMPE_US) == MOTIVI_EU["bandana-eu-antracite"]
    us = prodotto(printify="6a50d39f")
    atteso = catena.sfondo_giusto(us, MOTIVI_EU, STAMPE_US)
    assert atteso in STAMPE_US["6a50d39f"], atteso
    # deterministico: due chiamate devono dare lo stesso valore
    assert atteso == catena.sfondo_giusto(us, MOTIVI_EU, STAMPE_US)
    assert catena.sfondo_giusto(prodotto(), MOTIVI_EU, STAMPE_US) is None


def il_verdetto_complessivo_conta_solo_gli_attivi():
    istantanea = {"tabella_tipi": TABELLA, "prodotti": [
        prodotto(title="Buono", handle="bandana-eu-antracite",
                 tags=["bandana-eu", "personalizzabile"],
                 editor=MOTIVI_EU["bandana-eu-antracite"]),
        prodotto(title="Senza tag", tags=["cuccia"]),
        prodotto(title="Archiviato", status="ARCHIVED", tags=[]),
    ]}
    esito = catena.verifica(istantanea, STAMPE_US, MOTIVI_EU)
    assert esito["esaminati"] == 2, esito["esaminati"]
    assert len(esito["prodotti"]) == 1, esito["prodotti"]
    assert esito["prodotti"][0]["titolo"] == "Senza tag"


print("\nLa tabella dei tipi")
prova("la tabella si legge", la_tabella_si_legge)
prova("vince la prima riga che combacia", vince_la_prima_riga_che_combacia)
prova("i tag EU non pescano la riga americana", i_tag_eu_non_pescano_la_riga_americana)
prova("senza tag di tipo lo dice", senza_tag_di_tipo_lo_dice)

print("\nChi vede l'editor")
prova("senza 'personalizzabile' lo dice", senza_personalizzabile_lo_dice)
prova("i tre tag accendono tutti l'editor", i_tre_tag_accendono_tutti_l_editor)
prova("sul neutro lo sfondo non serve", sul_neutro_lo_sfondo_non_serve)
prova("i prodotti archiviati non si contano", i_prodotti_archiviati_non_si_contano)

print("\nLo sfondo e' quello che si stampa")
prova("senza sfondo lo dice", senza_sfondo_lo_dice)
prova("sulla linea EU sfondo e stampa devono coincidere",
      sulla_linea_eu_sfondo_e_stampa_devono_coincidere)
prova("sulla linea US lo sfondo deve essere uno dei file di stampa",
      sulla_linea_us_lo_sfondo_deve_essere_uno_dei_file_di_stampa)
prova("il ?v=1 di Printify non conta", il_v1_di_printify_non_conta)
prova("le stampe correnti si leggono da Printify", le_stampe_correnti_si_leggono_da_printify)
prova("sa dire cosa ci dovrebbe essere", sa_dire_cosa_ci_dovrebbe_essere)
prova("il verdetto complessivo conta solo gli attivi",
      il_verdetto_complessivo_conta_solo_gli_attivi)

print("\n%d verifiche superate." % superate)
if fallite:
    print("%d FALLITE" % len(fallite))
    sys.exit(1)
