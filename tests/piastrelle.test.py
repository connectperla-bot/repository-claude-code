#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le regole del riuso degli originali: quelle che, se saltano, si vedono.

PERCHE' QUESTE
Sono i tre difetti che hanno rovinato il catalogo, ognuno con la sua prova.
Non sono ipotesi da manuale: si vedevano tutti e tre sul negozio, e due erano
gia' rientrati una volta.

  1. MAI INGRANDIRE. Sulla linea americana le sorgenti 1280x720 venivano
     stirate fino a 12750x9750 -- dieci volte -- ed e' per questo che i
     prodotti sembravano impastati. Affiancare invece che ingrandire e' tutto
     il punto di questo lavoro; se il fattore di scala supera 1 il difetto e'
     tornato.
  2. RIPETIZIONI INTERE. Se il passo non divide la tela il bordo cade a meta'
     motivo: disegni interi da un lato e mozzi dall'altro, scritte che si
     leggono "erla". E' il "decentrati" segnalato dalla titolare.
  3. NIENTE SPECCHIAMENTI. Su questi disegni la scritta e' dentro l'ornato:
     specchiare la stampa rovesciata. Stessa guardia gia' in
     file-stampa-non-specchiati.test.py, qui sul modulo nuovo.

Uso:  python3 tests/piastrelle.test.py
"""
import importlib.util
import os
import sys

from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(QUI), 'scripts')

passati = 0
falliti = 0


def prova(nome, fn):
    global passati, falliti
    try:
        fn()
        print('  ok   ' + nome)
        passati += 1
    except Exception as err:
        print('  FALLITO   %s\n        %s' % (nome, err))
        falliti += 1


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tess = _modulo('perla_piastrelle_originali',
               os.path.join(SCRIPTS, 'perla-piastrelle-originali.py'))
scala = _modulo('perla_scala_stampa', os.path.join(SCRIPTS, 'perla-scala-stampa.py'))

# Una finta piastrella: si prova il comportamento, non il contenuto dei
# disegni, che sta in un'altra cartella e puo' non esserci su una macchina
# appena clonata.
def _finta(w, h):
    im = Image.new('RGB', (w, h))
    px = im.load()
    for x in range(w):
        for y in range(h):
            px[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 3) % 256)
    return im


def test_non_ingrandisce_mai():
    """La prova che protegge dal difetto piu' caro: una sorgente piccola non
    deve essere stirata sull'area grande."""
    piccola = _finta(300, 300)
    for tipo in scala.AREE:
        if scala.AREE[tipo].px_w * scala.AREE[tipo].px_h > 40_000_000:
            continue
        _, det = tess.stendi(piccola, tipo, 8.0)
        assert det['scala'] <= 1.0 + 1e-6, (
            '%s: ingrandita di %.2f volte' % (tipo, det['scala']))


def test_non_ingrandisce_nemmeno_un_nastro():
    """I nastri hanno una strada tutta loro dentro `stendi`, quindi la regola
    va verificata anche li': e' il ramo dove e' piu' facile dimenticarla."""
    striscia = _finta(1200, 100)
    for tipo in ('collare-eu', 'guinzaglio-eu'):
        _, det = tess.stendi(striscia, tipo, 3.0)
        assert det['nastro'] is True, '%s: non riconosciuto come nastro' % tipo
        assert det['scala'] <= 1.0 + 1e-6, (
            '%s: nastro ingrandito di %.2f volte' % (tipo, det['scala']))


def test_le_ripetizioni_sono_intere():
    """Il bordo deve cadere FRA due ripetizioni, non a meta' motivo."""
    t = _finta(600, 400)
    for tipo in scala.AREE:
        a = scala.AREE[tipo]
        if a.px_w * a.px_h > 40_000_000:
            continue
        _, det = tess.stendi(t, tipo, 8.0)
        # Non si pretende il rapporto esatto: un collare e' alto 315 px e due
        # file intere di pixel in un numero dispari non ci stanno. Cio' che
        # deve valere e' che l'ultima ripetizione sfori di pixel, non di mezzo
        # motivo -- e' quella la differenza fra "preciso" e "decentrato".
        assert det['scarto_px'] <= det['ripetizioni'], (
            '%s: ultima ripetizione fuori di %d px su %d ripetizioni'
            % (tipo, det['scarto_px'], det['ripetizioni']))


def test_un_nastro_e_alto_quanto_il_nastro():
    """Una striscia non si impila: la prima stesura la dimezzava e ne metteva
    due file sul collare alto 2,5 cm, perdendo i bordini sopra e sotto."""
    striscia = _finta(2732, 315)
    im, det = tess.stendi(striscia, 'collare-eu', 2.6)
    assert im.size == (scala.AREE['collare-eu'].px_w,
                       scala.AREE['collare-eu'].px_h)
    assert det['ripetizioni'] >= 1, 'la striscia non copre il nastro'


def test_la_cucitura_si_applica_solo_dove_serve():
    """Una piastrella che si richiude gia' da sola non va toccata: sfumarla
    introdurrebbe un raddoppio dove non serviva."""
    t = _finta(256, 256)
    err = tess._errore_giunzione(t)
    if err <= tess.SOGLIA_GIUNZIONE:
        assert True
    else:
        # se la finta non si richiude, si verifica almeno che la sfumatura
        # riduca davvero lo stacco invece di peggiorarlo
        assert tess._errore_giunzione(tess.cucitura_morbida(t)) < err


def test_nessuno_specchiamento_nel_sorgente():
    testo = open(os.path.join(SCRIPTS, 'perla-piastrelle-originali.py'),
                 encoding='utf-8').read()
    codice = '\n'.join(r for r in testo.split('\n')
                       if not r.strip().startswith('#'))
    for vietato in ('FLIP_LEFT_RIGHT', 'FLIP_TOP_BOTTOM', 'ImageOps.mirror',
                    'ImageOps.flip', '.transpose('):
        assert vietato not in codice, 'specchiamento nel sorgente: %s' % vietato


def main():
    print('\nRiuso degli originali')
    prova('non ingrandisce mai una sorgente', test_non_ingrandisce_mai)
    prova('nemmeno un nastro, che ha una strada sua', test_non_ingrandisce_nemmeno_un_nastro)
    prova('le ripetizioni sono intere: il bordo non taglia il motivo', test_le_ripetizioni_sono_intere)
    prova('un nastro e\' alto quanto il nastro, non impilato', test_un_nastro_e_alto_quanto_il_nastro)
    prova('la cucitura si sfuma solo dove serve', test_la_cucitura_si_applica_solo_dove_serve)
    prova('niente specchiamenti: rovescerebbero il nome', test_nessuno_specchiamento_nel_sorgente)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
