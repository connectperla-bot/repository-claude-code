#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Carica un file sul bersaglio firmato di stagedUploadsCreate.

themeFilesUpsert accetta anche il corpo inline, ma un CSS da 12 KB inline
significa ritrascriverlo a mano ogni volta, con il rischio di introdurre un
errore proprio nel file che si sta correggendo. Con lo staged upload il file
parte da disco, byte per byte, e l'MD5 sul tema si confronta con quello locale.

Uso: si incolla il JSON dei parametri (quello che torna stagedUploadsCreate)
     su stdin, e si passa il percorso del file.

    python3 tests/perla-carica-tema.py /tmp/tema/perla-type.css <<'JSON'
    {"url": "...", "parameters": [{"name": "...", "value": "..."}]}
    JSON
"""
import hashlib
import json
import subprocess
import sys


def main():
    percorso = sys.argv[1]
    t = json.load(sys.stdin)
    campi = []
    for p in t["parameters"]:
        campi += ["-F", "%s=%s" % (p["name"], p["value"])]
    campi += ["-F", "file=@" + percorso]
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        "-X", "POST", t["url"]] + campi, capture_output=True, text=True)
    md5 = hashlib.md5(open(percorso, "rb").read()).hexdigest()
    print("HTTP %s  md5 locale %s" % (r.stdout.strip(), md5))


if __name__ == "__main__":
    main()
