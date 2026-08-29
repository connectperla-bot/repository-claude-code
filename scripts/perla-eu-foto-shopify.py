#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara l'attacco delle foto EU rigenerate ai prodotti Shopify.

L'ANELLO CHE MANCAVA
perla-eu-foto-mockup.py fa due terzi del lavoro: chiede il mockup a Printful,
lo appiattisce su bianco e lo ospita su Cloudinary, scrivendo le URL in
out-foto/ospitate.json. Li' pero' si fermava. Attaccare quelle foto ai
prodotti non lo faceva nessuno: perla-usa-foto-shopify.py copre solo la linea
americana, e lo fa in un modo che qui non si puo' usare -- chiede a Printify
di ripubblicare, e Printful non ha niente del genere (ne' lo vogliamo: i
prodotti EU non sono collegati, altrimenti la personalizzazione salterebbe su
tutti e 66).

Risultato: i mockup nuovi esistevano ed erano pubblici, ma sul sito restavano
le foto vecchie. E' proprio il difetto che si stava correggendo -- il cliente
guarda un disegno e ne riceve un altro -- solo spostato di un passo.

PERCHE' NON SCRIVE DA SOLO
Stessa ragione di perla-editor-allinea.py: in config/printify.local.env non
c'e' un token Admin di Shopify, e non ce ne deve essere uno solo per questo.
Qui si PREPARA l'input delle mutation e lo si mette in una forma leggibile
prima di toccare il catalogo; a scriverlo e' chi ha gia' le credenziali.

L'ORDINE CONTA
Prima productCreateMedia con le foto nuove, poi productDeleteMedia sulle
vecchie. Mai il contrario: fra le due chiamate il prodotto resta scoperto, e
un prodotto senza foto in vetrina e' peggio di un prodotto con la foto
sbagliata. E' la stessa lezione della finestra cieca di venti minuti
documentata in perla-usa-foto-shopify.py.

QUALI SONO ANCORA DA FARE
Qui esce TUTTO cio' che ha una foto rigenerata, anche quello gia' attaccato:
senza un token Admin questo script non puo' guardare il negozio, quindi non
lo sa. A saperlo e' Shopify, e il modo per chiederglielo e' guardare gli id
dei media: quelli creati in un giro sono tutti piu' alti di quelli che
c'erano prima, quindi un prodotto che ha ancora un id vecchio e' un prodotto
rimasto indietro.

    query { products(first: 70, query: "handle:*fornitore-europeo*") {
      nodes { handle media(first: 12) { nodes { ... on MediaImage { id } } } } } }

Serve davvero: Printful risponde "Impossibile generare l'anteprima" su una
parte dei prodotti a ogni giro -- diciassette su sessantasei la prima volta,
poi sei, poi due -- e sono sempre gli stessi finche' non passano. Quindi si
attacca a scaglioni, e senza questo controllo si riattaccherebbero foto gia'
attaccate, lasciando doppioni.

USO
    python3 scripts/perla-eu-foto-shopify.py
"""
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)

MANIFEST = os.path.join(QUI, "perla-eu-prodotti.json")
OSPITATE = os.path.join(RADICE, "out-foto", "ospitate.json")
USCITA = os.path.join(RADICE, "generated-designs", "foto-eu-da-attaccare.json")

# Lo stesso testo alternativo che hanno gia' le foto EU sul negozio: e' anche
# il segnaposto che perla-eu-foto-mockup.py legge per sapere cosa e' gia'
# fatto (campo gia_fatta). Cambiarlo qui vorrebbe dire rompere la ripresa.
def alt(titolo):
    return "%s — Perla Italia" % titolo.replace("“", '"').replace("”", '"')


def da_attaccare():
    prodotti = json.load(open(MANIFEST))
    if not os.path.exists(OSPITATE):
        raise SystemExit("manca %s: prima gira perla-eu-foto-mockup.py"
                         % os.path.relpath(OSPITATE, RADICE))
    ospitate = json.load(open(OSPITATE))

    lavoro, saltati = [], []
    for p in prodotti:
        v = ospitate.get(p["handle"])
        # Le voci vecchie sono stringhe singole, cioe' foto di un giro
        # precedente: solo gli ELENCHI sono state rifatte adesso. Attaccare
        # una stringa vecchia rimetterebbe su il disegno che si sta togliendo.
        if not isinstance(v, list) or not v:
            saltati.append(p)
            continue
        lavoro.append({"id": p["id"], "titolo": p["title"], "handle": p["handle"],
                       "alt": alt(p["title"]), "nuove": v})
    return lavoro, saltati


def main():
    lavoro, saltati = da_attaccare()
    for v in lavoro:
        print("%-34s %d foto" % (v["titolo"][:34], len(v["nuove"])))
    if saltati:
        print("\n%d senza foto nuove, non si toccano:" % len(saltati))
        for p in saltati:
            print("   %s" % p["title"])

    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with open(USCITA, "w") as fh:
        json.dump(lavoro, fh, indent=1, ensure_ascii=False)
    print("\n%d prodotti, %d foto in totale, in %s"
          % (len(lavoro), sum(len(v["nuove"]) for v in lavoro),
             os.path.relpath(USCITA, RADICE)))
    print("Si attaccano con productCreateMedia; SOLO DOPO aver visto che le "
          "nuove ci sono, le vecchie si tolgono con productDeleteMedia.")


if __name__ == "__main__":
    main()
