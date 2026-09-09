#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le aree per variante, e i template che le usano.

PERCHE' ESISTE
La proprietaria ha guardato l'editor della medaglietta incisa e ha scritto:
"il cerchio e' un ovale e le altre due forme proprio non si aprono". La causa
era una sola: la tabella dei tipi tiene UN rapporto per tipo, e le tre
medagliette hanno tre aree diverse (756x907, 756x827, 744x496). Con il
rapporto mediano il tondo esce ovale, e l'osso -- 1,50 contro 0,91 -- sarebbe
uscito schiacciato del 65% IN STAMPA, che e' peggio.

snippets/perla-forme-varianti.liquid rimette i numeri veri, uno per variante.
Ma quei numeri vengono dal fornitore, e il fornitore li cambia senza dirlo:
se un domani l'osso diventa 800x500 e la tabella resta 744x496, l'editor torna
a mentire e nessuno se ne accorge fino al primo reso. Quindi qui la tabella si
confronta con i blueprint versionati in printify-blueprints/, che sono la
stessa fonte da cui li ho letti.

E si controlla che i template si chiudano: la tabella nuova ha portato dentro
main-product.liquid un for con un continue e un break, e uno snippet nuovo con
un case dentro cui vive un if. Un tag non chiuso li' non e' un errore
silenzioso -- e' la pagina prodotto che non si apre piu'.
"""
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
TEMA = os.path.join(RADICE, "theme")
BLUEPRINT = os.path.join(RADICE, "printify-blueprints")

superate = 0
fallite = []


def prova(titolo, funzione):
    global superate
    try:
        funzione()
        superate += 1
        print("  ok   " + titolo)
    except AssertionError as e:
        fallite.append((titolo, str(e)))
        print("  NO   %s\n       %s" % (titolo, e))


def leggi(percorso):
    with open(percorso, "rb") as fh:
        return fh.read().decode("utf-8")


def righe_forme():
    """Le righe della tabella, gia' spezzate in colonne."""
    testo = leggi(os.path.join(TEMA, "snippets", "perla-forme-varianti.liquid"))
    dati = re.sub(r"\{%-?\s*comment.*?endcomment\s*-?%\}", "", testo, flags=re.S)
    fuori = []
    for riga in dati.strip().split("#"):
        riga = riga.strip()
        if not riga:
            continue
        cols = riga.split("|")
        assert len(cols) >= 5, "riga malformata: %r" % riga
        fuori.append(cols)
    return fuori


# I tre blueprint e la posizione di stampa da cui leggere l'area. Sono gli
# stessi di scripts/perla-usa-prodotti-nuovi.py: se la' cambia il fornitore,
# qui il file non si trova piu' e il test lo dice invece di passare a vuoto.
SORGENTE = {
    "medaglietta_incisa": ("10674_228.json", "front"),
    "collare_pelle": ("10700_217.json", "front"),
    "giacchetto": ("10740_72.json", "back_dtf"),
}


def aree_del_fornitore(tipo):
    """{valore dell'opzione: (larghezza, altezza)} dal blueprint versionato."""
    nome, posizione = SORGENTE[tipo]
    dati = json.loads(leggi(os.path.join(BLUEPRINT, nome)))
    fuori = {}
    for v in dati["variants"]:
        # il titolo e' "Circle / Black / One size": la prima parola-chiave e'
        # la forma o la taglia, ed e' quella su cui la tabella fa combaciare
        pezzi = [p.strip() for p in v["title"].split("/")]
        for ph in v.get("placeholders", []):
            if ph["position"] != posizione:
                continue
            for pezzo in pezzi:
                fuori.setdefault(pezzo, set()).add((ph["width"], ph["height"]))
    return fuori


def ogni_riga_ha_l_area_del_fornitore():
    for cols in righe_forme():
        tipo, valore = cols[0], cols[1]
        larg, alt = int(cols[2]), int(cols[3])
        vere = aree_del_fornitore(tipo)
        assert valore in vere, "%s: l'opzione %r non esiste sul blueprint" % (tipo, valore)
        assert vere[valore] == {(larg, alt)}, (
            "%s / %s: in tabella %dx%d, dal fornitore %s"
            % (tipo, valore, larg, alt, sorted(vere[valore])))


def ogni_variante_del_fornitore_ha_la_sua_riga():
    """Nessuna variante deve restare senza area: resterebbe col rapporto
    mediano, cioe' col difetto che questa tabella e' nata per chiudere."""
    for tipo, (nome, posizione) in SORGENTE.items():
        coperte = set(c[1] for c in righe_forme() if c[0] == tipo)
        dati = json.loads(leggi(os.path.join(BLUEPRINT, nome)))
        for v in dati["variants"]:
            if not any(ph["position"] == posizione for ph in v.get("placeholders", [])):
                continue
            pezzi = [p.strip() for p in v["title"].split("/")]
            assert coperte & set(pezzi), (
                "%s: la variante %r non trova nessuna riga" % (tipo, v["title"]))


def nessuna_opzione_vale_per_due_righe():
    """Se due righe dello stesso tipo rispondono allo stesso valore, quale
    vince dipende dall'ordine: un'ambiguita' che si paga in stampa."""
    visti = {}
    for cols in righe_forme():
        chiave = (cols[0], cols[1])
        assert chiave not in visti, "riga doppia per %s / %s" % chiave
        visti[chiave] = True


def la_finestra_sta_dentro_l_area():
    for cols in righe_forme():
        sx, alto, dx, basso = [float(x) for x in cols[4].split(",")]
        dove = "%s / %s" % (cols[0], cols[1])
        assert 0 <= sx < dx <= 100, "%s: finestra orizzontale %s" % (dove, cols[4])
        assert 0 <= alto < basso <= 100, "%s: finestra verticale %s" % (dove, cols[4])
        # una finestra sotto un quinto dell'area non e' una finestra, e'
        # un'area sbagliata: meglio accorgersene qui
        assert (dx - sx) >= 20 and (basso - alto) >= 20, (
            "%s: finestra troppo piccola (%s)" % (dove, cols[4]))


def le_sagome_disegnate_sono_quelle_dichiarate():
    """Ogni sagoma nominata nella tabella deve avere il suo tracciato, e
    viceversa: un nome senza disegno lascia il rettangolo di prima senza
    dirlo."""
    testo = leggi(os.path.join(TEMA, "snippets", "perla-sagoma.liquid"))
    disegnate = set(re.findall(r"\{%-?\s*when\s+'([a-z]+)'", testo))
    nominate = set(c[5] for c in righe_forme() if len(c) > 5 and c[5])
    assert nominate <= disegnate, "sagome senza tracciato: %s" % sorted(nominate - disegnate)
    assert disegnate <= nominate, "tracciati che nessuno usa: %s" % sorted(disegnate - nominate)


def ogni_tracciato_sta_nel_suo_riquadro():
    """Le coordinate sono in millesimi dell'area. Qualche pixel fuori e'
    normale (il contorno del pezzo tocca il bordo, e sull'osso lo supera);
    molto fuori vuol dire tracciato preso da un'immagine di misura diversa."""
    testo = leggi(os.path.join(TEMA, "snippets", "perla-sagoma.liquid"))
    for forma, d in re.findall(r"when\s+'([a-z]+)'.*?<path d=\"([^\"]+)\"", testo, re.S):
        numeri = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
        assert numeri, "%s: tracciato vuoto" % forma
        assert min(numeri) > -30, "%s: esce di %g dal riquadro" % (forma, -min(numeri))
        assert max(numeri) < 1030, "%s: esce di %g dal riquadro" % (forma, max(numeri) - 1000)
        assert len(numeri) >= 40, "%s: solo %d coordinate, non e' una sagoma" % (forma, len(numeri))


# --------------------------------------------------------------------------
# I template si chiudono
# --------------------------------------------------------------------------

APRONO = ("if", "unless", "for", "case", "capture", "comment", "form",
          "paginate", "tablerow", "schema", "style", "javascript")


def conta(nomi, pila, dove):
    """Impila chi apre, spila chi chiude, e pretende che coincidano."""
    for tag in nomi:
        if tag in APRONO:
            pila.append(tag)
        elif tag.startswith("end") and tag[3:] in APRONO:
            atteso = tag[3:]
            assert pila, "%s: %s di troppo" % (dove, tag)
            aperto = pila.pop()
            assert aperto == atteso, "%s: aperto %s, chiuso %s" % (dove, aperto, tag)


def blocchi_bilanciati(percorso):
    dove = os.path.basename(percorso)
    testo = leggi(percorso)
    # Dentro {% comment %} puo' esserci qualsiasi cosa, anche un "endif"
    # scritto in mezzo a una frase: va tolto prima di contare.
    testo = re.sub(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", "",
                   testo, flags=re.S)

    # {% liquid %} non e' un blocco: non ha un endliquid, e dentro le
    # istruzioni si scrivono nude, una per riga. Si contano a parte -- e
    # anche li' i commenti vanno tolti prima, perche' sono in italiano e una
    # riga puo' cominciare per "for" o "if" senza esserlo.
    for corpo in re.findall(r"\{%-?\s*liquid\b(.*?)-?%\}", testo, flags=re.S):
        corpo = re.sub(r"^\s*comment\b.*?^\s*endcomment\b", "", corpo,
                       flags=re.S | re.M)
        pila = []
        conta((r.strip().split()[0] for r in corpo.splitlines() if r.strip()),
              pila, dove + " (liquid)")
        assert not pila, "%s: dentro {%% liquid %%} restano aperti %s" % (dove, pila)
    testo = re.sub(r"\{%-?\s*liquid\b.*?-?%\}", "", testo, flags=re.S)

    pila = []
    conta((m.group(1) for m in re.finditer(r"\{%-?\s*(\w+)", testo)), pila, dove)
    assert not pila, "%s: restano aperti %s" % (dove, pila)


TEMPLATE = [os.path.join(TEMA, "sections", "main-product.liquid"),
            os.path.join(TEMA, "snippets", "perla-photo-customizer-side.liquid"),
            os.path.join(TEMA, "snippets", "perla-sagoma.liquid"),
            os.path.join(TEMA, "snippets", "perla-forme-varianti.liquid")]


def i_template_si_chiudono():
    for p in TEMPLATE:
        blocchi_bilanciati(p)


def la_sagoma_riceve_tutto_quello_che_le_serve():
    """Il render dello snippet deve passargli i sei parametri: uno che manca
    diventa nil, e nil in Liquid non e' un errore -- e' un riquadro che
    scompare senza dire niente."""
    voluti = ("photo_type", "sagoma", "fin_sx", "fin_alto", "fin_dx", "fin_basso")
    trovati = 0
    for p in TEMPLATE[:2]:
        for chiamata in re.findall(r"render 'perla-sagoma'[^%]*", leggi(p)):
            trovati += 1
            for v in voluti:
                assert (v + ":") in chiamata, "%s: manca %s" % (os.path.basename(p), v)
    assert trovati == 2, "attese 2 chiamate a perla-sagoma, trovate %d" % trovati


def il_foglio_di_stile_e_il_codice_si_caricano():
    testo = leggi(TEMPLATE[0])
    assert "perla-forma.css" in testo, "il foglio di stile della sagoma non si carica"
    assert "perla-forma.js" in testo, "il codice della sagoma non si carica"
    for nome in ("perla-forma.css", "perla-forma.js"):
        assert os.path.exists(os.path.join(TEMA, "assets", nome)), "manca assets/%s" % nome


def le_frasi_nuove_esistono_nelle_due_lingue():
    for lingua in ("it.default.json", "en.json"):
        testo = leggi(os.path.join(TEMA, "locales", lingua))
        for chiave in ("finestra_nota", "forma_avviso", "type_incisione"):
            assert ('"%s"' % chiave) in testo, "%s: manca %s" % (lingua, chiave)


print("La tabella dice quello che dice il fornitore")
prova("ogni riga ha l'area del fornitore", ogni_riga_ha_l_area_del_fornitore)
prova("ogni variante del fornitore ha la sua riga",
      ogni_variante_del_fornitore_ha_la_sua_riga)
prova("nessuna opzione vale per due righe", nessuna_opzione_vale_per_due_righe)
prova("la finestra sta dentro l'area", la_finestra_sta_dentro_l_area)

print("\nLe sagome")
prova("le sagome disegnate sono quelle dichiarate",
      le_sagome_disegnate_sono_quelle_dichiarate)
prova("ogni tracciato sta nel suo riquadro", ogni_tracciato_sta_nel_suo_riquadro)

print("\nI template")
prova("i template si chiudono", i_template_si_chiudono)
prova("la sagoma riceve tutto quello che le serve",
      la_sagoma_riceve_tutto_quello_che_le_serve)
prova("il foglio di stile e il codice si caricano",
      il_foglio_di_stile_e_il_codice_si_caricano)
prova("le frasi nuove esistono nelle due lingue",
      le_frasi_nuove_esistono_nelle_due_lingue)

print("\n%d verifiche superate." % superate)
if fallite:
    print("%d FALLITE" % len(fallite))
    sys.exit(1)
