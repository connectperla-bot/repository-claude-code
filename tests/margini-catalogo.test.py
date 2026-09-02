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
    assert set(m.PRINTIFY) == {419, 562, 566, 570}, (
        "attesi cuccia 419, bandana 562, medaglietta 566, ciotola 570; "
        "trovati %s" % sorted(m.PRINTIFY))


prova("i blueprint Printify controllati sono quelli in vendita", blueprint_giusti)


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


def tipo_printify_dal_titolo():
    a = m.tipo_di({"handle": "perla-italia-cuccia-medallion-purple",
                   "title": u"Cuccia “Nobile”"})
    b = m.tipo_di({"handle": "qualsiasi", "title": u"Medaglietta “Aurora”"})
    assert a == "cuccia" and b == "medaglietta", (
        "sulla linea Printify il titolo e' l'unica cosa che distingue i tipi. "
        "Ottenuto: %s, %s" % (a, b))


prova("sulla linea Printify il tipo si legge dal titolo", tipo_printify_dal_titolo)


def preventivo_italiano():
    assert m.INDIRIZZO["country_code"] == "IT", (
        "il costo di spedizione dipende dal paese di consegna: chiederlo altrove "
        "darebbe un margine che non esiste")


prova("il preventivo si chiede verso l'Italia", preventivo_italiano)

print("\n  %d verifiche\n" % fatte)
