#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rifa' i file di stampa RIUSANDO i disegni originali, alla misura giusta.

LA STORIA, PERCHE' NON SI RIPETA
Un primo tentativo aveva rifatto i motivi ornati disegnandoli a codice. Erano
puliti e ripetibili, e molto piu' poveri degli originali: giudizio della
titolare, "davvero brutti, fatti a cavolo". Aveva ragione, e aveva anche la
soluzione: riusare quelli vecchi e ricentrarli.

Il difetto non era mai stato il disegno. Erano tre cose diverse, tutte di
lavorazione:

  la SCALA -- il medaglione disegnato per una bandana da 53 cm finiva tale e
  quale su un collare alto 2,5 cm;
  il CENTRAGGIO -- il bordo cadeva a meta' motivo, quindi disegni interi da un
  lato e mozzi dall'altro, scritte che si leggevano "erla";
  la RISOLUZIONE -- sulla linea americana sorgenti 1280x720 ingrandite fino a
  dieci volte, ed e' per questo che sembravano impastate.

Tutte e tre si correggono senza toccare il disegno, ed e' quello che fa questo
script: perla-piastrelle-originali.py estrae la piastrella vera, la porta alla
misura fisica giusta e la stende sull'area di stampa senza mai ingrandirla.

DOVE PESCA
  linea EU    generated-designs/motivi-stampa/_originali/ -- 62 file alla
              misura nativa di stampa, uno per prodotto, con lo stesso nome.
  linea USA   generated-designs/*.jpg -- le sorgenti di quella linea. Sono
              piccole (1280x720), ma AFFIANCATE a grandezza naturale danno un
              file nitido a qualunque misura, che e' esattamente cio' che
              ingrandirle non faceva.

QUANDO NON C'E' UN ORIGINALE BUONO NON SI INVENTA
Il prodotto viene elencato e lasciato com'e'. Scelta della titolare, ed e' la
piu' sensata: meglio mediocre e coerente col resto che rifatto e stonato.

USO
    python3 scripts/perla-rifai-motivi.py            # elenca il piano
    python3 scripts/perla-rifai-motivi.py --genera   # scrive i file
"""
import importlib.util
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
USCITA = os.path.join(RADICE, "generated-designs", "motivi-rifatti")
SORGENTI_USA = os.path.join(RADICE, "generated-designs")


def _modulo(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tessere = _modulo("perla_piastrelle_originali",
                  os.path.join(QUI, "perla-piastrelle-originali.py"))
scala = _modulo("perla_scala_stampa", os.path.join(QUI, "perla-scala-stampa.py"))

# Il passo, in centimetri, sui prodotti che non sono nastri. Sui nastri non
# serve: la striscia e' alta quanto il nastro e si ripete solo in orizzontale.
# La bandana americana usa lo stesso numero di quella europea, per scelta
# esplicita: chi compra le due versioni deve ricevere lo stesso prodotto.
# Prima stesura: 26 cm sulla bandana, cioe' il disegno alla scala con cui era
# stato creato. Guardato il foglio di contatto, su diversi originali il
# cartiglio "PERLA ITALIA" resta grande otto centimetri e il prodotto sembra
# un manifesto invece che un tessuto -- lo stesso difetto segnalato all'inizio,
# solo non piu' tagliato. Dimezzando il passo si dimezza anche la scritta, e il
# disegno si legge come stoffa. Il dettaglio non si perde: rimpicciolire una
# sorgente e' l'unica direzione che non impasta niente.
PASSO_CM = {
    "bandana-eu": 13.0, "bandana-usa": 13.0,
    "cuccia-usa": 16.0, "medaglietta-usa": 3.5, "ciotola-usa": 8.0,
}

NEUTRI = ("crea-il-tuo-design", "neutro", "personalizza")


def _originali_per(famiglia, cartella):
    """I nomi dei motivi disponibili per una famiglia, dal piu' lungo al piu'
    corto: cosi' 'damasco-classico' vince su 'damasco', che sarebbe un altro
    prodotto."""
    fuori = []
    for f in sorted(os.listdir(cartella)):
        if not f.lower().endswith((".jpg", ".png")):
            continue
        base = f.rsplit(".", 1)[0]
        if famiglia and not base.startswith(famiglia + "-"):
            continue
        fuori.append((base[len(famiglia) + 1:] if famiglia else base, f))
    return sorted(fuori, key=lambda x: -len(x[0]))


def famiglia(handle):
    for tipo in scala.AREE:
        radice = tipo.split("-")[0]
        if handle.startswith(radice + "-eu-") and tipo.endswith("-eu"):
            return tipo
    for parola, tipo in (("cuccia", "cuccia-usa"), ("bed", "cuccia-usa"),
                         ("bandana", "bandana-usa"), ("tag", "medaglietta-usa"),
                         ("medaglietta", "medaglietta-usa"),
                         ("ciotola", "ciotola-usa")):
        if parola in handle:
            return tipo
    return None


def sorgente(handle, titolo, tipo):
    """L'originale da cui pescare, o None."""
    if tipo.endswith("-eu"):
        fam = tipo.split("-")[0]
        slug = handle[len(fam) + 4:].replace("-fornitore-europeo", "")
        for nome, f in _originali_per(fam, tessere.ORIGINALI):
            if slug.startswith(nome):
                return os.path.join(tessere.ORIGINALI, f), nome
        return None, None

    # Linea americana: le sorgenti hanno nomi propri, si cerca per parole in
    # comune con handle e titolo. Il TITOLO conta di piu' -- e' l'unica delle
    # due cose che il cliente legge, e sulla linea americana i due non vanno
    # d'accordo: `bandana-damask-navy` si chiama Bandana "Paisley".
    testo = (titolo + " " + handle).lower()
    migliore = None
    for nome, f in _originali_per("", SORGENTI_USA):
        parole = [p for p in nome.lower().replace("_", "-").split("-")
                  if len(p) > 3 and p not in ("perla", "italia", "bandana",
                                              "cuccia", "collar", "tag", "new")]
        if not parole:
            continue
        punti = sum(1 for p in parole if p in testo)
        # Preferenza forte per la stessa famiglia. Senza, a parita' di parole
        # in comune vinceva il nome piu' lungo: la bandana "Diamante" pescava
        # dal disegno della CUCCIA "geometric charcoal silver" invece che da
        # quello della bandana omonima. Un disegno pensato per un altro
        # oggetto puo' anche funzionare, ma se quello giusto c'e' si usa
        # quello.
        if punti and nome.lower().startswith(tipo.split("-")[0]):
            punti += 10
        if punti and (migliore is None or punti > migliore[0]):
            migliore = (punti, os.path.join(SORGENTI_USA, f), nome)
    if migliore:
        return migliore[1], migliore[2]
    return None, None


def elenco_prodotti():
    voci = []
    for nome, linea in (("perla-eu-prodotti.json", "eu"),
                        ("perla-usa-prodotti.json", "usa")):
        p = os.path.join(QUI, nome)
        if os.path.exists(p):
            for v in json.load(open(p, encoding="utf-8")):
                voci.append((v["handle"], v.get("title", ""), v.get("id", ""), linea))
    return voci


def main(argv):
    scrivi = "--genera" in argv
    if scrivi:
        os.makedirs(USCITA, exist_ok=True)
    conteggio = {}
    saltati = []
    print("%-50s %-15s %-22s %s" % ("prodotto", "area", "originale", "esito"))
    for handle, titolo, _id, linea in elenco_prodotti():
        if any(p in handle.lower() for p in NEUTRI) or "crea il tuo" in titolo.lower():
            conteggio["neutro"] = conteggio.get("neutro", 0) + 1
            continue
        tipo = famiglia(handle)
        if tipo is None:
            conteggio["tipo-ignoto"] = conteggio.get("tipo-ignoto", 0) + 1
            saltati.append((handle, "tipo di prodotto non riconosciuto"))
            continue
        percorso, nome = sorgente(handle, titolo, tipo)
        if percorso is None:
            conteggio["senza-originale"] = conteggio.get("senza-originale", 0) + 1
            saltati.append((handle, "nessun originale corrispondente"))
            continue

        nota = ""
        if scrivi:
            t, info = tessere.piastrella(percorso)
            im, det = tessere.stendi(t, tipo, PASSO_CM.get(tipo, 8.0))
            im.save(os.path.join(USCITA, handle + ".jpg"), quality=94)
            nota = "scala %.2f, %.1f ripet.%s" % (
                det["scala"], det["ripetizioni"],
                " (sfumata)" if info["cucita"] else "")
        conteggio["rifatto"] = conteggio.get("rifatto", 0) + 1
        print("%-50s %-15s %-22s %s" % (handle[:50], tipo, nome[:22], nota))

    print()
    for k in sorted(conteggio):
        print("  %-18s %d" % (k, conteggio[k]))
    if saltati:
        print("\nLASCIATI COM'ERANO (nessun originale buono):")
        for h, perche in saltati:
            print("  %-52s %s" % (h[:52], perche))
    if not scrivi:
        print("\n(solo elenco: --genera per scrivere i file in %s)" % USCITA)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
