#!/usr/bin/env node
'use strict';

/**
 * perla-crea-tappetini.js
 *
 * Crea su Printify i tappetini a motivo, in BOZZA. Non tocca nessun prodotto
 * esistente.
 *
 * PERCHE' UNO SCRIPT A PARTE
 * create-draft-designs.js ha i design scritti a mano dentro main(): va bene
 * per due o tre, non per diciannove. Qui le definizioni si costruiscono dai
 * file gia' prodotti da perla-file-stampa-motivi.py, quindi aggiungere un
 * motivo domani significa rigenerare i file, non modificare questo file.
 *
 * Il metodo di chiamata (upload immagine + creazione prodotto) e' lo stesso di
 * create-draft-designs.js e perla-create-neutral-products.js.
 *
 * PRIMA DI LANCIARLO
 *   python3 scripts/perla-file-stampa-motivi.py --forma tappetino --tutti
 * che scrive generated-designs/motivi-stampa/tappetino-<motivo>.jpg
 *
 * LA BASE NEUTRA NON SI CREA QUI
 * "Tappetino Crea il Tuo Design" e' gia' previsto da
 * perla-create-neutral-products.js (chiave TAPPETINO, 34,99 euro): usare
 * quello, cosi' la base neutra resta identica a quella degli altri tipi.
 *
 * IL TAG CHE NON SI PUO' SBAGLIARE
 * Ogni prodotto esce con il tag 'tappetino'. Il tema lo pretende: la riga
 * "tappetino|tipo-tappetino,mat,tappetino|1.44|..." in
 * snippets/perla-print-areas.liquid accetta solo questi tre alias. Senza uno
 * di essi il canvas dello studio usa il rapporto predefinito e "Salva
 * anteprima" manda product_type vuoto, che il server rifiuta con "Tipo
 * prodotto non riconosciuto" -- e' il difetto ROUND 16e gia' documentato nel
 * tema, che era costato l'anteprima su cinque tipi prodotto su sei.
 *
 * Uso:
 *   node scripts/perla-crea-tappetini.js --prova      # non chiama l'API, mostra cosa farebbe
 *   node scripts/perla-crea-tappetini.js
 *   node scripts/perla-crea-tappetini.js --prezzo 3999
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const FILE_STAMPA = path.join(ROOT, 'generated-designs', 'motivi-stampa');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');

// Prezzo in centesimi. 34,99 e' lo stesso della base neutra tappetino in
// perla-create-neutral-products.js: partire allineati e ritoccare dopo dal
// pannello e' meglio che inventare qui un prezzo diverso senza motivo.
const PREZZO_PREDEFINITO = 3499;

// Printify fa fatica con raffiche di richieste: gli altri script del
// repository non ne mandano mai piu' di una alla volta, e neanche questo.
const PAUSA_MS = 900;

function leggiConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    throw new Error(
      'Config non trovato: ' + CONFIG_PATH + '\n' +
      'Copia config/printify.env.example in config/printify.local.env e inserisci le credenziali.'
    );
  }
  const testo = fs.readFileSync(CONFIG_PATH, 'utf8');
  function campo(nome, predefinito) {
    const m = testo.match(new RegExp('^' + nome + '=([^\\r\\n]*)', 'm'));
    const v = m ? m[1].trim() : '';
    return v || predefinito;
  }
  const apiKey = campo('PRINTIFY_API_KEY', '');
  const shopId = campo('PRINTIFY_SHOP_ID', '');
  if (!apiKey || !shopId) throw new Error('PRINTIFY_API_KEY o PRINTIFY_SHOP_ID mancanti in ' + CONFIG_PATH);
  return {
    apiKey,
    shopId,
    // stessi valori di render.yaml: il tappetino e' gia' configurato ovunque,
    // qui non si inventa niente di nuovo
    blueprintId: Number(campo('TAPPETINO_BLUEPRINT_ID', '855')),
    providerId: Number(campo('TAPPETINO_PROVIDER_ID', '70')),
    variantId: Number(campo('TAPPETINO_VARIANT_ID', '76892')),
  };
}

function attendi(ms) {
  return new Promise(function (r) { setTimeout(r, ms); });
}

function chiamaPrintify(apiKey, metodo, percorso, corpo) {
  const dati = corpo ? JSON.stringify(corpo) : null;
  const opzioni = {
    method: metodo,
    hostname: 'api.printify.com',
    path: '/v1' + percorso,
    headers: {
      Authorization: 'Bearer ' + apiKey,
      'Content-Type': 'application/json',
      'User-Agent': 'perla-crea-tappetini/1.0',
    },
  };
  if (dati) opzioni.headers['Content-Length'] = Buffer.byteLength(dati);
  return new Promise(function (risolvi, rifiuta) {
    const req = https.request(opzioni, function (res) {
      let corpoRisposta = '';
      res.on('data', function (c) { corpoRisposta += c; });
      res.on('end', function () {
        let json;
        try { json = JSON.parse(corpoRisposta); } catch (e) { json = corpoRisposta; }
        if (res.statusCode >= 200 && res.statusCode < 300) return risolvi(json);
        rifiuta(new Error('HTTP ' + res.statusCode + ' su ' + percorso + ': ' +
          JSON.stringify(json).slice(0, 400)));
      });
    });
    req.on('error', rifiuta);
    if (dati) req.write(dati);
    req.end();
  });
}

// Si legge il manifesto scritto dal generatore, non la cartella. E' li' che
// vive il giudizio sulla risoluzione: un ritaglio marcato "scarso" (un motivo
// senza sorgente quadrata rende 1204x803 invece di 4125x2865) stamperebbe
// sgranato su un tappetino vero, e va escluso qui invece che a occhio.
function fileDaCaricare() {
  const manifesto = path.join(FILE_STAMPA, 'files.json');
  if (!fs.existsSync(manifesto)) {
    throw new Error(
      'Manifesto non trovato: ' + manifesto + '\n' +
      'Genera prima i file:  python3 scripts/perla-file-stampa-motivi.py --forma tappetino --tutti'
    );
  }
  const voci = JSON.parse(fs.readFileSync(manifesto, 'utf8'));
  const elenco = [];
  let scartati = 0;
  voci.forEach(function (v) {
    if (v.forma !== 'tappetino') return;
    if (v.esito !== 'ok') {
      console.warn('  (scartato "' + v.motivo + '": ritaglio ' + v.larghezza + 'x' + v.altezza +
        ', troppo piccolo per la stampa)');
      scartati++;
      return;
    }
    const percorso = path.join(FILE_STAMPA, v.file);
    if (!fs.existsSync(percorso)) {
      console.warn('  (manca il file ' + v.file + ' citato dal manifesto)');
      return;
    }
    elenco.push({
      motivo: v.motivo,
      file: percorso,
      nomeFile: v.file,
      dimensioni: v.larghezza + 'x' + v.altezza,
    });
  });
  if (scartati) {
    console.warn('  ' + scartati + ' motivi scartati: rigenerali ad alta risoluzione se li vuoi.\n');
  }
  return elenco.sort(function (a, b) { return a.motivo.localeCompare(b.motivo); });
}

async function caricaImmagine(apiKey, percorso, nomeFile) {
  const base64 = fs.readFileSync(percorso).toString('base64');
  const res = await chiamaPrintify(apiKey, 'POST', '/uploads/images.json', {
    file_name: nomeFile,
    contents: base64,
  });
  return res.id;
}

// Il catalogo Printify viene letto PRIMA di creare qualsiasi cosa: lanciare
// due volte lo script non deve produrre trentotto tappetini. Il confronto e'
// sul titolo, che e' l'unica cosa stabile fra un giro e l'altro.
async function titoliEsistenti(apiKey, shopId) {
  const titoli = new Set();
  let pagina = 1;
  for (;;) {
    const res = await chiamaPrintify(apiKey, 'GET', '/shops/' + shopId + '/products.json?page=' + pagina + '&limit=100');
    const elenco = (res && res.data) || [];
    elenco.forEach(function (p) { titoli.add((p.title || '').trim()); });
    if (elenco.length < 100) break;
    pagina++;
    await attendi(PAUSA_MS);
  }
  return titoli;
}

function corpoProdotto(cfg, motivo, imageId, prezzo) {
  return {
    title: 'Tappetino "' + motivo + '"',
    description:
      'Il motivo ' + motivo + ' sul tappetino da pappa, in tinta con la cuccia e con il resto della collezione. ' +
      'Superficie morbida e base che resta ferma, per tenere in ordine la zona dei pasti.\n\n' +
      'Disegnato in Italia. Stampato dopo l\'ordine, quindi non ci sono rimanenze.\n\n' +
      'Lavabile. Spedizione tracciata.',
    blueprint_id: cfg.blueprintId,
    print_provider_id: cfg.providerId,
    variants: [{ id: cfg.variantId, price: prezzo, is_enabled: true }],
    print_areas: [
      {
        variant_ids: [cfg.variantId],
        placeholders: [
          {
            position: 'front',
            // Il file e' gia' ritagliato al rapporto dell'area di stampa
            // (1.44, vedi perla-file-stampa-motivi.py): centrato a scala 1.0
            // la riempie esattamente, senza bordi bianchi e senza deformare.
            images: [{ id: imageId, x: 0.5, y: 0.5, scale: 1.0, angle: 0 }],
          },
        ],
      },
    ],
    // 'tappetino' e' obbligatorio, vedi il commento in testa al file.
    tags: ['perla-italy', 'pet', 'tappetino', 'personalizzabile'],
  };
}

function argomenti() {
  const a = process.argv.slice(2);
  const out = { prova: false, prezzo: PREZZO_PREDEFINITO };
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--prova' || a[i] === '-n') out.prova = true;
    else if (a[i] === '--prezzo') out.prezzo = Number(a[++i]);
    else if (a[i] === '--help' || a[i] === '-h') {
      console.log(`
Crea su Printify i tappetini a motivo, in bozza.

  --prova, -n        mostra cosa farebbe senza chiamare l'API
  --prezzo <cent>    prezzo in centesimi (predefinito ${PREZZO_PREDEFINITO} = ${(PREZZO_PREDEFINITO / 100).toFixed(2)} euro)

Prima serve:  python3 scripts/perla-file-stampa-motivi.py --forma tappetino --tutti
`);
      process.exit(0);
    }
  }
  if (!Number.isFinite(out.prezzo) || out.prezzo <= 0) {
    throw new Error('--prezzo vuole un numero di centesimi, es. 3499');
  }
  return out;
}

async function main() {
  const args = argomenti();
  const daFare = fileDaCaricare();

  if (!daFare.length) {
    console.error('Nessun file tappetino-*.jpg in ' + path.relative(ROOT, FILE_STAMPA) + '.');
    console.error('Genera prima i file di stampa:');
    console.error('  python3 scripts/perla-file-stampa-motivi.py --forma tappetino --tutti');
    return 1;
  }

  console.log('\n=== Tappetini a motivo, ' + daFare.length + ' file trovati ===\n');

  if (args.prova) {
    const cfgProva = fs.existsSync(CONFIG_PATH) ? leggiConfig() : null;
    daFare.forEach(function (d) {
      const kb = Math.round(fs.statSync(d.file).size / 1024);
      console.log('  Tappetino "' + d.motivo + '"  <- ' + d.nomeFile + ' (' + kb + ' KB)');
    });
    console.log('\n  prezzo: ' + (args.prezzo / 100).toFixed(2) + ' euro');
    if (cfgProva) {
      console.log('  blueprint ' + cfgProva.blueprintId + ', provider ' + cfgProva.providerId +
        ', variante ' + cfgProva.variantId);
    }
    console.log('\n  Prova: nessuna chiamata all\'API. Togli --prova per creare davvero.');
    return 0;
  }

  const cfg = leggiConfig();
  console.log('  Negozio Printify ' + cfg.shopId + ', blueprint ' + cfg.blueprintId +
    ', provider ' + cfg.providerId + ', variante ' + cfg.variantId + '\n');

  console.log('  Leggo i prodotti gia' + '\' esistenti, per non crearne di doppi...');
  const esistenti = await titoliEsistenti(cfg.apiKey, cfg.shopId);
  console.log('  ' + esistenti.size + ' prodotti gia\' nel negozio.\n');

  const creati = [];
  let saltati = 0;
  for (const d of daFare) {
    const titolo = 'Tappetino "' + d.motivo + '"';
    if (esistenti.has(titolo)) {
      console.log('  = ' + titolo + ' esiste gia\', saltato');
      saltati++;
      continue;
    }
    try {
      const imageId = await caricaImmagine(cfg.apiKey, d.file, d.nomeFile);
      await attendi(PAUSA_MS);
      const prodotto = await chiamaPrintify(cfg.apiKey, 'POST', '/shops/' + cfg.shopId + '/products.json',
        corpoProdotto(cfg, d.motivo, imageId, args.prezzo));
      console.log('  + ' + titolo + '  -> printify_product_id = ' + prodotto.id);
      creati.push(prodotto.id);
    } catch (err) {
      // Una riga che fallisce non deve fermare le altre diciotto: stesso
      // isolamento degli errori usato dal sync ordini.
      console.error('  ! ' + titolo + ' NON creato: ' + err.message);
    }
    await attendi(PAUSA_MS);
  }

  console.log('\n' + creati.length + ' bozze create, ' + saltati + ' saltate perche\' gia\' esistenti.');
  if (creati.length) {
    console.log('\nPer pubblicarle su Shopify, dopo averle guardate su Printify:');
    console.log('  node scripts/perla-publish-drafts.js ' + creati.join(' '));
  }
  console.log('\nLa base "Tappetino Crea il Tuo Design" non si crea da qui:');
  console.log('  node scripts/perla-create-neutral-products.js');
  return 0;
}

main().then(function (codice) { process.exit(codice || 0); })
  .catch(function (err) { console.error('\nErrore:', err.message); process.exit(1); });
