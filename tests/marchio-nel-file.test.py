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

from PIL import Image, ImageDraw

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

    # ROUND 51 -- si guarda dove il MARCHIO e' pieno, non dove l'immagine
    # tornata e' opaca. Da quando c'e' il contorno le due cose non coincidono
    # piu': il contorno e' opaco anche lui, e sul fondo scuro e' scuro per
    # definizione, quindi il minimo lo dava lui e la prova falliva parlando di
    # un inchiostro che invece era stato schiarito benissimo. Il metro va preso
    # sul logo di partenza.
    pieno = [i for i, a in enumerate(logo.getchannel('A').getdata()) if a > 200]

    def piu_scuro(im):
        d = list(im.convert('RGB').getdata())
        return min(marchio._luminosita(d[i]) for i in pieno)

    def piu_chiaro(im):
        d = list(im.convert('RGB').getdata())
        return max(marchio._luminosita(d[i]) for i in pieno)

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


def test_si_legge_anche_sul_tessuto_a_righe():
    """Il difetto che ROUND 48 chiude, trovato sulla bandana "Marinara".

    Fin qui l'inchiostro si sceglieva da UNA media per tutto il riquadro. Su un
    tessuto a righe crema e blu quella media sta a meta' strada e non descrive
    nessuna delle due: misurato sul file vero, la scritta veniva incupita come
    su un fondo chiaro e dove cadeva sul blu lo stacco scendeva a 42, sotto i
    60 che marchio.py dichiara come minimo.

    Qui si ricostruisce quel tessuto e si misura lo stacco COLONNA PER COLONNA,
    non in media: la media era esattamente il modo di non vedere il difetto.
    """
    crema, blu = (238, 232, 220), (22, 32, 64)
    larghezza, altezza = 1400, 1500
    righe = Image.new('RGB', (larghezza, altezza), crema)
    for x in range(larghezza):
        # righe larghe un dito, come sulla Marinara
        if (x // 90) % 2:
            for y in range(altezza):
                righe.putpixel((x, y), blu)

    finito, box = marchio.componi(righe, 'medaglietta')
    assert box, 'nessun riquadro disegnato'
    x, y, largo, alto = box[0]
    largo, alto = round(largo), round(alto)
    ritaglio = finito.convert('RGB').crop((round(x), round(y),
                                           round(x) + largo, round(y) + alto))
    sotto = righe.crop((round(x), round(y), round(x) + largo, round(y) + alto))

    # SI GUARDANO I PIXEL DELL'INCHIOSTRO SCURO, cioe' "Italia": sono quelli
    # che spariscono su una riga blu se nessuno li schiarisce. Prendere invece
    # il massimo su una colonna intera risponderebbe a "qualcosa qui stacca?",
    # e l'oro del medaglione risponderebbe sempre di si' coprendo la scritta:
    # e' proprio cosi' che il difetto era passato inosservato.
    logo = marchio._marchio().resize((largo, alto), Image.LANCZOS)
    grigio = list(logo.convert('L').getdata())
    alfa = list(logo.getchannel('A').getdata())
    inchiostro = [i for i in range(len(alfa))
                  if alfa[i] > 200 and grigio[i] < marchio.SOGLIA_INCHIOSTRO]
    assert inchiostro, 'nessun pixel di inchiostro scuro nel marchio: prova inutile'

    stampato = list(ritaglio.getdata())
    tessuto_sotto = list(sotto.getdata())

    # Separati per riga: sulla crema e sulla blu la risposta giusta e' diversa,
    # e mescolarle rifarebbe l'errore della media unica.
    per_riga = {'chiara': [], 'scura': []}
    for i in inchiostro:
        luce_fondo = marchio._luminosita(tessuto_sotto[i])
        stacco = abs(marchio._luminosita(stampato[i]) - luce_fondo)
        per_riga['scura' if luce_fondo < 128 else 'chiara'].append(stacco)

    for nome, stacchi in per_riga.items():
        assert stacchi, 'il marchio non tocca nessuna riga %s: prova inutile' % nome
        stacchi.sort()
        mediano = stacchi[len(stacchi) // 2]
        assert mediano >= marchio.CONTRASTO_MINIMO, (
            'sulla riga %s la scritta non si legge: stacco mediano %.0f, ne '
            'servono %d' % (nome, mediano, marchio.CONTRASTO_MINIMO))


def test_la_scritta_non_sparisce_a_nessuna_luminosita():
    """Il difetto che ROUND 50 chiude: la scritta invisibile sui grigi medi.

    IL GUASTO
    I due inchiostri del marchio -- il crema e il quasi-nero -- stanno da PARTI
    OPPOSTE del fondo. Il passaggio fra l'uno e l'altro era sfumato su trenta
    livelli di luminosita', e mescolare a meta' due colori che stanno uno sopra
    e uno sotto il fondo non da' una via di mezzo: da' esattamente il fondo.

    Misurato sul nucleo pieno della scritta (i pixel che nel logo sono sotto 40,
    quindi non i bordi antialiasati), lo stacco del pixel che stacca DI PIU':

        fondo    prima   dopo
          110       90    131
          120       20    121      <- venti. La scritta non c'era.
          130       90    111

    Venti su un minimo di sessanta vuol dire che a quella luminosita' non
    esisteva un solo punto della scritta che si vedesse. Guardato a schermo su
    un grigio 120: "Perla Italia" spariva del tutto.

    PERCHE' IL TEST GUARDA IL PIXEL PIU' FORTE E NON LA MEDIA
    Perche' la domanda e' "si legge o no". Una media bassa puo' ancora essere
    una scritta leggibile con i bordi morbidi; ma se nemmeno il punto piu'
    contrastato arriva alla soglia, non c'e' niente da leggere. E' la misura
    che distingue i due casi -- ed e' quella che il test precedente non fa,
    perche' guarda TUTTO il marchio e li' basta una luce della perla a passare.
    """
    logo = marchio._marchio().resize((120, 200), Image.LANCZOS)
    grigio = list(logo.convert('L').getdata())
    alfa = list(logo.getchannel('A').getdata())
    nucleo = [i for i in range(len(alfa)) if alfa[i] > 200 and grigio[i] < 40]
    assert nucleo, 'nessun pixel di scritta piena: la prova non misurerebbe niente'

    peggiore = (999, None)
    for luce in range(0, 256, 5):
        colori = list(marchio._adatta(logo, float(luce)).convert('RGB').getdata())
        forte = max(abs(marchio._luminosita(colori[i]) - luce) for i in nucleo)
        if forte < peggiore[0]:
            peggiore = (forte, luce)
    assert peggiore[0] >= marchio.CONTRASTO_MINIMO, (
        'su fondo di luminosita\' %d la scritta non stacca da nessuna parte: '
        'il punto piu\' contrastato sta a %.0f, ne servono %d'
        % (peggiore[1], peggiore[0], marchio.CONTRASTO_MINIMO))



def _tessuto(misura, fondo, macchia, passo=17):
    """Un tessuto finto ma MOSSO: puntini regolari su un fondo."""
    im = Image.new('RGB', misura, fondo)
    d = ImageDraw.Draw(im)
    for y in range(0, misura[1], passo):
        for x in range(0, misura[0], passo):
            d.ellipse((x, y, x + 6, y + 6), fill=macchia)
    return im


def _con_cartella(tessuto, riquadro, colore=(246, 240, 230)):
    """Incolla una cartella chiara nel riquadro, come faceva ROUND 46."""
    im = tessuto.copy()
    s, a, largo, alto = riquadro
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((int(s), int(a), int(s + largo), int(a + alto)),
                        radius=12, fill=colore, outline=(180, 165, 140), width=3)
    return im


def test_la_cartella_incollata_si_riconosce():
    """La toppa: una regione chiara e piatta dentro un motivo che non lo e'.

    E' il controllo che non esisteva, ed e' per questo che la cartella crema e'
    rimasta in catalogo quattro giorni dopo che il codice aveva smesso di
    disegnarla: tutti i controlli guardavano i DATI del prodotto -- misure,
    copertura, livelli -- e la cartella sta dentro i PIXEL.

    Provato anche sui file veri scaricati da Printify il 3 settembre 2026:
    undici bandane con la cartella riconosciute su undici, otto pulite
    riconosciute su otto, e zero su ventisei bandane ricostruite.
    """
    misura = (600, 400)
    riquadro = (220, 90, 160, 220)
    tessuto = _tessuto(misura, (70, 90, 130), (40, 55, 90))

    pulito = marchio.toppa(tessuto, [riquadro])[0]
    assert not pulito['toppa'], (
        'un tessuto senza niente sopra non e\' una toppa: dentro %.2f, '
        'intorno %.2f' % (pulito['dentro'], pulito['intorno']))

    sporco = marchio.toppa(_con_cartella(tessuto, riquadro), [riquadro])[0]
    assert sporco['toppa'], (
        'la cartella incollata non e\' stata vista: dentro %.2f, intorno %.2f, '
        'bordo %.2f' % (sporco['dentro'], sporco['intorno'], sporco['bordo']))


def test_un_motivo_chiaro_non_e_una_toppa():
    """Il falso allarme da evitare: un disegno chiaro e piatto DAPPERTUTTO.

    E' il caso della bandana "Cachemire", crema su crema: dentro il riquadro
    e' chiara e piatta (0,54) esattamente come intorno (0,53). Se bastasse
    "chiara e piatta" senza il confronto, ogni motivo pallido del catalogo
    verrebbe segnalato -- e un controllo che grida sempre non lo guarda piu'
    nessuno.
    """
    misura = (600, 400)
    riquadro = (220, 90, 160, 220)
    pallido = _tessuto(misura, (243, 238, 228), (238, 233, 223), passo=23)
    e = marchio.toppa(pallido, [riquadro])[0]
    assert not e['toppa'], (
        'un motivo pallido su tutta la superficie non e\' una cartella: '
        'dentro %.2f, intorno %.2f, bordo %.2f' % (e['dentro'], e['intorno'], e['bordo']))


def test_la_cartella_chiara_su_fondo_chiaro_si_riconosce_dal_bordo():
    """Il caso che il confronto con l'anello NON puo' prendere.

    Su "Ramo", "Nobile" e "Fiorellino" -- motivi pallidi su crema -- la
    cartella misura 0,494 dentro e 0,498 intorno: non stacca di niente, perche'
    il tessuto e' chiaro e piatto quanto lei. Con la sola regola dell'anello
    erano tre bandane sbagliate su diciannove.

    Quello che una cartella ha e un tessuto no e' un BORDO DRITTO lungo quanto
    lei. Ed e' l'unico indizio che resta, qui.
    """
    misura = (600, 400)
    riquadro = (220, 90, 160, 220)
    pallido = _tessuto(misura, (240, 236, 226), (232, 228, 218), passo=23)
    e = marchio.toppa(_con_cartella(pallido, riquadro), [riquadro])[0]
    assert e['dentro'] - e['intorno'] < marchio.TOPPA_STACCO, (
        'prova mal costruita: qui la cartella deve NON staccare dall\'anello, '
        'se no non sta provando il bordo (dentro %.2f, intorno %.2f)'
        % (e['dentro'], e['intorno']))
    assert e['toppa'], (
        'la cartella su fondo chiaro va riconosciuta dal bordo dritto: '
        'bordo %.2f, ne serve %.2f' % (e['bordo'], marchio.TOPPA_BORDO))



def _tessuto_a_righe(misura, chiara, scura, larghezza=40):
    """Righe VERTICALI, come il collare "marinara"."""
    im = Image.new('RGB', misura, chiara)
    d = ImageDraw.Draw(im)
    for x in range(0, misura[0], larghezza * 2):
        d.rectangle((x, 0, x + larghezza, misura[1]), fill=scura)
    return im


def test_un_tessuto_a_righe_non_e_una_toppa():
    """Il falso allarme che ROUND 50 ha davvero preso, e come si toglie.

    Il collare "marinara" -- righe verticali navy e crema, nessuna cartella --
    veniva segnalato. Due volte, per due ragioni diverse, ed e' istruttivo:

      1. una riga crema dentro il riquadro e' CHIARA E PIATTA come una
         cartella, e il suo bordo e' alto quanto tutto il riquadro;
      2. su un collare il marchio si ripete otto volte, e basta che UNO degli
         otto riquadri cada su una riga larga.

    Quello che una riga non ha e' un bordo CHIUSO: ha il lato verticale, non
    quello orizzontale. Misurando il piu' debole dei due, la riga scende a zero
    e la cartella resta a 0,46 -- che e' il suo bordo, e non dipende dal
    tessuto sotto.
    """
    misura = (600, 400)
    riquadro = (220, 90, 160, 220)
    righe = _tessuto_a_righe(misura, (238, 232, 220), (26, 42, 78))
    e = marchio.toppa(righe, [riquadro])[0]
    assert e['bordo'] < marchio.TOPPA_BORDO, (
        'una riga non ha un bordo chiuso: dovrebbe misurare quasi zero, invece '
        '%.2f' % e['bordo'])
    assert not e['toppa'], (
        'un tessuto a righe non e\' una cartella: dentro %.2f, intorno %.2f, '
        'bordo %.2f' % (e['dentro'], e['intorno'], e['bordo']))

    # e la cartella VERA, sullo stesso tessuto a righe, si vede lo stesso
    sporco = marchio.toppa(_con_cartella(righe, riquadro), [riquadro])[0]
    assert sporco['toppa'], (
        'la cartella su tessuto a righe va vista comunque: dentro %.2f, '
        'bordo %.2f' % (sporco['dentro'], sporco['bordo']))



def test_l_inchiostro_non_va_a_chiazze():
    """Il difetto che ROUND 51 chiude, segnalato guardando i prodotti.

    "Su alcune il logo o e' troppo scuro o e' scansionato di luminosita' in
    base a quale parte del design copre". E' esatto: da ROUND 48 l'inchiostro
    si sceglieva PUNTO PER PUNTO seguendo il tessuto sotto, e su un motivo il
    marchio diventava un mosaico crema/nero.

    Non era un caso limite. Misurato sul riquadro del marchio dei 19 motivi
    bandana europei, contando quanta parte del fondo sta sopra la soglia:
    in DODICI il tessuto sta da tutte e due le parti, cioe' su dodici il
    marchio era a chiazze.

    QUI SI MISURA LA CHIAZZATURA
    Si compone il marchio su un tessuto a righe larghe -- il caso peggiore, due
    toni netti -- e si guarda quanto e' sparpagliato l'inchiostro del NUCLEO
    della scritta (i pixel che nel logo sono sotto 40, quindi non i bordi
    sfumati). Se l'inchiostro e' uno solo, quei pixel si somigliano; se e' un
    mosaico, stanno ai due estremi della scala.

        scarto fra il primo e il terzo quarto     prima   dopo
                                                  212     42

    Duecentododici su una scala di 255 vuol dire che meta' della scritta stava
    da una parte e meta' dall'altra: e' la definizione di "a chiazze".
    """
    logo = marchio._marchio().resize((160, 260), Image.LANCZOS)
    grigio = list(logo.convert('L').getdata())
    alfa = list(logo.getchannel('A').getdata())
    nucleo = [i for i in range(len(alfa)) if alfa[i] > 200 and grigio[i] < 40]
    assert nucleo, 'nessun pixel di scritta piena: la prova non misurerebbe niente'

    righe = _tessuto_a_righe((160, 260), (238, 232, 220), (26, 42, 78))
    pezzo = marchio._adatta(logo, marchio._mappa_fondo(righe))
    colori = list(pezzo.convert('RGB').getdata())
    luci = sorted(marchio._luminosita(colori[i]) for i in nucleo)
    sparpaglio = luci[3 * len(luci) // 4] - luci[len(luci) // 4]
    assert sparpaglio < 80, (
        'l\'inchiostro della scritta va a chiazze sul tessuto a due toni: '
        'fra il primo e il terzo quarto ci sono %.0f livelli, ne servono meno '
        'di 80' % sparpaglio)


def test_l_alone_non_e_una_cartella():
    """L'alone stacca il marchio, ma non deve diventare la toppa di prima.

    LA DISTINZIONE NON E' QUELLA CHE PENSAVO
    Scrivendo questa prova avevo dato per scontato che l'alone si riconoscesse
    perche' NON ha un bordo chiuso. La misura dice di no: il riquadro col
    marchio misura un bordo di 0,43, sopra la soglia. Ma quel bordo non e'
    dell'alone -- e' del MEDAGLIONE, che e' un cerchio con un contorno netto,
    e ce l'ha per disegno.

    Quello che davvero separa i due casi e' l'altra condizione, `dentro`:
    quanta parte del riquadro e' chiara E piatta.

        solo tessuto            dentro 0,00
        marchio con l'alone     dentro 0,06
        con la cartella         dentro 0,88

    Una cartella e' un campo pieno e uniforme; un marchio con un alone e' una
    sagoma sfumata su un tessuto che si vede ancora. Quindici volte di
    differenza, ed e' quella che il controllo guarda.
    """
    misura = (600, 400)
    riquadro = (220, 90, 160, 220)
    tessuto = _tessuto(misura, (70, 90, 130), (40, 55, 90))
    logo = marchio._marchio().resize((160, 220), Image.LANCZOS)

    con_alone = tessuto.convert('RGBA')
    s, a, largo, alto = riquadro
    sotto = tessuto.crop((s, a, s + largo, a + alto))
    con_alone.alpha_composite(marchio._adatta(logo, marchio._mappa_fondo(sotto)), (s, a))

    e = marchio.toppa(con_alone.convert('RGB'), [riquadro])[0]
    assert not e['toppa'], (
        'l\'alone e\' stato scambiato per una cartella: dentro %.2f, '
        'intorno %.2f, bordo %.2f' % (e['dentro'], e['intorno'], e['bordo']))
    assert e['dentro'] < marchio.TOPPA_DENTRO / 2.0, (
        'il riquadro col marchio non deve somigliare a un campo pieno e '
        'uniforme: dentro %.2f, la soglia della cartella e\' %.2f'
        % (e['dentro'], marchio.TOPPA_DENTRO))



def _fondo_a_maggioranza(misura, dominante, minoranza, larghezza=22, passo=70):
    """Un tessuto quasi tutto di un tono, con strisce dell'altro."""
    im = Image.new('RGB', misura, dominante)
    d = ImageDraw.Draw(im)
    for x in range(0, misura[0], passo):
        d.rectangle((x, 0, x + larghezza, misura[1]), fill=minoranza)
    return im


def test_il_contorno_regge_sul_tono_di_minoranza():
    """Il caso per cui il contorno esiste, e che senza non e' coperto.

    Con UN inchiostro solo per tutto il marchio, sul tono di maggioranza il
    marchio stacca per costruzione. Il problema e' l'altro tono: su un fondo
    quasi tutto scuro con qualche striscia chiara, l'inchiostro sara' crema, e
    dove una striscia chiara passa sotto una lettera quella lettera e' crema
    su crema.

    Non lo risolve un'ombra dietro: dove il marchio e' opaco, quello che c'e'
    sotto non si vede. Lo risolve un contorno, che esce da sotto le lettere e
    le circonda -- allora la FORMA si legge anche dove il colore no.

        stacco mediano sulla fascia di bordo, sulle strisce chiare
            senza contorno              40
            contorno largo e velato     94
            contorno stretto e pieno   142        (minimo richiesto 60)

    Si misura sulla fascia di bordo (alfa fra 10 e 250) e non sul pieno,
    perche' e' li' che un contorno lavora.
    """
    W, H = 200, 300
    fondo = _fondo_a_maggioranza((W, H), (30, 40, 70), (238, 232, 220))
    logo = marchio._marchio().resize((W, H), Image.LANCZOS)
    tela = fondo.convert('RGBA')
    tela.alpha_composite(marchio._adatta(logo, marchio._mappa_fondo(fondo)), (0, 0))
    finito = tela.convert('RGB')

    alfa = list(logo.getchannel('A').getdata())
    sotto = list(fondo.getdata())
    sopra = list(finito.getdata())
    bordo = [i for i in range(len(alfa))
             if 10 < alfa[i] < 250 and marchio._luminosita(sotto[i]) > 180]
    assert bordo, 'nessun pixel di bordo sulle strisce chiare: prova inutile'
    stacchi = sorted(abs(marchio._luminosita(sopra[i]) - marchio._luminosita(sotto[i]))
                     for i in bordo)
    mediano = stacchi[len(stacchi) // 2]
    assert mediano >= marchio.CONTRASTO_MINIMO, (
        'sul tono di minoranza il marchio non si stacca: il bordo fa %.0f, '
        'ne servono %d' % (mediano, marchio.CONTRASTO_MINIMO))


def test_il_contorno_non_lava_il_tessuto():
    """Il contorno deve staccare le lettere, non sbiancare la stoffa intorno.

    E' il difetto che la proprietaria ha visto e descritto meglio di quanto lo
    dicessero i numeri: "il logo con strisce di colore come se il design dove
    il logo viene applicato incidesse", "il logo che brilla". Con un contorno
    largo, sulla bandana a righe l'alone copriva un tono e non l'altro: il
    marchio sembrava a strisce perche' a strisce era diventato il tessuto
    INTORNO.

    LE PROPORZIONI DELLA PROVA NON SONO ARBITRARIE, e la prima stesura era
    inutile proprio per questo. Il raggio del contorno e' una frazione
    dell'ALTEZZA del marchio: su una tela 200x300 vale meno di un pixel per
    tutti e due i valori, quindi la prova passava anche col contorno largo che
    stava rovinando il catalogo. Qui la tela e' 360x600 e le righe sono larghe
    un sesto del marchio -- le stesse proporzioni della bandana marinara vera,
    dove il marchio e' alto 908 px e le righe 90.

    Misurato fuori dal marchio, scarto mediano per tono:

        raggio 0,0080   un tono 51, l'altro 0   ->  la striscia si vede
        raggio 0,0015   tutti e due 0           ->  la stoffa passa intera
    """
    W, H = 360, 600
    fondo = Image.new('RGB', (W, H), (238, 232, 220))
    disegno = ImageDraw.Draw(fondo)
    for x in range(0, W, 150):
        disegno.rectangle((x, 0, x + 60, H), fill=(30, 40, 70))
    logo = marchio._marchio().resize((W, H), Image.LANCZOS)
    tela = fondo.convert('RGBA')
    tela.alpha_composite(marchio._adatta(logo, marchio._mappa_fondo(fondo)), (0, 0))
    finito = tela.convert('RGB')

    alfa = list(logo.getchannel('A').getdata())
    sotto = list(fondo.getdata())
    sopra = list(finito.getdata())
    fuori = [i for i in range(len(alfa)) if alfa[i] < 40]

    def mediano(scelti):
        v = sorted(abs(marchio._luminosita(sopra[i]) - marchio._luminosita(sotto[i]))
                   for i in scelti)
        return v[len(v) // 2] if v else 0

    chiari = [i for i in fuori if marchio._luminosita(sotto[i]) > 170]
    scuri = [i for i in fuori if marchio._luminosita(sotto[i]) < 110]
    assert chiari and scuri, 'il tessuto di prova non ha tutti e due i toni'

    su_chiaro, su_scuro = mediano(chiari), mediano(scuri)
    # 8 e non 0: un contorno esiste, quindi qualcosa tocca. Quello che non deve
    # succedere e' che tocchi tanto -- e su un tono solo, che e' la striscia.
    peggio = max(su_chiaro, su_scuro)
    assert peggio <= 8, (
        'il contorno lava il tessuto: cambia di %.0f sul chiaro e %.0f sullo '
        'scuro. E\' cosi\' che il marchio sembra a strisce.'
        % (su_chiaro, su_scuro))


def test_l_inchiostro_segue_il_tono_dominante():
    """Un inchiostro solo va bene, ma dev'essere QUELLO GIUSTO.

    La mediana serve proprio a questo: su un tessuto per tre quarti scuro
    l'inchiostro dev'essere il crema, e su uno per tre quarti chiaro il
    quasi-nero. Con la media, su un due-toni netto, si finirebbe a meta' e si
    sceglierebbe male quasi sempre.
    """
    W, H = 200, 300
    logo = marchio._marchio().resize((W, H), Image.LANCZOS)
    grigio = list(logo.convert('L').getdata())
    alfa = list(logo.getchannel('A').getdata())
    nucleo = [i for i in range(len(alfa)) if alfa[i] > 200 and grigio[i] < 40]

    def luce_della_scritta(fondo):
        pezzo = marchio._adatta(logo, marchio._mappa_fondo(fondo))
        colori = list(pezzo.convert('RGB').getdata())
        luci = sorted(marchio._luminosita(colori[i]) for i in nucleo)
        return luci[len(luci) // 2]

    scuro = _fondo_a_maggioranza((W, H), (30, 40, 70), (238, 232, 220))
    chiaro = _fondo_a_maggioranza((W, H), (238, 232, 220), (30, 40, 70))
    su_scuro, su_chiaro = luce_della_scritta(scuro), luce_della_scritta(chiaro)
    assert su_scuro > 150, (
        'su un tessuto in maggioranza SCURO la scritta deve essere chiara: '
        'misura %.0f' % su_scuro)
    assert su_chiaro < 110, (
        'su un tessuto in maggioranza CHIARO la scritta deve essere scura: '
        'misura %.0f' % su_chiaro)


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
    prova('si legge anche sul tessuto a righe', test_si_legge_anche_sul_tessuto_a_righe)
    prova('la scritta non sparisce a nessuna luminosita\' del fondo',
          test_la_scritta_non_sparisce_a_nessuna_luminosita)

    print('\nLa cartella incollata')
    prova('una cartella dentro un motivo mosso si riconosce',
          test_la_cartella_incollata_si_riconosce)
    prova('un motivo chiaro dappertutto NON e\' una cartella',
          test_un_motivo_chiaro_non_e_una_toppa)
    prova('una cartella chiara su fondo chiaro si riconosce dal bordo',
          test_la_cartella_chiara_su_fondo_chiaro_si_riconosce_dal_bordo)
    prova('un tessuto a righe NON e\' una cartella',
          test_un_tessuto_a_righe_non_e_una_toppa)

    print('\nUn inchiostro solo, e un alone')
    prova('l\'inchiostro non va a chiazze sul tessuto a due toni',
          test_l_inchiostro_non_va_a_chiazze)
    prova('l\'alone stacca il marchio ma non e\' una cartella',
          test_l_alone_non_e_una_cartella)
    prova('il contorno regge anche sul tono di minoranza',
          test_il_contorno_regge_sul_tono_di_minoranza)
    prova('il contorno non lava il tessuto intorno',
          test_il_contorno_non_lava_il_tessuto)
    prova('l\'inchiostro segue il tono dominante del tessuto',
          test_l_inchiostro_segue_il_tono_dominante)

    print('\n%d verifiche superate.' % passati +
          (' %d FALLITE.' % falliti if falliti else ''))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
