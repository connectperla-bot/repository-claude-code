#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I tre prodotti americani nuovi: collare di pelle, medaglietta incisa, parka.

COSA SONO E PERCHE' STANNO QUI
Il 4 settembre la proprietaria li ha visti sul catalogo Printify e li ha
scelti: "hanno aggiunto un collare di pelle engraving che e' interessante...
aggiungi anche i vestiti per i cani". Le condizioni le ha dette lei:
visibili SOLO in America, prezzi giusti, e NESSUN disegno -- solo il "Crea il
Tuo Design", che e' la scheda neutra su cui il cliente porta il suo.

    prodotto                 blueprint  fornitore      varianti  area
    Collare in Pelle          10700     Fulfill Engine    28     1650x150
    Medaglietta Incisa        10674     Taylor            15      756x907
    Giacchetto Parka          10740     Print Clever       6     2126x2717

SOLO AMERICA, E VIENE DA SE'
snippets/perla-region-hidden.liquid mostra al visitatore europeo SOLO i
prodotti con un tag *-eu, e a chi sta fuori SOLO quelli senza. Non c'e'
niente da accendere: basta non dare a questi tre nessun tag europeo. E fuori
dall'Europa il negozio spedisce in un paese solo, gli Stati Uniti.

IL PREZZO NON SI PUO' FARE PRIMA
Printify espone il costo di una variante solo sui prodotti che esistono nel
negozio: dal catalogo si leggono le misure e le varianti, non i soldi. Quindi
prima si creano le bozze, poi perla-verifica-margini.py legge i costi veri e
perla-prezzi-margine.py fa il prezzo con la regola del 20% e la riserva del
5%. Nessuno va in vendita prima di avere il suo prezzo.

DUE DECORAZIONI CHE NON SONO STAMPA
Collare e medaglietta si INCIDONO (engraving e laser-engraving): il file non
e' un motivo a colori ma un segno, e quello che resta sul pezzo e' il solco.
Per questo il disegno neutro di questi due e' la scritta del marchio in nero
su trasparente, non il medaglione dorato -- un degrade inciso diventa una
macchia. Il parka invece si stampa (DTF sul dorso) e porta il marchio intero.

USO
    python3 scripts/perla-usa-prodotti-nuovi.py                # elenca, non tocca
    python3 scripts/perla-usa-prodotti-nuovi.py --disegna      # solo i file neutri
    python3 scripts/perla-usa-prodotti-nuovi.py --crea         # carica e crea le bozze

Le bozze nascono NON pubblicate. Si pubblicano dopo, a prezzo fatto, con
    node scripts/perla-publish-drafts.js <id> <id> <id>
e subito dopo va messa la giacenza sulla Sede del negozio -- il perche' sta
scritto per intero in perla-publish-drafts.js.
"""
import argparse
import base64
import importlib.util
import json
import os
import sys

from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
DISEGNI = os.path.join(RADICE, "generated-designs")
MARCHIO = os.path.join(DISEGNI, "perla-combined-logo.png")
REGISTRO = os.path.join(DISEGNI, "usa-prodotti-nuovi.json")

# La scritta "Perla Italia" sta nella meta' bassa del marchio combinato, il
# medaglione nella meta' alta. Il taglio e' a occhio ma verificato: sotto
# questa frazione non c'e' nessun pezzo del medaglione.
TAGLIO_SCRITTA = 0.60

NERO = (26, 24, 22)


# ==========================================================================
# I TRE PRODOTTI
# ==========================================================================
#
# `marchio` dice quanto e' grande il segno neutro e dove sta, in frazioni
# dell'area di stampa. Sono misure scelte perche' il marchio resti DISCRETO:
# la proprietaria l'aveva gia' chiesto sui prodotti americani di prima --
# "su printify e' brutto appiccicato cosi' grosso al centro, rendilo piu'
# piccolo e discreto".
PRODOTTI = [
    {
        "chiave": "collare-pelle",
        "blueprint": 10700, "provider": 217, "posizione": "front",
        "titolo": u"Collare in Pelle “Crea il Tuo Design”",
        "segno": "scritta",
        # sulla fettuccia il segno si misura in ALTEZZA: la striscia e' 11:1,
        # e ragionare in larghezza darebbe una scritta alta due pixel
        "marchio": {"altezza": 0.55, "x": 0.5, "y": 0.5},
        "taglie": [u"Small", u"Medium", u"Large", u"Extra Large"],
    },
    {
        "chiave": "medaglietta-incisa",
        "blueprint": 10674, "provider": 228, "posizione": "front",
        "titolo": u"Medaglietta Incisa “Crea il Tuo Design”",
        "segno": "scritta",
        "marchio": {"larghezza": 0.62, "x": 0.5, "y": 0.5},
        # LA FORMA NON E' IL SUO RETTANGOLO, e sulla medaglietta si vede.
        # L'area di stampa e' il rettangolo che CONTIENE il pezzo, ma il
        # pezzo e' un cerchio, un cuore o un osso: un marchio largo il 62%
        # del rettangolo esce dal cuore e dall'osso, e il primo mockup lo ha
        # mostrato subito. Ogni forma ha la sua misura, presa dentro la
        # sagoma e non dentro il rettangolo.
        "per_misura": {
            (756, 907): {"larghezza": 0.46, "x": 0.5, "y": 0.5},   # cerchio
            (756, 827): {"larghezza": 0.42, "x": 0.5, "y": 0.44},  # cuore
            (744, 496): {"larghezza": 0.40, "x": 0.5, "y": 0.5},   # osso
        },
        "taglie": [u"One size"],
    },
    {
        "chiave": "giacchetto",
        "blueprint": 10740, "provider": 72, "posizione": "back_dtf",
        "titolo": u"Giacchetto Parka “Crea il Tuo Design”",
        "segno": "marchio",
        # in alto sul dorso, come una placca: al centro e grande era proprio
        # il difetto da non ripetere
        "marchio": {"larghezza": 0.30, "x": 0.5, "y": 0.30},
        "taglie": [u"XS", u"S", u"M", u"L", u"XL", u"2XL"],
    },
]


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aree = _modulo("aree_stampa", os.path.join(QUI, "aree-stampa.py"))
marchio = _modulo("marchio", os.path.join(QUI, "marchio.py"))
margini = _modulo("perla_verifica_margini",
                  os.path.join(QUI, "perla-verifica-margini.py"))
listino = _modulo("perla_prezzi_margine",
                  os.path.join(QUI, "perla-prezzi-margine.py"))
testi = _modulo("perla_descrizioni", os.path.join(QUI, "perla-descrizioni.py"))
carica = _modulo("perla_usa_carica_stampe",
                 os.path.join(QUI, "perla-usa-carica-stampe.py"))


# ==========================================================================
# IL SEGNO NEUTRO
# ==========================================================================

def _scritta_nera():
    """La scritta del marchio, nera piena su trasparente.

    Si ritaglia dal marchio combinato invece di riscriverla con un font: e'
    la stessa lettera che sta su tutto il resto del negozio, e un font
    "simile" si vedrebbe subito accanto agli altri prodotti.

    Nera piena e non oro perche' questa immagine va su una macchina che
    incide: legge il segno, non il colore. Un oro sfumato inciderebbe una
    macchia invece di una lettera.
    """
    im = Image.open(MARCHIO).convert("RGBA")
    w, h = im.size
    basso = im.crop((0, int(TAGLIO_SCRITTA * h), w, h))
    riquadro = basso.split()[3].getbbox()
    if riquadro is None:
        raise RuntimeError("la scritta del marchio e' tutta trasparente: %s" % MARCHIO)
    scritta = basso.crop(riquadro)
    pieno = Image.new("RGBA", scritta.size, NERO + (0,))
    pieno.putalpha(scritta.split()[3])
    return pieno


# QUANTO E' SCURO IL PARKA, MISURATO E NON DICHIARATO
#
# Il marchio del parka finisce su un tessuto che nel nostro file NON C'E': lo
# mette Printify sotto la stampa. marchio._adatta() vuole sapere quanto e'
# chiaro il fondo per scegliere inchiostro e alone, e qui bisogna dirglielo.
#
# La prima volta l'avevo DICHIARATO, 178, la luminosita' di un khaki da
# manuale, e mi sbagliavo di centoventi punti. "Khaki" nel nome della
# variante e' un verde oliva scuro: misurato sul dorso della foto di
# catalogo del blueprint 10740 il colore mediano e' (65, 56, 39), che fa 57.
# Sta sotto FONDO_SCURO, quindi l'inchiostro quasi nero della scritta viene
# tirato verso il crema e l'alone e' scuro -- l'esatto contrario di quello
# che avrebbe fatto col numero inventato, dove "Italia" sarebbe rimasto nero
# su verde scuro e non si sarebbe letto.
#
# Il numero si rimisura dalla foto del fornitore, non si indovina:
#   python3 -c "..." su generated-designs/ (vedi il commento in cima)
PARKA = 57


def _marchio_intero():
    """Il marchio combinato, con l'inchiostro e l'alone del suo fondo.

    Passa da marchio._adatta() come tutto il resto del catalogo: senza,
    l'oro finirebbe su un khaki quasi della stessa luminosita' e la scritta
    "Perla" sparirebbe -- si vedrebbe solo "Italia", che e' in quasi-nero.
    E' lo stesso difetto che la proprietaria aveva descritto sui prodotti di
    prima, "il logo o e' troppo scuro o e' scansionato di luminosita'".
    """
    im = Image.open(MARCHIO).convert("RGBA")
    riquadro = im.split()[3].getbbox()
    if riquadro:
        im = im.crop(riquadro)
    return marchio._adatta(im, PARKA)


def disegna(prod, misura):
    """Scrive il file neutro della misura ESATTA dell'area. Torna il percorso.

    Esatta, e non piu' piccolo da ingrandire: su Printify `scale` e' relativa
    all'area, quindi un file gia' giusto sta a scale=1 e non si tocca. E' la
    stessa regola di perla-usa-carica-stampe.py.

    UN FILE PER MISURA, e qui non e' un vezzo. Le varianti di questi tre
    blueprint non hanno affatto la stessa area:

        collare      1650x150  1795x189  1950x195  1950x270
        medaglietta   756x907   756x827   744x496  (cerchio, cuore, osso)
        parka        1181x1181 1535x1535 1535x2362 1654x2717 2126x2717

    Un file solo, messo a scale=1 su tutte, lascerebbe scoperta meta'
    dell'osso e sforerebbe sull'XS del parka. E' esattamente il difetto che
    aree-stampa.py e' stato scritto per chiudere, e print_areas di Printify
    accetta piu' voci apposta.
    """
    aw, ah = misura
    tela = Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
    segno = _scritta_nera() if prod["segno"] == "scritta" else _marchio_intero()
    m = prod.get("per_misura", {}).get(tuple(misura), prod["marchio"])
    if "larghezza" in m:
        larg = int(round(m["larghezza"] * aw))
        alt = int(round(larg * segno.size[1] / float(segno.size[0])))
    else:
        alt = int(round(m["altezza"] * ah))
        larg = int(round(alt * segno.size[0] / float(segno.size[1])))
    # su un'area quasi quadrata la misura scelta puo' sforare sull'altro
    # lato: si rimpicciolisce finche' ci sta, invece di uscire dal bordo
    if larg > aw:
        alt = int(round(alt * aw / float(larg)))
        larg = aw
    if alt > ah:
        larg = int(round(larg * ah / float(alt)))
        alt = ah
    segno = segno.resize((max(larg, 1), max(alt, 1)), Image.LANCZOS)
    tela.paste(segno, (int(round(m["x"] * aw - larg / 2.0)),
                       int(round(m["y"] * ah - alt / 2.0))), segno)
    percorso = os.path.join(DISEGNI, "%s-neutro-perla-%dx%d.png"
                            % (prod["chiave"], aw, ah))
    tela.save(percorso)
    return percorso


# ==========================================================================
# CREAZIONE SU PRINTIFY
# ==========================================================================

def misure(prod, token):
    """I gruppi di varianti che condividono la misura dell'area di stampa.

    Le misure arrivano da printify-blueprints/<bp>_<pp>.json, che aree-stampa
    scarica e versiona da solo la prima volta: cosi' la volta dopo i test
    girano senza rete.
    """
    elenco = aree.varianti(prod["blueprint"], prod["provider"], token)
    gruppi = aree.gruppi(elenco, prod["posizione"])
    if not gruppi:
        raise RuntimeError("nessuna variante di %s ha l'area %s"
                           % (prod["chiave"], prod["posizione"]))
    return gruppi


def da_creare(prod, gruppi, immagini):
    """Il corpo di POST /products.json, con TUTTE le varianti abilitate.

    Tutte e non una sola: qui la taglia la sceglie il cliente e il collare ne
    ha quattro per sette colori di pelle. La variante da ordinare poi la
    ritrova scripts/varianti-fornitore.js dal titolo, che su Shopify e su
    Printify e' lo stesso.

    Una voce di print_areas per gruppo, ognuna col SUO file: e' la
    correzione di ROUND 47, e qui nasce gia' giusta invece di essere
    riparata dopo.

    Il prezzo qui e' un segnaposto: i prezzi veri li scrive
    perla-prezzi-margine.py DOPO, quando Printify avra' esposto i costi. Un
    prodotto non pubblicato non li fa vedere a nessuno.
    """
    ids = [i for g in gruppi for i in g["variant_ids"]]
    return {
        "title": prod["titolo"],
        "description": descrizione(prod),
        "blueprint_id": prod["blueprint"],
        "print_provider_id": prod["provider"],
        "variants": [{"id": i, "price": 9900, "is_enabled": True} for i in ids],
        "print_areas": [{
            "variant_ids": g["variant_ids"],
            "placeholders": [{
                "position": prod["posizione"],
                "images": [{"id": immagini[g["misura"]], "x": 0.5, "y": 0.5,
                            "scale": 1, "angle": 0}],
            }],
        } for g in gruppi],
    }


def descrizione(prod):
    return testi.DESCRIZIONI[prod["chiave"]]


def registro():
    if os.path.exists(REGISTRO):
        with open(REGISTRO) as fh:
            return json.load(fh)
    return {}


def salva_registro(dati):
    with open(REGISTRO, "w") as fh:
        json.dump(dati, fh, indent=1, ensure_ascii=False)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--disegna", action="store_true",
                   help="costruisce solo i file neutri, senza toccare Printify")
    a.add_argument("--crea", action="store_true",
                   help="carica i file e crea le tre bozze su Printify")
    a.add_argument("--rifai", action="store_true",
                   help="ricarica i disegni e li rimette sulle bozze gia' create")
    a.add_argument("--prezzi", action="store_true",
                   help="calcola i prezzi dai costi veri e li scrive sulle bozze")
    a.add_argument("--margine", type=float, default=100 * listino.MARGINE,
                   help="margine sul prezzo di vendita, in percento")
    opz = a.parse_args()

    chiavi = carica.chiavi()
    token = chiavi.get("PRINTIFY_API_KEY")
    negozio = chiavi.get("PRINTIFY_SHOP_ID")
    if not (token and negozio):
        sys.exit("mancano PRINTIFY_API_KEY o PRINTIFY_SHOP_ID in config/printify.local.env")

    fatti = registro()
    if opz.prezzi:
        margini.ambiente()
        tasso, quando = margini.cambio_usd_eur()
        vera = margini.iva_da_un_ordine_printify()
        riserva = vera if vera is not None else margini.RISERVA_IMPOSTA_USA
        print("cambio 1 USD = %.4f EUR (%s)" % (tasso, quando))
        print("imposta americana: %.0f%% (%s)\n"
              % (100 * riserva, "letta da un ordine vero" if vera is not None
                 else "riserva, nessun ordine da cui leggerla"))

    for prod in PRODOTTI:
        prod["_token"] = token
        gruppi = misure(prod, token)
        quante = sum(len(g["variant_ids"]) for g in gruppi)
        gia = fatti.get(prod["chiave"], {})
        print("%-20s bp %-6d %2d varianti in %d misure   %s"
              % (prod["chiave"], prod["blueprint"], quante, len(gruppi),
                 gia.get("id", "-- da creare --")))
        for g in gruppi:
            print("     %5dx%-5d %d varianti" % (g["misura"][0], g["misura"][1],
                                                 len(g["variant_ids"])))

        if opz.prezzi and gia.get("id"):
            prodotto = carica.api("GET", "/v1/shops/%s/products/%s.json"
                                  % (negozio, gia["id"]), token=token)
            nuovi, righe, sped = prezzi(prod, prodotto, tasso, riserva,
                                        opz.margine / 100.0)
            print("   spedizione USA %.2f $ a copia" % sped)
            visti = set()
            for titolo, costo, prezzo, marg in righe:
                # una riga per COSTO: ventotto varianti con lo stesso costo
                # sono una decisione sola, e ventotto righe uguali la
                # nasconderebbero
                if round(costo, 2) in visti:
                    continue
                visti.add(round(costo, 2))
                print("     %-30s costo %6.2f -> %6.2f  (%.1f%%)"
                      % (titolo, costo, prezzo, marg))
            r = carica.api("PUT", "/v1/shops/%s/products/%s.json" % (negozio, gia["id"]),
                           corpo={"variants": [{"id": i, "price": c, "is_enabled": True}
                                               for i, c in nuovi.items()]}, token=token)
            print("   prezzi scritti su %d varianti%s"
                  % (len(nuovi), "" if "id" in r else ": " + json.dumps(r)[:300]))

        if not (opz.disegna or opz.crea or opz.rifai):
            continue

        percorsi = {g["misura"]: disegna(prod, g["misura"]) for g in gruppi}
        print("   %d disegni neutri: %s" % (
            len(percorsi), ", ".join(sorted(os.path.basename(p) for p in percorsi.values()))))

        if opz.rifai and gia.get("id"):
            # IL PUT VUOLE print_areas INTERO: quello che non si rimanda va
            # perso. Si riscrive tutto, che qui e' semplice perche' il
            # prodotto ha una sola posizione di stampa e nessun altro
            # livello da salvare.
            immagini = {}
            for misura, percorso in percorsi.items():
                immagini[misura] = carica.carica_immagine(percorso, token)["id"]
            corpo = da_creare(prod, gruppi, immagini)
            r = carica.api("PUT", "/v1/shops/%s/products/%s.json" % (negozio, gia["id"]),
                           corpo={"print_areas": corpo["print_areas"]}, token=token)
            if "id" not in r:
                print("   NON aggiornato: %s" % json.dumps(r)[:500])
                continue
            gia["immagini"] = {"%dx%d" % m: i for m, i in immagini.items()}
            fatti[prod["chiave"]] = gia
            salva_registro(fatti)
            print("   disegni rimessi sulla bozza %s" % gia["id"])

        if opz.crea and not gia.get("id"):
            immagini = {}
            for misura, percorso in percorsi.items():
                su = carica.carica_immagine(percorso, token)
                immagini[misura] = su["id"]
            print("   caricate su Printify: %s" % ", ".join(sorted(immagini.values())))
            corpo = da_creare(prod, gruppi, immagini)
            r = carica.api("POST", "/v1/shops/%s/products.json" % negozio,
                           corpo=corpo, token=token)
            if "id" not in r:
                print("   NON creato: %s" % json.dumps(r)[:500])
                continue
            fatti[prod["chiave"]] = {
                "id": r["id"], "titolo": prod["titolo"],
                "blueprint": prod["blueprint"], "provider": prod["provider"],
                "immagini": {"%dx%d" % m: i for m, i in immagini.items()}}
            salva_registro(fatti)
            print("   creato come bozza: %s" % r["id"])

    if not (opz.disegna or opz.crea or opz.rifai or opz.prezzi):
        print("\nNiente e' stato toccato. --disegna per i file, --crea per le bozze,"
              "\n--rifai per rimetterli su bozze gia' create, --prezzi per i prezzi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
