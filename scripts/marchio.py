#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mette il marchio DENTRO il file di stampa, non sopra come livello a parte.

PERCHE' NON E' PIU' UN LIVELLO SEPARATO

Fino a ROUND 46 il marchio viveva come seconda immagine dentro il placeholder
Printify, con coordinate sue. Due difetti nascevano da li', e sono arrivati
tutti e due in catalogo:

1. SPARIVA. perla-usa-marchio.py --rimuovi toglieva il livello sovrapposto da
   bandane e medagliette perche' "il marchio e' gia' dentro l'artwork" -- vero
   quando fu scritto. Ma perla-usa-carica-stampe.py aveva nel frattempo
   sostituito quell'artwork con i nativi europei, che sono motivo e basta.
   Due operazioni giuste da sole lasciano il prodotto senza nessun marchio.
2. ERA SGRANATO O TAGLIATO. In catalogo giravano CINQUE file di marchio
   diversi ("LOGO PERLA - Copia.PNG" 554x408, "logo-full.png" 600x507,
   "v2-01-logo-centrale.png", "v3-square-coaster-logo.png",
   "perla-combined-logo.png"), a scale copiate da un prodotto all'altro. Sulla
   cuccia il piu' piccolo veniva stampato largo 1350 px: ingrandito 2,4 volte.

Composto qui, il marchio nasce alla risoluzione del file di stampa, non puo'
essere rimosso per sbaglio, e non c'e' piu' nessuna scala da mantenere
allineata a mano fra prodotti diversi.

QUANTO GRANDE: FRAZIONE DEL LATO CORTO, NON PIXEL
La misura e' espressa come frazione del LATO CORTO dell'area. E' l'unica che
resta coerente fra varianti di misura fisica diversa: il collare S e' una
fettuccia da 1 pollice (229 px), il collare M da 1,5 (338 px), e un marchio
alto "il 72% della fettuccia" si vede uguale su tutti e due, mentre un marchio
"alto 240 px" sul primo sarebbe fuori misura.

DOVE: DENTRO LA FORMA VERA DEL PRODOTTO
L'area di stampa e' sempre un rettangolo, il prodotto quasi mai. La bandana e'
un TRIANGOLO e la medaglietta un CERCHIO: un marchio centrato nel rettangolo
puo' cadere benissimo fuori dal tessuto. Non e' teoria -- e' il difetto
descritto in perla-usa-marchio.py, dove il marchio a y=0,863 finiva oltre la
punta della bandana e veniva tagliato. area_sicura() modella la forma vera e
componi() si rifiuta di uscirne.

MAI INGRANDITO
Il file del marchio e' 1600 px di larghezza. Se la misura richiesta chiede piu'
di tanto, si scende a 1600 e lo si dice: rimetterlo sgranato sarebbe rifare da
capo il difetto che questo modulo esiste per togliere.
"""
import os

from PIL import Image, ImageChops, ImageFilter

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
MARCHIO = os.path.join(RADICE, "generated-designs", "perla-combined-logo.png")

# Il nome con cui il marchio si riconosce nei file gia' costruiti, e i nomi dei
# livelli-marchio che questo modulo rende obsoleti su Printify.
NOME = "perla-combined-logo.png"

# ==========================================================================
# QUALI MOTIVI IL MARCHIO CE L'HANNO GIA'
# ==========================================================================
# Aggiungere il marchio a un motivo che lo contiene gia' non e' un dettaglio:
# e' il difetto "marchio doppio" gia' corretto una volta su bandane e
# medagliette (commit 962ade7). Quindi si compone SOLO dove manca davvero.
#
# La classificazione e' stata fatta GUARDANDO i diciannove nativi europei a
# risoluzione piena -- provino d'insieme e poi zoom a 1:1 sui dubbi -- e non
# leggendo i nomi, che su questo progetto mentono regolarmente:
# bandana-damasco-reale.jpg non e' un damasco, e' un ramo d'ulivo su crema
# senza un filo di marchio.
#
# Due modi in cui un nativo porta gia' il marchio, validi tutti e due:
#   medaglione singolo   art-deco-rosa, diamanti, lino, marinara, onde-dorate,
#                        paisley-cammeo, tartan, terracotta
#   scritta ripetuta     barocco, damasco-diamante, erbario, floreale-elegante,
#                        ghirigori, onde, paisley-rosa, ramo-dulivo
#
# Chi rivede questa tabella rifaccia lo stesso: guardi le immagini.
# ==========================================================================
# I NATIVI CON UN MEDAGLIONE SOLO: il marchio c'e', ma non si puo' contarci
# ==========================================================================
# Otto nativi portano UN SOLO medaglione "Perla Italia", sempre nello stesso
# punto: centro a x=0,81 y=0,79 (misurato su tutti e otto cercando la finestra
# a saturazione massima, e confermato correlando il file del logo -- non e'
# un'interpretazione).
#
# E QUEL MEDAGLIONE E' ANCHE MAL COMPOSTO. Guardato a 1:1 su terracotta,
# tartan, marinara e lino: la scritta "Perla" e' semitrasparente e sotto si
# legge il motivo, e al centro della perla c'e' un buco che lascia passare il
# fondo -- rosso sul terracotta, verde sul tartan, blu sul marinara. E'
# esattamente quello che la titolare ha descritto, "il logo trasparente che fa
# vedere un puntino nero". Un altro motivo per toglierlo e rifarlo qui, dove
# il logo si incolla opaco.
#
# "Il nativo ha il marchio" e' vero per il nativo INTERO e falso per un suo
# ritaglio. Sulla medaglietta "Green Geometric" (area 810x900, ritagliata da
# bandana-diamanti) quel medaglione e' finito sul bordo ed e' stato tagliato
# dal tondo: si vedeva una falce d'oro a destra e nient'altro. Guardato il
# mockup vero, non dedotto. Affiancando il nativo il medaglione si ripete a
# caso e a volte cade sulla punta della bandana, dove viene mozzato.
#
# Quindi: si RITAGLIA via il medaglione dal nativo, e il marchio lo si compone
# noi dove deve stare. Il ritaglio tiene i due terzi sinistri a piena altezza,
# che e' la porzione piu' grande che lo esclude di sicuro.
#
# OTTO, NON QUATTRO. Questa tabella nacque con quattro nomi perche' i nativi
# europei erano quindici. Adesso sono diciannove, e i quattro arrivati dopo
# (lino, marinara, tartan, terracotta) portano lo stesso identico medaglione,
# nello stesso punto. Cercarlo a occhio una volta sola e poi fidarsi della
# lista e' come il difetto e' passato: la lista qui sotto e' stata rifatta
# misurando tutti e diciannove i nativi in due modi indipendenti che danno lo
# stesso risultato -- il picco di saturazione, e la correlazione con
# perla-combined-logo.png, che nei nativi col medaglione sta fra 0,58 e 0,89 e
# in tutti gli altri non supera 0,51.
NATIVI_CON_MEDAGLIONE = {
    "bandana-art-deco-rosa.jpg",
    "bandana-diamanti.jpg",
    "bandana-lino.jpg",
    "bandana-marinara.jpg",
    "bandana-onde-dorate.jpg",
    "bandana-paisley-cammeo.jpg",
    "bandana-tartan.jpg",
    "bandana-terracotta.jpg",
}

# Il medaglione, in frazione del nativo: centro (0,81 - 0,79).
#
# IL BASSO ERA SBAGLIATO. Fino a qui il riquadro finiva a 0,84, che taglia via
# la parola "Italia": bastava finche' serviva solo a decidere SE un ritaglio lo
# escludeva, non appena serve a coprirlo davvero. Misurato sul nativo dal fondo
# piu' pulito (bandana-lino, crema uniforme): il marchio va da 0,71 a 0,94 in
# orizzontale e da 0,61 a 0,95 in verticale.
MEDAGLIONE = (0.70, 0.61, 0.95, 0.95)
# Il ritaglio che lo esclude, in frazione del nativo (sinistra, alto, destra, basso).
RITAGLIO_SENZA_MEDAGLIONE = (0.0, 0.0, 0.66, 1.0)


def esclude_il_medaglione(ritaglio, dimensioni):
    """Vero se questo ritaglio (in pixel) lascia gia' fuori il medaglione.

    Serve per non ritagliare due volte: bandana-onde-dorate ha gia' un
    ritaglio esplicito a (0, 0, 4125, 1850) messo in una tornata precedente,
    e 1850 sta ben sopra il medaglione, che comincia a 0,66 di 4125 = 2722.
    """
    if not ritaglio:
        return False
    w, h = dimensioni
    _, _, destra, basso = ritaglio
    return destra <= MEDAGLIONE[0] * w or basso <= MEDAGLIONE[1] * h


NATIVI_SENZA_MARCHIO = {
    "bandana-damasco-reale.jpg",   # rami d'ulivo verdi su crema, niente scritte
    "bandana-ulivo-nuovo.jpg",     # foglie tenui su crema, niente scritte
    "bandana-ulivo.jpg",           # damasco bordeaux e oro pieno, niente scritte
}


def serve(nativo):
    """Vero se a questo motivo il marchio va aggiunto.

    I motivi GEOMETRICI sono disegnati da perla-motivi-nuovi.py e non hanno
    marchio per costruzione: si passa None e la risposta e' sempre si'.
    """
    if not nativo:
        return True
    base = os.path.basename(nativo)
    # I quattro col medaglione singolo contano come "senza marchio": il loro
    # viene ritagliato via, perche' su un ritaglio non ci si puo' contare.
    return base in NATIVI_SENZA_MARCHIO or base in NATIVI_CON_MEDAGLIONE

LIVELLI_OBSOLETI = ("LOGO PERLA - Copia.PNG", "logo-full.png",
                    "perla-combined-logo.png", "v2-01-logo-centrale.png",
                    "v3-square-coaster-logo.png")


# ==========================================================================
# GEOMETRIA PER TIPO DI PRODOTTO
# ==========================================================================
# altezza:   quanto e' alto il marchio, in frazione del LATO CORTO dell'area
# centro:    dove sta il suo centro, in frazione dell'area (solo se ripeti=0)
# ripeti:    quante volte lungo la lunghezza; 0 = una volta sola, al centro.
#            Serve sui prodotti a nastro (collare, guinzaglio, fascia della
#            ciotola), dove un marchio solo su un metro di fettuccia non si
#            vedrebbe mai -- ed e' anche come era disegnato l'artwork
#            originale, che sul collare ripeteva la cartella quattro volte.
# forma:     come e' fatto il prodotto davvero, per l'area sicura.
#
# I NUMERI VANNO GUARDATI, NON CREDUTI. Sono la prima proposta, tarata sulle
# proporzioni dell'artwork originale (sulla bandana la cartella occupava circa
# un sesto del lato; sul collare si ripeteva quattro volte per riga). Prima di
# applicarli a settanta prodotti se ne fa UNO per tipo e si guarda il mockup:
# e' la stessa regola scritta in perla-usa-carica-stampe.py.
GEOMETRIA = {
    "collare":     {"altezza": 0.72, "ripeti": 8,  "forma": "rettangolo"},
    "guinzaglio":  {"altezza": 0.72, "ripeti": 12, "forma": "rettangolo"},
    "ciotola":     {"altezza": 0.55, "ripeti": 6,  "forma": "rettangolo"},
    # ROUND 53 -- 0,22 e non 0,34, e piu' in basso.
    #
    # A 0,34 il marchio era alto un terzo della bandana e cadeva in mezzo
    # esatto: la proprietaria l'ha detto cosi', "e' brutto appiccicato cosi'
    # grosso al centro, rendilo piu' piccolo e discreto". Guardati affiancati
    # sullo stesso tessuto pulito, a 0,34 il marchio E' il prodotto, a 0,22 e'
    # una firma sul prodotto, a 0,15 "Italia" non si legge piu'.
    #
    # 0,22 e' anche esattamente la misura della bandana EUROPEA, che nessuno
    # ha mai segnalato: le due linee vendono lo stesso oggetto e adesso lo
    # firmano allo stesso modo.
    #
    # Il centro scende da 0,42 a 0,48 -- resta dentro la fascia sicura del
    # triangolo (0,20-0,60 dell'altezza: a 0,48 il marchio va da 604 a 1116 su
    # un limite di 1395) e smette di essere in mezzo esatto.
    "bandana":     {"altezza": 0.22, "ripeti": 0, "centro": (0.50, 0.48),
                    "forma": "triangolo"},
    # La bandana EUROPEA non e' un triangolo. Printful stampa un quadrato
    # 44x44 e lo fotografa steso: nel mockup si vede tutto il quadrato, bordo
    # compreso. Modellarla come la bandana americana spingerebbe il marchio
    # nella fascia alta di un triangolo che qui non esiste.
    #
    # Il centro non e' quello del quadrato di proposito: e' la firma d'angolo
    # che i motivi hanno gia' addosso (misurata a 0,81 - 0,79), tirata dentro
    # quel tanto che basta perche' la cartella non tocchi l'orlo cucito.
    "bandana_eu":  {"altezza": 0.22, "ripeti": 0, "centro": (0.78, 0.76),
                    "forma": "rettangolo"},
    "medaglietta": {"altezza": 0.62, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "cerchio"},
    "cuccia":      {"altezza": 0.22, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "rettangolo"},
    "tappetino":   {"altezza": 0.22, "ripeti": 0, "centro": (0.50, 0.50),
                    "forma": "rettangolo"},
}

# Quanto bordo dell'area non e' tessuto visibile. Sulla cuccia il bordo si
# arrotola sotto (e' la ragione per cui il marchio vecchio finiva nella parte
# nascosta, vedi perla-usa-marchio.py); sugli altri e' margine di taglio.
MARGINE = {"cuccia": 0.10, "tappetino": 0.06}
MARGINE_PREDEFINITO = 0.04


def _marchio(percorso=None):
    im = Image.open(percorso or MARCHIO)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    # Il file ha 120 px di trasparente per lato: ritagliarlo significa che
    # "altezza 0,72" e' 0,72 di marchio VISIBILE e non di aria intorno.
    riquadro = im.getchannel("A").getbbox()
    return im.crop(riquadro) if riquadro else im


def area_sicura(tipo, area):
    """Il rettangolo dentro cui il marchio si vede davvero, in pixel.

    Torna (sinistra, alto, destra, basso). Per triangolo e cerchio e' il piu'
    grande rettangolo utile inscritto nella forma, non il rettangolo di stampa.
    """
    aw, ah = area
    forma = GEOMETRIA.get(tipo, {}).get("forma", "rettangolo")
    m = MARGINE.get(tipo, MARGINE_PREDEFINITO)

    if forma == "cerchio":
        # cerchio inscritto, poi il quadrato inscritto nel cerchio: e' il
        # riquadro dentro cui qualunque cosa resta sulla medaglietta
        r = min(aw, ah) / 2.0 * (1 - m)
        lato = r * 1.41421356 / 2.0
        return (aw / 2.0 - lato, ah / 2.0 - lato, aw / 2.0 + lato, ah / 2.0 + lato)

    if forma == "triangolo":
        # Bandana: base in alto, punta in basso. A quota y la stoffa e' larga
        # (1 - y) della base. Si prende la fascia alta 20%-60%, dove il
        # triangolo e' ancora largo piu' di meta' -- sotto, la punta stringe in
        # fretta ed e' li' che il marchio vecchio veniva tagliato.
        y0, y1 = 0.20 * ah, 0.60 * ah
        largo = (1 - 0.60) * aw * (1 - m)   # larghezza alla quota piu' stretta
        return (aw / 2.0 - largo / 2.0, y0, aw / 2.0 + largo / 2.0, y1)

    return (aw * m, ah * m, aw * (1 - m), ah * (1 - m))


def riquadri(tipo, area, marchio_wh):
    """Dove va disegnato il marchio: una lista di (sinistra, alto, larghezza, altezza).

    Solleva ValueError se non ci sta nell'area sicura: meglio fermarsi qui che
    scoprire dal cliente che il marchio e' mozzato.
    """
    if tipo not in GEOMETRIA:
        raise ValueError("tipo senza geometria del marchio: %r (previsti: %s)"
                         % (tipo, ", ".join(sorted(GEOMETRIA))))
    g = GEOMETRIA[tipo]
    aw, ah = area
    mw, mh = marchio_wh

    alto_px = g["altezza"] * min(aw, ah)
    largo_px = alto_px * mw / float(mh)
    # mai ingrandito oltre la sua risoluzione vera
    if largo_px > mw:
        largo_px = float(mw)
        alto_px = largo_px * mh / float(mw)

    s, a, d, b = area_sicura(tipo, area)
    if largo_px > (d - s) or alto_px > (b - a):
        raise ValueError(
            "il marchio (%dx%d px) non entra nell'area sicura di %s "
            "(%dx%d px su un'area %dx%d): abbassa GEOMETRIA[%r]['altezza']."
            % (largo_px, alto_px, tipo, d - s, b - a, aw, ah, tipo))

    if not g.get("ripeti"):
        cx, cy = g.get("centro", (0.5, 0.5))
        cx, cy = cx * aw, cy * ah
        # riportato dentro l'area sicura se il centro chiesto lo porterebbe fuori
        cx = min(max(cx, s + largo_px / 2), d - largo_px / 2)
        cy = min(max(cy, a + alto_px / 2), b - alto_px / 2)
        return [(cx - largo_px / 2, cy - alto_px / 2, largo_px, alto_px)]

    n = int(g["ripeti"])
    cy = (a + b) / 2.0
    passo = (d - s) / float(n)
    fuori = []
    for i in range(n):
        cx = s + passo * (i + 0.5)
        fuori.append((cx - largo_px / 2, cy - alto_px / 2, largo_px, alto_px))
    return fuori


# I due inchiostri del marchio: il medaglione e "Perla" sono oro, "Italia" e'
# quasi nera. Da qui nasce tutto il problema risolto sotto.
ORO = (214, 178, 96)
INCHIOSTRO_SCURO = (28, 26, 24)
# Il crema per cui il logo e' stato disegnato: e' il colore in cui l'inchiostro
# scuro si trasforma quando il tessuto sotto e' troppo buio per contenerlo.
CREMA = (246, 240, 230)
# Scarto di luminosita' sotto il quale un inchiostro sparisce nel fondo.
CONTRASTO_MINIMO = 60
# Sopra questa, il fondo e' cosi' chiaro che all'oro basta pochissimo aiuto.
FONDO_CHIARISSIMO = 205
# Di quanto si incupisce l'oro sui fondi medi e su quelli chiarissimi.
#
# PERCHE' DUE VALORI FISSI E NON UNA FORMULA. Provato: far inseguire all'oro
# la soglia di contrasto, incupendolo punto per punto in base al fondo, migliora
# ogni numero -- sulla salvia i pixel sotto soglia scendono dal 51% al 2% -- e
# rovina il marchio. La ragione e' che "l'oro" non e' un colore solo: dentro ci
# sono anche le luci della PERLA, e moltiplicarle per 0,3 le spegne. Guardato a
# schermo, il medaglione diventa una macchia grigia. Il numero diceva meglio,
# l'occhio diceva peggio, e su un logo decide l'occhio.
CUPEZZA_MEDIO = 0.62
CUPEZZA_CHIARO = 0.80
# Sotto questa luminosita' un pixel del logo e' "inchiostro scuro".
SOGLIA_INCHIOSTRO = 100
# Un pixel del marchio con alfa sotto questa soglia lascia vedere il tessuto:
# sono quelli che presente() usa per capire su che fondo sta guardando.
ALFA_TRASPARENTE = 20
# Lato corto della mappa del fondo, in pixel. Vedi _mappa_fondo().
MAPPA_FONDO = 48


def _luminosita(rgb):
    """La luminosita' percepita di un colore. La usano i test per misurare lo
    stacco fra inchiostro e tessuto invece di giudicarlo a occhio."""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


# Dove passare dall'inchiostro scuro al crema: nel punto in cui i due staccano
# UGUALE dal fondo, cioe' a meta' strada fra le loro luminosita'. E' l'unica
# scelta che tiene, e la ragione e' aritmetica: per ogni fondo, il piu'
# contrastato dei due inchiostri stacca almeno di (crema - scuro)/2 -- qui 109,
# quasi il doppio del minimo richiesto. Qualunque altro punto lascerebbe una
# fascia di fondi in cui NESSUNO dei due basta.
FONDO_SCURO = (_luminosita(CREMA) + _luminosita(INCHIOSTRO_SCURO)) / 2.0

# L'ALONE: quanto largo e quanto denso.
#
# Il raggio e' una frazione dell'ALTEZZA del marchio, non un numero di pixel:
# lo stesso marchio si compone alto 908 px su una bandana e 227 px su un
# collare, e un alone di "12 px" sarebbe una nuvola sul secondo e un filo sul
# primo.
#
# IL RAGGIO E' STRETTO, E C'E' VOLUTO PIU' DI UN GIRO PER STRINGERLO ABBASTANZA.
#
# A 0,045 -- 41 px su un marchio alto 908 -- il contorno non era un contorno:
# era una NUVOLA, cioe' la cartella crema un'altra volta con i bordi sfumati.
# A 0,008 sembrava risolto: i numeri dicevano che le lettere staccavano e che
# il tessuto si rivedeva.
#
# I NUMERI DICEVANO GIUSTO E L'OCCHIO NO, e a vederlo la proprietaria e' stata
# piu' precisa di qualunque misura: "il logo con strisce di colore come se il
# design dove il logo viene applicato incidesse", "il logo che brilla".
# Guardato a 1:1 sulla bandana marinara aveva ragione: le righe blu SPARIVANO
# dietro un alone biancastro largo una lettera, e sul tartan il quadrettato si
# sbiadiva. Il contorno non lavava il marchio -- lavava il TESSUTO INTORNO, e
# siccome sul crema non si vedeva e sul blu si', il marchio sembrava a strisce.
#
# Misurato sul riquadro del marchio della marinara, pixel di solo tessuto:
#
#     raggio      tessuto lavato    scarto mediano       stacco delle lettere
#                                 sul blu / sul crema    sul tono di minoranza
#     0,0080         44.421 px         19 / 0                   112
#     0,0030         20.081 px          0 / 0                   114
#     0,0015         10.823 px          0 / 0                   113
#
# Lo stacco non cambia -- quello lo fa il profilo, non l'area -- mentre il
# tessuto toccato scende di quattro volte. A 0,0015 le righe passano intere
# sotto le lettere e il contorno si legge come parte del marchio, come il
# filetto di un carattere contornato. Il guadagno sale a 7 perche' su un
# raggio cosi' corto serve piu' spinta per arrivare a bordo pieno.
ALONE_RAGGIO = 0.0015
ALONE_OPACITA = 1.00
# Quanto la sagoma sfocata viene "gonfiata" prima di essere usata come alone.
#
# PERCHE' SERVE, e l'ho scoperto misurando invece che immaginando. Un alone
# fatto solo sfocando la sagoma sta SOTTO il marchio: dove il marchio e' opaco
# non si vede affatto. Misurato su un tessuto in maggioranza scuro con strisce
# chiare, guardando i pixel di scritta che cadono sulle strisce: lo stacco
# restava 8 con l'alone e 8 senza. Serviva a niente proprio nel caso per cui
# l'avevo aggiunto.
#
# Moltiplicando la sfocatura e tagliandola a 255 si ottiene invece un CONTORNO:
# pieno subito fuori dalle lettere, sfumato piu' in la'. Cosi' ogni lettera ha
# un bordo del tono opposto, e la sua FORMA si legge anche dove il suo colore
# somiglia al tessuto -- che e' come si mette un marchio sopra una fotografia.
GUADAGNO_ALONE = 7.0


def _cupezza(fondo):
    """Di quanto incupire l'oro perche' stacchi da un fondo di quella luminosita'.

    IL DIFETTO CHE CHIUDE, MISURATO
    Fino a qui l'oro si incupiva di un fattore FISSO: 0,62 sotto FONDO_CHIARISSIMO
    e 0,80 sopra. Su un avorio funziona. Su un fondo di mezzo no, e non e'
    un'opinione -- contando i pixel opachi del marchio che restano sotto i
    CONTRASTO_MINIMO=60 che questo file stesso dichiara:

        fondo             luce   sotto i 60
        antracite          38        0%
        navy               33        0%
        senape            179       19%
        bordeaux           64       24%
        oro (laurel)      163       37%
        salvia            156       50%

    Su meta' del marchio, sulla salvia, l'inchiostro non staccava. La ragione
    e' aritmetica: l'oro nativo sta a 179, incupito di 0,62 arriva a 111, e su
    un fondo a 156 sono 45 di scarto -- sotto la soglia. Con la cartella crema
    non si vedeva, perche' il marchio aveva un fondo tutto suo; e' lo stesso
    difetto che ROUND 48 ha trovato sul tessuto a righe, un passo piu' in la'.

    LA REGOLA
    Invece di due fattori scelti a mano, uno solo che insegue la soglia: l'oro
    va portato a CONTRASTO_MINIMO SOTTO il fondo. Verso il basso, perche' da
    179 in su c'e' poco spazio prima del bianco, mentre verso il nero ce n'e'
    sempre.

        fondo 120  ->  0,34    fondo 179  ->  0,66
        fondo 156  ->  0,54    fondo 205  ->  0,81 (tagliato a 0,80)

    I due vecchi valori non spariscono: 0,80 resta il tetto, ed e' esattamente
    quello che la regola calcola sul chiarissimo. Il fisso 0,62 corrispondeva
    a un fondo di 171: giusto per quello, sbagliato per tutti gli altri.
    """
    voluta = (fondo - CONTRASTO_MINIMO - MARGINE_CONTRASTO) / float(LUMINOSITA_ORO)
    return max(CUPEZZA_MINIMA, min(CUPEZZA_MASSIMA, voluta))


def _mappa_fondo(ritaglio, vista=None):
    """La luminosita' del tessuto sotto il marchio, PUNTO PER PUNTO.

    PERCHE' NON BASTA LA MEDIA
    Fino a ROUND 48 qui c'era _fondo_medio(): un numero solo per tutto il
    riquadro. Su un tessuto uniforme e' giusto; su uno a righe e' un numero che
    non descrive nessuna delle due.

    Misurato sulla bandana "Marinara", che ha righe crema e blu larghe un dito:
    il marchio ci cade a cavallo, la media finiva a meta' strada, e la scritta
    "Italia" veniva incupita come su un fondo chiaro. Dove pero' cadeva sul
    blu, lo stacco scendeva a 42,5 -- sotto i 60 che questo stesso file
    dichiara come minimo, in tre colonne su tredici. La cartella crema di prima
    nascondeva il difetto dando al marchio un fondo tutto suo; toltala, e'
    venuto fuori.

    QUANTO GROSSOLANA
    Il marchio deve seguire le FASCE del tessuto, non i singoli fili: una mappa
    a 48 px sul lato corto, sfocata e poi riportata alla misura del marchio, fa
    esattamente questo. Seguire ogni filo darebbe un inchiostro che cambia
    dentro la stessa lettera, che si legge peggio di uno sbagliato.

    LA MASCHERA
    In componi() il tessuto e' tutto in vista e non serve. In presente() no: li
    il marchio e' gia' posato e copre proprio quello che vorremmo misurare.
    Allora si guarda solo dove il marchio e' trasparente (`vista`) e si lascia
    che le zone coperte prendano il colore del tessuto che le circonda -- e'
    una media pesata locale, la stessa cosa che fa una sfocatura, ma contando
    solo i pixel che sono davvero tessuto.
    """
    w, h = ritaglio.size
    lato = max(1, min(MAPPA_FONDO, min(w, h)))
    corto = float(min(w, h))
    piccolo = (max(1, round(w * lato / corto)), max(1, round(h * lato / corto)))
    grigio = ritaglio.convert("L")

    if vista is None:
        mappa = grigio.resize(piccolo, Image.BOX)
    else:
        # visto/peso: la somma del tessuto visibile diviso quanto ce n'era.
        visto = ImageChops.multiply(grigio, vista).resize(piccolo, Image.BOX)
        peso = vista.resize(piccolo, Image.BOX)
        v, p = list(visto.getdata()), list(peso.getdata())
        noti = [255.0 * v[i] / p[i] for i in range(len(p)) if p[i]]
        # Se una cella non ha nemmeno un pixel di tessuto in vista, prende la
        # media di quelle che ce l'hanno: meglio del nero, che direbbe "fondo
        # scurissimo" e schiarirebbe l'inchiostro senza motivo.
        media = sum(noti) / len(noti) if noti else 128.0
        mappa = Image.new("L", piccolo)
        mappa.putdata([min(255, int(255.0 * v[i] / p[i])) if p[i] else int(media)
                       for i in range(len(p))])

    mappa = mappa.filter(ImageFilter.GaussianBlur(1.2))
    return mappa.resize(ritaglio.size, Image.BICUBIC)


def _mediana(mappa):
    """La luminosita' MEDIANA di una mappa del fondo.

    Mediana e non media: su un tessuto a due toni la media cade in mezzo e non
    descrive nessuno dei due, mentre la mediana cade su quello che occupa piu'
    superficie -- che e' il fondo su cui il marchio sta davvero.
    """
    istogramma = mappa.histogram()
    quanti = sum(istogramma)
    if not quanti:
        return 128.0
    meta = quanti / 2.0
    corsa = 0
    for valore, n in enumerate(istogramma):
        corsa += n
        if corsa >= meta:
            return float(valore)
    return 128.0


def _adatta(pezzo, fondo):
    """Il marchio con l'inchiostro giusto per il fondo, e un alone che lo stacca.

    PERCHE' NON C'E' LA CARTELLA
    Fino a ROUND 47 dietro al marchio si disegnava una cartella crema con
    doppio bordo. Il logo ha DUE inchiostri, l'oro e il quasi-nero, e non
    esiste un fondo del catalogo su cui si leggano tutti e due: la cartella li
    staccava in un colpo solo. Ma su un collare copriva quasi tutto il nastro,
    e la proprietaria l'ha detta cosi': "il logo e' stato appiccicato con uno
    sfondo bianco gigantesco e non mi piace, vorrei solo il logo con la
    scritta".

    PERCHE' NON C'E' PIU' NEMMENO IL MOSAICO
    ROUND 48 aveva sostituito la cartella con una scelta PUNTO PER PUNTO: dove
    il tessuto e' scuro l'inchiostro diventa crema, dove e' chiaro resta nero.
    Su un fondo uniforme e' perfetto. Su un motivo no, e i motivi sono la
    regola: misurato sul riquadro del marchio dei 19 motivi bandana europei,
    in DODICI il tessuto sta da tutte e due le parti della soglia. Li' il
    marchio diventava un mosaico crema/nero -- la proprietaria l'ha visto e
    l'ha descritto cosi': "il logo e' scansionato di luminosita' in base a
    quale parte del design copre".

    COSA FA ADESSO, IN DUE MOSSE
    1. UN INCHIOSTRO SOLO per tutto il marchio, scelto dalla luminosita'
       mediana del tessuto sotto. Il marchio torna a essere un oggetto solo,
       come un marchio deve essere.
    2. UN CONTORNO morbido nel tono opposto, ricavato dalla sagoma del
       marchio stesso. Non e' la cartella: non ha lati, non e' un rettangolo,
       non ha una forma sua -- e' il profilo delle lettere e del medaglione
       che sfuma nel tessuto. E' cio' che regge dove un inchiostro solo non
       basterebbe: sui motivi a due toni, dove il marchio cade anche sul tono
       che gli somiglia.

       LA PRIMA VERSIONE DI QUESTO CONTORNO NON SERVIVA A NIENTE, e vale la
       pena dirlo perche' sembrava ovvio che servisse. Era la sagoma solo
       sfocata, disegnata SOTTO il marchio: dove il marchio e' opaco non si
       vede affatto. Misurato su un tessuto in maggioranza scuro con strisce
       chiare, guardando i pixel di scritta caduti sulle strisce, lo stacco
       era 8 con e 8 senza. Gonfiando la sfocatura (GUADAGNO_ALONE) il
       contorno esce invece DA SOTTO le lettere e le circonda: sulla fascia di
       bordo lo stacco passa da 40 a 142, contro i 60 richiesti. Una forma
       si legge dal suo profilo, non dal suo riempimento.

       E il contorno va STRETTO, non largo. A raggio 0,045 era una nuvola
       che copriva il tessuto -- la cartella un'altra volta, solo coi
       bordi sfumati -- e staccava 94. A 0,008, pieno invece che velato,
       il tessuto si rivede sotto il marchio e lo stacco sale a 142.
       Guardati affiancati sulla bandana marinara, i due non si
       somigliano nemmeno.

    L'ORO NON SI TOCCA, e vale la pena scriverlo perche' l'ho provato: far
    inseguire all'oro la soglia di contrasto, incupendolo in proporzione al
    fondo, migliora ogni numero -- sulla salvia i pixel sotto soglia scendono
    dal 51% al 2% -- e rovina il marchio. Dentro "l'oro" ci sono anche le luci
    della PERLA, e moltiplicarle per 0,3 le spegne: il medaglione diventa una
    macchia grigia. Il numero diceva meglio, l'occhio diceva peggio.
    """
    # Un fondo uniforme si accetta anche come numero: e' cosi' che si ragiona
    # quando si prova una regola sola alla volta ("il marchio su un antracite a
    # 40"), e obbligare a costruire un'immagine per dirlo renderebbe il codice
    # di prova meno leggibile del codice provato.
    luce = float(fondo) if not hasattr(fondo, "point") else _mediana(fondo)

    grigio = pezzo.convert("L")
    rgb = pezzo.convert("RGB")
    alfa = pezzo.getchannel("A")
    scuro = luce < FONDO_SCURO

    if scuro:
        # L'inchiostro quasi nero tirato verso il crema. Quanto ogni pixel e'
        # scuro, da 0 a 255, e' la forza con cui viene tirato: sfumata e non a
        # gradino, se no il bordo antialiasato delle lettere si stacca come un
        # ritaglio di carta.
        forza = grigio.point(
            lambda v: int(255 * (1.0 - v / float(SOGLIA_INCHIOSTRO)))
            if v < SOGLIA_INCHIOSTRO else 0)
        rgb = Image.composite(Image.new("RGB", pezzo.size, CREMA), rgb, forza)
        tono_alone = INCHIOSTRO_SCURO
    else:
        # L'oro incupito, il quasi-nero lasciato stare: sul chiaro si legge da
        # solo. Quanto incupire dipende da quanto e' chiaro il fondo.
        chiaro = grigio.point(lambda v: 255 if v >= SOGLIA_INCHIOSTRO else 0)
        cupezza = CUPEZZA_CHIARO if luce >= FONDO_CHIARISSIMO else CUPEZZA_MEDIO
        rgb = Image.composite(rgb.point(lambda v: int(v * cupezza)), rgb, chiaro)
        tono_alone = CREMA

    marchio_inchiostrato = rgb.convert("RGBA")
    marchio_inchiostrato.putalpha(alfa)

    # L'ALONE. La sagoma del marchio, sfocata e attenuata, nel tono opposto a
    # quello dell'inchiostro. Si disegna SOTTO, quindi dove il marchio e' opaco
    # non si vede affatto: esce solo intorno alle lettere e al medaglione, che
    # e' esattamente dove serve.
    raggio = max(1.0, ALONE_RAGGIO * pezzo.size[1])
    sagoma = alfa.filter(ImageFilter.GaussianBlur(raggio))
    sagoma = sagoma.point(
        lambda v: int(min(255, v * GUADAGNO_ALONE) * ALONE_OPACITA))
    fuori = Image.new("RGBA", pezzo.size, tono_alone + (0,))
    fuori.putalpha(sagoma)
    fuori.alpha_composite(marchio_inchiostrato)
    return fuori

def componi(immagine, tipo, percorso_marchio=None):
    """Disegna il marchio sul file di stampa gia' costruito.

    Torna (immagine, riquadri_usati). I riquadri servono ai test e all'audit
    per verificare che il marchio ci sia davvero e stia dove deve, senza
    doverlo cercare a occhio dentro un file da 15600 px.
    """
    base = immagine.convert("RGBA") if immagine.mode != "RGBA" else immagine.copy()
    logo = _marchio(percorso_marchio)
    box = riquadri(tipo, base.size, logo.size)

    for s, a, largo, alto in box:
        largo, alto = max(1, round(largo)), max(1, round(alto))
        # solo riduzione: riquadri() ha gia' impedito il caso contrario
        pezzo = logo.resize((largo, alto), Image.LANCZOS)
        # Il fondo si misura PRIMA di posare il marchio: dopo sarebbe coperto
        # proprio dove conta. E si misura riquadro per riquadro, non una volta
        # sola: sul collare il marchio si ripete otto volte lungo la fettuccia
        # e il motivo sotto cambia da un capo all'altro.
        sotto = base.convert("RGB").crop(
            (round(s), round(a), round(s) + largo, round(a) + alto))
        pezzo = _adatta(pezzo, _mappa_fondo(sotto))
        base.alpha_composite(pezzo, (round(s), round(a)))

    return base.convert("RGB"), box


# ==========================================================================
# LA TOPPA: RICONOSCERE UN MARCHIO APPOGGIATO SU UNA CARTELLA
# ==========================================================================
# Fino a ROUND 47 dietro al marchio si disegnava una cartella crema. Il codice
# non lo fa piu', ma i file gia' in catalogo sono piu' vecchi del codice: il 3
# settembre 2026, sui 48 prodotti Printify attivi, 11 bandane su 20, 7 cucce su
# 12 e 2 medagliette ce l'avevano ancora. Nessun controllo se n'era accorto,
# perche' tutti guardavano i DATI del prodotto (misure, copertura, livelli) e
# la cartella sta dentro i PIXEL.
#
# COME SI RICONOSCE, SENZA SAPERE CHE FORMA HA
# Una cartella incollata e' una regione grande, CHIARA e PIATTA -- piatta vuol
# dire che ogni punto somiglia ai suoi vicini -- dentro un motivo che intorno
# piatto non e'. Le due condizioni servono tutte e due: da sola, "chiara e
# piatta" segnalerebbe ogni disegno su fondo avorio. E' il CONFRONTO col
# tessuto intorno che distingue una cartella incollata da un tessuto chiaro.
TOPPA_CHIARA = 170     # sopra questa luminosita' un pixel e' "chiaro"
TOPPA_PIATTA = 6       # scarto dal proprio sfocato sotto il quale e' "piatto"
TOPPA_DENTRO = 0.30    # tanta di quella superficie dentro il riquadro
TOPPA_STACCO = 0.20    # e tanta di piu' che nell'anello intorno
#
# IL SECONDO SEGNALE, E PERCHE' SERVE
# Il confronto con l'anello non basta quando il tessuto intorno e' gia' chiaro
# e piatto: su "Ramo", "Nobile" e "Fiorellino" -- motivi pallidi su crema -- la
# cartella misura 0,494 dentro e 0,498 intorno, cioe' non stacca affatto.
# Misurato: da sola, la regola dell'anello prendeva 16 bandane su 19.
#
# Ma una cartella ha una cosa che un tessuto non ha: un BORDO DRITTO, lungo
# quanto lei. Contando per ogni colonna quanta parte dell'altezza fa un salto
# netto di luminosita', le undici bandane con la cartella danno tutte
# esattamente 0,455 -- e' il suo bordo -- mentre i motivi puliti vanno da 0,040
# a 0,770. Da solo nemmeno questo basterebbe (il motivo a cerchi "Vortice" fa
# 0,770), ma i due insieme si coprono a vicenda: il bordo dritto conta solo
# dentro una regione gia' chiara e piatta. Cosi' fanno 19 su 19.
# 0,42 e non 0,40: la cartella misura sempre 0,455-0,46 -- e' il suo bordo, e
# non dipende dal motivo -- mentre una cuccia damascata pallida ricostruita
# SENZA cartella arrivava a 0,400 esatti per via del suo stesso disegno. La
# soglia sta in mezzo, larga da tutte e due le parti.
TOPPA_BORDO = 0.42     # quanta altezza deve avere un bordo per essere "dritto"
TOPPA_SALTO = 18       # di quanto deve saltare la luminosita' per essere bordo


def _chiaro_e_piatto(ritaglio):
    """Quanti pixel sono chiari E piatti, e su quanti in tutto."""
    grigio = ritaglio.convert("L")
    scarto = ImageChops.difference(grigio, grigio.filter(ImageFilter.GaussianBlur(2)))
    maschera = ImageChops.multiply(
        grigio.point(lambda v: 255 if v >= TOPPA_CHIARA else 0),
        scarto.point(lambda v: 255 if v <= TOPPA_PIATTA else 0))
    return maschera.histogram()[255], grigio.width * grigio.height


def _linea_piu_lunga(salti, larghezza, altezza, per_colonne):
    """La frazione piu' alta di una colonna (o riga) che fa un salto netto."""
    dati = list(salti.getdata())
    meglio = 0.0
    if per_colonne:
        for x in range(larghezza):
            forti = sum(1 for y in range(altezza) if dati[y * larghezza + x] > TOPPA_SALTO)
            meglio = max(meglio, forti / float(altezza))
    else:
        for y in range(altezza):
            riga = dati[y * larghezza:(y + 1) * larghezza]
            forti = sum(1 for v in riga if v > TOPPA_SALTO)
            meglio = max(meglio, forti / float(larghezza))
    return meglio


def _bordo_dritto(ritaglio):
    """Quanto e' CHIUSO il bordo piu' netto dentro il riquadro, da 0 a 1.

    Si guarda in una miniatura a misura fissa: cosi' la soglia vale uguale su
    una bandana da 4275 px e su una medaglietta da 810, e la sfocatura del
    ridimensionamento spegne il rumore del tessuto senza spegnere un bordo
    vero, che e' lungo.

    PERCHE' SERVONO TUTTE E DUE LE DIREZIONI
    Con le sole colonne, il collare "marinara" -- righe verticali navy e crema,
    nessuna cartella -- misurava 1,00: una riga crema dentro il riquadro e'
    chiara e piatta come una cartella, e il suo bordo e' alto quanto tutto il
    riquadro. Era l'unico falso allarme su 62 motivi europei, e non e' un caso
    isolato: qualunque tessuto rigato lo darebbe.
    Una cartella pero' e' CHIUSA: ha un bordo verticale E uno orizzontale. Una
    riga ha solo il verticale. Prendendo il piu' DEBOLE dei due, la riga scende
    a quasi zero e la cartella resta alta.
    """
    grigio = ritaglio.convert("L").resize((120, 200), Image.BILINEAR)
    w, h = grigio.size
    vert = ImageChops.difference(grigio.crop((1, 0, w, h)), grigio.crop((0, 0, w - 1, h)))
    oriz = ImageChops.difference(grigio.crop((0, 1, w, h)), grigio.crop((0, 0, w, h - 1)))
    return min(_linea_piu_lunga(vert, w - 1, h, True),
               _linea_piu_lunga(oriz, w, h - 1, False))


def toppa(immagine, box, allarga=0.6):
    """C'e' una cartella incollata dietro al marchio? Torna la misura.

    Per ogni riquadro del marchio da' {"dentro", "intorno", "bordo", "toppa"}:
    quanto del riquadro e' chiaro-e-piatto, quanto lo e' l'anello di tessuto
    attorno, quanto e' lungo il bordo dritto piu' lungo, e il verdetto. L'anello si prende allargando il riquadro del 60% e
    togliendo il riquadro stesso -- ritagliato ai bordi dell'immagine, perche'
    PIL riempie di nero quello che sborda e il nero direbbe "tessuto scurissimo
    e mosso" proprio dove non c'e' tessuto affatto.

    Sola misura: non tocca l'immagine.
    """
    rgb = immagine.convert("RGB")
    W, H = rgb.size
    esiti = []
    for s, a, largo, alto in box:
        s, a = int(round(s)), int(round(a))
        largo, alto = max(1, int(round(largo))), max(1, int(round(alto)))
        dentro_n, dentro_tot = _chiaro_e_piatto(rgb.crop((s, a, s + largo, a + alto)))
        ms, ma = int(largo * allarga / 2), int(alto * allarga / 2)
        largo_box = (max(0, s - ms), max(0, a - ma),
                     min(W, s + largo + ms), min(H, a + alto + ma))
        fuori_n, fuori_tot = _chiaro_e_piatto(rgb.crop(largo_box))
        anello_tot = fuori_tot - dentro_tot
        dentro = dentro_n / float(max(1, dentro_tot))
        intorno = (fuori_n - dentro_n) / float(anello_tot) if anello_tot > 0 else dentro
        bordo = _bordo_dritto(rgb.crop((s, a, s + largo, a + alto)))
        esiti.append({
            "dentro": round(dentro, 3),
            "intorno": round(intorno, 3),
            "bordo": round(bordo, 3),
            # SERVONO TUTTE E DUE, non una qualunque. Prima bastava una delle
            # due e il collare "marinara" passava per cartella: uno degli otto
            # riquadri ripetuti lungo la fettuccia cadeva su una riga crema
            # larga, quindi "chiaro e piatto dentro, mosso intorno" -- ma di
            # cartella non c'era l'ombra, e il suo bordo infatti misura 0,00.
            #
            # Il bordo chiuso invece non manca MAI a una cartella vera: su
            # tutte quelle trovate -- 11 file Printify e 7 motivi europei --
            # misura 0,455-0,46, sempre, perche' e' il bordo della cartella e
            # non dipende dal tessuto che ha sotto. Farne una condizione
            # necessaria toglie il falso allarme senza perdere niente.
            #
            # `intorno` resta misurato e riportato: serve a capire un caso
            # guardando i numeri, anche se non entra piu' nel verdetto.
            "toppa": bool(dentro >= TOPPA_DENTRO and bordo >= TOPPA_BORDO),
        })
    return esiti


def presente(immagine, box, percorso_marchio=None, soglia=18.0):
    """Vero se nei riquadri indicati c'e' davvero il marchio.

    Confronta i pixel del file finito con il marchio ridisegnato sul fondo che
    quel file ha in quel punto. Serve al test: "il marchio c'e'" deve essere
    una misura, non una speranza -- e' esattamente il controllo che mancava
    quando bandane e medagliette sono rimaste senza.
    """
    if not box:
        return False
    logo = _marchio(percorso_marchio)
    rgb = immagine.convert("RGB")
    for s, a, largo, alto in box:
        largo, alto = max(1, round(largo)), max(1, round(alto))
        ritaglio = rgb.crop((round(s), round(a), round(s) + largo, round(a) + alto))
        pezzo = logo.resize((largo, alto), Image.LANCZOS)
        # L'INCHIOSTRO ATTESO DIPENDE DAL FONDO, quindi va ricavato anche qui.
        # Il fondo pero' adesso e' coperto dal marchio: lo si legge dove il
        # marchio e' trasparente, che e' esattamente il tessuto rimasto in
        # vista. Senza questo, dopo ROUND 47 presente() direbbe "manca" su ogni
        # prodotto scuro, perche' cerca un "Italia" nero che li' e' crema.
        alfa = pezzo.getchannel("A")
        vista = alfa.point(lambda v: 255 if v < ALFA_TRASPARENTE else 0)
        if vista.getbbox():
            pezzo = _adatta(pezzo, _mappa_fondo(ritaglio, vista))
        # dove il marchio e' opaco, il file finito deve somigliare al marchio
        maschera = alfa.point(lambda v: 255 if v > 200 else 0)
        if not maschera.getbbox():
            continue
        atteso = pezzo.convert("RGB")
        punti = [(p, q) for p, q, m in zip(
            ritaglio.getdata(), atteso.getdata(), maschera.getdata()) if m]
        if not punti:
            continue
        scarto = sum(abs(p[i] - q[i]) for p, q in punti for i in range(3)) / (3.0 * len(punti))
        if scarto > soglia:
            return False
    return True
