#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Costo fornitore + spedizione fornitore -> prezzo, e il margine che ne esce.

I prezzi qui sotto sono quelli APPLICATI il 22 agosto: rilanciando lo script si
vede subito il margine di ogni famiglia con i costi di oggi, e se un fornitore
ritocca i suoi si scopre qui, non a fine mese.

I COSTI SONO MISURATI, NON STIMATI
Printify: /v1/catalog/.../shipping.json e i costi delle varianti dei prodotti
veri del negozio. Printful: api.printful.com/products/<id> (pubblico), e il
collare torna 17,23 esatto come il file printful-catalog/749.json gia' nel
repository -- controprova che i numeri sono quelli giusti.

IL CAMBIO
Il negozio ha base EUR e il listino USA e' una conversione allo 0% di
scostamento: Shopify vende a 48,00 $ una bandana da 39,99 €, cioe' applica
1,2003. Si usa quello, perche' e' il cambio con cui il negozio incassa davvero.

LA SPEDIZIONE EUROPEA
E' l'unico numero che non ho potuto leggere: le tariffe Printful stanno dietro
autenticazione e la chiave vive solo su Render. Qui e' un parametro dichiarato
(SPED_EU), non un numero nascosto in mezzo agli altri: cambiandolo si vede
subito quanto sposta.
"""
CAMBIO = 1.2003          # EUR -> USD, quello che applica Shopify
SPED_EU = 5.00           # DA CONFERMARE: allocazione spedizione Printful, in USD
# Scala scelta con Emanuele e Nicola: 40% di base, e piu' si sale col costo
# piu' il margine scende. Un pezzo caro che rende il 30% porta a casa piu'
# euro di uno che rende il 45% e resta sullo scaffale.
def margine(sbarcato):
    if sbarcato <= 25:  return 0.42
    if sbarcato <= 50:  return 0.40
    if sbarcato <= 100: return 0.35
    return 0.30

# (nome, costo USD, spedizione USD, prezzo EUR attuale, mercato)
VOCI = [
    ("Medaglietta",              11.27,  5.49,  24.90, "USA"),
    ("Bandana 20x10",            14.25,  5.49,  28.90, "USA"),
    ("Bandana 27x13",            16.05,  5.49,  31.90, "USA"),
    ("Ciotola 16oz",             24.72, 14.29,  54.90, "USA"),
    ("Cuccia 28x18",             29.26, 26.19,  71.90, "USA"),
    ("Cuccia 40x30",             49.50, 29.99, 101.90, "USA"),
    ("Cuccia 50x40",             79.86, 49.99, 154.90, "USA"),
    ("Bandana EU",               10.15, SPED_EU, 21.90, "EU"),
    ("Collare EU",               17.23, SPED_EU, 32.90, "EU"),
    ("Guinzaglio EU",            19.77, SPED_EU, 35.90, "EU"),
    ("Ciotola EU 530 ml",        21.49, SPED_EU, 36.90, "EU"),
    ("Ciotola EU 950 ml",        24.49, SPED_EU, 41.90, "EU"),
]


def arrotonda(eur):
    """Alla cifra ,90 piu' vicina verso l'alto: una scala sola per tutti."""
    import math
    return math.floor(eur) + 0.90 if eur - int(eur) <= 0.90 else math.floor(eur) + 1.90


def main():
    print("cambio %.4f  |  spedizione EU ipotizzata %.2f$  |  margine 42%% fino a 25$, poi 40 / 35 / 30%%\n"
          % (CAMBIO, SPED_EU))
    print("%-19s %7s %7s %8s  %9s %8s   %9s %8s  %s" %
          ("", "costo$", "sped$", "totale$", "in vetrina €", "margine", "proposto €", "margine", ""))
    for nome, costo, sped, oggi_eur, mercato in VOCI:
        sbarcato = costo + sped
        oggi_usd = oggi_eur * CAMBIO
        marg_oggi = (oggi_usd - sbarcato) / oggi_usd
        obiettivo = margine(sbarcato)
        nuovo_eur = arrotonda((sbarcato / (1 - obiettivo)) / CAMBIO)
        marg_nuovo = (nuovo_eur * CAMBIO - sbarcato) / (nuovo_eur * CAMBIO)
        delta = (nuovo_eur - oggi_eur) / oggi_eur * 100
        segno = "  %+.0f%%" % delta if abs(delta) >= 3 else ""
        print("%-19s %7.2f %7.2f %8.2f  %9.2f %7.0f%%   %9.2f %7.0f%%%s" %
              (nome, costo, sped, sbarcato, oggi_eur, marg_oggi * 100,
               nuovo_eur, marg_nuovo * 100, segno))


if __name__ == "__main__":
    main()
