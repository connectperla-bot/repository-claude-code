#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica il codice che SCRIVE sul catalogo vivo.

PERCHE' ESISTE
Dei dieci difetti corretti nella tornata di ROUND 47, nessuno e' stato trovato
da un test: due dal primo caricamento vero che falliva, tre guardando un
mockup o un file costruito, tre in produzione a meta' giro, uno incrociando i
dati a mano. Il catalogo era a posto perche' qualcuno l'aveva guardato, non
perche' qualcosa se ne sarebbe accorto il giorno dopo.

Questo file copre la parte piu' pericolosa: perla-usa-carica-stampe.py, che e'
l'unico pezzo del progetto che riscrive i prodotti veri su Printify.

PERCHE' SI PUO' PROVARE SENZA RETE
aree_per_variante() prende `carica` da fuori proprio per questo, e la
geometria la legge da printify-blueprints/, che e' nel repository. Quindi il
prodotto finto qui sotto usa BLUEPRINT VERI (562 Pet Bandana, provider 70) e
misure vere: se domani quel file cambia, il test se ne accorge.

USO
    python3 tests/caricamento-aree.test.py

Richiede Pillow.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(QUI, '..', 'scripts')


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


carica_stampe = _modulo('carica_stampe', os.path.join(SCRIPTS, 'perla-usa-carica-stampe.py'))
costruttore = _modulo('costruttore', os.path.join(SCRIPTS, 'perla-usa-file-stampa.py'))

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


# ==========================================================================
# IL PRODOTTO FINTO, COSTRUITO SUL CASO VERO
# ==========================================================================
# E' la bandana "Vintage Damask", quella su cui il primo caricamento e' stato
# rifiutato. Blueprint 562 / provider 70, due varianti vive (101403 e 101404,
# misure diverse) e una TERZA che il blueprint non elenca piu': la 70849
# ('25" x 12"'), ritirata dal fornitore e rimasta attaccata al prodotto.

SORGENTE = 'bandana-damask-navy-perla.jpg'


def prodotto(varianti=None, immagini=None, posizioni=('front',)):
    varianti = varianti if varianti is not None else [
        {'id': 101403, 'is_enabled': True,  'is_available': True},
        {'id': 101404, 'is_enabled': True,  'is_available': True},
        {'id': 70849,  'is_enabled': False, 'is_available': False},   # ritirata
    ]
    immagini = immagini if immagini is not None else [
        {'id': 'x', 'name': SORGENTE, 'width': 1024, 'height': 1024,
         'x': 0.5, 'y': 0.5, 'scale': 1.5}]
    return {
        'id': 'finto', 'title': 'Vintage Damask Pet Bandana — Burgundy & Gold',
        'blueprint_id': 562, 'print_provider_id': 70,
        'variants': varianti,
        'print_areas': [{
            'variant_ids': [v['id'] for v in varianti],
            'placeholders': [{'position': p, 'images': list(immagini)} for p in posizioni],
        }],
    }


class Stampe(object):
    """Sostituisce la cartella dei file costruiti con una finta.

    file_costruito() guarda il disco: senza questo il test direbbe cose
    diverse a seconda di cosa c'e' in generated-designs/, cioe' non direbbe
    niente.
    """

    def __init__(self, misure):
        self.misure = misure

    def __enter__(self):
        self.dove = tempfile.mkdtemp()
        self.prima = carica_stampe.STAMPE
        carica_stampe.STAMPE = self.dove
        for misura in self.misure:
            nome = costruttore.nome_uscita(SORGENTE, misura) + '.jpg'
            with open(os.path.join(self.dove, nome), 'wb') as fh:
                fh.write(b'x')
        return self

    def __exit__(self, *_):
        carica_stampe.STAMPE = self.prima
        shutil.rmtree(self.dove, ignore_errors=True)


def caricatore():
    """Finta `carica`: registra cosa le viene chiesto e risponde come Printify."""
    chiamate = []

    def carica(percorso):
        chiamate.append(os.path.basename(percorso))
        return {'id': 'up%d' % len(chiamate), 'file_name': os.path.basename(percorso),
                'width': 1, 'height': 1, 'mime_type': 'image/jpeg'}
    carica.chiamate = chiamate
    return carica


# ==========================================================================

def test_copre_tutte_le_varianti_anche_le_ritirate():
    """L'errore 8251: print_areas deve elencarle TUTTE, non solo le abilitate."""
    with Stampe([(4275, 2325), (3150, 1691)]):
        aree, errore = aree_per(prodotto())
    assert not errore, 'errore inatteso: %s' % errore
    coperte = set()
    for voce in aree:
        coperte |= set(voce['variant_ids'])
    assert coperte == {101403, 101404, 70849}, (
        'print_areas copre %s invece di tutte e tre le varianti del prodotto: '
        'Printify rifiuta con 8251 "Variants do not match selected blueprint"'
        % sorted(coperte))


def test_un_gruppo_per_misura_e_nessuna_variante_in_due_gruppi():
    with Stampe([(4275, 2325), (3150, 1691)]):
        aree, errore = aree_per(prodotto())
    assert not errore, errore
    assert len(aree) == 2, 'attesi 2 gruppi (le due misure), trovati %d' % len(aree)
    viste = []
    for voce in aree:
        for vid in voce['variant_ids']:
            assert vid not in viste, 'la variante %s compare in due gruppi' % vid
            viste.append(vid)


def test_ogni_immagine_a_scala_uno_e_centrata():
    """Il file E' della misura dell'area: qualunque altro valore la deforma."""
    with Stampe([(4275, 2325), (3150, 1691)]):
        aree, errore = aree_per(prodotto())
    assert not errore, errore
    for voce in aree:
        for ph in voce['placeholders']:
            for im in ph['images']:
                assert im['scale'] == 1.0 and im['x'] == 0.5 and im['y'] == 0.5, (
                    'immagine a scale=%s x=%s y=%s invece di 1 / 0,5 / 0,5'
                    % (im['scale'], im['x'], im['y']))


def test_ogni_gruppo_riceve_il_file_della_sua_misura():
    """Il difetto originale: un file solo su misure diverse."""
    with Stampe([(4275, 2325), (3150, 1691)]):
        carica = caricatore()
        aree, errore = aree_per(prodotto(), carica)
    assert not errore, errore
    assert sorted(carica.chiamate) == sorted([
        costruttore.nome_uscita(SORGENTE, (4275, 2325)) + '.jpg',
        costruttore.nome_uscita(SORGENTE, (3150, 1691)) + '.jpg',
    ]), 'file caricati: %s' % carica.chiamate


def test_si_ferma_se_manca_il_file_di_una_variante_vendibile():
    with Stampe([(4275, 2325)]):        # manca quello della 3150x1691
        aree, errore = aree_per(prodotto())
    assert aree is None and errore and 'manca il file' in errore, (
        'con un file mancante su una variante VENDIBILE bisogna fermarsi, '
        'non aggiornare a meta\'. Risposta: %s / %s' % (aree, errore))


def test_un_gruppo_senza_file_ma_senza_varianti_vendibili_si_aggrega():
    varianti = [
        {'id': 101404, 'is_enabled': True,  'is_available': True},    # 4275x2325
        {'id': 101403, 'is_enabled': False, 'is_available': False},   # 3150x1691
    ]
    with Stampe([(4275, 2325)]):        # manca quello della variante spenta
        aree, errore = aree_per(prodotto(varianti=varianti))
    assert not errore, 'non si doveva fermare: %s' % errore
    coperte = set()
    for voce in aree:
        coperte |= set(voce['variant_ids'])
    assert coperte == {101403, 101404}, (
        'la variante senza file doveva aggregarsi al gruppo piu\' grande, '
        'coperte: %s' % sorted(coperte))


def test_nessuna_variante_abilitata_non_scrive_niente():
    varianti = [{'id': 101403, 'is_enabled': False, 'is_available': False}]
    with Stampe([(4275, 2325), (3150, 1691)]):
        aree, errore = aree_per(prodotto(varianti=varianti))
    assert aree is None and 'nessuna variante abilitata' in (errore or ''), (
        'un prodotto morto non va riscritto: %s / %s' % (aree, errore))


def test_i_placeholder_vuoti_non_si_rimandano():
    """Le medagliette hanno un retro dichiarato e VUOTO. Rimandarlo fa fallire
    il PUT con "print_areas.N.placeholders.M.images: required"."""
    p = prodotto()
    p['print_areas'][0]['placeholders'].append({'position': 'back', 'images': []})
    with Stampe([(4275, 2325), (3150, 1691)]):
        aree, errore = aree_per(p)
    assert not errore, errore
    for voce in aree:
        for ph in voce['placeholders']:
            assert ph['images'], 'placeholder %s rimandato vuoto' % ph['position']


def aree_per(p, carica=None):
    return carica_stampe.aree_per_variante(
        p, 'bandana', SORGENTE, False, None, carica or caricatore())


# ==========================================================================
# DAL NOME DEL FILE ALLA SORGENTE
# ==========================================================================

def test_risale_alla_sorgente_da_tutte_le_forme_in_circolazione():
    casi = {
        'bandana-damask-navy-perla.jpg': 'bandana-damask-navy-perla.jpg',
        'bandana-da-bandana-damask-navy-perla.jpg': 'bandana-damask-navy-perla.jpg',
        'bandana-da-bandana-damask-navy-perla-4275x2325.jpg': 'bandana-damask-navy-perla.jpg',
        # con lo spazio: "Olive Branch" stampava PINATA DOLIVO.jpg, e il
        # nome del file costruito se lo porta dentro
        'bandana-da-PINATA DOLIVO-4275x2325.jpg': 'PINATA DOLIVO.jpg',
    }
    for nome, atteso in casi.items():
        avuto = carica_stampe.sorgente_del_livello(nome)
        assert avuto == atteso, '%s -> %s invece di %s' % (nome, avuto, atteso)
    assert carica_stampe.sorgente_del_livello('perla-combined-logo.png') is None
    assert carica_stampe.sorgente_del_livello(None) is None


def test_la_chiave_di_catalogo_piu_lunga_vince():
    """"Copy of Perla Italy Luxury..." combacia con due chiavi: vince la piu'
    precisa, altrimenti il duplicato stampa il file dell'originale."""
    chiave = carica_stampe.chiave_catalogo(
        'Copy of Perla Italy Luxury - Cuccia Damasco Elegante')
    assert chiave and chiave.startswith('Copy of'), (
        'scelta la chiave %r invece di quella con "Copy of"' % chiave)
    assert carica_stampe.chiave_catalogo('Titolo che non esiste') is None


def test_identifica_va_per_titolo_sulle_cucce_e_per_file_sul_resto():
    # cuccia: per titolo, perche' quattro stampano geometrici disegnati
    p = prodotto()
    p['title'] = 'Baroque Royal Pet Bed'
    identita, da_catalogo = carica_stampe.identifica(p, 'cuccia')
    assert da_catalogo is True and identita == 'Baroque Royal Pet Bed', (
        'sulla cuccia si va per titolo: %s / %s' % (identita, da_catalogo))

    # bandana: per file stampato, perche' i titoli mentono
    identita, da_catalogo = carica_stampe.identifica(prodotto(), 'bandana')
    assert da_catalogo is False and identita == SORGENTE, (
        'sulla bandana si va per file: %s / %s' % (identita, da_catalogo))


def test_i_prodotti_neutri_non_si_toccano():
    """"Crea il Tuo Design": solo il marchio, l'immagine la porta il cliente."""
    solo_logo = [{'id': 'l', 'name': 'perla-combined-logo.png',
                  'width': 1600, 'height': 2528, 'x': 0.5, 'y': 0.86, 'scale': 0.04}]
    identita, _ = carica_stampe.identifica(prodotto(immagini=solo_logo), 'bandana')
    assert identita is None, (
        'un prodotto con solo il marchio non ha un motivo da sostituire, '
        'ma identifica() ha risposto %r' % identita)


# ==========================================================================
# IL FILE TROPPO GRANDE
# ==========================================================================

def test_non_carica_mai_un_file_sopra_il_limite():
    """Prima restituiva il file comunque e Printify rispondeva
    "The POST data is too large": il prodotto restava indietro in silenzio."""
    from PIL import Image
    import random
    dove = tempfile.mkdtemp()
    try:
        # rumore: non si comprime, quindi resta sopra qualunque limite basso
        im = Image.new('RGB', (600, 600))
        random.seed(1)
        im.putdata([(random.randint(0, 255), random.randint(0, 255),
                     random.randint(0, 255)) for _ in range(600 * 600)])
        percorso = os.path.join(dove, 'grande.jpg')
        im.save(percorso, quality=95)

        prima = carica_stampe.LIMITE_MB
        carica_stampe.LIMITE_MB = 0.0005      # ~500 byte: irraggiungibile
        try:
            carica_stampe.alleggerisci(percorso)
        except RuntimeError as err:
            assert 'qualita' in str(err), 'errore poco chiaro: %s' % err
            return
        finally:
            carica_stampe.LIMITE_MB = prima
        raise AssertionError(
            'alleggerisci() ha restituito un file sopra il limite invece di '
            'sollevare: e\' il difetto della cuccia "Luxury Paisley"')
    finally:
        shutil.rmtree(dove, ignore_errors=True)


def main():
    print('print_areas per gruppo di varianti')
    prova('copre tutte le varianti, anche quelle ritirate dal blueprint',
          test_copre_tutte_le_varianti_anche_le_ritirate)
    prova('un gruppo per misura, nessuna variante in due gruppi',
          test_un_gruppo_per_misura_e_nessuna_variante_in_due_gruppi)
    prova('ogni immagine a scala 1 e centrata', test_ogni_immagine_a_scala_uno_e_centrata)
    prova('ogni gruppo riceve il file della SUA misura',
          test_ogni_gruppo_riceve_il_file_della_sua_misura)
    prova('i placeholder vuoti non si rimandano', test_i_placeholder_vuoti_non_si_rimandano)

    print('\nQuando fermarsi e quando andare avanti')
    prova('si ferma se manca il file di una variante vendibile',
          test_si_ferma_se_manca_il_file_di_una_variante_vendibile)
    prova('si aggrega se la variante senza file non e\' vendibile',
          test_un_gruppo_senza_file_ma_senza_varianti_vendibili_si_aggrega)
    prova('un prodotto senza varianti abilitate non si riscrive',
          test_nessuna_variante_abilitata_non_scrive_niente)

    print('\nCosa stampa questo prodotto')
    prova('risale alla sorgente da tutte le forme di nome',
          test_risale_alla_sorgente_da_tutte_le_forme_in_circolazione)
    prova('fra due chiavi di catalogo vince la piu\' lunga',
          test_la_chiave_di_catalogo_piu_lunga_vince)
    prova('per titolo sulle cucce, per file sul resto',
          test_identifica_va_per_titolo_sulle_cucce_e_per_file_sul_resto)
    prova('i prodotti neutri non si toccano', test_i_prodotti_neutri_non_si_toccano)

    print('\nIl file troppo grande')
    prova('non carica mai un file sopra il limite',
          test_non_carica_mai_un_file_sopra_il_limite)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
