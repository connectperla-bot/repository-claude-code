#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggiorna su Shopify le foto dei prodotti americani, e SOLO le foto.

IL PROBLEMA
Dopo aver rifatto i file di stampa su Printify, le immagini sul negozio erano
rimaste quelle vecchie: mostravano il disegno impastato di prima, mentre in
stampa partiva quello nuovo. Il cliente comprava una cosa e ne riceveva
un'altra. Prima erano uguali e brutte; dopo erano diverse, che e' peggio.

LA STRADA, E LE DUE CHE HO SCARTATO
Printify e' collegato a Shopify come canale di vendita, e sa ripubblicare un
prodotto scegliendo COSA sincronizzare. Si chiede solo `images` e si lascia
tutto il resto a false: le foto vengono rifatte, e titolo e descrizione --
che su Shopify sono in italiano e scritti a mano ("Cuccia Tribale", non
"Geometric Tribal Pet Bed — Rustic Brown Cozy Dog & Cat Cushion") -- non
vengono toccati. Verificato su un prodotto prima di lanciarlo su tutti.

Scartata la prima idea: rigenerare le foto come fa perla-eu-foto-mockup.py.
Quello e' scritto per la linea EUROPEA, che passa da Printful e da una
generazione di mockup lenta e da ritmare. Qui i mockup Printify li ha gia'
rifatti da solo quando abbiamo cambiato le print_areas.

Scartata la seconda: prendere le URL dei mockup Printify e darle a Shopify con
productCreateMedia. Funzionava, ma quelle URL escono a 1200x1200 (provate le
varianti ?width=2048: tornano sempre 1200), mentre l'app Printify carica su
Shopify a 2048 -- cioe' la stessa misura delle foto che stiamo sostituendo.
La strada nativa da' l'immagine piu' grande E meno codice.

QUALI PRODOTTI
Solo quelli il cui motivo e' stato davvero sostituito, riconosciuti dal nome
del livello di stampa. I quattro "Copy of" restano fuori: non hanno un
external.id, cioe' su Shopify non esistono, e ripubblicarli non aggiornerebbe
niente.

USO
    python3 scripts/perla-usa-foto-shopify.py            # elenca e basta
    python3 scripts/perla-usa-foto-shopify.py --tutti
    python3 scripts/perla-usa-foto-shopify.py --tutti --tipo cuccia
"""
import json
import os
import subprocess
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)

# I livelli che questo giro ha sostituito: e' il prefisso che
# perla-usa-file-stampa.py da' ai file che costruisce.
MIEI = ('cuccia-baroque-royal', 'cuccia-vintage-damask', 'cuccia-luxury-paisley',
        'cuccia-ornate-medallion', 'cuccia-luxurious-navy', 'cuccia-perla-italy',
        'cuccia-copy-of', 'cuccia-geometric', 'cuccia-personalized', 'cuccia-teal-',
        'bandana-da-', 'medaglietta-da-',
        # Meta' delle medagliette non passa da "medaglietta-da-": il loro
        # disegno si chiama "tag-...-perla.jpg", nome ereditato dalla prima
        # ondata. Senza questo prefisso restavano fuori dalla ripubblicazione e
        # tenevano su Shopify la foto vecchia.
        'tag-')

TIPO = {419: 'cuccia', 562: 'bandana', 566: 'medaglietta', 570: 'ciotola', 784: 'collare'}

# Si sincronizzano SOLO le immagini. Ogni altro campo a false, e non per
# prudenza generica: su Shopify titoli e descrizioni sono italiani e scritti a
# mano, mentre su Printify sono stringhe SEO inglesi. Mettere title:true qui
# vorrebbe dire riscrivere il catalogo in inglese senza accorgersene.
COSA = {"title": False, "description": False, "images": True,
        "variants": False, "tags": False, "keyFeatures": False,
        "shipping_template": False}


def chiavi():
    valori = {}
    with open(os.path.join(RADICE, 'config', 'printify.local.env')) as fh:
        for riga in fh:
            riga = riga.strip()
            if riga and not riga.startswith('#') and '=' in riga:
                k, v = riga.split('=', 1)
                valori[k.strip()] = v.strip()
    return valori


def api(metodo, percorso, token, corpo=None):
    cmd = ['curl', '-s', '-X', metodo, '-H', 'Authorization: Bearer ' + token,
           '-H', 'Content-Type: application/json', 'https://api.printify.com' + percorso]
    tmp = None
    if corpo is not None:
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        json.dump(corpo, tmp); tmp.close()
        cmd[1:1] = ['--data-binary', '@' + tmp.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    finally:
        if tmp:
            os.unlink(tmp.name)
    return out


def da_aggiornare(prodotti, tipo_voluto=None):
    fuori = []
    for p in prodotti:
        if p['blueprint_id'] == 784:
            continue
        tocco = any((im.get('name') or '').startswith(MIEI)
                    for pa in p.get('print_areas', [])
                    for ph in pa.get('placeholders', [])
                    for im in ph.get('images', []))
        if not tocco:
            continue
        tipo = TIPO[p['blueprint_id']]
        if tipo_voluto and tipo != tipo_voluto:
            continue
        esterno = (p.get('external') or {}).get('id')
        fuori.append((tipo, p['id'], esterno, p['title'], p.get('is_locked')))
    return fuori


def main():
    env = chiavi()
    token, shop = env['PRINTIFY_API_KEY'], env['PRINTIFY_SHOP_ID']
    tutti = '--tutti' in sys.argv
    tipo_voluto = None
    if '--tipo' in sys.argv:
        tipo_voluto = sys.argv[sys.argv.index('--tipo') + 1]

    prodotti, pagina = [], 1
    while True:
        d = json.loads(api('GET', '/v1/shops/%s/products.json?limit=50&page=%d' % (shop, pagina), token))
        prodotti += d['data']
        if pagina >= d['last_page']:
            break
        pagina += 1

    lavoro = da_aggiornare(prodotti, tipo_voluto)
    collegati = [x for x in lavoro if x[2]]
    orfani = [x for x in lavoro if not x[2]]
    print('%d prodotti col motivo rifatto, %d collegati a Shopify' % (len(lavoro), len(collegati)))
    if orfani:
        print('%d senza prodotto Shopify, saltati:' % len(orfani))
        for o in orfani:
            print('   ' + o[3][:62])

    if not tutti:
        for t, _, esterno, titolo, _ in collegati:
            print('  da fare  %-12s %-52s -> Shopify %s' % (t, titolo[:52], esterno))
        print('\n(elenco soltanto: aggiungi --tutti per applicare)')
        return

    fatti, falliti = 0, []
    for t, pid, esterno, titolo, bloccato in collegati:
        if bloccato:
            print('  BLOCCATO su Printify, saltato: ' + titolo[:52])
            falliti.append(titolo)
            continue
        r = api('POST', '/v1/shops/%s/products/%s/publish.json' % (shop, pid), token, COSA)
        # risposta attesa: {} -- Printify accoda la pubblicazione e l'app
        # Shopify carica le immagini nei secondi successivi
        if r.strip() not in ('{}', ''):
            print('  ERRORE %-46s %s' % (titolo[:46], r[:120]))
            falliti.append(titolo)
            continue
        fatti += 1
        print('  %-12s %-52s ok' % (t, titolo[:52]))
        # Printify limita a 600 chiamate al minuto ma l'app Shopify carica
        # nove immagini per prodotto: senza pausa si accodano tutte insieme
        time.sleep(1.5)

    print('\n%d prodotti ripubblicati (solo immagini)' % fatti)
    for f in falliti:
        print('  DA RIFARE: ' + f[:62])
    if fatti:
        print(FINESTRA_CIECA % fatti)


# QUANTO CI METTE DAVVERO, E COSA SUCCEDE NEL FRATTEMPO
#
# Qui c'era scritto "ricontrolla fra qualche minuto". Sono venti, e nel
# frattempo il prodotto sul negozio resta SENZA NESSUNA FOTO: l'app Printify
# prima toglie le vecchie e poi carica le nuove, e in mezzo mediaCount e'
# zero. Misurato sulle quattordici medagliette: pubblicate alle 12:21, ancora
# a zero alle 12:40, tornate a posto alle 12:42.
#
# Non e' un dettaglio da nota a pie' di pagina: sono prodotti in vendita che
# per venti minuti si presentano senza immagine. Va detto PRIMA di lanciare il
# comando, e va detto quanto dura, cosi' chi lo lancia sceglie quando farlo.
#
# Se dopo mezz'ora un prodotto e' ancora a zero, la coda di Printify si e'
# incastrata: si sblocca con publishing_succeeded.json e si ripubblica. Sulla
# medaglietta "Nobile" ha funzionato al primo colpo -- ma attenzione, se nel
# frattempo la coda si sblocca da sola le immagini si caricano DUE volte e
# vanno tolte le doppie.
FINESTRA_CIECA = '''
%d prodotti sono ora in ripubblicazione su Printify.

ATTENZIONE: per una ventina di minuti quei prodotti sul negozio restano SENZA
FOTO. L'app Printify toglie le immagini vecchie e carica le nuove in due
momenti diversi, e in mezzo la scheda prodotto e' senza immagine.

Fra mezz'ora ricontrolla che mediaCount sia > 0 su tutti. Se qualcuno e'
ancora a zero, la coda si e' incastrata: sblocca con
  POST /v1/shops/<shop>/products/<id>/publishing_succeeded.json
e ripubblica. Se poi ne trovi con le foto doppie, la coda si era sbloccata da
sola: le doppie si tolgono con productDeleteMedia.'''


if __name__ == '__main__':
    main()
