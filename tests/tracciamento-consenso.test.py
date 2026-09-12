#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il tracciamento parte solo col consenso, e solo se c'e' un ID.

PERCHE' QUESTA PROVA ESISTE
snippets/perla-analytics.liquid e' l'unico punto del tema che carica Microsoft
Clarity, Google Analytics e il pixel di Meta. Ha due modi di rompersi, opposti
e tutti e due silenziosi:

  - si rompe il cancello del consenso, e il negozio traccia i clienti senza
    permesso. Nessuno se ne accorge guardando il sito: si vede solo in
    un'ispezione, o in una lettera del Garante;
  - si rompe l'avvio, e non si misura piu' niente. Anche questo non si vede:
    il sito funziona benissimo, semplicemente i cruscotti restano vuoti.

Il primo costa una multa, il secondo costa mesi di dati. tests/cookie-consenso
prova la barra -- se compare, cosa manda, come si riapre -- ma si ferma li': di
quello che succede DOPO il consenso non guardava niente.

COSA CONTROLLA
Legge il Liquid e verifica le regole che devono restare vere qualunque cosa si
tocchi dentro:

  1. senza nessun ID lo snippet non stampa una riga di JavaScript;
  2. i tre caricatori si chiamano solo da dentro avvia(), che e' il cancello;
  3. avvia() esce subito se il consenso non c'e';
  4. il consenso dato a pagina aperta fa partire il tracciamento senza
     ricaricare (l'evento visitorConsentCollected);
  5. gli ID passano da | json, cosi' un'impostazione scritta male non puo'
     iniettare codice ne' rompere lo script;
  6. non torna il <img> di riserva del pixel Meta: quello partirebbe SEMPRE,
     consenso o no, perche' senza JavaScript non c'e' modo di chiederlo;
  7. lo snippet resta in fondo al <body>. Nel <head> l'API del consenso di
     Shopify non esiste ancora, e il cancello non avrebbe niente a cui
     chiedere -- e' esattamente il difetto che c'era prima di ROUND 47.

COSA NON PUO' CONTROLLARE
Che gli ID ci siano. Quelli stanno nelle impostazioni del tema, non nel
codice, e finche' sono vuoti non si misura niente -- il che e' lo stato
corretto di un negozio che non ha ancora aperto i due account.

Uso:  python3 tests/tracciamento-consenso.test.py
"""
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
SNIPPET = os.path.join(RADICE, "theme", "snippets", "perla-analytics.liquid")
LAYOUT = os.path.join(RADICE, "theme", "layout", "theme.liquid")

COMMENTO_LIQUID = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", re.S)
COMMENTO_JS = re.compile(r"^\s*//.*$", re.M)

fatte = 0


def prova(nome, fn):
    global fatte
    try:
        fn()
        print("  ok   " + nome)
        fatte += 1
    except AssertionError as e:
        print("  FALLITO   %s\n        %s" % (nome, e))
        sys.exit(1)


GREZZO = open(SNIPPET, encoding="utf-8").read()
CODICE = COMMENTO_JS.sub("", COMMENTO_LIQUID.sub("", GREZZO))

print("\nIl tracciamento e il consenso")


def niente_id_niente_codice():
    """Il blocco intero sta dentro un if sugli ID."""
    m = re.search(r"\{%-?\s*if\s+([^%]*?)-?%\}", CODICE)
    assert m, "non c'e' piu' nessun {% if %} a guardia dello snippet"
    condizione = m.group(1)
    for chiave in ("clarity_id", "ga4_id", "meta_id"):
        assert chiave in condizione, (
            "la guardia non nomina piu' %s: con quell'ID vuoto lo snippet "
            "stamperebbe JavaScript per niente.\n        guardia: %s"
            % (chiave, condizione.strip()))
    assert "!= blank" in condizione, (
        "la guardia non controlla piu' che gli ID non siano vuoti: %s"
        % condizione.strip())
    i_script = CODICE.find("<script")
    assert -1 < m.start() < i_script, (
        "lo <script> non e' piu' dentro la guardia: uscirebbe sempre.")


prova("senza nessun ID non esce una riga di JavaScript", niente_id_niente_codice)


def i_caricatori_stanno_dietro_il_cancello():
    m = re.search(r"function\s+avvia\s*\(\)\s*\{(.*?)\n      \}", CODICE, re.S)
    assert m, "non c'e' piu' una funzione avvia(): il cancello e' sparito"
    dentro = m.group(1)
    fuori = CODICE[:m.start()] + CODICE[m.end():]
    for nome in ("clarity", "ga4", "meta"):
        assert re.search(r"\b%s\(\)" % nome, dentro), (
            "avvia() non chiama piu' %s(): quel tracciamento non partirebbe mai"
            % nome)
        chiamate_fuori = re.findall(r"(?<!function )\b%s\(\)" % nome, fuori)
        assert not chiamate_fuori, (
            "%s() viene chiamato anche fuori da avvia(), cioe' fuori dal "
            "cancello del consenso: partirebbe senza permesso." % nome)


prova("Clarity, GA4 e Meta si chiamano solo da dentro avvia()",
      i_caricatori_stanno_dietro_il_cancello)


def il_cancello_e_chiuso():
    m = re.search(r"function\s+avvia\s*\(\)\s*\{(.*?)\n      \}", CODICE, re.S)
    prima_riga = m.group(1).strip().splitlines()[0]
    assert "consentito()" in prima_riga and "return" in prima_riga, (
        "la prima cosa che fa avvia() non e' piu' uscire quando manca il "
        "consenso. Adesso fa: %s" % prima_riga)
    assert re.search(r"function\s+consentito", CODICE), "sparita consentito()"
    assert "analyticsProcessingAllowed" in CODICE, (
        "consentito() non chiede piu' analyticsProcessingAllowed() a Shopify: "
        "sta decidendo da sola se c'e' il consenso.")


prova("avvia() esce subito se il consenso non c'e'", il_cancello_e_chiuso)


def il_consenso_tardivo_conta():
    assert "visitorConsentCollected" in CODICE, (
        "sparito l'ascolto di visitorConsentCollected: chi accetta il banner a "
        "pagina gia' aperta non verrebbe misurato finche' non ricarica.")


prova("il consenso dato a pagina aperta fa partire il tracciamento",
      il_consenso_tardivo_conta)


def gli_id_sono_messi_in_sicurezza():
    for variabile, impostazione in (("CLARITY", "clarity_id"),
                                    ("GA4", "ga4_id"),
                                    ("META", "meta_id")):
        riga = [l for l in CODICE.splitlines() if ("var %s =" % variabile) in l]
        assert riga, "sparita la variabile %s" % variabile
        assert "| json" in riga[0], (
            "%s non passa piu' da | json: un'impostazione scritta male "
            "romperebbe lo script, o ci infilerebbe codice.\n        %s"
            % (impostazione, riga[0].strip()))


prova("gli ID passano da | json e non possono rompere lo script",
      gli_id_sono_messi_in_sicurezza)


def niente_pixel_di_riserva():
    assert not re.search(r"facebook\.com/tr|<noscript", CODICE, re.I), (
        "e' tornato il pixel <img> di riserva di Meta. Quello parte SEMPRE, "
        "consenso o no, perche' senza JavaScript non c'e' modo di chiederlo: "
        "e' tracciamento senza permesso travestito da compatibilita'.")


prova("nessun pixel di riserva che sfugge al consenso", niente_pixel_di_riserva)


def sta_in_fondo_al_body():
    layout = open(LAYOUT, encoding="utf-8").read()
    i = layout.find("render 'perla-analytics'")
    assert i != -1, "theme.liquid non richiama piu' perla-analytics"
    fine_head = layout.find("</head>")
    assert fine_head != -1 and i > fine_head, (
        "perla-analytics e' tornato dentro il <head>. Li' "
        "window.Shopify.customerPrivacy non esiste ancora -- arriva con "
        "content_for_header -- quindi il cancello non avrebbe niente a cui "
        "chiedere il consenso. E' il difetto che c'era prima di ROUND 47.")


prova("lo snippet sta dopo il <head>, dove l'API del consenso esiste",
      sta_in_fondo_al_body)

print("\n  %d verifiche\n" % fatte)
