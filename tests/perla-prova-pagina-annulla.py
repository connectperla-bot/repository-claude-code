#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La pagina "annulla ordine" vista dal browser, col servizio finto.

Il servizio ha il suo collaudo (tests/perla-prova-annullamento.js); qui si
guarda l'altra meta': cosa vede il cliente. Le risposte del servizio sono
inventate da Playwright, cosi' si possono provare anche i casi che dal vivo non
si riescono a creare -- "la stampa e' gia' partita", "il servizio non risponde".

Le due cose che devono essere vere: il pulsante di conferma compare SOLO quando
si puo' davvero annullare, e dopo l'annullamento il modulo sparisce (nessuno
deve poter premere due volte).

Prima serve la copia locale della pagina, con l'indirizzo del servizio
impostato nella sezione (in produzione lo mette la titolare dall'editor):

    python3 tests/perla-specchio.py /pages/annulla-ordine annulla
    python3 -u tests/perla-prova-pagina-annulla.py
"""
import http.server, os, socketserver, threading, json
from playwright.sync_api import sync_playwright
class Muto(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
os.chdir("/tmp/specchio/annulla")
srv=socketserver.TCPServer(("127.0.0.1",0),Muto); porta=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()

CASI = [
  ("si puo' annullare, poi si conferma", 200, {"esito":"ok","numero":"#1042","annullabile":True},
   200, {"esito":"annullato","numero":"#1042","messaggio":"Fatto: l'ordine #1042 è annullato e non verrà stampato."}),
  ("stampa gia' partita", 200, {"esito":"ok","numero":"#1042","annullabile":False,
   "messaggio":"La stampa è già iniziata, quindi non possiamo più annullarlo."}, None, None),
  ("ordine non trovato", 404, {"esito":"non_trovato","messaggio":"Non troviamo un ordine con questo numero e questa email."}, None, None),
  ("servizio giu'", 502, {"esito":"errore","messaggio":"Non riusciamo a controllare l'ordine in questo momento."}, None, None),
]

with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,executable_path="/opt/pw-browsers/chromium",
                         args=["--no-sandbox","--disable-dev-shm-usage"])
    for nome, statoS, corpoS, statoA, corpoA in CASI:
        ctx=b.new_context(viewport={"width":1440,"height":900},locale="it-IT")
        p=ctx.new_page()
        err=[]; p.on("pageerror", lambda e: err.append(str(e)[:130]))
        def instrada(route):
            u=route.request.url
            if u.endswith("/ordine/stato"):
                route.fulfill(status=statoS, content_type="application/json", body=json.dumps(corpoS))
            elif u.endswith("/ordine/annulla"):
                route.fulfill(status=statoA, content_type="application/json", body=json.dumps(corpoA))
            else:
                route.abort()
        p.route("https://esempio-collaudo.invalid/**", instrada)
        p.goto("http://127.0.0.1:%d/index.html"%porta, wait_until="load", timeout=60000)
        p.wait_for_timeout(1500)
        p.evaluate("()=>{const o=document.querySelector('.popup-overlay');if(o)o.remove();"
                   "document.documentElement.style.overflow='';document.body.style.overflow='';}")
        p.evaluate("""()=>{const f=document.querySelector('[data-annulla-form]');
                     f.numero.value='#1042'; f.email.value='mario@example.it';}""")
        p.evaluate("()=>document.querySelector('[data-annulla-cerca]').click()")
        p.wait_for_timeout(900)
        dopo = p.evaluate("""()=>{const e=document.querySelector('[data-annulla-esito]');
          const c=document.querySelector('[data-annulla-conferma]');
          return {esito:e.textContent.trim().slice(0,60), classe:e.className, nascosto:e.hidden,
                  confermaVisibile:!c.hidden};}""")
        riga = {"passo1": dopo}
        if statoA is not None and dopo["confermaVisibile"]:
            p.evaluate("()=>document.querySelector('[data-annulla-conferma-si]').click()")
            p.wait_for_timeout(900)
            riga["passo2"] = p.evaluate("""()=>{const e=document.querySelector('[data-annulla-esito]');
              const c=document.querySelector('[data-annulla-conferma]');
              const f=document.querySelector('[data-annulla-form]');
              return {esito:e.textContent.trim().slice(0,60), classe:e.className,
                      confermaVisibile:!c.hidden, moduloVisibile:!f.hidden};}""")
        print(nome); print("   " + json.dumps(riga, ensure_ascii=False))
        if err: print("   errori JS:", err[:2])
        if nome.startswith("si puo"):
            p.locator(".annulla").screenshot(path="/tmp/shots/annulla-fatto.png")
        ctx.close()
    b.close()
srv.shutdown()
