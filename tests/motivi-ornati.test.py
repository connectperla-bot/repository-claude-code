#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le tre proprieta' che i motivi ornati devono avere, e che a occhio sfuggono.

PERCHE' PROPRIO QUESTE TRE
Sono i tre difetti trovati sul negozio il 23 agosto guardando i mockup di
tutti e 115 i prodotti. Non sono ipotesi: sono cose che i clienti vedevano.

  1. LA CUCITURA. Sulle bandane "Damask Navy" e "Green Floral" si vedeva una
     riga verticale netta a meta': due copie di un disegno affiancate, e gli
     originali non combaciavano ai bordi. Qui si misura lo stacco al punto in
     cui la piastrella si richiude e lo si confronta con la variazione interna
     del motivo. Se il salto al bordo e' piu' grande di quello che il motivo
     fa al suo interno, la cucitura si vede.

  2. IL MARCHIO TAGLIATO. "erla", "Italia" mozzato: la scritta cotta nel
     disegno cadeva dove capitava. La titolare ha scelto di tenerla, piccola
     e mai tagliata, quindi "mai tagliata" va verificato -- e va verificato su
     TUTTE le aree di stampa, perche' e' sul guinzaglio alto 219 px che una
     regola scritta pensando alla bandana si rompe.

  3. LA SCALA FISICA. Il difetto piu' caro e il meno visibile in anteprima: un
     passo in pixel buono per la bandana e' otto volte troppo grande sul
     guinzaglio. Si verifica che lo stesso motivo, chiesto a 3 cm, esca a 3 cm
     su ogni prodotto -- in centimetri, non in pixel.

Uso:  python3 tests/motivi-ornati.test.py
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


ornati = _modulo('perla_motivi_ornati', os.path.join(SCRIPTS, 'perla-motivi-ornati.py'))
scala = _modulo('perla_scala_stampa', os.path.join(SCRIPTS, 'perla-scala-stampa.py'))


# ---- 1. nessuna cucitura --------------------------------------------------

def _stacco(im, orizzontale=True):
    """Quanto saltano i pixel fra un bordo e l'altro, e quanto saltano dentro.

    Torna (bordo, interno). Se il motivo e' una piastrella vera il bordo
    destro continua nel sinistro, quindi il primo numero deve stare nello
    stesso ordine di grandezza del secondo.
    """
    px = im.convert('L').load()
    W, H = im.size
    if orizzontale:
        bordo = sum(abs(px[W - 1, y] - px[0, y]) for y in range(H)) / float(H)
        interno = sum(abs(px[x + 1, y] - px[x, y])
                      for y in range(0, H, max(1, H // 60))
                      for x in range(0, W - 1, max(1, W // 60)))
        n = len(range(0, H, max(1, H // 60))) * len(range(0, W - 1, max(1, W // 60)))
    else:
        bordo = sum(abs(px[x, H - 1] - px[x, 0]) for x in range(W)) / float(W)
        interno = sum(abs(px[x, y + 1] - px[x, y])
                      for x in range(0, W, max(1, W // 60))
                      for y in range(0, H - 1, max(1, H // 60)))
        n = len(range(0, W, max(1, W // 60))) * len(range(0, H - 1, max(1, H // 60)))
    return bordo, interno / float(max(1, n))


def test_le_piastrelle_si_richiudono():
    pal = ornati.PALETTE['navy']
    lato = 600
    for nome, fn in sorted(ornati.MOTIVI.items()):
        im = fn(lato, lato, lato / 3.0, pal)
        for verso, etichetta in ((True, 'destra-sinistra'), (False, 'sopra-sotto')):
            bordo, interno = _stacco(im, verso)
            # Tre volte la variazione interna: sotto questa soglia l'occhio non
            # trova una riga, perche' il salto al bordo non spicca su quello
            # che il motivo fa gia' da solo.
            assert bordo <= interno * 3 + 2, (
                '%s: cucitura %s, stacco al bordo %.1f contro %.1f dentro'
                % (nome, etichetta, bordo, interno))


# ---- 2. il marchio non tocca mai il bordo ---------------------------------

def test_il_marchio_non_e_mai_tagliato():
    for tipo in sorted(scala.AREE):
        a = scala.AREE[tipo]
        if a.px_w * a.px_h > 40_000_000:
            continue          # la cuccia si prova sotto, in scala
        im = Image.new('RGB', (a.px_w, a.px_h), (0, 0, 0))
        n = ornati.marchi_interi(im, tipo, colore=(255, 255, 255), opacita=1.0)
        assert n >= 1, '%s: nessun marchio stampato' % tipo
        px = im.load()
        for x in range(a.px_w):
            assert px[x, 0] == (0, 0, 0), '%s: marchio sul bordo alto' % tipo
            assert px[x, a.px_h - 1] == (0, 0, 0), '%s: marchio sul bordo basso' % tipo
        for y in range(a.px_h):
            assert px[0, y] == (0, 0, 0), '%s: marchio sul bordo sinistro' % tipo
            assert px[a.px_w - 1, y] == (0, 0, 0), '%s: marchio sul bordo destro' % tipo


def test_il_marchio_ci_sta_anche_sul_pezzo_piu_stretto():
    """Il guinzaglio e' alto 219 px: e' li' che una regola pensata sulla
    bandana si rompe, ed e' li' che va guardato."""
    im = Image.new('RGB', (12389, 219), (0, 0, 0))
    n = ornati.marchi_interi(im, 'guinzaglio-eu', colore=(255, 255, 255), opacita=1.0)
    assert n >= 1, 'sul guinzaglio non entra nessun marchio'


# ---- 3. la scala e' fisica, non in pixel ----------------------------------

def test_lo_stesso_motivo_esce_della_stessa_misura_reale():
    for cm in (2.0, 3.0):
        for tipo in sorted(scala.AREE):
            px = scala.passo_px(tipo, cm)
            reale = px / scala.px_per_cm(tipo)
            assert abs(reale - cm) < 0.01, (
                '%s: chiesti %.1f cm, tornati %.2f' % (tipo, cm, reale))


def test_il_passo_troppo_grande_viene_ridotto():
    """La protezione contro il difetto che sul prodotto non si corregge piu':
    il medaglione gigante sul collare alto 2,5 cm."""
    for tipo in ('collare-eu', 'guinzaglio-eu', 'medaglietta-usa'):
        enorme = scala.AREE[tipo].px_h * 4
        sicuro = scala.passo_sicuro(tipo, enorme)
        assert scala.ripetizioni(tipo, sicuro) >= scala.RIPETIZIONI_MINIME - 1e-6, (
            '%s: %0.1f ripetizioni, ne servono %0.1f'
            % (tipo, scala.ripetizioni(tipo, sicuro), scala.RIPETIZIONI_MINIME))


def test_un_passo_che_ci_sta_non_viene_toccato():
    """La riduzione deve scattare solo dove serve: se accorciasse anche i passi
    buoni, ogni motivo uscirebbe piu' fitto del disegnato."""
    passo = scala.AREE['bandana-eu'].px_h / 12.0
    assert scala.passo_sicuro('bandana-eu', passo) == passo


# ---- 4. niente specchiamenti, come nella famiglia geometrica --------------

def test_nessun_flip_nel_sorgente():
    """Stessa guardia di file-stampa-non-specchiati.test.py: su un motivo che
    contiene il marchio, specchiare stampa il nome rovesciato."""
    testo = open(os.path.join(SCRIPTS, 'perla-motivi-ornati.py'), encoding='utf-8').read()
    codice = '\n'.join(r for r in testo.split('\n')
                       if not r.strip().startswith('#'))
    for vietato in ('FLIP_LEFT_RIGHT', 'FLIP_TOP_BOTTOM', 'ImageOps.mirror',
                    'ImageOps.flip', 'transpose('):
        assert vietato not in codice, 'specchiamento nel sorgente: %s' % vietato


def main():
    print('\nLe piastrelle si richiudono')
    prova('nessuna cucitura visibile, su tutti e nove i motivi', test_le_piastrelle_si_richiudono)

    print('\nIl marchio')
    prova('non tocca mai il bordo, su ogni area di stampa', test_il_marchio_non_e_mai_tagliato)
    prova('entra anche sul guinzaglio, alto 219 px', test_il_marchio_ci_sta_anche_sul_pezzo_piu_stretto)
    prova('niente specchiamenti: rovescerebbero il nome', test_nessun_flip_nel_sorgente)

    print('\nLa scala e\' in centimetri, non in pixel')
    prova('lo stesso motivo esce della stessa misura reale ovunque', test_lo_stesso_motivo_esce_della_stessa_misura_reale)
    prova('il passo troppo grande per il pezzo viene ridotto', test_il_passo_troppo_grande_viene_ridotto)
    prova('un passo che ci sta non viene toccato', test_un_passo_che_ci_sta_non_viene_toccato)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
