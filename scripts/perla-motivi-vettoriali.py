#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I motivi Perla disegnati come codice, non come immagini.

PERCHE'
I file di stampa venivano da immagini 1200px ingrandite fino a 4125: nitidezza
misurata 10,4 contro i 50,9 degli assetti nativi. Ingrandire non aggiunge
dettaglio, e nessun filtro lo inventa.

Un motivo scritto in SVG non ha una risoluzione: ha delle forme. Lo si rende a
4125px o a 40.000, ed e' sempre alla misura giusta. E un <pattern> SVG si ripete
per costruzione -- niente giunte da nascondere, niente scritte specchiate. Erano
i due difetti che avevano fatto fallire le tre prove di affiancamento:
  specchio          nitidezza 69,5  ma il marchio si legge "AIJATI AA ITALIA"
  ripetizione secca nitidezza 69,7  ma giunta netta, salto 51/255
  ripetizione sfumata 68,7          ma giunta ancora visibile (3,1x)

COME SI RIPETE SENZA GIUNTE
Gli elementi si disegnano ANCHE sui quattro angoli del modulo. SVG ritaglia quel
che esce dal riquadro, e il modulo vicino disegna la meta' mancante: le due
meta' combaciano perche' sono lo stesso disegno. Per questo ogni motivo qui sotto
mette le sue forme in (0,0), (L,0), (0,L), (L,L) e al centro.

IL MARCHIO
Sta in un SECONDO pattern, con il modulo molto piu' largo di quello del motivo,
cosi' compare ogni tanto invece che in ogni cella. Non e' mai specchiato ne'
ruotato: e' testo, e il testo si legge in un verso solo.

Uso:
    python3 scripts/perla-motivi-vettoriali.py <cartella>
    python3 scripts/perla-motivi-vettoriali.py <cartella> --solo diamanti
    python3 scripts/perla-motivi-vettoriali.py <cartella> --area bandana-eu
"""
import math
import os
import sys

# --- aree di stampa reali dei fornitori -------------------------------------
# ripetizioni = quanti moduli sul lato CORTO.
#
# Questi numeri sono stati sbagliati due volte, in due direzioni opposte, e
# vale la pena lasciarne traccia.
#
# A 7 ripetizioni i bordi erano perfetti ma il motivo era vuoto: il dettaglio a
# scala di pixel segnava 2,8 contro i 34,1 di un assetto nativo. Allora sono
# saliti a 32, e la misura e' arrivata a 25,5 -- ma guardando le immagini
# l'ornato era sparito: il damasco era diventato una griglia di puntini,
# l'ulivo una maglia. Inseguire il numero aveva mangiato il disegno.
#
# Questi sono la via di mezzo, scelti guardando: su una bandana da 55cm, 12
# moduli fanno un motivo da 4,5cm -- il passo di una stampa tessile vera, dove
# l'ornato si riconosce da vicino e il campo resta fitto da lontano.
#
# La nitidezza non e' in gioco: qui non si ingrandisce niente, si rende da
# geometria. La densita' e' una scelta di disegno, non una misura da ottimizzare.
#
# Sulle fasce strette il lato corto e' l'altezza, quindi bastano poche
# ripetizioni verticali: la densita' la da' la lunghezza.
AREE = {
    "collare-printify":  (7257, 338, 1.9),
    "collare-eu":        (7169, 315, 1.9),
    "bandana-printify":  (4275, 2325, 7.5),
    "bandana-eu":        (4125, 4125, 12.0),
    "ciotola-eu":        (6496, 803, 3.0),
    "guinzaglio-eu":     (12389, 219, 1.5),
}

NAVY   = "#16223f"
ORO    = "#c9a24f"
ORO_CH = "#e2c48a"
BORDO  = "#5c1526"
CREMA  = "#f2ead9"
VERDE  = "#1f5d43"
SALVIA = "#9dba98"
NERO   = "#14161a"
ARG    = "#c8ccd4"
PETR   = "#14565c"
TERRA  = "#c96f4a"


# --- i motivi ---------------------------------------------------------------
# Ognuno restituisce (lato del modulo, elementi SVG, colore di fondo, colore
# del marchio). Le coordinate sono nel sistema del modulo: la scala la mette
# _componi() in base all'area.


def fondo(L, colore, fitto=5, dim=3.0, op=".3"):
    """Il tessuto di piccoli segni dietro al motivo principale.

    Ce l'hanno tutti i damaschi veri, e non e' decorazione: e' quello che fa
    sembrare ricco un tessuto invece che stampato. Serve anche a una cosa
    misurabile -- porta dettaglio alla scala del pixel, che senza restava
    quello di un'immagine sfocata (2,8 contro i 34,1 di un assetto nativo).

    I segni stanno su una griglia sfalsata e arrivano fino ai bordi del modulo,
    cosi' si incastrano con quelli dei moduli vicini senza mostrare la giunta.
    """
    p = []
    passo = L / fitto
    for i in range(fitto + 1):
        for j in range(fitto + 1):
            x = i * passo + (passo / 2 if j % 2 else 0)
            y = j * passo
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dim}" fill="{colore}" opacity="{op}"/>')
            p.append(f'<path d="M {x-dim*2.4:.1f} {y+passo/2:.1f} L {x:.1f} {y+passo/2-dim*1.5:.1f} '
                     f'L {x+dim*2.4:.1f} {y+passo/2:.1f} L {x:.1f} {y+passo/2+dim*1.5:.1f} Z" '
                     f'fill="{colore}" opacity="{op}"/>')
    return p

def diamanti():
    L, sf, tr = 240, NERO, ARG
    p = fondo(L, ARG, fitto=6, dim=2.4, op=".22")
    for dx, dy in ((0, 0), (L, 0), (0, L), (L, L), (L / 2, L / 2)):
        p.append(f'<path d="M {dx} {dy-70} L {dx+70} {dy} L {dx} {dy+70} L {dx-70} {dy} Z" fill="none" stroke="{tr}" stroke-width="3"/>')
        p.append(f'<path d="M {dx} {dy-30} L {dx+30} {dy} L {dx} {dy+30} L {dx-30} {dy} Z" fill="{tr}" opacity=".5"/>')
        p.append(f'<circle cx="{dx}" cy="{dy}" r="7" fill="{tr}"/>')
    return L, p, sf, ARG


def medaglioni():
    L, sf = 260, NAVY
    p = fondo(L, ORO_CH, fitto=6, dim=2.6, op=".26")
    for dx, dy in ((0, 0), (L, 0), (0, L), (L, L), (L / 2, L / 2)):
        p.append(f'<path d="M {dx} {dy-88} L {dx+88} {dy} L {dx} {dy+88} L {dx-88} {dy} Z" fill="none" stroke="{ORO}" stroke-width="4"/>')
        for a in range(4):
            ang = math.radians(90 * a)
            px, py = dx + math.cos(ang) * 40, dy + math.sin(ang) * 40
            p.append(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="26" ry="15" transform="rotate({90*a} {px:.1f} {py:.1f})" fill="none" stroke="{ORO_CH}" stroke-width="2.5"/>')
        p.append(f'<circle cx="{dx}" cy="{dy}" r="11" fill="{ORO}"/>')
    return L, p, sf, ORO


def damasco():
    """Reticolo a ogiva con palmetta: lo scheletro di ogni damasco."""
    L, sf, h = 300, BORDO, 150
    p = fondo(L, ORO, fitto=7, dim=2.6, op=".24")
    for dx in (0, L):
        for dy in (-L, 0, L):
            p.append(f'<path d="M {dx} {dy} C {dx-h*0.9} {dy+h*0.5}, {dx-h*0.9} {dy+h*1.5}, {dx} {dy+L} C {dx+h*0.9} {dy+h*1.5}, {dx+h*0.9} {dy+h*0.5}, {dx} {dy} Z" fill="none" stroke="{ORO}" stroke-width="3.5"/>')
    cx, cy = L / 2, L / 2
    for s in (1, -1):
        p.append(f'<path d="M {cx} {cy+s*52} C {cx+s*34} {cy+s*30}, {cx+s*42} {cy-s*6}, {cx} {cy-s*20} C {cx-s*42} {cy-s*6}, {cx-s*34} {cy+s*30}, {cx} {cy+s*52} Z" fill="{ORO}" opacity=".85"/>')
        for lato in (1, -1):
            p.append(f'<path d="M {cx} {cy+s*14} C {cx+lato*44} {cy+s*22}, {cx+lato*62} {cy+s*56}, {cx+lato*30} {cy+s*74}" fill="none" stroke="{ORO}" stroke-width="3"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="{ORO}"/>')
    return L, p, sf, ORO_CH


def tartan():
    L, sf = 240, "#173a2a"
    scuro, rosso = "#0d241a", "#a8322f"
    p = fondo(L, "#ffffff", fitto=8, dim=1.8, op=".10")
    for pos in (0, 120):
        p.append(f'<rect x="{pos}" y="0" width="46" height="{L}" fill="{scuro}"/>')
        p.append(f'<rect x="0" y="{pos}" width="{L}" height="46" fill="{scuro}" opacity=".62"/>')
    for pos, col, sp in ((60, rosso, 12), (180, ORO, 5)):
        p.append(f'<rect x="{pos}" y="0" width="{sp}" height="{L}" fill="{col}" opacity=".92"/>')
        p.append(f'<rect x="0" y="{pos}" width="{L}" height="{sp}" fill="{col}" opacity=".62"/>')
    return L, p, sf, ORO_CH


def marinara():
    """Righe a passo regolare: il modulo contiene due periodi interi da 80."""
    L, sf = 160, CREMA
    p = fondo(L, NAVY, fitto=6, dim=1.8, op=".16")
    for base in (0, 80):
        p.append(f'<rect x="0" y="{base}" width="{L}" height="34" fill="{NAVY}"/>')
        p.append(f'<rect x="0" y="{base+50}" width="{L}" height="7" fill="{ORO}"/>')
    return L, p, sf, NAVY


def chevron():
    L, sf = 200, PETR
    p = fondo(L, ORO_CH, fitto=6, dim=2.2, op=".2")
    for k in range(-1, 3):
        y = k * 100
        p.append(f'<path d="M 0 {y+60} L {L/2} {y} L {L} {y+60}" fill="none" stroke="{ORO}" stroke-width="10"/>')
        p.append(f'<path d="M 0 {y+92} L {L/2} {y+32} L {L} {y+92}" fill="none" stroke="{ORO}" stroke-width="3.5" opacity=".7"/>')
    return L, p, sf, ORO_CH


def onde():
    L, sf = 260, PETR
    p = fondo(L, ORO_CH, fitto=7, dim=2.2, op=".2")
    for k in range(-1, 5):
        y = k * 65
        p.append(f'<path d="M 0 {y+40} C {L*0.25} {y}, {L*0.25} {y+80}, {L*0.5} {y+40} C {L*0.75} {y}, {L*0.75} {y+80}, {L} {y+40}" fill="none" stroke="{ORO_CH}" stroke-width="5" opacity=".85"/>')
        p.append(f'<path d="M 0 {y+56} C {L*0.25} {y+16}, {L*0.25} {y+96}, {L*0.5} {y+56} C {L*0.75} {y+16}, {L*0.75} {y+96}, {L} {y+56}" fill="none" stroke="{ORO_CH}" stroke-width="2" opacity=".5"/>')
    return L, p, sf, ORO_CH


def minimal():
    L, sf = 180, "#2c2f36"
    p = fondo(L, ARG, fitto=6, dim=2.0, op=".18")
    for dx, dy in ((0, 0), (L, 0), (0, L), (L, L), (L / 2, L / 2)):
        p.append(f'<circle cx="{dx}" cy="{dy}" r="26" fill="none" stroke="{ARG}" stroke-width="2.5" opacity=".8"/>')
        p.append(f'<circle cx="{dx}" cy="{dy}" r="5" fill="{ARG}" opacity=".9"/>')
    return L, p, sf, ARG


def ulivo():
    """Rami d'ulivo su due file sfalsate, piu' i rami di bordo che completano
       quelli dei moduli vicini."""
    L, sf = 300, VERDE
    def ramo(x, y, rot):
        d = [f'<g transform="translate({x} {y}) rotate({rot})">',
             f'<path d="M -110 0 C -40 -18, 40 -18, 110 0" fill="none" stroke="{SALVIA}" stroke-width="4"/>']
        for i in range(-4, 5):
            fx = i * 26
            for s in (1, -1):
                d.append(f'<ellipse cx="{fx}" cy="{s*17}" rx="19" ry="8.5" transform="rotate({s*26} {fx} {s*17})" fill="{SALVIA}" opacity=".92"/>')
            if i % 2 == 0:
                d.append(f'<ellipse cx="{fx+13}" cy="0" rx="9" ry="12" fill="{CREMA}" opacity=".9"/>')
        d.append('</g>')
        return "".join(d)
    p = fondo(L, CREMA, fitto=7, dim=2.4, op=".18") + [
        ramo(L / 2, L * 0.25, -8), ramo(L / 2, L * 0.75, 8),
        ramo(0, L * 0.5, 8), ramo(L, L * 0.5, 8)]
    return L, p, sf, CREMA


# Non tutti i motivi vogliono lo stesso passo. "ulivo" e' un ramo lungo e
# orizzontale dentro un modulo quadrato: alla densita' degli altri i rami si
# accavallano e il campo diventa una maglia, non un uliveto. Gli serve piu'
# spazio. Il numero moltiplica le ripetizioni dell'area: sotto 1 = motivo piu'
# grande e piu' rado.
DENSITA = {"ulivo": 0.45, "marinara": 0.8}

MOTIVI = {
    "diamanti": diamanti, "medaglioni": medaglioni, "damasco": damasco,
    "tartan": tartan, "marinara": marinara, "chevron": chevron,
    "onde": onde, "minimal": minimal, "ulivo": ulivo,
}


# --- composizione -----------------------------------------------------------

def _componi(nome, w, h, ripetizioni):
    lato, elementi, sfondo, col_marchio = MOTIVI[nome]()
    ripetizioni = max(1.0, ripetizioni * DENSITA.get(nome, 1.0))
    scala = (min(w, h) / ripetizioni) / lato
    tile = lato * scala
    corpo = "\n".join("        " + e for e in elementi)

    # Il marchio in un pattern suo, con modulo molto piu' largo: compare ogni
    # tanto e resta dritto. Il corpo si scala col motivo perche' la scritta
    # deve stare in proporzione al disegno, non alla pagina.
    tile_m = tile * 3.5
    corpo_alto = tile_m * 0.5
    dim = tile * 0.115

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <pattern id="motivo" width="{tile:.3f}" height="{tile:.3f}" patternUnits="userSpaceOnUse">
      <rect width="{tile:.3f}" height="{tile:.3f}" fill="{sfondo}"/>
      <g transform="scale({scala:.6f})">
{corpo}
      </g>
    </pattern>
    <pattern id="marchio" width="{tile_m:.3f}" height="{tile_m:.3f}" patternUnits="userSpaceOnUse">
      <text x="{tile_m/2:.1f}" y="{corpo_alto:.1f}" font-family="Georgia,'Times New Roman',serif"
            font-size="{dim:.2f}" letter-spacing="{dim*0.28:.2f}" fill="{col_marchio}"
            opacity=".92" text-anchor="middle">PERLA ITALIA</text>
    </pattern>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#motivo)"/>
  <rect width="{w}" height="{h}" fill="url(#marchio)"/>
</svg>'''


def produci(nome, cartella, aree=None):
    import cairosvg
    fatti = []
    for area in (aree or list(AREE)):
        w, h, rip = AREE[area]
        svg = _componi(nome, w, h, rip)
        base = os.path.join(cartella, f"perla-{nome}-{area}")
        open(base + ".svg", "w", encoding="utf-8").write(svg)
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base + ".png",
                         output_width=w, output_height=h)
        fatti.append((nome, area, base + ".svg", base + ".png", w, h))
    return fatti


def main():
    cartella = sys.argv[1]
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    area = sys.argv[sys.argv.index("--area") + 1] if "--area" in sys.argv else None
    os.makedirs(cartella, exist_ok=True)
    for n in ([solo] if solo else list(MOTIVI)):
        for _, a, svg, png, w, h in produci(n, cartella, [area] if area else None):
            print("%-40s svg %4d kB   png %6d kB   %dx%d" % (
                os.path.basename(png), os.path.getsize(svg) // 1024,
                os.path.getsize(png) // 1024, w, h))


if __name__ == "__main__":
    main()
