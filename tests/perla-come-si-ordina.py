#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le foto dei passaggi, e il video, per la pagina "Come si ordina".

PERCHE' COSI'
Chromium in questo ambiente non esce in rete (vedi perla-specchio.py), quindi
la pagina si copia prima in locale con curl e poi si apre da un server sul
loopback. Il JS del tema gira davvero: lo studio di personalizzazione si apre,
il nome si scrive, il consigliatore di taglia risponde. Le schermate sono
quindi il sito vero, non un disegno di come dovrebbe essere.

IL CURSORE DISEGNATO
Una registrazione dello schermo senza puntatore e' incomprensibile: le cose
cambiano e non si capisce perche'. Playwright non registra il cursore, quindi
se ne disegna uno nella pagina e lo si muove prima di ogni clic. E' l'unico
modo per cui un video del genere si capisca senza voce narrante.

USO
    python3 tests/perla-come-si-ordina.py            # foto + video
    python3 tests/perla-come-si-ordina.py --solo-foto
"""
import http.server
import os
import socketserver
import subprocess
import sys
import threading

from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium"
FFMPEG = "/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux"
SPECCHIO = "/tmp/specchio/prodotto"
USCITA = "/tmp/come-si-ordina"

CURSORE = """
(() => {
  if (document.getElementById('perla-cursore')) return;
  const c = document.createElement('div');
  c.id = 'perla-cursore';
  c.style.cssText = 'position:fixed;z-index:2147483647;width:26px;height:26px;' +
    'pointer-events:none;left:-50px;top:-50px;transition:left .5s cubic-bezier(.4,0,.2,1),' +
    'top .5s cubic-bezier(.4,0,.2,1);';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26">' +
    '<path d="M4 2 L4 20 L9 15.5 L12 22 L15 20.5 L12 14.5 L19 14 Z" ' +
    'fill="#132A4A" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  window.__perlaCursore = (x, y) => { c.style.left = x + 'px'; c.style.top = y + 'px'; };
  window.__perlaClic = () => {
    const o = document.createElement('div');
    const r = c.getBoundingClientRect();
    o.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;border-radius:50%;' +
      'border:2px solid #C8862B;left:' + (r.left - 12) + 'px;top:' + (r.top - 12) + 'px;' +
      'width:48px;height:48px;opacity:.9;transition:transform .45s,opacity .45s;';
    document.body.appendChild(o);
    requestAnimationFrame(() => { o.style.transform = 'scale(.35)'; o.style.opacity = '0'; });
    setTimeout(() => o.remove(), 500);
  };
})()
"""


def servi(radice):
    os.chdir(radice)
    srv = socketserver.TCPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d/index.html" % srv.server_address[1]


def pulisci(p):
    """Via il popup sconto: coprirebbe ogni schermata."""
    for sel in ("text=No, grazie", ".popup__close", "[data-popup-close]"):
        try:
            if p.locator(sel).count():
                p.locator(sel).first.click(timeout=2500)
                p.wait_for_timeout(500)
                break
        except Exception:
            pass
    p.evaluate("()=>{const o=document.querySelector('.popup-overlay');if(o)o.remove();"
               "document.documentElement.style.overflow='';document.body.style.overflow='';}")


def punta(p, sel, pausa=900):
    """Porta il cursore disegnato sopra l'elemento e lo fa 'battere'."""
    try:
        el = p.locator(sel).first
        el.scroll_into_view_if_needed(timeout=4000)
        p.wait_for_timeout(350)
        box = el.bounding_box()
        if not box:
            return False
        p.evaluate("([x,y])=>window.__perlaCursore(x,y)",
                   [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        p.wait_for_timeout(pausa)
        p.evaluate("()=>window.__perlaClic()")
        p.wait_for_timeout(350)
        return True
    except Exception:
        return False


def clic(p, sel):
    if not punta(p, sel):
        return False
    try:
        p.locator(sel).first.click(timeout=4000)
        p.wait_for_timeout(900)
        return True
    except Exception:
        try:
            p.locator(sel).first.evaluate("e=>e.click()")
            p.wait_for_timeout(900)
            return True
        except Exception:
            return False


def scatta(p, n, nome):
    os.makedirs(USCITA, exist_ok=True)
    percorso = "%s/%d-%s.png" % (USCITA, n, nome)
    p.screenshot(path=percorso)
    print("  %d. %-26s %s" % (n, nome, percorso))
    return percorso


def passeggiata(p):
    """I passaggi, nell'ordine in cui li fa un cliente. Ognuno e' tollerante:
    se un pezzo dell'interfaccia non c'e', si prosegue invece di fermarsi --
    meglio sei foto su sette che nessuna."""
    fatti = []
    p.evaluate(CURSORE)

    p.evaluate("()=>window.scrollTo(0,0)")
    p.wait_for_timeout(700)
    fatti.append(scatta(p, 1, "la-scheda"))

    # 2 — la taglia
    if clic(p, "[data-taglia-apri]"):
        try:
            p.fill("[data-taglia-peso]", "12")
            p.wait_for_timeout(400)
        except Exception:
            pass
        clic(p, "[data-taglia-calcola]")
        fatti.append(scatta(p, 2, "la-taglia"))

    # 3 — si apre lo studio
    for sel in ("[data-open-studio]", "text=Personalizza", ".product__customize",
                "[data-photo-customizer] button", "text=Aggiungi il suo nome"):
        if clic(p, sel):
            break
    p.wait_for_timeout(1200)
    fatti.append(scatta(p, 3, "lo-studio"))

    # 4 — il nome. Non si scrive dentro la tela: il tema ha un campo normale
    # nel modulo prodotto, `properties[Nome inciso]`, ed e' quello che finisce
    # nell'ordine. Il pulsante "+ Testo" aggiunge invece un livello libero
    # sulla tela di Fabric, che non e' il passaggio che il cliente compie.
    for sel in ("input[name='properties[Nome inciso]']", "[data-name-text]"):
        try:
            if p.locator(sel).count():
                punta(p, sel, 700)
                p.locator(sel).first.fill("MILO")
                p.locator(sel).first.dispatch_event("input")
                p.wait_for_timeout(1200)
                break
        except Exception:
            pass
    fatti.append(scatta(p, 4, "il-nome"))

    # 5 — il carattere e il colore
    clic(p, "[data-name-font] >> nth=1")
    clic(p, "[data-name-color-swatch] >> nth=2")
    fatti.append(scatta(p, 5, "colore-e-carattere"))

    # 6 — l'anteprima sul prodotto vero
    for sel in ("text=Genera anteprima reale", "[data-generate-preview]"):
        if clic(p, sel):
            p.wait_for_timeout(1500)
            break
    fatti.append(scatta(p, 6, "anteprima"))

    # 7 — nel carrello. Prima si chiude lo studio, se no il pannello copre il
    # pulsante e la foto mostrerebbe la stessa schermata di prima.
    for sel in (".photo-studio__close", "[data-studio-close]", ".studio__close"):
        if clic(p, sel):
            break
    p.wait_for_timeout(800)
    for sel in ("[data-add-to-cart]", "button[name='add']", ".product__add"):
        if clic(p, sel):
            break
    p.wait_for_timeout(1600)
    fatti.append(scatta(p, 7, "nel-carrello"))
    return fatti


def main(argv):
    solo_foto = "--solo-foto" in argv
    if not os.path.isdir(SPECCHIO):
        print("Manca %s: esegui prima\n"
              "  python3 tests/perla-specchio.py /products/<handle> prodotto" % SPECCHIO)
        return 1
    src = servi(SPECCHIO)
    os.makedirs(USCITA, exist_ok=True)

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, executable_path=CHROME,
                               args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = b.new_context(
            # 1100 e non 800: il pannello dello studio e' piu' alto di una
            # finestra normale, e con 800 il pulsante "+ Testo" resta sotto la
            # piega -- Playwright rifiuta di premerlo ("element is outside of
            # the viewport") e il nome non veniva mai scritto.
            viewport={"width": 1280, "height": 1100}, locale="it-IT",
            record_video_dir=None if solo_foto else USCITA + "/video",
            record_video_size={"width": 1280, "height": 1100})
        p = ctx.new_page()
        p.goto(src, wait_until="load", timeout=60000)
        p.wait_for_timeout(2500)
        pulisci(p)
        print("\nPassaggi:")
        passeggiata(p)
        video = p.video.path() if not solo_foto else None
        ctx.close()
        b.close()

    if video and os.path.exists(video):
        finale = USCITA + "/come-si-ordina.mp4"
        # webm -> mp4: Shopify riproduce l'mp4 ovunque, il webm non su Safari.
        subprocess.run([FFMPEG, "-y", "-i", video, "-vf",
                        "scale=1280:-2,fps=24", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", "-crf", "24", finale],
                       check=False, capture_output=True)
        if os.path.exists(finale):
            print("\nvideo: %s (%.1f MB)" % (finale, os.path.getsize(finale) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
