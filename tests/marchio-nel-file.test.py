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


def test_niente_cartella_dietro_al_marchio():
    """Il difetto che ROUND 47 chiude: "uno sfondo bianco gigantesco".

    Il marchio deve stare DIRETTAMENTE sul tessuto. Si guarda un punto dentro
    il riquadro del marchio ma fuori dalla sua sagoma: li' deve esserci ancora
    la stoffa, non il crema di una toppa. Il collare e' il caso peggiore --
    otto marchi su una fettuccia alta 315 px -- ed e' quello che si misura.
    """
    tessuto = (22, 32, 64)
    finito, box = marchio.componi(Image.new('RGB', (7169, 315), tessuto), 'collare')
    x, y, largo, alto = box[0]
    # angolo in alto a sinistra del riquadro: la sagoma del logo li' non arriva
    punto = finito.convert('RGB').getpixel((round(x + largo * 0.03), round(y + alto * 0.02)))
    scarto = abs(marchio._luminosita(punto) - marchio._luminosita(tessuto))
    assert scarto < 12, (
        'dentro il riquadro del marchio, fuori dalla sagoma, il fondo e\' cambiato '
        'di %.0f: c\'e\' ancora una cartella dietro' % scarto)


def test_l_inchiostro_si_adatta_al_fondo():
    """Su fondo scuro "Italia" schiarisce; su fondo chiaro l'oro si incupisce.

    Sono le due sparizioni documentate in _adatta(): senza la prima regola,
    "Italia" nera su navy non si legge; senza la seconda, l'oro su senape si
    confonde col fondo. Si misura sul pezzo, non a occhio.
    """
    logo = marchio._marchio().resize((120, 200), Image.LANCZOS)

    def piu_scuro(im):
        rgb = im.convert('RGB')
        alfa = im.getchannel('A')
        return min(marchio._luminosita(p) for p, a in zip(rgb.getdata(), alfa.getdata()) if a > 200)

    def piu_chiaro(im):
        rgb = im.convert('RGB')
        alfa = im.getchannel('A')
        return max(marchio._luminosita(p) for p, a in zip(rgb.getdata(), alfa.getdata()) if a > 200)

    su_scuro = marchio._adatta(logo, 40)
    assert piu_scuro(su_scuro) > piu_scuro(logo) + 60, (
        'su fondo scuro l\'inchiostro nero non e\' stato schiarito: '
        'resta a %.0f' % piu_scuro(su_scuro))

    su_medio = marchio._adatta(logo, 168)
    assert piu_chiaro(su_medio) < piu_chiaro(logo) - 30, (
        'su fondo medio l\'oro non e\' stato incupito: resta a %.0f'
        % piu_chiaro(su_medio))


def test_si_legge_su_qualunque_fondo():
    """Chiaro, scuro, dorato: dopo l'adattamento il marchio stacca sempre.

    E' la promessa che la cartella manteneva e che adesso deve mantenere
    l'inchiostro da solo. Si misura il contrasto fra il pixel piu' estremo del
    marchio e il fondo su cui e' posato.
    """
    logo = marchio._marchio().resize((120, 200), Image.LANCZOS)
    for nome, rgb in (('antracite', (38, 38, 40)), ('senape', (206, 178, 110)),
                      ('avorio', (238, 232, 220)), ('navy', (22, 32, 64)),
                      ('bordeaux', (120, 40, 45)), ('salvia', (150, 163, 132))):
        fondo = marchio._luminosita(rgb)
        pezzo = marchio._adatta(logo, fondo)
        colori = pezzo.convert('RGB')
        alfa = pezzo.getchannel('A')
        scarti = [abs(marchio._luminosita(p) - fondo)
                  for p, a in zip(colori.getdata(), alfa.getdata()) if a > 200]
        assert max(scarti) >= marchio.CONTRASTO_MINIMO, (
            'su fondo %s il marchio non stacca: scarto massimo %.0f, ne servono %d'
            % (nome, max(scarti), marchio.CONTRASTO_MINIMO))


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
    prova('niente cartella: il marchio sta sul tessuto',
          test_niente_cartella_dietro_al_marchio)
    prova('l\'inchiostro si adatta al fondo', test_l_inchiostro_si_adatta_al_fondo)
    prova('si legge su qualunque fondo', test_si_legge_su_qualunque_fondo)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
