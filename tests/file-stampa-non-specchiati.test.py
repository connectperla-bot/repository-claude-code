#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica che i file di stampa non contengano tasselli ribaltati.

PERCHE' ESISTE
Alla titolare sono arrivate quattro bandane con il marchio "PERLA ITALIA"
capovolto e riflesso. La causa era in perla-build-eu-print-files.py: file e
colonne alterne venivano specchiate (FLIP_TOP_BOTTOM / FLIP_LEFT_RIGHT) per
far combaciare i bordi. Su una texture astratta e' il metodo giusto; su questi
motivi, che contengono una scritta, stampa il marchio a rovescio.

PERCHE' COSI'
Guardare le statistiche dell'immagine finita non basta: su un damascato fitto
un tassello ribaltato somiglia moltissimo a uno dritto, e la misura non
distingue (provato). Qui si costruisce invece una sorgente sintetica con un
segno palesemente asimmetrico -- una L nera nell'angolo in alto a sinistra --
e si controlla dove finisce in ogni tassello dell'uscita. Se qualcuno domani
reintroduce uno specchiamento, la L compare capovolta e il test fallisce.

USO
    python3 tests/file-stampa-non-specchiati.test.py

Richiede Pillow.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scripts'))

import importlib.util

_MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'scripts', 'perla-build-eu-print-files.py')
_spec = importlib.util.spec_from_file_location('costruttore', _MOD)
costruttore = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(costruttore)

passati = 0
falliti = 0


def prova(descrizione, fn):
    global passati, falliti
    try:
        fn()
        passati += 1
        print('  ok   ' + descrizione)
    except AssertionError as err:
        falliti += 1
        print('  FALLITO   ' + descrizione)
        print('        ' + str(err))
    except Exception as err:
        # un errore imprevisto e' un fallimento come gli altri: il runner deve
        # arrivare in fondo e dire quante prove sono andate male, non morire
        # sulla prima
        falliti += 1
        print('  ERRORE    ' + descrizione)
        print('        %s: %s' % (type(err).__name__, err))


def sorgente_con_segno(larghezza, altezza, trim, ripetizioni=1):
    """Striscia chiara con una L nera, ripetuta `ripetizioni` volte.

    Il trim di costruisci() taglia `trim` pixel sopra e sotto, quindi il segno
    va disegnato dentro quello che resta, o sparisce prima di essere ripetuto.

    Con ripetizioni > 1 la striscia diventa periodica come lo sono i motivi
    veri (misurato sulle sei sorgenti reali: si ripetono con uno scarto fra
    0,22 e 0,60 su 255), e costruisci() puo' allineare la giunzione al periodo.
    """
    im = Image.new('RGB', (larghezza, altezza), (230, 230, 230))
    px = im.load()
    alto = trim + 2
    basso = altezza - trim - 2
    utile = basso - alto
    braccio_v = max(4, utile // 2)
    braccio_o = max(4, larghezza // (20 * ripetizioni))
    periodo = larghezza // ripetizioni
    for r in range(ripetizioni):
        x0 = r * periodo + 4
        for y in range(alto, alto + braccio_v):      # asta verticale della L
            for x in range(x0, x0 + max(2, braccio_o // 6)):
                px[x, y] = (0, 0, 0)
        y0 = alto + braccio_v
        for y in range(y0, min(basso, y0 + max(2, utile // 8))):   # piede della L
            for x in range(x0, x0 + braccio_o):
                px[x, y] = (0, 0, 0)
    return im


def segni(im, soglia=110):
    """Trova ogni occorrenza del segno e ne restituisce l'orientamento.

    Non si assume dove i tasselli cadano: si cercano le macchie scure ovunque
    siano finite. Per ognuna si confronta il baricentro con il centro del suo
    rettangolo. La L ha l'asta in alto a sinistra e il piede in basso: il
    baricentro sta dunque a sinistra del centro e sotto di esso. Se un tassello
    e' stato ribaltato, uno dei due segni si inverte -- ed e' esattamente il
    difetto che si vuole impedire.
    """
    g = im.convert('L')
    w, h = g.size
    dati = g.load()
    visto = [[False] * w for _ in range(h)]
    trovati = []

    for y0 in range(h):
        for x0 in range(w):
            if dati[x0, y0] >= soglia or visto[y0][x0]:
                continue
            # riempimento iterativo: niente ricorsione, le macchie possono
            # essere grandi e Python ha un limite di profondita' basso
            pila = [(x0, y0)]
            visto[y0][x0] = True
            punti = []
            while pila:
                x, y = pila.pop()
                punti.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not visto[ny][nx] \
                            and dati[nx, ny] < soglia:
                        visto[ny][nx] = True
                        pila.append((nx, ny))
            if len(punti) < 40:
                continue                       # rumore, non il segno
            xs = [p[0] for p in punti]
            ys = [p[1] for p in punti]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            centro_x = (min(xs) + max(xs)) / 2.0
            centro_y = (min(ys) + max(ys)) / 2.0
            tocca_bordo = min(xs) == 0 or min(ys) == 0 or max(xs) == w - 1 or max(ys) == h - 1
            trovati.append({
                'x': min(xs), 'y': min(ys),
                'verso_x': 'sinistra' if cx < centro_x else 'destra',
                'verso_y': 'basso' if cy > centro_y else 'alto',
                'tagliato': tocca_bordo,
            })
    return trovati


def _costruisci_da(sorgente, larghezza, altezza, trim, feather):
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '.sorgente-prova.png')
    sorgente.save(percorso)
    try:
        return costruttore.costruisci(percorso, larghezza, altezza,
                                      trim=trim, feather=feather)
    finally:
        if os.path.exists(percorso):
            os.remove(percorso)


def test_tasselli_tutti_nello_stesso_verso():
    """Su un motivo periodico ogni segno resta intero e nello stesso verso.

    E' il caso dei sei motivi veri. La tela e' abbastanza larga e alta da
    richiedere piu' colonne E piu' righe di tasselli.
    """
    trim = 14
    sorgente = sorgente_con_segno(600, 200, trim, ripetizioni=3)
    out = _costruisci_da(sorgente, 1800, 520, trim, 20)

    # i segni tranciati dal bordo dell'area hanno un rettangolo incompleto,
    # quindi il confronto col centro non direbbe nulla: si scartano
    marchi = [m for m in segni(out) if not m['tagliato']]

    assert len(marchi) >= 6, (
        'attese almeno 6 occorrenze intere del segno, trovate %d' % len(marchi))

    versi_x = set(m['verso_x'] for m in marchi)
    versi_y = set(m['verso_y'] for m in marchi)

    assert versi_x == {'sinistra'}, (
        'il segno punta in direzioni diverse: %s. Una colonna e\' specchiata '
        '(FLIP_LEFT_RIGHT). Occorrenze: %s'
        % (sorted(versi_x), [(m['x'], m['y'], m['verso_x']) for m in marchi]))
    assert versi_y == {'basso'}, (
        'il segno e\' capovolto in qualche tassello: %s. Una riga e\' '
        'ribaltata (FLIP_TOP_BOTTOM). Occorrenze: %s'
        % (sorted(versi_y), [(m['x'], m['y'], m['verso_y']) for m in marchi]))


def test_motivo_non_periodico_resta_intatto():
    """Senza periodo la giunzione e' netta, ma il disegno non viene toccato.

    E' la scelta di fondo di questa correzione: non si altera mai l'artwork
    per nascondere una giunzione. Ne' specchiandolo (stampava il marchio
    capovolto) ne' dissolvendolo -- provato, con una dissolvenza di 20px un
    segno a cavallo della giunzione perde meta' delle sue forme e arriva
    mutilato. Qui si verifica che ogni occorrenza sia intera e dritta anche
    su questo ramo.
    """
    trim = 14
    sorgente = sorgente_con_segno(600, 200, trim, ripetizioni=1)
    out = _costruisci_da(sorgente, 1800, 520, trim, 20)

    marchi = [m for m in segni(out) if not m['tagliato']]
    assert len(marchi) >= 3, \
        'attese almeno 3 occorrenze intere, trovate %d' % len(marchi)

    versi_x = set(m['verso_x'] for m in marchi)
    versi_y = set(m['verso_y'] for m in marchi)
    assert versi_x == {'sinistra'} and versi_y == {'basso'}, (
        'il segno e\' stato alterato dalla giunzione: x=%s y=%s. Occorrenze: %s'
        % (sorted(versi_x), sorted(versi_y),
           [(m['x'], m['y'], m['verso_x'], m['verso_y']) for m in marchi]))


def test_riconoscimento_del_periodo():
    """Il periodo si trova quando c'e' e non si inventa quando non c'e'."""
    trim = 14
    periodico = sorgente_con_segno(600, 200, trim, ripetizioni=3)
    p = costruttore._periodo_orizzontale(periodico.crop((0, trim, 600, 200 - trim)))
    assert p is not None, 'periodo non riconosciuto su una striscia periodica'
    assert abs(p - 200) <= 4, 'periodo atteso ~200, trovato %s' % p

    piatto = sorgente_con_segno(600, 200, trim, ripetizioni=1)
    p = costruttore._periodo_orizzontale(piatto.crop((0, trim, 600, 200 - trim)))
    assert p is None, \
        'trovato un periodo (%s) su una striscia che non si ripete' % p


def test_nessun_flip_nel_sorgente():
    """Rete di sicurezza: la parola FLIP non deve ricomparire nello script."""
    with open(_MOD, 'r') as fh:
        righe = fh.readlines()
    colpevoli = [(i + 1, r.strip()) for i, r in enumerate(righe)
                 if 'transpose(' in r and 'FLIP' in r]
    assert not colpevoli, (
        'e\' tornato uno specchiamento in perla-build-eu-print-files.py: %s'
        % colpevoli)


def test_la_striscia_larga_non_viene_ripetuta():
    """Se la sorgente e' gia' piu' larga dell'area, si ritaglia e basta.

    E' il caso della ciotola (6496 di larghezza contro 7169 della striscia):
    nessuna giunzione orizzontale da nascondere, quindi nessuna dissolvenza.
    """
    src = Image.new('RGB', (900, 100), (200, 100, 50))
    fuori = costruttore._fascia_orizzontale(src, 600, 40)
    assert fuori.size == (600, 100), 'attese (600, 100), ottenute %s' % (fuori.size,)
    assert fuori.getpixel((300, 50)) == (200, 100, 50), \
        'il ritaglio ha alterato i colori'


def main():
    print('\nOrientamento dei tasselli')
    prova('su un motivo periodico ogni segno e\' intero e dritto', test_tasselli_tutti_nello_stesso_verso)
    prova('senza periodo il disegno resta comunque intatto', test_motivo_non_periodico_resta_intatto)
    prova('nessuno specchiamento e\' rientrato nel codice', test_nessun_flip_nel_sorgente)

    print('\nAllineamento delle giunzioni')
    prova('il periodo si trova quando c\'e\', e non si inventa', test_riconoscimento_del_periodo)

    print('\nCasi limite')
    prova('una striscia gia\' larga viene solo ritagliata', test_la_striscia_larga_non_viene_ripetuta)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
