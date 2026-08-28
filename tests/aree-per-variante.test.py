#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica che nessuna variante resti con una fascia vuota o col disegno tagliato.

PERCHE' ESISTE
Il catalogo americano e' arrivato a 66 prodotti rotti su 70 per un difetto
che NON si vedeva guardando il prodotto: perla-usa-carica-stampe.py scriveva
UNA voce print_areas con dentro tutte le varianti, e su Printify `scale` e' la
larghezza come frazione dell'AREA. Le varianti pero' hanno proporzioni diverse:

    collare S 5764x229 (25,2:1)   contro XL 9519x338 (28,2:1)
    cuccia 28"x18" 8850x5850 (1,51) contro 50"x40" 15600x12600 (1,24)

Il file costruito per la variante grande, messo a scale=1, sul collare M
lasciava il 24% di fettuccia bianca e sulla cuccia 28"x18" tagliava il 18% del
disegno. Sulla variante per cui il file era stato costruito era perfetto: e'
per questo che e' rimasto in catalogo per tre tornate di riparazioni.

PERCHE' COSI'
Non si prova che "il codice fa quello che fa": si prova l'INVARIANTE, cioe'
che per ogni variante di ogni blueprint del repository il file previsto copra
l'area esatta. E si prova anche il contrario -- che il metodo vecchio, un
solo file per tutte, su questi stessi dati fallisce -- altrimenti un test che
passa non direbbe niente.

USO
    python3 tests/aree-per-variante.test.py
"""
import glob
import importlib.util
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(QUI, '..', 'scripts')


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def blueprint_disponibili():
    """I blueprint versionati che hanno davvero delle varianti."""
    fuori = []
    for percorso in sorted(glob.glob(os.path.join(QUI, '..', 'printify-blueprints', '*.json'))):
        base = os.path.basename(percorso)[:-5]
        if '_' not in base:
            continue
        bp, pr = base.split('_', 1)
        with open(percorso) as fh:
            if not json.load(fh).get('variants'):
                continue      # 254_70.json e' salvato vuoto
        fuori.append((int(bp), int(pr)))
    return fuori


# ==========================================================================

def test_ogni_variante_finisce_in_un_gruppo():
    for bp, pr in blueprint_disponibili():
        elenco = aree.varianti(bp, pr)
        for posizione in aree.posizioni(elenco):
            con_quella_posizione = {v['id'] for v in elenco
                                    if posizione in v['placeholders']}
            raccolte = set()
            for g in aree.gruppi(elenco, posizione):
                assert not (raccolte & set(g['variant_ids'])), (
                    'blueprint %s: la variante compare in due gruppi' % bp)
                raccolte |= set(g['variant_ids'])
            assert raccolte == con_quella_posizione, (
                'blueprint %s posizione %s: %d varianti su %d finiscono in un gruppo'
                % (bp, posizione, len(raccolte), len(con_quella_posizione)))


def test_il_file_del_gruppo_copre_esatto():
    """Un file costruito alla misura del gruppo: zero vuoto, zero taglio."""
    for bp, pr in blueprint_disponibili():
        elenco = aree.varianti(bp, pr)
        for posizione in aree.posizioni(elenco):
            for g in aree.gruppi(elenco, posizione):
                c = aree.copertura(g['misura'], g['misura'], 0.5, 0.5, 1.0)
                assert c['vuoto'] < 1e-9, (
                    'blueprint %s misura %s: fascia vuota %.4f' % (bp, g['misura'], c['vuoto']))
                assert c['taglio'] < 1e-9, (
                    'blueprint %s misura %s: taglio %.4f' % (bp, g['misura'], c['taglio']))
                assert abs(c['ingrandimento'] - 1.0) < 1e-9, (
                    'blueprint %s misura %s: ingrandimento %.4f'
                    % (bp, g['misura'], c['ingrandimento']))


def test_il_metodo_vecchio_su_questi_dati_fallisce():
    """La prova che il test sopra non e' una tautologia.

    Se un giorno si torna a scrivere un solo file per tutte le varianti,
    questo test dice esattamente quanto si perde. Deve fallire su almeno un
    blueprint reale, altrimenti vuol dire che i dati non contengono piu' il
    caso che stiamo prevenendo e il test va rivisto.
    """
    rotti = []
    for bp, pr in blueprint_disponibili():
        elenco = aree.varianti(bp, pr)
        for posizione in aree.posizioni(elenco):
            gruppi = aree.gruppi(elenco, posizione)
            if len(gruppi) < 2:
                continue
            piu_grande = gruppi[0]['misura']
            for g in gruppi[1:]:
                c = aree.copertura(g['misura'], piu_grande, 0.5, 0.5, 1.0)
                if c['vuoto'] > 0.01 or c['taglio'] > 0.02:
                    rotti.append((bp, g['misura'], c['vuoto'], c['taglio']))
    assert rotti, ("nessun blueprint mostra piu' il difetto del file unico: "
                   "o i dati sono cambiati, o questo test non protegge piu' niente")
    for bp, misura, vuoto, taglio in rotti:
        print('       (con un file solo: blueprint %s su %dx%d -> %.0f%% vuoto, %.0f%% tagliato)'
              % (bp, misura[0], misura[1], vuoto * 100, taglio * 100))


def test_la_copertura_misura_quello_che_dice():
    """Casi calcolati a mano, per non fidarsi della funzione sulla parola."""
    # immagine larga il doppio dell'area e alta uguale: meta' esce dai lati
    c = aree.copertura((100, 100), (200, 100), 0.5, 0.5, 2.0)
    assert abs(c['vuoto']) < 1e-9, 'copre tutto: vuoto %.4f' % c['vuoto']
    assert abs(c['taglio'] - 0.5) < 1e-9, "meta' fuori: taglio %.4f" % c['taglio']

    # immagine larga come l'area ma alta la meta': resta meta' area scoperta
    c = aree.copertura((100, 100), (200, 100), 0.5, 0.5, 1.0)
    assert abs(c['vuoto'] - 0.5) < 1e-9, "meta' scoperta: vuoto %.4f" % c['vuoto']
    assert abs(c['taglio']) < 1e-9, 'niente esce: taglio %.4f' % c['taglio']

    # il caso vero del collare M, quello che ha rotto il catalogo
    c = aree.copertura((7257, 338), (9519, 338), 0.5, 0.5, 1.0)
    assert 0.23 < c['vuoto'] < 0.25, 'collare M: atteso ~24%% di vuoto, misurato %.3f' % c['vuoto']


def test_scala_per_coprire_toglie_il_vuoto():
    for area, immagine in (((7257, 338), (9519, 338)), ((8850, 5850), (15600, 12600))):
        s = aree.scala_per_coprire(area, immagine)
        c = aree.copertura(area, immagine, 0.5, 0.5, s)
        assert c['vuoto'] < 1e-6, ('scala_per_coprire lascia %.4f di vuoto su %s'
                                   % (c['vuoto'], (area, immagine)))


def main():
    print('Raggruppamento delle varianti')
    prova('ogni variante finisce in uno e un solo gruppo', test_ogni_variante_finisce_in_un_gruppo)

    print('\nCopertura')
    prova('la copertura misura quello che dice', test_la_copertura_misura_quello_che_dice)
    prova('il file del gruppo copre l\'area esatta', test_il_file_del_gruppo_copre_esatto)
    prova('scala_per_coprire toglie davvero il vuoto', test_scala_per_coprire_toglie_il_vuoto)

    print('\nProva che il test protegga qualcosa')
    prova('col metodo vecchio questi stessi dati falliscono',
          test_il_metodo_vecchio_su_questi_dati_fallisce)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
