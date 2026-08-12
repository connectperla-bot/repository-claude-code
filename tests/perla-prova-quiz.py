#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Percorre il quiz come un cliente e controlla il consiglio che ne esce.

Il quiz sceglie un prodotto vero fra sedici combinazioni palette x tipo, e le
sedici schede stanno tutte in pagina con [hidden]: quella giusta e' l'unica
che resta. Qui si verifica proprio questo, su quattro percorsi diversi --
che la scheda visibile sia una sola, che sia la combinazione attesa, che la
foto e la frase ci siano, e che la pagina non sfondi in orizzontale.

Prima serve la copia locale della home:

    python3 tests/perla-specchio.py / quiz
    python3 tests/perla-prova-quiz.py
"""
import http.server, os, socketserver, threading, json
from playwright.sync_api import sync_playwright

class Muto(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

os.chdir("/tmp/specchio/quiz")
srv = socketserver.TCPServer(("127.0.0.1", 0), Muto)
porta = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

PERCORSI = [
    ("mare", "large", "chiaro", "collare"),
    ("campagna", "small", "scuro", "bandana"),
    ("casa", "cat", "rosso", "ciotola"),
    ("citta", "medium", "misto", "guinzaglio"),
]

CLICK = "(sel)=>{const e=document.querySelector(sel); if(!e) throw new Error('manca '+sel); e.click();}"

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium",
                           args=["--no-sandbox", "--disable-dev-shm-usage"])
    for luogo, taglia, pelo, tipo in PERCORSI:
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="it-IT")
        p = ctx.new_page()
        errori = []
        p.on("pageerror", lambda e: errori.append(str(e)[:160]))
        p.goto("http://127.0.0.1:%d/index.html" % porta, wait_until="load", timeout=60000)
        p.wait_for_timeout(1800)
        p.evaluate("()=>{const o=document.querySelector('.popup-overlay');if(o)o.remove();"
                   "document.documentElement.style.overflow='';document.body.style.overflow='';}")
        p.locator(".quiz").first.scroll_into_view_if_needed()
        p.wait_for_timeout(500)

        p.evaluate("""()=>{const i=document.querySelector('.quiz__step[data-key="petname"] input[type=text]');
                        i.value='Aron'; i.dispatchEvent(new Event('input',{bubbles:true}));}""")
        p.evaluate(CLICK, '.quiz__step[data-key="petname"] [data-quiz-next]')
        p.wait_for_timeout(400)
        for chiave, valore in (("luogo", luogo), ("taglia", taglia), ("pelo", pelo)):
            p.evaluate(CLICK, '.quiz__step[data-key="%s"] .quiz__option[data-value="%s"]' % (chiave, valore))
            p.wait_for_timeout(500)
        p.evaluate(CLICK, '.quiz__step[data-key="interesse"] .quiz__option[data-tipo="%s"]' % tipo)
        p.wait_for_timeout(900)

        esito = p.evaluate("""()=>{
          const vis = [...document.querySelectorAll('.quiz__pick')].filter(a=>!a.hidden);
          const box = document.querySelector('[data-quiz-consigli]');
          const h = document.querySelector('[data-quiz-hint]');
          const r = vis[0] ? vis[0].getBoundingClientRect() : null;
          const link = document.querySelector('[data-quiz-shop-link]');
          return {
            visibili: vis.length,
            combo: vis[0] ? vis[0].getAttribute('data-combo') : null,
            nome: vis[0] ? vis[0].querySelector('.quiz__pick-nome').textContent : null,
            prezzo: vis[0] ? vis[0].querySelector('.quiz__pick-prezzo').textContent : null,
            larghezza: r ? Math.round(r.width) : 0,
            altezza: r ? Math.round(r.height) : 0,
            boxVisibile: box ? !box.hidden : false,
            frase: h ? h.textContent : '',
            cane: document.querySelector('.quiz__result .pet-name').textContent,
            bottone: link ? link.getAttribute('href') : null,
            sfonda: document.documentElement.scrollWidth > window.innerWidth + 1
          };}""")
        atteso = luogo + "|" + tipo
        ok = (esito["visibili"] == 1 and esito["combo"] == atteso and esito["boxVisibile"]
              and esito["altezza"] > 40 and not esito["sfonda"] and esito["cane"] == "Aron"
              and len(esito["frase"]) > 60)
        print(("OK  " if ok else "KO  ") + atteso)
        print("    " + json.dumps(esito, ensure_ascii=False))
        if errori:
            print("    errori JS:", errori[:3])
        if luogo == "mare":
            p.locator(".quiz").first.screenshot(path="/tmp/shots/quiz-risultato.png")
        ctx.close()
    b.close()
srv.shutdown()
