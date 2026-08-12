#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copia in locale una pagina del negozio, per poterla guardare davvero.

PERCHE' NON SI NAVIGA E BASTA
In questo ambiente Chromium non esce in rete: il proxy riceve solo GET e mai una
CONNECT, quindi ogni https finisce in ERR_CONNECTION_RESET (provato con proxy a
livello di browser, di contesto e da riga di comando; curl invece passa). Senza
browser non si vedono ne' schermate ne' stili calcolati, e i difetti visivi si
possono solo indovinare.

Allora: curl scarica la pagina e i suoi file (CSS, JS, immagini, font), le URL
assolute diventano relative, e Chromium apre il risultato da file:// -- niente
rete, rendering vero. Il JS del tema gira, quindi si vedono anche le animazioni
e si possono leggere gli stili calcolati.

    python3 tests/perla-specchio.py <percorso> <nome> [--tema ID]
    python3 tests/perla-specchio.py / home
    python3 tests/perla-specchio.py /products/collare-eu-... collare
"""
import os
import re
import subprocess
import sys
import hashlib

BASE = "https://perlaitaly.com"
DEST = "/tmp/specchio"


def scarica(url, dest):
    if os.path.exists(dest):
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-sL", "-m", "90", "-o", dest, url], capture_output=True)
    return r.returncode == 0 and os.path.getsize(dest) > 0


def main():
    percorso = sys.argv[1] if len(sys.argv) > 1 else "/"
    nome = sys.argv[2] if len(sys.argv) > 2 else "pagina"
    tema = sys.argv[4] if len(sys.argv) > 4 else "196807885144"
    cartella = os.path.join(DEST, nome)
    os.makedirs(os.path.join(cartella, "f"), exist_ok=True)

    sep = "&" if "?" in percorso else "?"
    url = BASE + percorso + sep + "preview_theme_id=" + tema
    html_path = os.path.join(cartella, "index.html")
    # il preview_theme_id viaggia in un cookie: senza barattolo, la prima
    # risposta e' un 302 che lo perde e si finisce sul tema pubblicato.
    ck = os.path.join(cartella, "cookie.txt")
    subprocess.run(["curl", "-sL", "-c", ck, "-b", ck, "-m", "120", "-o", "/dev/null", url], check=True)
    subprocess.run(["curl", "-sL", "-c", ck, "-b", ck, "-m", "120", "-o", html_path, url], check=True)
    h = open(html_path, encoding="utf-8", errors="replace").read()
    print("pagina: %d byte" % len(h))

    # ogni URL assoluta di un file statico diventa un file dentro f/
    trovate = set()
    for m in re.finditer(r'(?:https:)?//(?:perlaitaly\.com|cdn\.shopify\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/[^\s"\'()<>\\]+', h):
        trovate.add(m.group(0))
    print("file referenziati: %d" % len(trovate))

    fatti = 0
    for u in sorted(trovate):
        pieno = ("https:" + u) if u.startswith("//") else u
        est = re.search(r'\.([a-z0-9]{2,5})(?:\?|$)', pieno.lower())
        est = est.group(1) if est else "bin"
        if est not in ("css", "js", "png", "jpg", "jpeg", "webp", "svg", "gif", "woff", "woff2", "ico"):
            continue
        # "./" davanti: senza, un import di modulo ES fallisce con
        # "Failed to resolve module specifier" e meta' del tema non gira.
        loc = "./f/" + hashlib.md5(pieno.encode()).hexdigest()[:16] + "." + est
        if scarica(pieno, os.path.join(cartella, loc[2:])):
            h = h.replace(u, loc)
            fatti += 1
    # i CSS di Google Fonts puntano a loro volta ai .woff2: si riscrivono anche li'
    for f in os.listdir(os.path.join(cartella, "f")):
        if not f.endswith(".css"):
            continue
        p = os.path.join(cartella, "f", f)
        c = open(p, encoding="utf-8", errors="replace").read()
        for m in set(re.findall(r'https://fonts\.gstatic\.com/[^\s"\')]+', c)):
            loc = hashlib.md5(m.encode()).hexdigest()[:16] + ".woff2"
            if scarica(m, os.path.join(cartella, "f", loc)):
                c = c.replace(m, loc)
        open(p, "w", encoding="utf-8").write(c)

    open(html_path, "w", encoding="utf-8").write(h)
    print("scaricati %d file -> %s" % (fatti, html_path))


if __name__ == "__main__":
    main()
