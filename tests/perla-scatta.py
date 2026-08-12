#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fotografa una pagina copiata in locale da perla-specchio.py.

Chromium apre file:// (in rete non riesce a uscire, vedi perla-specchio.py),
quindi il rendering e' vero: JS eseguito, stili calcolati leggibili.

    python3 tests/perla-scatta.py home              desktop 1440
    python3 tests/perla-scatta.py home --mobile     telefono 390
"""
import http.server
import os
import socketserver
import sys
import threading
from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium"


def main():
    nome = sys.argv[1] if len(sys.argv) > 1 else "home"
    mobile = "--mobile" in sys.argv
    # Non file://: Chromium blocca l'import dei moduli ES da file://, e senza
    # quei moduli motion.js non parte -- le sezioni restano a opacita' zero e
    # sembrano vuote. Un server locale toglie di mezzo il problema (il loopback
    # e' in NO_PROXY, quindi il browser ci arriva).
    radice = "/tmp/specchio/%s" % nome
    os.chdir(radice)
    srv = socketserver.TCPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    src = "http://127.0.0.1:%d/index.html" % porta
    suff = "mob" if mobile else "desk"
    os.makedirs("/tmp/shots", exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, executable_path=CHROME,
                               args=["--no-sandbox", "--disable-dev-shm-usage",
                                     "--allow-file-access-from-files"])
        ctx = b.new_context(
            viewport={"width": 390, "height": 844} if mobile else {"width": 1440, "height": 900},
            is_mobile=mobile, has_touch=mobile, locale="it-IT",
            device_scale_factor=2 if mobile else 1)
        p = ctx.new_page()
        errori = []
        p.on("pageerror", lambda e: errori.append(str(e)[:140]))
        p.goto(src, wait_until="load", timeout=60000)
        p.wait_for_timeout(2500)
        # il popup sconto copre tutto: si chiude come farebbe un cliente
        for sel in ("text=No, grazie", ".popup__close", "[data-popup-close]"):
            try:
                if p.locator(sel).count():
                    p.locator(sel).first.click(timeout=3000)
                    p.wait_for_timeout(600)
                    break
            except Exception:
                pass
        p.evaluate("()=>{const o=document.querySelector('.popup-overlay');if(o)o.remove();"
                   "document.documentElement.style.overflow='';document.body.style.overflow='';}")
        p.wait_for_timeout(400)
        # Le sezioni compaiono con un IntersectionObserver: senza scorrere,
        # una schermata a pagina intera le prende tutte a opacita' zero e
        # sembra che manchi meta' del sito. Si scorre fino in fondo e si torna su.
        p.evaluate("""async ()=>{
          const passo = window.innerHeight * 0.7;
          for (let y = 0; y < document.body.scrollHeight; y += passo) {
            window.scrollTo(0, y);
            await new Promise(r => setTimeout(r, 220));
          }
          window.scrollTo(0, 0);
          await new Promise(r => setTimeout(r, 500));
        }""")
        # ...ma scorrere non basta: il tema ha uno scorrimento morbido tutto suo
        # (motion.js sposta un contenitore con transform) e nello specchio non
        # parte, quindi window.scrollTo non muove niente e le rivelazioni non
        # scattano mai. Misurato: 3 elementi su 34 rivelati -- e la stessa cosa
        # sul tema pubblicato, che nessuno ha toccato, quindi e' un limite dello
        # specchio e non un difetto del sito. Si forza lo stato finale: le
        # schermate mostrano l'animazione finita, che e' quello che serve
        # guardare. Per collaudare l'animazione mentre avviene serve il sito vero.
        p.evaluate("""()=>{
          document.querySelectorAll('[data-reveal]').forEach(e => e.classList.add('is-visible'));
          document.querySelectorAll('[data-words],[data-rule],[data-blinds],[data-curtain]')
            .forEach(e => e.classList.add('is-in', 'in'));
          document.querySelectorAll('.stagger-item').forEach(e => e.classList.add('stagger-in'));
        }""")
        p.wait_for_timeout(900)
        p.wait_for_timeout(800)
        p.screenshot(path="/tmp/shots/%s-%s-alto.png" % (suff, nome))
        p.screenshot(path="/tmp/shots/%s-%s-intera.png" % (suff, nome), full_page=True)
        for sel, etichetta in (("header", "header"), (".hero", "hero"), (".story", "story"),
                               ("[data-marquee]", "marquee"), ("footer", "footer"),
                               (".quiz", "quiz")):
            try:
                if p.locator(sel).count():
                    p.locator(sel).first.scroll_into_view_if_needed(timeout=5000)
                    p.wait_for_timeout(700)
                    p.locator(sel).first.screenshot(path="/tmp/shots/%s-%s-%s.png" % (suff, nome, etichetta))
            except Exception as e:
                print("  (%s non fotografato: %s)" % (etichetta, str(e)[:60]))
        print("misure:", p.evaluate("()=>JSON.stringify({h:document.body.scrollHeight})"))
        if errori:
            print("errori JS:", errori[:5])
        # dati utili per i difetti segnalati
        print(p.evaluate("""()=>{
          const q=s=>document.querySelector(s);
          const perle=q('#perla-pearls');
          const mq=q('[data-marquee]');
          const tr=mq?mq.querySelectorAll('.marquee__track'):[];
          const st=tr[0]?getComputedStyle(tr[0]):null;
          return JSON.stringify({
            perle: perle?{w:perle.width,h:perle.height,op:getComputedStyle(perle).opacity,
                          disp:getComputedStyle(perle).display,z:getComputedStyle(perle).zIndex,
                          disegnato: (()=>{try{const c=perle.getContext('2d');
                            const d=c.getImageData(0,0,Math.min(perle.width,200),Math.min(perle.height,200)).data;
                            let n=0;for(let i=3;i<d.length;i+=4) if(d[i]>8) n++;return n;}catch(e){return 'no';}})()}:'assente',
            marquee: mq?{tracce:tr.length, anim:st&&st.animationName, dur:st&&st.animationDuration,
                         traccia:Math.round(tr[0].getBoundingClientRect().width),
                         box:Math.round(mq.getBoundingClientRect().width)}:'assente'
          },null,1);}"""))
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    main()
