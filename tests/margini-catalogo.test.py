#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il controllo dei margini misura le varianti GIUSTE?

IL GUASTO CHE QUESTA PROVA CERCA
scripts/perla-verifica-margini.py chiede a Printful quanto costa la variante
19186 per sapere quanto costa un collare EU. Ma la variante che finisce
davvero nell'ordine del cliente la sceglie scripts/varianti-fornitore.js, con
la sua tabella. Se i due elenchi si separano -- qualcuno cambia un id di la'
e non di qua -- il controllo continua a rispondere, con numeri puliti e
sbagliati: direbbe che il margine e' buono su una variante che non vendiamo,
e la vendita in perdita resterebbe li'.

Un numero sbagliato che sembra giusto e' peggio di un errore, perche' nessuno
va a ricontrollarlo. Quindi qui i due elenchi si confrontano.

Si controlla anche che tipo_di() riconosca il tipo dai dati veri della
vetrina: sulla linea EU dall'handle, perche' i titoli sono stati rinominati e
non descrivono piu' il disegno; sulla linea Printify dal titolo, perche' li'
l'handle non dice il tipo.

Uso:  python3 tests/margini-catalogo.test.py
"""
import importlib.util
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
SCRIPT = os.path.join(RADICE, "scripts", "perla-verifica-margini.py")
MAPPA = os.path.join(RADICE, "scripts", "varianti-fornitore.js")

fatte = 0


def prova(nome, fn):
    global fatte
    try:
        fn()
        print("  ok   " + nome)
        fatte += 1
    except AssertionError as e:
        print("  FALLITO   " + nome + "\n        " + str(e))
        sys.exit(1)


def carica():
    # Niente bytecode: durante una prova a rovescio (si guasta lo script
    # apposta e si controlla che il test se ne accorga) il .pyc rimasto da
    # prima veniva riletto al posto del sorgente, e il test rispondeva sul
    # file di ieri. Un test che legge una cache non e' un test.
    sys.dont_write_bytecode = True
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location("margini", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def id_dal_javascript(blocco):
    """Gli id numerici dentro il blocco `nome: { ... }` di varianti-fornitore.js"""
    testo = open(MAPPA, encoding="utf-8").read()
    i = testo.index(blocco + ": {")
    j = testo.index("}", i)
    return set(int(x) for x in re.findall(r":\s*(\d{4,6})", testo[i:j]))


m = carica()

print("\nControllo dei margini")


def varianti_combaciano():
    for tipo, blocco in (("collare-eu", "collare_eu"),
                         ("bandana-eu", "bandana_eu"),
                         ("ciotola-eu", "ciotola_eu")):
        attesi = id_dal_javascript(blocco)
        usati = set(v for _, v, _ in m.PRINTFUL[tipo])
        assert usati <= attesi, (
            "%s: il controllo dei margini quota %s, ma la mappa che sceglie la "
            "variante negli ordini conosce solo %s"
            % (tipo, sorted(usati - attesi), sorted(attesi)))
        assert usati, "%s: nessuna variante da quotare" % tipo


prova("le varianti Printful quotate sono quelle che finiscono negli ordini",
      varianti_combaciano)


def guinzaglio_a_parte():
    v = m.PRINTFUL["guinzaglio-eu"]
    assert len(v) == 1 and v[0][1] == 19126, (
        "guinzaglio_eu resta fuori da varianti-fornitore.js apposta (Printful lo "
        "fa in una misura sola): l'id sta in configurazione, e qui deve essere "
        "lo stesso. Trovato: %s" % (v,))


prova("il guinzaglio EU ha una misura sola, e l'id combacia", guinzaglio_a_parte)


def blueprint_giusti():
    # Elencati per nome uno per uno, e non contati: un elenco dice quale
    # manca, un conteggio dice solo che qualcosa non torna. I primi quattro
    # sono la linea americana di sempre; i tre di mezzo li ha scelti la
    # proprietaria dal catalogo Printify il 4 settembre; il tappetino e' di
    # settembre e sta su tutti e due i mercati con lo stesso blueprint.
    atteso = {419: "cuccia", 562: "bandana", 566: "medaglietta", 570: "ciotola",
              10700: "collare-pelle", 10674: "medaglietta-incisa",
              10740: "giacchetto", 623: "tappetino"}
    assert m.PRINTIFY == atteso, (
        "i blueprint quotati non sono quelli in vendita.\n  attesi:  %s\n  "
        "trovati: %s" % (sorted(atteso.items()), sorted(m.PRINTIFY.items())))


prova("i blueprint Printify controllati sono quelli in vendita", blueprint_giusti)


def tipi_nuovi_non_si_confondono():
    """I tre nuovi cominciano come tre tipi che esistono gia'.

    "Collare in Pelle" comincia per Collare, "Medaglietta Incisa" per
    Medaglietta: se il tipo si leggesse dalla prima parola del titolo, il
    collare di pelle da 31,26 di costo verrebbe misurato sul costo del
    collare europeo da 24,58, e la medaglietta incisa da 13,02 su quella
    stampata da 15,52. Nessuno dei due errori si vede guardando la tabella:
    escono due margini plausibili e sbagliati.

    Per questo tipo_di() guarda prima l'handle. Qui si controlla che li
    distingua davvero, e insieme che NON rubi i prodotti vecchi.
    """
    casi = [
        ({"handle": "collare-in-pelle-crea-il-tuo-design",
          "title": u"Collare in Pelle “Crea il Tuo Design”"}, "collare-pelle"),
        ({"handle": "medaglietta-incisa-crea-il-tuo-design",
          "title": u"Medaglietta Incisa “Crea il Tuo Design”"}, "medaglietta-incisa"),
        ({"handle": "giacchetto-parka-crea-il-tuo-design",
          "title": u"Giacchetto Parka “Crea il Tuo Design”"}, "giacchetto"),
        # e i vecchi restano quelli di prima
        ({"handle": "collare-eu-tartan-fornitore-europeo",
          "title": u"Collare “Tartan”"}, "collare-eu"),
        ({"handle": "perla-italy-medaglietta-neutro-personalizza-il-tuo-design",
          "title": u"Medaglietta “Crea il Tuo Design”"}, "medaglietta"),
    ]
    for prodotto, atteso in casi:
        avuto = m.tipo_di(prodotto)
        assert avuto == atteso, (
            "%s doveva dare il tipo %s, ha dato %s"
            % (prodotto["handle"], atteso, avuto))
    # ogni tipo nominato in PRINTIFY_HANDLE deve esistere fra quelli quotati
    for prefisso, tipo in m.PRINTIFY_HANDLE.items():
        assert tipo in m.PRINTIFY.values(), (
            "l'handle %s promette il tipo %s, che non e' fra i blueprint "
            "quotati: nessun costo lo raggiungerebbe" % (prefisso, tipo))


prova("i tre tipi nuovi non si confondono con quelli vecchi",
      tipi_nuovi_non_si_confondono)


def tipo_eu_dall_handle():
    a = m.tipo_di({"handle": "collare-eu-tartan-fornitore-europeo",
                   "title": u"Collare “Tartan”"})
    b = m.tipo_di({"handle": "ciotola-eu-floreale-smeraldo-oro-fornitore-europeo",
                   "title": u"Ciotola “Toile Rubino”"})
    assert a == "collare-eu" and b == "ciotola-eu", (
        "un handle EU deve dare il tipo EU. La seconda riga e' un caso vero: quel "
        "prodotto si chiama “Toile Rubino” ma l'handle dice floreale-smeraldo, "
        "e il costo va accostato al tipo, non al nome. Ottenuto: %s, %s" % (a, b))


prova("sulla linea EU il tipo si legge dall'handle", tipo_eu_dall_handle)


def tipo_eu_dal_tag():
    """Gli handle EU sono stati accorciati: il tipo deve reggere lo stesso.

    Prima erano "collare-eu-tartan-fornitore-europeo", adesso sono
    "collare-tartan". Se il tipo si cercasse solo nell'handle, tutti e 66 gli
    europei resterebbero senza costo quotato e il controllo sul margine
    smetterebbe di guardarli -- senza dire niente, perche' un prodotto senza
    costo finisce nell'elenco "senza" e non fa fallire nessuna soglia. Il tag
    e' il segno che e' rimasto, ed e' quello vero: dice chi stampa."""
    casi = [
        ({"handle": "collare-tartan", "title": u"Collare \u201cTartan\u201d",
          "tags": ["collare regolabile", "collare-eu", "eu shipping"]}, "collare-eu"),
        ({"handle": "ciotola-toile-rubino", "title": u"Ciotola \u201cToile Rubino\u201d",
          "tags": "ciotola-eu, personalizzabile"}, "ciotola-eu"),
        ({"handle": "guinzaglio-onda", "title": u"Guinzaglio \u201cOnda\u201d",
          "tags": ["guinzaglio-eu"]}, "guinzaglio-eu"),
        ({"handle": "bandana-notte", "title": u"Bandana \u201cNotte\u201d",
          "tags": ["bandana-eu"]}, "bandana-eu"),
    ]
    for prodotto, atteso in casi:
        avuto = m.tipo_di(prodotto)
        assert avuto == atteso, (
            "%s ha il tag %s: doveva dare %s, ha dato %s"
            % (prodotto["handle"], atteso, atteso, avuto))
    # e un Printify non deve essere scambiato per europeo solo perche' il tipo
    # nel titolo si assomiglia
    fuori = m.tipo_di({"handle": "perla-italia-collare-damask-burgundy-gold",
                       "title": u"Collare \u201cDamasco\u201d",
                       "tags": ["dog collar", "printify"]})
    assert fuori != "collare-eu", (
        "un prodotto senza tag europeo non puo' finire sui costi Printful. "
        "Ottenuto: %s" % fuori)


prova("sulla linea EU il tipo si legge dal tag anche con l'handle corto",
      tipo_eu_dal_tag)


def tipo_printify_dal_titolo():
    a = m.tipo_di({"handle": "perla-italia-cuccia-medallion-purple",
                   "title": u"Cuccia “Nobile”"})
    b = m.tipo_di({"handle": "qualsiasi", "title": u"Medaglietta “Aurora”"})
    assert a == "cuccia" and b == "medaglietta", (
        "sulla linea Printify il titolo e' l'unica cosa che distingue i tipi. "
        "Ottenuto: %s, %s" % (a, b))


prova("sulla linea Printify il tipo si legge dal titolo", tipo_printify_dal_titolo)


def alias_tappetino_copre_la_scheda():
    """Il costo del tappetino si accosta al titolo ITALIANO della scheda.

    Il fornitore chiama la variante 'Bone shape (19" x 14") / White', la
    scheda la chiama 'Osso piccolo (48x36 cm)'. Il foglio dei margini accosta
    il costo per titolo: se i due elenchi si separano, le trentasei varianti
    dei tappetini escono dal conto SENZA UN ERRORE -- finiscono nell'elenco
    "senza costo noto" in coda, e il foglio continua a dire "sotto il 20%: 0"
    perche' quelle righe non le sta piu' guardando. E' successo davvero.

    Qui si chiede che ogni titolo italiano che varianti-fornitore.js conosce
    sia raggiungibile da ALIAS_VARIANTE: le due tabelle devono dire la stessa
    cosa, una per gli ordini e una per i costi.
    """
    sorgente = open(os.path.join(RADICE, "scripts", "varianti-fornitore.js"),
                    encoding="utf-8").read()
    blocco = re.search(r"tappetino:\s*\{(.*?)\}", sorgente, re.S)
    assert blocco, "varianti-fornitore.js non ha piu' la mappa tappetino"
    italiani = {t for t in re.findall(r"'([^']+)':\s*\d+", blocco.group(1))
                if "shape" not in t.lower()}
    assert italiani, "nessun titolo italiano nella mappa tappetino"

    raggiunti = set(m.ALIAS_VARIANTE.get(623, {}).values())
    mancanti = sorted(italiani - raggiunti)
    assert not mancanti, (
        "questi titoli di scheda non hanno un alias nei costi, quindi le loro "
        "varianti uscirebbero dal foglio in silenzio: %s" % ", ".join(mancanti))


prova("il tappetino: il costo raggiunge i titoli italiani della scheda",
      alias_tappetino_copre_la_scheda)


def pareggia_le_due_scritture():
    """Virgolette dritte o curve, x o ×: il catalogo usa tutt'e due."""
    a = m._pareggia(u'Bone shape (30" × 18") / White')
    b = m._pareggia(u'Bone shape (30” x 18”) / White')
    assert a == b, (
        "lo stesso titolo scritto in due modi deve pareggiarsi, altrimenti "
        "l'alias non aggancia: %r contro %r" % (a, b))
    assert a in m.ALIAS_VARIANTE[623], (
        "il titolo pareggiato deve essere una chiave viva di ALIAS_VARIANTE, "
        "non una che non incontra mai niente: %r" % a)


prova("virgolette e segno per non separano i due cataloghi",
      pareggia_le_due_scritture)


def preventivo_italiano():
    assert m.INDIRIZZO["country_code"] == "IT", (
        "il costo di spedizione dipende dal paese di consegna: chiederlo altrove "
        "darebbe un margine che non esiste")


prova("il preventivo si chiede verso l'Italia", preventivo_italiano)

print("\n  %d verifiche\n" % fatte)
