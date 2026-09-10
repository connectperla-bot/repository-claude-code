#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ricalca la SAGOMA di un pezzo dal mockup del fornitore.

PERCHE' ESISTE
snippets/perla-sagoma.liquid disegna sopra la tela dell'editor il contorno
vero del pezzo, cosi' chi personalizza vede dove finisce quello che scrive. I
tracciati di cerchio, cuore e osso della medaglietta erano stati ricalcati a
mano una volta sola, e il metodo era descritto a parole in quel file ma non
esisteva da nessuna parte come codice: rifarlo per un pezzo nuovo voleva dire
ricominciare da capo.

IL METODO, CHE E' QUELLO GIA' DOCUMENTATO
Si manda al fornitore un file a TINTA PIATTA grande quanto tutta l'area di
stampa dichiarata e si riscarica il mockup. Su quel mockup l'unica cosa scura
e' il pezzo: tutto il resto e' il fondo bianco dello studio fotografico. Il
contorno di quella macchia E' la sagoma -- non un disegno somigliante, la
forma vera fotografata dal fornitore.

  1. soglia sulla luminosita': dentro/fuori;
  2. si tiene la macchia piu' grande (le ombre staccate si buttano);
  3. si segue il bordo (traccia di Moore, otto direzioni);
  4. si semplifica (Douglas-Peucker) finche' il tracciato non e' leggibile
     senza perdere gli angoli;
  5. si normalizza sull'AREA DI STAMPA, non sul riquadro della macchia.

PERCHE' IL RIQUADRO DELLA MACCHIA NON BASTA -- ED E' IL PUNTO
La tela dell'editor ha il rapporto dell'AREA DI STAMPA dichiarata (la riga in
perla-print-areas.liquid), non quello del pezzo. Se la sagoma si normalizza
sul proprio riquadro, il contorno esce giusto di forma e sbagliato di posto:
misurato sul tappetino a osso, il pezzo ha rapporto 1,46 mentre l'area di
stampa e' 1,31, e chi personalizza vedrebbe il bordo dove non e'.

Il pezzo non riempie l'area di stampa: l'area dichiarata deborda tutto
intorno, e quello che cade fuori dalla sagoma il fornitore lo taglia. Sui due
tappetini il margine perso e' circa il 5% per lato in larghezza e l'8% in
altezza -- non e' un dettaglio, e' dove NON va messo il cammeo.

E allora a cosa serve la scacchiera: a misurare quel debordo. Si manda, con la
stessa tinta piatta, un file a scacchiera di passo noto (10 x 8 caselle) e si
riscarica il mockup. Le caselle si vedono anche dove il pezzo le taglia, e il
loro PASSO in pixel dice quanto e' grande sul mockup una casella dell'area di
stampa. Da li' l'area intera: passo x colonne, centrata sul pezzo -- il
fornitore centra sempre la grafica sulla sagoma, ed e' verificato su tutti e
due i pezzi, i centri cadono a due pixel l'uno dall'altro.

Le coordinate escono in millesimi, come le tre sagome che c'erano gia': con
preserveAspectRatio="none" il tracciato cade dove cade sul pezzo, qualunque
sia la larghezza della colonna.

SENZA SCACCHIERA
Si ricade sul riquadro della macchia, che e' giusto solo per i pezzi che
riempiono l'area di stampa da bordo a bordo (le medagliette). Lo script lo
dice a voce quando succede.

USO
    python3 scripts/perla-ricalca-sagoma.py sonda/piatto-73844.jpg --nome osso \
        --scacchiera sonda/scacchiera-73844.jpg --griglia 10x8
    python3 scripts/perla-ricalca-sagoma.py foto.jpg --nome pesce --tolleranza 3.5
"""
import argparse
import sys

from PIL import Image

VICINI = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def maschera(im, soglia):
    """Vero dove c'e' il pezzo. Il fondo dello studio e' bianco, il pezzo no."""
    g = im.convert("L")
    w, h = g.size
    px = g.load()
    return [[px[x, y] < soglia for x in range(w)] for y in range(h)], w, h


def macchia_piu_grande(m, w, h):
    """La componente connessa piu' grande: le ombre staccate si buttano."""
    visto = [[False] * w for _ in range(h)]
    migliore, misura_migliore = None, 0
    for y0 in range(h):
        for x0 in range(w):
            if not m[y0][x0] or visto[y0][x0]:
                continue
            pila, celle = [(x0, y0)], []
            visto[y0][x0] = True
            while pila:
                x, y = pila.pop()
                celle.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and m[ny][nx] and not visto[ny][nx]:
                        visto[ny][nx] = True
                        pila.append((nx, ny))
            if len(celle) > misura_migliore:
                misura_migliore, migliore = len(celle), celle
    if not migliore:
        sys.exit("Nessuna macchia trovata: la soglia e' sbagliata o il mockup e' vuoto.")
    dentro = [[False] * w for _ in range(h)]
    for x, y in migliore:
        dentro[y][x] = True
    return dentro, misura_migliore


def traccia(m, w, h):
    """Traccia di Moore: si segue il bordo tenendo il pieno sulla stessa mano."""
    partenza = None
    for y in range(h):
        for x in range(w):
            if m[y][x]:
                partenza = (x, y)
                break
        if partenza:
            break
    bordo = [partenza]
    x, y = partenza
    direzione = 0
    for _ in range(8 * w * h):
        trovato = False
        for k in range(8):
            d = (direzione + 6 + k) % 8
            nx, ny = x + VICINI[d][0], y + VICINI[d][1]
            if 0 <= nx < w and 0 <= ny < h and m[ny][nx]:
                x, y, direzione = nx, ny, d
                bordo.append((x, y))
                trovato = True
                break
        if not trovato:
            break
        if (x, y) == partenza and len(bordo) > 2:
            break
    return bordo


def semplifica(punti, tolleranza):
    """Douglas-Peucker: butta i punti che non cambiano la forma."""
    if len(punti) < 3:
        return punti
    inizio, fine = punti[0], punti[-1]
    dx, dy = fine[0] - inizio[0], fine[1] - inizio[1]
    lungh = (dx * dx + dy * dy) ** 0.5
    peggiore, distanza = 0, 0.0
    for i in range(1, len(punti) - 1):
        p = punti[i]
        if lungh == 0:
            d = ((p[0] - inizio[0]) ** 2 + (p[1] - inizio[1]) ** 2) ** 0.5
        else:
            d = abs(dy * p[0] - dx * p[1] + fine[0] * inizio[1] - fine[1] * inizio[0]) / lungh
        if d > distanza:
            peggiore, distanza = i, d
    if distanza <= tolleranza:
        return [inizio, fine]
    return (semplifica(punti[:peggiore + 1], tolleranza)[:-1]
            + semplifica(punti[peggiore:], tolleranza))



def _linee(cambi, tolleranza=3):
    """Raggruppa in linee le transizioni raccolte su tante scansioni."""
    cambi = sorted(cambi)
    linee, gruppo = [], [cambi[0]]
    for v in cambi[1:]:
        if v - gruppo[-1] <= tolleranza:
            gruppo.append(v)
        else:
            linee.append((sum(gruppo) / float(len(gruppo)), len(gruppo)))
            gruppo = [v]
    linee.append((sum(gruppo) / float(len(gruppo)), len(gruppo)))
    return linee


def _passo(linee, minimo=12):
    """Il passo della scacchiera: la spaziatura che si ripete.

    Fra le transizioni non ci sono solo i confini delle caselle: c'e' anche il
    BORDO del pezzo, e sul tappetino a osso il bordo e' una rientranza, quindi
    le scansioni verticali lo incontrano quasi sempre allo stesso posto e fa un
    gruppo forte come una casella. Partire dalla prima e dall'ultima linea e
    dividere -- che sarebbe la cosa ovvia -- misurava il passo dell'osso con
    quattro pixel di errore, cioe' il 4% sbagliato sull'area intera.

    Quindi non si sceglie: si vota. Ogni linea fa da ancora a turno, e vince
    quella su cui si allineano piu' linee a multipli interi del passo. I bordi
    del pezzo sono due, le caselle sette o nove: la maggioranza e' sempre delle
    caselle. Poi il passo si rifinisce ai minimi quadrati sulle sole linee che
    hanno votato, e i bordi restano fuori dal conto.
    """
    forti = [v for v, n in linee if n >= minimo]
    if len(forti) < 3:
        forti = [v for v, _ in linee]
    salti = sorted(forti[i + 1] - forti[i] for i in range(len(forti) - 1))
    if not salti:
        return None
    stima = salti[len(salti) // 2]
    if stima <= 0:
        return None

    migliore, quanti = None, 0
    for ancora in forti:
        gruppo = [v for v in forti
                  if abs((v - ancora) - round((v - ancora) / stima) * stima) < stima * 0.10]
        if len(gruppo) > quanti:
            migliore, quanti = gruppo, len(gruppo)
    if not migliore or len(migliore) < 2:
        return stima

    # Minimi quadrati su indice -> posizione: pendenza = passo.
    indici = [round((v - migliore[0]) / stima) for v in migliore]
    mi = sum(indici) / float(len(indici))
    mv = sum(migliore) / float(len(migliore))
    sopra = sum((indici[k] - mi) * (migliore[k] - mv) for k in range(len(migliore)))
    sotto = sum((i - mi) ** 2 for i in indici)
    return sopra / sotto if sotto else stima


def area_di_stampa(percorso, colonne, righe, centro):
    """Il riquadro dell'area di stampa in pixel del mockup.

    Ritorna (x0, y0, x1, y1). Il passo viene dalla scacchiera, il centro dal
    pezzo: il fornitore centra la grafica sulla sagoma.
    """
    im = Image.open(percorso).convert("RGB")
    w, h = im.size
    px = im.load()

    def rosso(p):
        r, g, b = p
        return r > 110 and g < 120 and b < 120

    def cambi(punti):
        s = [rosso(p) for p in punti]
        return [i for i in range(1, len(s)) if s[i] != s[i - 1]]

    orizzontali, verticali = [], []
    for y in range(int(h * 0.30), int(h * 0.70), 4):
        orizzontali += cambi([px[x, y] for x in range(w)])
    for x in range(int(w * 0.25), int(w * 0.75), 4):
        verticali += cambi([px[x, y] for y in range(h)])
    if not orizzontali or not verticali:
        sys.exit("Nella scacchiera non si vedono caselle: soglia o file sbagliato.")

    px_x = _passo(_linee(orizzontali))
    px_y = _passo(_linee(verticali))
    if not px_x or not px_y:
        sys.exit("Passo della scacchiera non misurabile.")
    larg, alt = px_x * colonne, px_y * righe
    cx, cy = centro
    return cx - larg / 2.0, cy - alt / 2.0, cx + larg / 2.0, cy + alt / 2.0


def main():
    a = argparse.ArgumentParser()
    a.add_argument("immagine")
    a.add_argument("--nome", default="sagoma")
    a.add_argument("--soglia", type=int, default=225,
                   help="sotto questa luminosita' e' pezzo, sopra e' fondo")
    a.add_argument("--tolleranza", type=float, default=2.5,
                   help="quanto si puo' semplificare, in pixel del mockup")
    a.add_argument("--scacchiera",
                   help="mockup della scacchiera dello STESSO pezzo, per misurare l'area di stampa")
    a.add_argument("--griglia", default="10x8",
                   help="caselle della scacchiera, colonne x righe (predefinito 10x8)")
    opz = a.parse_args()

    im = Image.open(opz.immagine)
    m, w, h = maschera(im, opz.soglia)
    m, celle = macchia_piu_grande(m, w, h)
    xs = [x for y in range(h) for x in range(w) if m[y][x]]
    ys = [y for y in range(h) for x in range(w) if m[y][x]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

    bordo = traccia(m, w, h)
    ridotto = semplifica(bordo, opz.tolleranza)

    if opz.scacchiera:
        colonne, righe = (int(v) for v in opz.griglia.lower().split("x"))
        rx0, ry0, rx1, ry1 = area_di_stampa(
            opz.scacchiera, colonne, righe, ((x0 + x1) / 2.0, (y0 + y1) / 2.0))
        print("area di stampa: %.1f,%.1f -> %.1f,%.1f (rapporto %.4f)"
              % (rx0, ry0, rx1, ry1, (rx1 - rx0) / (ry1 - ry0)), file=sys.stderr)
        print("il pezzo occupa il %.1f%% in larghezza e il %.1f%% in altezza"
              % (100.0 * (x1 - x0) / (rx1 - rx0), 100.0 * (y1 - y0) / (ry1 - ry0)),
              file=sys.stderr)
    else:
        print("SENZA SCACCHIERA: normalizzo sul riquadro del pezzo. Giusto solo "
              "se il pezzo riempie l'area di stampa bordo a bordo.", file=sys.stderr)
        rx0, ry0, rx1, ry1 = x0, y0, x1, y1

    larg = float(rx1 - rx0) or 1.0
    alt = float(ry1 - ry0) or 1.0
    punti = [(round(1000.0 * (px - rx0) / larg, 1), round(1000.0 * (py - ry0) / alt, 1))
             for px, py in ridotto]
    # Chiudere il giro: l'ultimo punto coincide col primo, e Z fa il resto.
    if punti and punti[0] == punti[-1]:
        punti = punti[:-1]

    d = "M" + " L".join("%s,%s" % p for p in punti) + " Z"
    print("%s: macchia %d px, riquadro %dx%d, contorno %d punti -> %d dopo la semplificazione"
          % (opz.nome, celle, x1 - x0 + 1, y1 - y0 + 1, len(bordo), len(punti)),
          file=sys.stderr)
    print("rapporto del pezzo: %.4f" % (float(x1 - x0) / (y1 - y0)), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
