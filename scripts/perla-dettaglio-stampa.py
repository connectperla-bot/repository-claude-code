#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La foto nitida del tessuto di collari e guinzagli, presa dal file di stampa.

PERCHE' ESISTE
La titolare ha scritto: "i collari e guinzagli sono spesso sgranati a causa
del design lungo e schiacciato". Ha ragione su cosa si vede, ma la causa non
e' la stampa: e' la FOTO.

    file di stampa del collare      7169 x  315 px  (216 dpi)
    file di stampa del guinzaglio  12389 x  219 px
    mockup Printful                 1000 x 1000 px, sempre

Il mockup e' l'unica cosa che Printful sa fare, e la fa a 1000 px: dentro ci
sta un nastro lungo ventidue volte la sua altezza, quindi la fettuccia esce
alta un'ottantina di pixel. Misurato sul collare "Barocco": la fettuccia
occupa 90 px nel mockup e 315 px nel file di stampa, cioe' il cliente guarda
un TERZO E MEZZO dei dettagli che riceve. Il prodotto e' nitido; la sua
fotografia no.

COSA NON FUNZIONA, PROVATO
  * ingrandire il mockup con un filtro di nitidezza: gia' fatto in
    perla-eu-foto-mockup.py (w_2400,e_sharpen:100). Il gradiente medio passa
    da 15,24 a 16,10. Recupera qualcosa, ma i pixel mancano e nessun filtro
    li inventa;
  * chiedere a Printful un mockup piu' grande: create-task non ha un
    parametro di larghezza, i mockup sono 1000x1000 e basta;
  * il gruppo di stili "Product details" del catalogo 749: sono fotografie
    della BUSTA di spedizione, con la scritta "WARNING plastic bags can be
    dangerous". Guardate;
  * gli stili "Lifestyle": il collare e' arrotolato su un tavolo e occupa
    MENO frazione di inquadratura del mockup piatto che c'e' gia'.

COSA FA QUESTO
Ritaglia dal file di stampa, a risoluzione NATIVA e senza nessun
ingrandimento, tre (o quattro) strisce larghe quanto la tela e alte quanto la
fettuccia, prese da punti lontani fra loro del disegno, e le posa su una tela
1000x1000 con l'aria bianca fra l'una e l'altra -- lo stesso bianco su cui
stanno tutte le altre foto del catalogo, cosi' la galleria resta uniforme.

Ogni pixel della foto e' un pixel del file che si stampa: nessuna
interpolazione, nessuna invenzione. E' la massima nitidezza possibile.

TRE STRISCE E NON UNA
Una striscia sola lascia 685 px di bianco su 1000 e sembra un banner. Tre
riempiono l'inquadratura e -- prese da un terzo, due terzi e fine del file --
mostrano tre porzioni DIVERSE del disegno, non tre copie: su un motivo che si
ripete ogni 1741 px e' materiale davvero diverso.

USO
    python3 scripts/perla-dettaglio-stampa.py                 # elenco, non tocca
    python3 scripts/perla-dettaglio-stampa.py --costruisci
    python3 scripts/perla-dettaglio-stampa.py --costruisci --carica
    python3 scripts/perla-dettaglio-stampa.py --costruisci --solo barocco,onda

--carica ospita le immagini sulla stessa strada gia' in uso (la rotta /upload
del servizio, che e' anche l'unica URL che urlCompositoValida accetta) e
scrive generated-designs/dettaglio-da-attaccare.json. ATTACCARLE non lo fa
questo script: come perla-eu-foto-shopify.py, prepara l'input e lo lascia
leggere prima che tocchi il catalogo, perche' un token Admin di Shopify non
sta in config/printify.local.env e non ci deve stare.
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
PRODOTTI = os.path.join(QUI, "perla-eu-prodotti.json")
CACHE = os.path.join(RADICE, "generated-designs", "dettagli-stampa")
USCITA = os.path.join(RADICE, "generated-designs", "dettaglio-da-attaccare.json")
UPLOAD = "https://perla-upload-endpoint-yizy.onrender.com/upload"

LATO = 1000
# I tipi che soffrono lo schiacciamento: nastri lunghissimi e bassi. La bandana
# e' quadrata e la ciotola e' 8:1, e a 1000 px si vedono benissimo tutte e due.
TIPI = ("collare-eu", "guinzaglio-eu")
# L'aria MINIMA fra una striscia e l'altra: serve perche' si legga che sono
# porzioni distinte e non un unico pezzo di carta da parati. E' un minimo e non
# una misura fissa perche' decide quante strisce entrano: a 24 px sul collare
# ce ne stavano due e restavano 300 px di bianco in fondo, a 12 ne entrano tre
# e la tela e' piena. Lo spazio vero viene poi ripartito su quello che avanza.
ARIA = 12


def catalogo(solo=None):
    with open(PRODOTTI) as fh:
        dati = json.load(fh)
    fuori = []
    for v in dati:
        if not any(v["handle"].startswith(t) for t in TIPI):
            continue
        # La base neutra dello studio di personalizzazione e' un fondo piatto:
        # una foto del suo tessuto non direbbe niente a nessuno.
        if "crea-il-tuo-design" in v["handle"]:
            continue
        if solo and not any(s in v["handle"] for s in solo):
            continue
        fuori.append(v)
    return fuori


def scarica(voce):
    os.makedirs(CACHE, exist_ok=True)
    percorso = os.path.join(CACHE, voce["handle"] + "-stampa.jpg")
    if not os.path.exists(percorso):
        r = subprocess.run(["curl", "-sSL", "-m", "300", "-o", percorso,
                            voce["pattern"]], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(percorso):
            raise RuntimeError("non scaricato: %s" % (r.stderr[:150] or voce["pattern"]))
    return percorso


def quante_strisce(altezza):
    """Quante fettucce alte `altezza` px entrano nella tela, con l'aria.

    Il collare e' alto 315 e ce ne stanno tre; il guinzaglio e' alto 219 e ce
    ne stanno quattro. Non e' una costante perche' i due nastri hanno misure
    diverse e fissarne una lascerebbe mezzo riquadro vuoto su uno dei due.
    """
    n = 1
    while (n + 1) * altezza + (n + 2) * ARIA <= LATO:
        n += 1
    return n


def dettaglio(percorso):
    """La tela 1000x1000 col tessuto a grandezza naturale, e quanto si guadagna.

    Torna (immagine, quante strisce, ingrandimento). L'ingrandimento e' sempre
    1.0 per costruzione: se un giorno non lo fosse, il ritaglio starebbe
    inventando pixel e la foto tornerebbe sgranata come quella che sostituisce.
    """
    im = Image.open(percorso).convert("RGB")
    w, h = im.size
    if w <= LATO:
        raise RuntimeError("il file di stampa e' largo %d px: non c'e' niente "
                           "da ritagliare a 1:1" % w)
    alta = min(h, LATO - 2 * ARIA)
    n = quante_strisce(alta)
    vuoto = (LATO - n * alta) // (n + 1)
    tela = Image.new("RGB", (LATO, LATO), (255, 255, 255))
    for i in range(n):
        # punti lontani fra loro: cosi' le strisce mostrano parti diverse del
        # disegno invece della stessa ripetizione tre volte
        x0 = int(round(i * (w - LATO) / float(max(1, n - 1))))
        tela.paste(im.crop((x0, 0, x0 + LATO, alta)), (0, vuoto + i * (alta + vuoto)))
    return tela, n, 1.0


def ospita(percorso):
    r = subprocess.run(["curl", "-s", "-m", "300", "-X", "POST", UPLOAD,
                        "-F", "photo=@" + percorso], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("risposta illeggibile da /upload: " + r.stdout[:200])
    url = d.get("url") or d.get("secure_url") or (d.get("data") or {}).get("url")
    if not url:
        raise RuntimeError("nessuna URL da /upload: " + json.dumps(d)[:200])
    return url


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--costruisci", action="store_true")
    ap.add_argument("--carica", action="store_true")
    ap.add_argument("--solo", help="sottostringhe di handle separate da virgola")
    args = ap.parse_args()

    solo = [s for s in (args.solo or "").split(",") if s] or None
    voci = catalogo(solo)
    if not voci:
        raise SystemExit("nessun prodotto scelto")
    if args.carica and not args.costruisci:
        raise SystemExit("--carica va usato insieme a --costruisci")

    if not args.costruisci:
        for v in voci:
            print("%-58s %s" % (v["handle"][:58], v["title"]))
        print("\n%d fra collari e guinzagli (--costruisci per fare le foto)"
              % len(voci))
        return

    os.makedirs(CACHE, exist_ok=True)
    fatte = []
    for i, v in enumerate(voci, 1):
        try:
            stampa = scarica(v)
            tela, n, scala = dettaglio(stampa)
            dest = os.path.join(CACHE, v["handle"] + "-dettaglio.jpg")
            tela.save(dest, quality=95, subsampling=0)
            riga = {"handle": v["handle"], "titolo": v["title"], "id": v["id"],
                    "file": os.path.relpath(dest, RADICE),
                    "strisce": n, "ingrandimento": scala,
                    "alt": "%s — il tessuto a grandezza naturale" % v["title"]}
            if args.carica:
                riga["url"] = ospita(dest)
            fatte.append(riga)
            print("%2d/%d  %-40s %d strisce  %s"
                  % (i, len(voci), v["title"][:40], n, riga.get("url", "")))
        except (RuntimeError, OSError) as err:
            print("%2d/%d  %-40s FALLITO: %s"
                  % (i, len(voci), v["title"][:40], str(err)[:90]))

    if args.carica and fatte:
        with open(USCITA, "w") as fh:
            json.dump(fatte, fh, indent=1, ensure_ascii=False)
        print("\n%d foto ospitate, elenco in %s"
              % (len(fatte), os.path.relpath(USCITA, RADICE)))
        print("Si attaccano con productCreateMedia e si portano in prima "
              "posizione con productReorderMedia. In quest'ordine: prima si "
              "crea, si aspetta READY, poi si riordina. Nessuna foto va "
              "tolta -- l'intera resta, scala di una posizione.")


if __name__ == "__main__":
    main()
