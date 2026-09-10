#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La foto che manca a collari e guinzagli: il prodotto col nome sopra.

PERCHE' NON BASTAVA RILANCIARE perla-eu-foto-mockup.py
Ventiquattro collari su ventiquattro e undici guinzagli su undici hanno UNA
foto sola, mentre le bandane ne hanno in media 4,9 e le cucce 8,5. Sembrava
uno script rimasto indietro. Non lo era: chiamando /generate-mockup per tutti
e quattro i tipi EU con lo stesso disegno, Printful risponde

    collare_eu     1 inquadratura
    guinzaglio_eu  1 inquadratura
    bandana_eu     2 inquadrature

Una sola inquadratura e' il TETTO di quello che lo stampatore sa dare per
questi due prodotti. Nessun parametro la alza (create-task accetta solo
variant_ids, files, format, options, option_groups, product_options).

Quindi la seconda foto va costruita, e quella che manca davvero e' ovvia: su un
collare personalizzato il nome E' il prodotto, e non c'era una sola immagine
che lo mostrasse. Si prende il file di stampa vero, ci si scrive un nome con lo
stesso font che l'editor ha attivo di partenza (Cormorant Garamond 600), e lo
si manda a Printful come se fosse il disegno di un cliente. Non e' un
fotomontaggio: e' esattamente cio' che riceve chi ordina quel nome.

DOVE VA MESSO IL NOME, E COME L'HO SCOPERTO
Al primo tentativo il nome era al centro del file di stampa -- il posto dove lo
mette l'editor -- e nel mockup NON SI VEDEVA. Allora ho stampato sulla striscia
i numeri 10, 20, ... 90 alle rispettive percentuali e ho generato il mockup:
si leggono il 20 e il 70, il 50 e' nascosto dall'avvolgimento e dalla fibbia.

La finestra visibile va all'incirca dal dodici al ventisei per cento. Al venti
per cento "Luna" entrava ma usciva a destra -- nel mockup si leggeva "Lun" --
quindi il predefinito e' il DICIASSETTE per cento, con cui la parola ci sta
tutta. Un nome molto lungo sbordera' comunque: e' un limite del prodotto, non
di questo script.

Vale la pena dirlo anche fuori di qui: e' la stessa geometria che decide dove
finisce il nome di un cliente vero, e l'editor il nome lo mette al CENTRO --
cioe' nella parte che non si vede.

USO
    python3 scripts/perla-eu-foto-col-nome.py                    # tutti e 35
    python3 scripts/perla-eu-foto-col-nome.py --max 1            # prova
    python3 scripts/perla-eu-foto-col-nome.py --tipi guinzaglio_eu
    python3 scripts/perla-eu-foto-col-nome.py --solo crea-il-tuo-design
    python3 scripts/perla-eu-foto-col-nome.py --nome Milo --posizione 0.17

Scrive out-foto-nome/ospitate.json (handle -> URL ospitata), che va poi
attaccata ai prodotti su Shopify con productCreateMedia. Riprende da dove si
era fermato: il contenitore si riavvia e si porta via il disco, ma il manifest
dice cosa e' gia' fatto.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))
UPLOAD = "https://perla-upload-endpoint-yizy.onrender.com/upload"
MOCKUP = "https://perla-upload-endpoint-yizy.onrender.com/generate-mockup"
FONT_URL = ("https://fonts.gstatic.com/s/cormorantgaramond/v21/"
            "co3umX5slCNuHLi8bLeY9MK7whWMhyjypVO7abI26QOD_iE9GnM.ttf")
FONT = "/tmp/cormorant600.ttf"
OUT = "out-foto-nome"

# Le aree di stampa vere, le stesse di PRINTFUL_MOCKUP_CONFIG in
# scripts/perla-upload-endpoint.js: se divergono, il nome esce di scala.
AREA = {"collare_eu": (7169, 315), "guinzaglio_eu": (12389, 219)}

# Printful risponde 429 dopo poche chiamate ravvicinate e dice lui quanti
# secondi aspettare. Quarantacinque e' il ritmo che regge senza farsi rifiutare.
PAUSA = 45

CHIARO = (243, 233, 218)   # #F3E9DA, la crema del tema
SCURO = (19, 42, 74)       # #132A4A, l'inchiostro


def font():
    if not os.path.exists(FONT):
        subprocess.run(["curl", "-sfL", "-m", "60", "-o", FONT, FONT_URL], check=True)
    return FONT


def posta(url, dati=None, file=None):
    cmd = ["curl", "-s", "-m", "300", "-X", "POST", url]
    if dati is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(dati)]
    if file:
        cmd += ["-F", "photo=@" + file]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": "risposta illeggibile", "detail": r.stdout[:200]}


def attesa_429(d):
    testo = json.dumps(d)
    if "429" not in testo:
        return None
    m = re.search(r"try again after (\d+) second", testo)
    return int(m.group(1)) + 5 if m else 65


# Gli handle qui dentro sono quelli lunghi con "-eu-": arrivano
# dall'istantanea perla-eu-prodotti.json, non dal negozio, dove da
# settembre sono corti (collare-barocco). Non vanno allineati: i file
# gia' su Cloudinary portano questi nomi.
def tipo_di(handle):
    if handle.startswith("collare-eu"):
        return "collare_eu"
    if handle.startswith("guinzaglio-eu"):
        return "guinzaglio_eu"
    return None


def scrivi_il_nome(pattern_url, tipo, nome, posizione, dest):
    """Il file di stampa vero, col nome dove si vede. Torna (misura, tinta)."""
    w, h = AREA[tipo]
    u = pattern_url.replace("/image/upload/",
                            "/image/upload/w_%d,h_%d,c_fill/" % (w, h))
    grezzo = dest + ".src"
    subprocess.run(["curl", "-sfL", "-m", "180", "-o", grezzo, u], check=True)
    im = Image.open(grezzo).convert("RGB")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)

    # Il colore si sceglie guardando il disegno DOVE va il nome, come farebbe
    # un cliente: chiaro su fondo scuro, scuro su fondo chiaro. Un nome che non
    # si legge sarebbe una foto peggiore di nessuna foto.
    x = int(w * posizione)
    finestra = im.crop((max(0, x - w // 20), 0, min(w, x + w // 20), h)).resize((40, 12))
    pixel = list(finestra.getdata())
    lum = sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixel) / len(pixel)
    colore = CHIARO if lum < 128 else SCURO

    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font(), int(h * 0.62))
    b = d.textbbox((0, 0), nome, font=f)
    d.text((x - (b[2] - b[0]) / 2 - b[0], (h - (b[3] - b[1])) / 2 - b[1]),
           nome, font=f, fill=colore)
    im.save(dest, "JPEG", quality=94)
    os.remove(grezzo)
    return (w, h), ("chiaro" if colore == CHIARO else "scuro"), round(lum)


def su_bianco(sorgente, dest):
    """Printful torna un PNG col fondo trasparente: si appiattisce su bianco,
    come tutto il resto del catalogo."""
    im = Image.open(sorgente)
    if im.mode in ("RGBA", "LA"):
        sfondo = Image.new("RGB", im.size, (255, 255, 255))
        sfondo.paste(im, mask=im.split()[-1])
        im = sfondo
    else:
        im = im.convert("RGB")
    im.save(dest, "JPEG", quality=92)
    return im.size


# Il nome NON e' incluso nel prezzo: lo scrive il cliente nello studio, e la
# scheda lo dice ("Personalizzabile con il nome del tuo cane"). Una foto che
# mostra un collare gia' inciso dice il contrario, ed e' la segnalazione della
# titolare: "perche' aggiungi il nome ai prodotti? non devi aggiungerlo, in
# caso solo consigliarlo al cliente".
#
# La didascalia sta DENTRO l'immagine e non nella scheda di proposito: la foto
# gira da sola su Google Immagini, su Pinterest, nella scheda del feed Google
# Shopping, e in tutti quei posti il testo della scheda non la accompagna. Se
# l'avviso sta nel testo, chi vede solo la foto non lo legge mai.
DIDASCALIA = "esempio — il nome lo scegli tu"


def didascalia(percorso, testo=DIDASCALIA):
    """Stampa la didascalia nella fascia bianca sotto il prodotto.

    DOVE. Il mockup Printful e' 1000x1000 col pezzo al centro: sotto restano
    circa duecento pixel di fondo bianco vuoto. La riga va li', a un ventesimo
    dal bordo, quindi non copre mai il prodotto -- non si sceglie una posizione
    "che sembra libera", si usa quella che il fornitore lascia libera sempre.

    COME. Un inchiostro solo, il blu del tema, e un corpo piccolo: deve
    togliere l'equivoco, non gridare. Il font e' lo stesso dell'editor, cosi'
    la riga sembra parte della fotografia e non un'etichetta appiccicata.

    E' un'operazione che si puo' rifare quante volte si vuole sullo stesso
    file? NO -- ristamperebbe la riga sopra a se stessa, un po' piu' scura. Chi
    chiama questa funzione parte sempre dal mockup pulito.
    """
    im = Image.open(percorso).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font(), max(14, int(h * 0.034)))
    b = d.textbbox((0, 0), testo, font=f)
    d.text(((w - (b[2] - b[0])) / 2 - b[0], h - int(h * 0.05) - (b[3] - b[1]) - b[1]),
           testo, font=f, fill=SCURO)
    im.save(percorso, "JPEG", quality=92)
    return im.size


def main():
    args = sys.argv[1:]
    massimo = 999
    tipi = {"collare_eu", "guinzaglio_eu"}
    nome = "Luna"
    posizione = 0.17
    if "--max" in args:
        massimo = int(args[args.index("--max") + 1])
    if "--tipi" in args:
        tipi = set(args[args.index("--tipi") + 1].split(","))
    if "--nome" in args:
        nome = args[args.index("--nome") + 1]
    if "--posizione" in args:
        posizione = float(args[args.index("--posizione") + 1])
    # --solo restringe a handle precisi, come negli altri script di foto: serve
    # per rifare le poche rimaste indietro senza rimettere in coda tutte e 35.
    solo = None
    if "--solo" in args:
        solo = [s for s in args[args.index("--solo") + 1].split(",") if s]
    # La didascalia si puo' spegnere, ma e' accesa di default: se un domani si
    # decide di toglierla, si toglie da qui e non riscrivendo la funzione.
    senza_didascalia = "--senza-didascalia" in args

    os.makedirs(OUT, exist_ok=True)
    p_out = os.path.join(OUT, "ospitate.json")
    ospitate = json.load(open(p_out)) if os.path.exists(p_out) else {}

    # --ridai-didascalia: rimette la didascalia sulle foto GIA' fatte, senza
    # ripassare da Printful.
    #
    # Serve perche' le trentacinque foto erano gia' state generate, ospitate e
    # attaccate quando e' arrivata la segnalazione sulla didascalia. Rifare il
    # giro intero vorrebbe dire mezz'ora di chiamate al fornitore e i suoi
    # fallimenti intermittenti (tre passate per arrivare a trentacinque su
    # trentacinque), per riottenere esattamente gli stessi mockup che sono gia'
    # sul disco.
    #
    # Il mockup pulito NON si tocca: la didascalia va su una COPIA
    # (-mockup-didascalia.jpg). Cosi' rilanciare questo modo dieci volte da'
    # dieci volte lo stesso risultato, invece di ristampare la riga sopra a se
    # stessa sempre piu' scura.
    if "--ridai-didascalia" in args:
        rifatte = 0
        for handle, voce in sorted(ospitate.items()):
            pulito = os.path.join(OUT, handle[:60] + "-mockup.jpg")
            if not os.path.exists(pulito):
                print("%-46s manca il mockup su disco, saltata" % handle[:46])
                continue
            con_riga = os.path.join(OUT, handle[:60] + "-mockup-didascalia.jpg")
            shutil.copy(pulito, con_riga)
            didascalia(con_riga)
            ospite = posta(UPLOAD, file=con_riga)
            if not ospite.get("url"):
                print("%-46s ospitare fallito: %s" % (handle[:46], str(ospite)[:60]))
                continue
            voce["url"] = ospite["url"]
            voce["didascalia"] = DIDASCALIA
            json.dump(ospitate, open(p_out, "w"), indent=1, ensure_ascii=False)
            rifatte += 1
            print("%-46s %s" % (handle[:46], ospite["url"][-28:]))
        print("\n%d foto con la didascalia, riscritte in %s" % (rifatte, p_out))
        return
    prodotti = json.load(open(os.path.join(QUI, "perla-eu-prodotti.json")))

    coda = [p for p in prodotti
            if tipo_di(p["handle"]) in tipi and p["handle"] not in ospitate
            and (not solo or any(s in p["handle"] for s in solo))][:massimo]
    print("%d da fare (%d gia' fatte). Nome '%s' al %d%% della striscia.\n"
          % (len(coda), len(ospitate), nome, round(posizione * 100)))

    for i, p in enumerate(coda, 1):
        tipo = tipo_di(p["handle"])
        base = os.path.join(OUT, p["handle"][:60])
        stampa = base + "-stampa.jpg"
        try:
            misura, tinta, lum = scrivi_il_nome(p["pattern"], tipo, nome, posizione, stampa)
        except Exception as e:
            print("%2d/%d  %-34s file di stampa fallito: %s"
                  % (i, len(coda), p["title"][:34], str(e)[:80]))
            continue

        u = posta(UPLOAD, file=stampa)
        if not u.get("url"):
            print("%2d/%d  %-34s upload fallito: %s"
                  % (i, len(coda), p["title"][:34], str(u)[:90]))
            time.sleep(PAUSA)
            continue

        d = None
        for _ in range(4):
            d = posta(MOCKUP, {"product_type": tipo, "composite_image_id": "solo-url",
                               "composite_image_url": u["url"]})
            if d.get("images"):
                break
            att = attesa_429(d)
            if att:
                print("   429, aspetto %ds" % att)
                time.sleep(att)
                continue
            break
        if not d or not d.get("images"):
            print("%2d/%d  %-34s mockup fallito: %s"
                  % (i, len(coda), p["title"][:34], str(d)[:90]))
            time.sleep(PAUSA)
            continue

        grezzo = base + "-mockup.png"
        finito = base + "-mockup.jpg"
        subprocess.run(["curl", "-sfL", "-m", "180", "-o", grezzo, d["images"][0]])
        if not os.path.exists(grezzo) or os.path.getsize(grezzo) < 5000:
            print("%2d/%d  %-34s scarico del mockup fallito" % (i, len(coda), p["title"][:34]))
            time.sleep(PAUSA)
            continue
        mis = su_bianco(grezzo, finito)
        os.remove(grezzo)
        if not senza_didascalia:
            didascalia(finito)

        ospite = posta(UPLOAD, file=finito)
        if not ospite.get("url"):
            print("%2d/%d  %-34s ospitare la foto e' fallito: %s"
                  % (i, len(coda), p["title"][:34], str(ospite)[:90]))
            time.sleep(PAUSA)
            continue

        ospitate[p["handle"]] = {"url": ospite["url"], "nome": nome,
                                 "id": p["id"], "titolo": p["title"]}
        json.dump(ospitate, open(p_out, "w"), indent=1, ensure_ascii=False)
        print("%2d/%d  %-34s %s  nome %s (luminosita' %d)"
              % (i, len(coda), p["title"][:34], mis, tinta, lum))
        time.sleep(PAUSA)

    print("\n%d foto ospitate in %s" % (len(ospitate), p_out))


if __name__ == "__main__":
    main()
