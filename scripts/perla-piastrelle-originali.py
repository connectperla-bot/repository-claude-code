#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estrae la piastrella vera dai disegni originali, e la stende sul prodotto.

PERCHE' ESISTE
I disegni originali del catalogo sono belli: damascati d'oro su navy, acanti,
il cartiglio "PERLA ITALIA" e il monogramma PI dentro l'ornato. Il difetto che
si vedeva sul negozio -- motivi giganti tagliati sul collare, scritte mozzate
dal bordo, cuciture a meta' bandana -- non era del disegno. Era della SCALA,
del RITAGLIO e del CENTRAGGIO.

Un tentativo precedente li aveva sostituiti con motivi disegnati a codice.
Puliti, ripetibili, e molto piu' poveri: giudizio della titolare, "davvero
brutti, fatti a cavolo", ed era giusto. La strada e' l'opposto: tenere il
disegno originale e correggere quello che davvero non andava.

COME
Se un motivo si ripete, allora esiste un rettangolo -- il periodo -- che
contiene tutto il disegno. Ritagliato quello, si ottiene una piastrella che
si affianca senza giunzioni, perche' e' esattamente cio' che il disegno gia'
faceva al suo interno. Da li' in poi la si puo' portare a qualunque misura
fisica e stendere su qualunque area di stampa.

LE TRE REGOLE
  1. MAI SPECCHIARE. Su questi disegni la scritta e' dentro l'ornato, e
     specchiare la stampa rovesciata. Su un prodotto di lusso e' un difetto,
     non una texture. (Lo diceva gia' perla-file-stampa-motivi.py.)
  2. MAI INGRANDIRE. E' l'errore che ha impastato la linea americana: sorgenti
     1280x720 stirate fino a 12750x9750, dieci volte. Se la misura fisica
     richiesta comportasse di superare il 100%, si tiene il 100% e si
     accettano piu' ripetizioni. `stendi` lo impone, non lo raccomanda.
  3. LA GIUNZIONE SI TOCCA SOLO SE SERVE. Quando il periodo e' esatto, il
     ritaglio e' gia' ripetibile e non va sfiorato: qualita' perfetta, zero
     fantasmi. La fusione sfumata e' il ripiego per quando non lo e'.

IL MARCHIO, GRATIS
Affiancando piastrelle INTERE e allineando la griglia perche' divida la tela
(passo_intero in perla-scala-stampa.py), ogni cartiglio "PERLA ITALIA" resta
intero per costruzione. E riducendo la piastrella alla misura fisica giusta
diventa piccolo da solo. Le due cose che la titolare aveva chiesto -- piccolo
e mai tagliato -- vengono dal riuso, senza aggiungere niente.

USO
    from perla_piastrelle_originali import piastrella, stendi
    t, info = piastrella("generated-designs/motivi-stampa/_originali/bandana-barocco.jpg")
    im = stendi(t, "collare-eu", passo_cm=2.6)

Eseguito direttamente misura tutti gli originali e stampa la tabella.
"""
import importlib.util
import os
import sys

import numpy as np
from PIL import Image, ImageChops

Image.MAX_IMAGE_PIXELS = None

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ORIGINALI = os.path.join(RADICE, "generated-designs", "motivi-stampa", "_originali")


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scala = _modulo("perla_scala_stampa", os.path.join(QUI, "perla-scala-stampa.py"))

# Su quale lato si lavora per cercare il periodo. Piu' grande e' piu' preciso e
# piu' lento; 900 e' il compromesso gia' usato da periodo_relativo() in
# perla-usa-file-stampa.py, e sui 62 originali basta.
LAVORO = 900

# Il periodo non puo' essere piu' piccolo di un dodicesimo del lato: sotto
# quella soglia si aggancia alla grana della stampa invece che al motivo, ed
# e' l'errore che rendeva "periodici" disegni che non lo sono.
PERIODO_MINIMO = 1 / 12.0
# Ne' piu' grande di meta': oltre, non e' una ripetizione, e' l'immagine.
PERIODO_MASSIMO = 0.5


def _grigio(im, lato=LAVORO):
    g = im.convert("L")
    g.thumbnail((lato, lato), Image.LANCZOS)
    return np.asarray(g, dtype=np.float32)


def _scarto(a, passo, asse):
    """Quanto differisce l'immagine da se stessa spostata di `passo`.

    E' la misura su cui si regge tutto: sul periodo giusto il disegno si
    sovrappone a se stesso e lo scarto crolla. Si confronta l'immagine INTERA,
    non la sua proiezione su una riga: proiettando, un damascato fitto si
    appiattisce in una linea quasi costante e il minimo sparisce nel rumore.
    """
    if asse == 0:
        if passo >= a.shape[1]:
            return 1e9
        return float(np.abs(a[:, passo:] - a[:, :-passo]).mean())
    if passo >= a.shape[0]:
        return 1e9
    return float(np.abs(a[passo:, :] - a[:-passo, :]).mean())


def periodo_2d(im, minimo=PERIODO_MINIMO, massimo=PERIODO_MASSIMO):
    """Il periodo di ripetizione nei due assi, come frazione del lato.

    Torna (fx, fy, qualita_x, qualita_y). La qualita' e' lo scarto sul periodo
    scelto diviso lo scarto medio: 0 vuol dire ripetizione perfetta, vicino a
    1 vuol dire che quel periodo non spiega niente e il disegno non e'
    periodico su quell'asse.
    """
    a = _grigio(im)
    h, w = a.shape
    esiti = []
    for asse, n in ((0, w), (1, h)):
        p_min = max(4, int(n * minimo))
        p_max = max(p_min + 1, int(n * massimo))
        scarti = [(_scarto(a, p, asse), p) for p in range(p_min, p_max)]
        if not scarti:
            esiti.append((0.5, 1.0))
            continue
        media = sum(s for s, _ in scarti) / len(scarti)
        migliore, passo = min(scarti)
        qualita = migliore / media if media else 1.0
        esiti.append((passo / float(n), qualita))
    return esiti[0][0], esiti[1][0], esiti[0][1], esiti[1][1]


def _errore_giunzione(t, solo_x=False):
    """Quanto si nota la giunzione affiancando la piastrella a se stessa.

    Si confronta con la variazione INTERNA: su un damascato fitto un salto di
    dieci livelli e' invisibile, su un fondo quasi piatto si vede. Il numero
    che conta e' quindi il rapporto, non il valore assoluto.
    """
    a = np.asarray(t.convert("L"), dtype=np.float32)
    bordo_x = float(np.abs(a[:, -1] - a[:, 0]).mean())
    bordo_y = float(np.abs(a[-1, :] - a[0, :]).mean())
    dentro = float((np.abs(np.diff(a, axis=1)).mean() +
                    np.abs(np.diff(a, axis=0)).mean()) / 2)
    if dentro <= 0.01:
        return 999.0
    return (bordo_x if solo_x else max(bordo_x, bordo_y)) / dentro


def cucitura_morbida(t, banda=0.16, solo_x=False):
    """Rende ripetibile una piastrella che non lo e' del tutto.

    Si sfasa di meta' -- cosi' i bordi finiscono al centro -- e si fonde la
    croce di giunzione con una sfumatura. NON si specchia: specchiare
    stamperebbe la scritta rovesciata, che su questi disegni e' il difetto
    peggiore possibile.

    E' un ripiego, non la strada maestra: introduce un lieve raddoppio dove la
    sfumatura attraversa un dettaglio. Si applica solo quando il periodo non
    e' abbastanza esatto perche' il ritaglio si richiuda da solo.
    """
    w, h = t.size
    dy = 0 if solo_x else h // 2
    sfasata = ImageChops.offset(t, w // 2, dy)
    bw = max(1, int(w * banda))
    x = np.arange(w, dtype=np.float32)
    mx = np.clip(np.abs(x - w / 2.0) / bw, 0, 1)
    if solo_x:
        m = np.repeat(mx[None, :], h, axis=0)
    else:
        bh = max(1, int(h * banda))
        y = np.arange(h, dtype=np.float32)
        my = np.clip(np.abs(y - h / 2.0) / bh, 0, 1)
        m = np.minimum(mx[None, :], my[:, None])
    maschera = Image.fromarray((m * 255).astype(np.uint8), "L")
    return Image.composite(sfasata, ImageChops.offset(sfasata, w // 2, dy),
                           maschera)


# Sopra questo rapporto la giunzione si vede e va sfumata. Sotto, il ritaglio
# si richiude gia' da solo e toccarlo peggiorerebbe soltanto.
SOGLIA_GIUNZIONE = 2.6


def piastrella(percorso, forza_cucitura=False):
    """La piastrella ripetibile di questo originale, e come e' stata ottenuta.

    Torna (immagine, info). `info` porta il periodo trovato, la qualita' e se
    la giunzione e' stata sfumata: serve a decidere a colpo d'occhio quali
    originali sono usciti perfetti e quali no.
    """
    im = Image.open(percorso).convert("RGB")
    fx, fy, qx, qy = periodo_2d(im)
    W, H = im.size

    # LE STRISCE SI TRATTANO PER QUELLO CHE SONO.
    # Collare, guinzaglio e ciotola sono nastri: il disegno si ripete in
    # orizzontale e in verticale NON si ripete affatto, perche' in verticale
    # c'e' una fascia sola, spesso con bordino sopra e sotto. Misurato sui 43
    # originali a striscia: qualita' orizzontale 0,07-0,22 (ripetizione netta),
    # verticale 0,33-0,97 (nessuna). Cercare un periodo verticale su un nastro
    # significa ritagliare a meta' la fascia e perdere i bordini.
    # La piastrella di un nastro e' quindi ALTA QUANTO IL NASTRO.
    striscia = W / float(H) > 4.0

    # Quando la qualita' e' scarsa il periodo trovato non e' un periodo: e' il
    # minimo del rumore, e fidarsene ritaglia un francobollo arbitrario. Sulle
    # bandane -- che sono composizioni uniche, non ripetizioni: qualita' 0,8-0,98
    # su quasi tutte -- si prende invece meta' del disegno, che conserva la
    # composizione, e si sfuma la giunzione.
    fidarsi_x = qx < 0.55
    fidarsi_y = qy < 0.55

    pw = max(8, int(round(W * (fx if fidarsi_x else 0.5))))
    ph = H if striscia else max(8, int(round(H * (fy if fidarsi_y else 0.5))))
    # Dal centro: i bordi degli originali sono la parte piu' irregolare, e su
    # diversi c'e' una cornice che nel motivo non deve entrare.
    x0 = (W - pw) // 2
    y0 = (H - ph) // 2
    t = im.crop((x0, y0, x0 + pw, y0 + ph))

    err = _errore_giunzione(t, solo_x=striscia)
    cucita = False
    if forza_cucitura or err > SOGLIA_GIUNZIONE:
        # Su un nastro si sfuma SOLO in orizzontale: sfumare anche sopra e
        # sotto impasterebbe i bordini, che sono il bello della striscia.
        t = cucitura_morbida(t, solo_x=striscia)
        cucita = True
    return t, {"periodo": (pw, ph), "frazione": (fx, fy),
               "qualita": (qx, qy), "giunzione": err, "cucita": cucita,
               "striscia": striscia, "sorgente": (W, H)}


def _divisore(dimensione, passo, massimo):
    """Il passo che divide la tela un numero intero di volte, senza mai
    superare `massimo`.

    `passo_intero` da solo non basta e la prova lo ha dimostrato: arrotondando
    il numero di ripetizioni puo' restituire un passo PIU' GRANDE di quello
    chiesto -- su una ciotola americana usciva 375 px da una sorgente di 300,
    cioe' un ingrandimento del 25% introdotto proprio dalla funzione che
    doveva sistemare il centraggio. Qui, se il passo intero sfora, si passa al
    divisore successivo: piu' ripetizioni, ma nessun pixel inventato.
    """
    n = max(1, int(round(dimensione / float(passo))))
    while dimensione / float(n) > massimo:
        n += 1
    return dimensione / float(n)


def stendi(t, tipo, passo_cm, marchio=None):
    """Porta la piastrella alla misura fisica giusta e riempie l'area di stampa.

    Le tre correzioni che questo negozio aspettava, tutte qui dentro:

      la MISURA si sceglie in centimetri e diventa pixel diversi su ogni
      prodotto -- e' la ragione per cui il medaglione usciva gigante sul
      collare e invisibile sulla cuccia;

      il CENTRAGGIO viene da passo_intero: il passo si porta a dividere la
      tela un numero intero di volte, cosi' il bordo cade FRA due ripetizioni
      invece che a meta' motivo. E' il "decentrati" che si vedeva sul negozio,
      con i disegni interi da un lato e mozzi dall'altro;

      l'INGRANDIMENTO non e' permesso. Se la misura chiesta imponesse di
      superare il 100% della sorgente si tiene il 100%: meglio piu'
      ripetizioni che un disegno impastato.

    UN NASTRO NON SI IMPILA.
    Prima stesura: la piastrella veniva rimpicciolita finche' il suo passo
    stava due volte nel lato corto. Su una striscia da collare -- 2732x315 --
    significava dimezzarla e metterne due file una sopra l'altra sul nastro
    alto 2,5 cm. Ma quella striscia E' il nastro: ha i bordini sopra e sotto e
    va alta quanto l'area, ripetuta solo in orizzontale. Il caso si riconosce
    dalle proporzioni, di entrambe le parti, e non da una tabella da tenere
    aggiornata.
    """
    a = scala.AREE[tipo]
    tw, th = t.size
    nastro = (tw / float(th) > 4.0) and (a.px_w / float(a.px_h) > 4.0)

    if nastro:
        # Altezza piena se la sorgente ce la fa; se e' piu' bassa NON la si
        # stira -- si ripete anche in verticale. Prima stesura: `resize` alla
        # altezza dell'area comunque, che su una sorgente piu' bassa era un
        # ingrandimento mascherato. Trovato dalla prova, non a occhio.
        alt = min(a.px_h, th)
        larghezza = max(1, int(round(_divisore(a.px_w, tw * (alt / float(th)),
                                               massimo=tw))))
        piccola = t.resize((larghezza, alt), Image.LANCZOS)
        ripetizioni = max(1, int(round(a.px_w / float(larghezza))))
        scarto = abs(ripetizioni * larghezza - a.px_w)
    else:
        voluto = scala.passo_sicuro(tipo, scala.passo_px(tipo, passo_cm))
        # Mai oltre il 100%: comanda il lato corto della piastrella.
        passo = min(voluto, float(min(tw, th)))
        ph = _divisore(a.px_h, passo, massimo=th)
        pw = _divisore(a.px_w, ph * (tw / float(th)), massimo=tw)
        piccola = t.resize((max(1, int(round(pw))), max(1, int(round(ph)))),
                           Image.LANCZOS)
        ripetizioni = max(1, int(round(a.px_h / float(piccola.height))))
        scarto = abs(ripetizioni * piccola.height - a.px_h)

    fattore = piccola.height / float(th)
    tela = Image.new("RGB", (a.px_w, a.px_h))
    for x in range(0, a.px_w, piccola.width):
        for y in range(0, a.px_h, piccola.height):
            tela.paste(piccola, (x, y))
    if marchio:
        marchio(tela, tipo)
    # `scarto` e' di quanti pixel l'ultima ripetizione sfora o resta corta.
    # Non puo' essere sempre zero -- un collare e' alto 315 px e due file
    # intere di pixel non ci stanno in un numero dispari -- ma deve restare
    # nell'ordine del pixel: un pixel non si vede, mezzo motivo si'.
    return tela, {"scala": fattore, "ripetizioni": ripetizioni,
                  "scarto_px": scarto, "nastro": nastro}


def _tabella():
    files = sorted(f for f in os.listdir(ORIGINALI)
                   if f.lower().endswith((".jpg", ".png")))
    print("%-34s %11s %9s %9s %s" %
          ("originale", "periodo", "qualita", "giunzione", "esito"))
    perfetti = cuciti = 0
    for f in files:
        t, info = piastrella(os.path.join(ORIGINALI, f))
        if info["cucita"]:
            cuciti += 1
        else:
            perfetti += 1
        print("%-34s %5dx%-5d %4.2f/%4.2f %8.1f  %s" %
              (f[:34], info["periodo"][0], info["periodo"][1],
               info["qualita"][0], info["qualita"][1], info["giunzione"],
               "sfumata" if info["cucita"] else "esatta"))
    print("\n  %d piastrelle esatte, %d sfumate, su %d originali"
          % (perfetti, cuciti, len(files)))


if __name__ == "__main__":
    _tabella()
    sys.exit(0)
