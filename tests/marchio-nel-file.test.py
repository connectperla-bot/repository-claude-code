#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica che il marchio ci sia, si veda, e non sia doppio.

PERCHE' ESISTE
Trentaquattro prodotti su settanta sono finiti in vendita senza nessun
marchio stampato, e nessuno se n'era accorto. Non per una svista singola: per
due operazioni giuste prese una alla volta. perla-usa-carica-stampe.py aveva
sostituito l'artwork americano con i nativi europei; perla-usa-marchio.py
aveva tolto il livello logo sovrapposto perche' "l'artwork lo contiene gia'"
-- vero prima della sostituzione, falso dopo.

Su altri diciotto il livello c'era ma stava FUORI dal bordo dell'area
(x=-0,084, y=1,044 sulla cuccia "Geometric Tribal"): presente nei dati,
invisibile in stampa. Contare i livelli non basta: bisogna guardare dove
cadono.

E c'e' il difetto opposto, gia' arrivato in catalogo una volta (commit
962ade7): il marchio DOPPIO, quando lo si aggiunge a un motivo che lo
contiene gia'. Dodici nativi europei su quindici ce l'hanno dentro.

USO
    python3 tests/marchio-nel-file.test.py

Richiede Pillow.
"""
import glob
import importlib.util
import json
import os
import sys

from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(QUI, '..', 'scripts')


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


marchio = _modulo('marchio', os.path.join(SCRIPTS, 'marchio.py'))
aree = _modulo('aree_stampa', os.path.join(SCRIPTS, 'aree-stampa.py'))

passati = 0
falliti = 0


def prova(descrizione, fn):
    global passati, falliti
    try:
        fn()
        passati += 1
        print('  ok   %s' % descrizione)
    except AssertionError as err:
        falliti += 1
        print('  FALLITO  %s\n           %s' % (descrizione, err))


def misure_reali():
    """Tutte le misure di stampa vere del repository, per tipo di prodotto."""
    tipi = {419: 'cuccia', 562: 'bandana', 566: 'medaglietta',
            784: 'collare', 570: 'ciotola', 855: 'tappetino'}
    fuori = []
    for percorso in sorted(glob.glob(os.path.join(QUI, '..', 'printify-blueprints', '*.json'))):
        base = os.path.basename(percorso)[:-5]
        if '_' not in base:
            continue
        bp, pr = (int(x) for x in base.split('_', 1))
        tipo = tipi.get(bp)
        if not tipo:
            continue
        with open(percorso) as fh:
            if not json.load(fh).get('variants'):
                continue
        for g in aree.gruppi(aree.varianti(bp, pr)):
            fuori.append((tipo, g['misura']))
    return fuori


# ==========================================================================

def test_non_si_aggiunge_dove_ce_gia():
    """I motivi con la SCRITTA RIPETUTA il marchio ce l'hanno ovunque.

    Questi sono diversi dai quattro col medaglione singolo (test sotto): qui
    la scritta si ripete su tutto il motivo, quindi qualunque ritaglio ne
    contiene comunque. Aggiungerne un altro sarebbe il marchio doppio.
    """
    for gia in ('bandana-barocco.jpg', 'bandana-floreale-elegante.jpg',
                'bandana-ramo-dulivo.jpg', 'bandana-ghirigori.jpg'):
        assert not marchio.serve(gia), (
            '%s il marchio ce l\'ha gia\' dentro: aggiungerlo lo raddoppia' % gia)


def test_si_aggiunge_dove_manca():
    for manca in marchio.NATIVI_SENZA_MARCHIO:
        assert marchio.serve(manca), '%s non ha marchio: va aggiunto' % manca
    assert marchio.serve(None), 'i motivi disegnati non hanno mai marchio'


def test_il_medaglione_singolo_viene_ritagliato_via():
    """Quattro nativi hanno UN solo medaglione, e su un ritaglio non vale.

    E' il difetto trovato sul mockup della medaglietta "Green Geometric":
    ritagliata da bandana-diamanti, il medaglione del nativo e' finito sul
    bordo ed e' stato mozzato dal tondo. "Il nativo ha il marchio" e' vero per
    il nativo intero e falso per una sua porzione.
    """
    for n in marchio.NATIVI_CON_MEDAGLIONE:
        assert marchio.serve(n), (
            '%s ha un medaglione solo: va ritagliato via e il marchio ricomposto' % n)

    # il ritaglio previsto deve davvero lasciare fuori il medaglione
    s, a, d, b = marchio.RITAGLIO_SENZA_MEDAGLIONE
    ms, ma, md, mb = marchio.MEDAGLIONE
    assert d <= ms or b <= ma, (
        'il ritaglio %s non esclude il medaglione %s'
        % (marchio.RITAGLIO_SENZA_MEDAGLIONE, marchio.MEDAGLIONE))

    # un ritaglio esplicito che gia' lo esclude non va rifatto (onde-dorate)
    assert marchio.esclude_il_medaglione((0, 0, 4125, 1850), (4125, 4125)), (
        'il ritaglio storico di onde-dorate esclude gia\' il medaglione')
    assert not marchio.esclude_il_medaglione(None, (4125, 4125)), (
        'senza ritaglio il medaglione c\'e\' ancora')


def test_sta_sempre_dentro_l_area_sicura():
    """Il difetto della punta della bandana, ma per ogni tipo e ogni misura."""
    logo = marchio._marchio()
    for tipo, misura in misure_reali():
        s, a, d, b = marchio.area_sicura(tipo, misura)
        for x, y, largo, alto in marchio.riquadri(tipo, misura, logo.size):
            assert x >= s - 0.5 and y >= a - 0.5, (
                '%s %s: il marchio esce in alto/sinistra (%.0f,%.0f contro %.0f,%.0f)'
                % (tipo, misura, x, y, s, a))
            assert x + largo <= d + 0.5 and y + alto <= b + 0.5, (
                '%s %s: il marchio esce in basso/destra (%.0f,%.0f contro %.0f,%.0f)'
                % (tipo, misura, x + largo, y + alto, d, b))


def test_non_viene_mai_ingrandito():
    logo = marchio._marchio()
    for tipo, misura in misure_reali():
        for _, _, largo, alto in marchio.riquadri(tipo, misura, logo.size):
            assert largo <= logo.size[0] + 0.5, (
                '%s %s: marchio largo %.0f px da un file di %d px: e\' ingrandito'
                % (tipo, misura, largo, logo.size[0]))


def test_si_ferma_se_non_ci_sta():
    """Meglio fermarsi che stampare un marchio mozzato."""
    try:
        marchio.riquadri('medaglietta', (810, 900), (4000, 1000))
    except ValueError:
        return
    raise AssertionError('un marchio troppo largo per l\'area doveva sollevare ValueError')


def test_composto_e_ritrovato():
    """componi() lo mette, presente() lo trova, e senza non lo trova."""
    fondo = Image.new('RGB', (1200, 1300), (30, 40, 70))
    finito, box = marchio.componi(fondo, 'medaglietta')
    assert box, 'nessun riquadro disegnato'
    assert marchio.presente(finito, box), 'il marchio composto non viene ritrovato'
    assert not marchio.presente(fondo, box), (
        'presente() trova il marchio anche dove non c\'e\': non protegge niente')


def test_la_cartella_compare_solo_dove_serve():
    """Su fondo chiaro il marchio d'oro sparirebbe: serve la cartella."""
    chiaro = Image.new('RGB', (1200, 1300), (206, 178, 110))   # senape, come "laurel navy"
    scuro = Image.new('RGB', (1200, 1300), (18, 22, 34))

    def fuori_dal_logo(im, box):
        """Un punto dentro la cartella ma fuori dalla sagoma del marchio."""
        x, y, largo, alto = box[0]
        return im.convert('RGB').getpixel((round(x + largo * 0.04), round(y + alto * 0.02)))

    f_chiaro, box = marchio.componi(chiaro, 'medaglietta')
    prima = marchio._luminosita((206, 178, 110))
    dopo = marchio._luminosita(fuori_dal_logo(f_chiaro, box))
    assert dopo < prima - 40, (
        'su fondo chiaro la cartella non e\' comparsa: luminosita\' %.0f -> %.0f' % (prima, dopo))

    f_scuro, box2 = marchio.componi(scuro, 'medaglietta')
    dopo_scuro = marchio._luminosita(fuori_dal_logo(f_scuro, box2))
    assert dopo_scuro < 45, (
        'su fondo gia\' scuro la cartella e\' una toppa inutile: luminosita\' %.0f' % dopo_scuro)


def main():
    print('Dove va messo e dove no')
    prova('non si aggiunge ai motivi che lo contengono gia\'', test_non_si_aggiunge_dove_ce_gia)
    prova('si aggiunge ai tre motivi che ne sono privi', test_si_aggiunge_dove_manca)
    prova('il medaglione singolo si ritaglia via invece di fidarsene',
          test_il_medaglione_singolo_viene_ritagliato_via)

    print('\nDove cade')
    prova('sta dentro l\'area sicura di ogni tipo e ogni misura',
          test_sta_sempre_dentro_l_area_sicura)
    prova('non viene mai ingrandito oltre i suoi 1600 px', test_non_viene_mai_ingrandito)
    prova('si ferma se non ci sta invece di mozzarlo', test_si_ferma_se_non_ci_sta)

    print('\nChe si veda davvero')
    prova('composto e poi ritrovato nel file', test_composto_e_ritrovato)
    prova('la cartella compare sul chiaro e non sullo scuro',
          test_la_cartella_compare_solo_dove_serve)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
