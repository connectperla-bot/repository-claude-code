#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica i verdetti dell'audit. L'audit ha gia' sbagliato una volta.

PERCHE' ESISTE
perla-verifica-prodotti.py e' il metro con cui si decide se il catalogo e'
sano. Se sbaglia lui, tutto il resto e' costruito sulla sabbia -- e ha gia'
sbagliato: alla prima esecuzione dava "marchio fuori dall'area" su diciotto
collari. Non era vero. Quei prodotti non hanno NESSUNA variante abilitata,
quindi non c'era nemmeno una variante su cui misurare dove cade il marchio: il
ciclo girava a vuoto, marchi_dentro restava zero, e il verdetto usciva lo
stesso. Se ne e' accorto un incrocio fatto a mano, non un test.

I prodotti finti qui sotto usano BLUEPRINT VERI presi da
printify-blueprints/, quindi le misure sono quelle di produzione.

USO
    python3 tests/audit-verdetti.test.py
"""
import importlib.util
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(QUI, '..', 'scripts')


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit = _modulo('audit', os.path.join(SCRIPTS, 'perla-verifica-prodotti.py'))

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


# La bandana vera: blueprint 562 provider 70, misure 4275x2325 e 3150x1691.
def bandana(immagini, varianti=None, aree_separate=False):
    varianti = varianti if varianti is not None else [
        {'id': 101403, 'is_enabled': True, 'is_available': True},
        {'id': 101404, 'is_enabled': True, 'is_available': True},
    ]
    ids = [v['id'] for v in varianti]
    if aree_separate:
        # come le scrive perla-usa-carica-stampe.py: una voce per misura
        misure = {101404: (4275, 2325), 101403: (3150, 1691)}
        aree = [{'variant_ids': [i],
                 'placeholders': [{'position': 'front', 'images': [
                     dict(im, width=misure[i][0], height=misure[i][1])
                     for im in immagini]}]}
                for i in ids if i in misure]
    else:
        aree = [{'variant_ids': ids,
                 'placeholders': [{'position': 'front', 'images': list(immagini)}]}]
    return {'id': 'finto', 'title': 'Bandana di prova',
            'blueprint_id': 562, 'print_provider_id': 70,
            'external': {'id': '123'}, 'variants': varianti, 'print_areas': aree}


def esamina(p, manifesto=None):
    return audit.esamina(p, None, {}, manifesto or {})


FILE_GIUSTO = {'id': 'a', 'name': 'bandana-da-x-4275x2325.jpg',
               'width': 4275, 'height': 2325, 'x': 0.5, 'y': 0.5, 'scale': 1.0}


# ==========================================================================

def test_senza_varianti_abilitate_nessun_verdetto_inventato():
    """IL FALSO POSITIVO DEI COLLARI, in forma di test."""
    spente = [{'id': 101403, 'is_enabled': False, 'is_available': False},
              {'id': 101404, 'is_enabled': False, 'is_available': False}]
    logo = {'id': 'l', 'name': 'perla-combined-logo.png', 'width': 1600,
            'height': 2528, 'x': 0.5, 'y': 0.86, 'scale': 0.04}
    difetti, _ = esamina(bandana([logo], varianti=spente))
    assert any('nessuna variante abilitata' in d for d in difetti), (
        'un prodotto morto va detto: %s' % difetti)
    for parola in ('marchio', 'tagliato', 'fascia vuota', 'sgranato'):
        assert not any(parola in d for d in difetti), (
            'verdetto "%s" su un prodotto senza NESSUNA variante da misurare: '
            'e\' il falso positivo dei diciotto collari. Difetti: %s'
            % (parola, difetti))


def test_un_file_giusto_non_da_nessun_difetto():
    manifesto = {'bandana-da-x-4275x2325.jpg': 'composto',
                 'bandana-da-x-3150x1691.jpg': 'composto'}
    difetti, _ = esamina(bandana([FILE_GIUSTO], aree_separate=True), manifesto)
    assert not difetti, 'un prodotto a posto non deve avere difetti: %s' % difetti


def test_riconosce_il_difetto_originale():
    """Un file solo, della misura grande, su tutte le varianti."""
    difetti, _ = esamina(bandana([FILE_GIUSTO]), {'bandana-da-x-4275x2325.jpg': 'composto'})
    assert any('una sola area' in d for d in difetti), (
        'un print_areas solo per due misure diverse va segnalato: %s' % difetti)


def test_riconosce_lo_sgranato():
    """Una variante sola, cosi' il verdetto non si confonde con "una sola area"."""
    una = [{'id': 101404, 'is_enabled': True, 'is_available': True}]
    piccolo = dict(FILE_GIUSTO, width=1280, height=720)
    difetti, _ = esamina(bandana([piccolo], varianti=una),
                         {'bandana-da-x-4275x2325.jpg': 'composto'})
    assert any('sgranato' in d for d in difetti), (
        'un file 1280x720 su un\'area 4275x2325 e\' ingrandito 3 volte: %s' % difetti)


def test_riconosce_un_riferimento_morto():
    """Un livello senza nome: Printify rifiuta l'aggiornamento con
    "Provided images do not exist" finche' glielo si rimanda."""
    senza_nome = {'id': 'morto', 'width': 566, 'height': 147,
                  'x': 0.5, 'y': 0.5, 'scale': 1.0}
    difetti, _ = esamina(bandana([FILE_GIUSTO, senza_nome], aree_separate=True))
    assert any('riferimento morto' in d for d in difetti), (
        'un livello senza nome va segnalato: %s' % difetti)


def test_il_marchio_dentro_il_file_non_e_marchio_mancante():
    """Da ROUND 47 il marchio non e' piu' un LIVELLO. Contare i livelli
    direbbe "senza marchio" su tutto il catalogo appena riparato."""
    manifesto = {'bandana-da-x-4275x2325.jpg': 'composto',
                 'bandana-da-x-3150x1691.jpg': 'composto'}
    difetti, _ = esamina(bandana([FILE_GIUSTO], aree_separate=True), manifesto)
    assert not any('senza marchio' in d for d in difetti), (
        'il marchio e\' nel file secondo il manifesto: %s' % difetti)

    # e senza manifesto vale la convenzione "-perla.jpg" degli artwork originali
    artwork = dict(FILE_GIUSTO, name='bandana-damask-navy-perla.jpg')
    difetti, _ = esamina(bandana([artwork], aree_separate=True))
    assert not any('senza marchio' in d for d in difetti), (
        'gli artwork "-perla.jpg" hanno il marchio dentro: %s' % difetti)


def test_senza_marchio_da_nessuna_parte_lo_dice():
    nudo = dict(FILE_GIUSTO, name='motivo-qualunque.jpg')
    difetti, _ = esamina(bandana([nudo], aree_separate=True))
    assert any('senza marchio' in d for d in difetti), (
        'nessun marchio ne\' nel motivo ne\' come livello: %s' % difetti)


def test_il_marchio_fuori_dal_bordo_si_vede():
    """Su diciotto prodotti il livello c'era ma stava FUORI dall'area
    (x=-0,084, y=1,044 sulla cuccia "Geometric Tribal")."""
    fuori = {'id': 'l', 'name': 'perla-combined-logo.png', 'width': 1600,
             'height': 2528, 'x': -0.084, 'y': 1.044, 'scale': 0.1}
    nudo = dict(FILE_GIUSTO, name='motivo-qualunque.jpg')
    difetti, _ = esamina(bandana([nudo, fuori], aree_separate=True))
    assert any('marchio fuori' in d for d in difetti), (
        'un marchio fuori dal bordo c\'e\' nei dati e non si stampa: %s' % difetti)


# ==========================================================================
# CIO' CHE E' GIA' DECISO
# ==========================================================================

def test_noto_riconosce_archiviati_e_neutri_dai_dati():
    spente = [{'id': 101403, 'is_enabled': False, 'is_available': False}]
    p = bandana([FILE_GIUSTO], varianti=spente)
    assert audit.noto(p, ['qualcosa']) and 'archiviato' in audit.noto(p, ['x']), (
        'un prodotto senza varianti abilitate e\' archiviato, non rotto')

    logo = {'id': 'l', 'name': 'perla-combined-logo.png', 'width': 1600,
            'height': 2528, 'x': 0.5, 'y': 0.5, 'scale': 0.04}
    neutro = bandana([logo])
    assert audit.noto(neutro, ['x']) and 'neutro' in audit.noto(neutro, ['x']), (
        '"Crea il Tuo Design" ha solo il marchio di proposito')

    # un prodotto normale con un difetto vero NON e' un caso noto
    nudo = dict(FILE_GIUSTO, name='motivo-qualunque.jpg')
    assert audit.noto(bandana([nudo]), ['senza marchio']) is None, (
        'un difetto vero non va nascosto fra i casi noti')


def test_le_categorie_raggruppano_le_percentuali():
    a = audit.categoria('tagliato fino al 18% del disegno')
    b = audit.categoria('tagliato fino al 5% del disegno')
    assert a == b, ('due percentuali diverse dello stesso difetto devono finire '
                    'nella stessa riga del riepilogo: %r / %r' % (a, b))


def main():
    print('Verdetti')
    prova('senza varianti abilitate non inventa verdetti',
          test_senza_varianti_abilitate_nessun_verdetto_inventato)
    prova('un file giusto non da\' nessun difetto', test_un_file_giusto_non_da_nessun_difetto)
    prova('riconosce il difetto originale (una sola area per due misure)',
          test_riconosce_il_difetto_originale)
    prova('riconosce lo sgranato', test_riconosce_lo_sgranato)
    prova('riconosce un riferimento morto', test_riconosce_un_riferimento_morto)

    print('\nIl marchio')
    prova('il marchio dentro il file non e\' marchio mancante',
          test_il_marchio_dentro_il_file_non_e_marchio_mancante)
    prova('senza marchio da nessuna parte lo dice', test_senza_marchio_da_nessuna_parte_lo_dice)
    prova('il marchio fuori dal bordo si vede', test_il_marchio_fuori_dal_bordo_si_vede)

    print('\nCio\' che e\' gia\' deciso')
    prova('noto() riconosce archiviati e neutri dai dati',
          test_noto_riconosce_archiviati_e_neutri_dai_dati)
    prova('le categorie raggruppano le percentuali', test_le_categorie_raggruppano_le_percentuali)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
