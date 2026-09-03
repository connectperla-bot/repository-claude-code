#!/usr/bin/env node
/**
 * Il contrasto del testo, misurato dal browser e non dedotto dal CSS.
 *
 * PERCHE' NON BASTA LEGGERE IL CSS
 * Il colore di una scritta arriva da una catena di regole, variabili e
 * ereditarieta' che solo il browser sa risolvere; e il fondo su cui cade non
 * e' quasi mai quello dell'elemento stesso, ma di un antenato. Qui si
 * chiedono gli stili CALCOLATI e si risale finche' non si trova un fondo
 * opaco -- che e' cosa vede davvero l'occhio.
 *
 * QUELLO CHE QUESTO CONTROLLO NON PUO' FARE, ed e' importante saperlo: dove
 * il fondo e' una FOTOGRAFIA non esiste nessun colore CSS che la descriva.
 * Li' esce un falso allarme (bianco su "crema", 1,04) e il contrasto vero si
 * misura sui pixel: si nasconde la scritta, si fotografa cio' che le sta
 * dietro e si guarda la luminanza. E' cosi' che e' stato misurato il titolo
 * dell'eroe -- vedi il commento in assets/perla-tocco.css.
 *
 * SUL SITO VIVO NON ARRIVA, da questo ambiente: il browser non passa dal
 * proxy. Si scarica la pagina con curl, si scaricano i suoi fogli di stile,
 * si riscrivono i link e si apre da file://. I colori sono gli stessi.
 *
 * USO
 *     node scripts/perla-verifica-contrasto.js file:///percorso/pagina.html
 */
const { chromium } = require('playwright');

const PAGINE = process.argv.slice(2);
if (!PAGINE.length) {
  console.error('serve almeno una pagina da guardare');
  process.exit(2);
}

// In questo ambiente il browser di Playwright non e' quello che la libreria
// si aspetta: si punta a quello installato.
const BROWSER = process.env.PERLA_CHROMIUM
  || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

(async () => {
  const browser = await chromium.launch({ executablePath: BROWSER, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let fuoriTotali = 0;

  for (const url of PAGINE) {
    await page.goto(url, { waitUntil: 'load', timeout: 90000 });
    await page.waitForTimeout(800);
    const esito = await page.evaluate(() => {
      function lum(c) {
        const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
      }
      function rgb(s) {
        const m = s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
        return m ? { c: [ +m[1], +m[2], +m[3] ], a: m[4] === undefined ? 1 : +m[4] } : null;
      }
      function fondo(el) {
        let n = el;
        while (n && n !== document.documentElement) {
          const b = rgb(getComputedStyle(n).backgroundColor);
          if (b && b.a > 0.5) return b.c;
          n = n.parentElement;
        }
        return [255, 255, 255];
      }
      const fuori = [];
      const nodi = document.querySelectorAll('body *');
      for (const el of nodi) {
        if (!el.offsetParent && getComputedStyle(el).position !== 'fixed') continue;
        // solo il testo PROPRIO dell'elemento: quello dei figli lo misura il figlio
        const testo = Array.from(el.childNodes)
          .filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
        if (testo.length < 2) continue;
        const st = getComputedStyle(el);
        if (st.visibility === 'hidden' || st.opacity === '0') continue;
        const f = rgb(st.color); if (!f) continue;
        const b = fondo(el);
        const c = f.c.map((v, i) => v * f.a + b[i] * (1 - f.a));
        const L1 = lum(c), L2 = lum(b);
        const r = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
        const px = parseFloat(st.fontSize);
        const grande = px >= 24 || (px >= 18.66 && parseInt(st.fontWeight, 10) >= 700);
        const minimo = grande ? 3.0 : 4.5;
        if (r < minimo) {
          fuori.push({ tag: el.tagName.toLowerCase(), cls: (el.className || '').toString().slice(0, 40),
                       testo: testo.slice(0, 42), r: +r.toFixed(2), minimo, px: Math.round(px),
                       colore: st.color, fondo: 'rgb(' + b.join(',') + ')' });
        }
      }
      return { totali: nodi.length, fuori };
    });

    console.log('\n=== ' + url);
    console.log('elementi guardati: ' + esito.totali + ' | sotto la soglia: ' + esito.fuori.length);
    const visti = new Set();
    for (const f of esito.fuori) {
      const chiave = f.cls + '|' + f.r;
      if (visti.has(chiave)) continue;
      visti.add(chiave);
      console.log('  %s  min %s  .%s  "%s"  %s su %s  (%dpx)',
        String(f.r).padStart(5), f.minimo, f.cls || f.tag, f.testo, f.colore, f.fondo, f.px);
    }
    fuoriTotali += esito.fuori.length;
  }

  await browser.close();
  process.exit(fuoriTotali ? 1 : 0);
})();
