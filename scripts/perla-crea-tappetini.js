#!/usr/bin/env node
'use strict';

/**
 * perla-crea-tappetini.js
 *
 * Crea su Printify i tappetini da pappa, in BOZZA. Non tocca nessun prodotto
 * esistente.
 *
 * PERCHE' UNO SCRIPT A PARTE
 * create-draft-designs.js ha i design scritti a mano dentro main(): va bene
 * per due o tre, non per una collezione. Qui le definizioni si costruiscono
 * dai file gia' prodotti da perla-tappetini-motivi.py, quindi aggiungere un
 * motivo domani significa rigenerare i file, non modificare questo file.
 *
 * ROUND 59 -- TRE COSE CAMBIATE, E NESSUNA E' UN DETTAGLIO
 *
 * 1. IL FORNITORE. Era 855/70 (Printed Mint), scelto sulla carta e mai usato:
 *    verso l'Italia costa 20,39 di spedizione, cioe' fuori da qualunque
 *    margine. E' 623/10 (MWW On Demand), dove l'Italia sta nella fascia
 *    europea a 7,79 dollari, la piu' bassa di tutto il catalogo Printify.
 *
 * 2. TRE VARIANTI, NON UNA. E due aree di stampa diverse:
 *      73844 osso   19x14 pollici   3150x2400   1,31
 *      73845 osso   30x18 pollici   4800x3000   1,60
 *      73846 pesce  19x14 pollici   3150x2400   1,31
 *    Il formato grande NON e' il piccolo ingrandito: cambia il rapporto.
 *    Mandare un file solo e lasciare che il fornitore lo adatti vuol dire
 *    stamparlo schiacciato su una delle due misure. Printify accetta piu'
 *    voci in print_areas, ognuna coi suoi variant_ids: un gruppo per misura,
 *    e ogni gruppo riceve il file fatto per lui.
 *
 * 3. DUE MERCATI. Il tappetino e' l'unico tipo con lo STESSO fornitore in
 *    Europa e in America, ma resta una scheda per mercato: i prezzi sono in
 *    due valute e i tempi sono diversi (10-30 giorni verso l'Italia contro
 *    2-5 verso gli Stati Uniti, misurati sul catalogo del fornitore). La
 *    scheda europea porta il tag 'tappetino-eu', che e' anche cio' che il
 *    filtro geografico del tema guarda.
 *
 * IL TAG CHE NON SI PUO' SBAGLIARE
 * Ogni prodotto esce con 'tappetino' o 'tappetino-eu'. Il tema li pretende:
 * la riga "tappetino|tipo-tappetino,mat,tappetino,tappetino-eu|1.31|..." in
 * snippets/perla-print-areas.liquid accetta solo questi alias. Senza uno di
 * essi il canvas dello studio usa il rapporto predefinito e "Salva anteprima"
 * manda product_type vuoto, che il server rifiuta con "Tipo prodotto non
 * riconosciuto" -- e' il difetto ROUND 16e gia' documentato nel tema, che era
 * costato l'anteprima su cinque tipi prodotto su sei.
 *
 * PRIMA DI LANCIARLO
 *   python3 scripts/perla-tappetini-motivi.py
 * che scrive generated-designs/tappetini/tappetino-{piccolo,grande}-<motivo>.jpg
 *
 * LA BASE NEUTRA NON SI CREA QUI
 * "Tappetino Crea il Tuo Design" e' gia' previsto da
 * perla-create-neutral-products.js: usare quello, cosi' la base neutra resta
 * identica a quella degli altri tipi.
 *
 * Uso:
 *   node scripts/perla-crea-tappetini.js --prova            # non chiama l'API
 *   node scripts/perla-crea-tappetini.js --mercato eu
 *   node scripts/perla-crea-tappetini.js --mercato usa
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const FILE_STAMPA = path.join(ROOT, 'generated-designs', 'tappetini');
const CONFIG_PATH = path.join(ROOT, 'config', 'printify.local.env');

// Le tre varianti del blueprint 623/10, raggruppate per AREA DI STAMPA. Il
// gruppo, non la variante, e' l'unita' che conta: un file per area.
const GRUPPI = [
  { misura: 'piccolo', variantIds: [73844, 73846], area: '3150x2400' },
  { misura: 'grande',  variantIds: [73845],        area: '4800x3000' },
];

// I due mercati. I prezzi sono quelli decisi dalla titolare, e i margini con
// cui tornano stanno in scripts/perla-verifica-margini.py: 25,9% e 25,1% in
// Europa con l'IVA al 22% pagata davvero, 26,7% e 26,0% negli Stati Uniti.
const MERCATI = {
  eu: {
    tag: 'tappetino-eu',
    prezzi: { 73844: 3490, 73846: 3490, 73845: 4990 },
    consegna: 'Consegna in 2-4 settimane: il fornitore stampa e spedisce, e verso l\'Italia i tempi sono questi. Preferiamo scriverlo.',
  },
  usa: {
    tag: 'tappetino',
    prezzi: { 73844: 3290, 73846: 3290, 73845: 4990 },
    consegna: 'Consegna in 1-2 settimane.',
  },
};

// Printify fa fatica con raffiche di richieste: gli altri script del
// repository non ne mandano mai piu' di una alla volta, e neanche questo.
const PAUSA_MS = 900;

// Printify rifiuta limit oltre 50 ("The limit may not be greater than 50"):
// era 100 e passava, adesso no.
const PER_PAGINA = 50;

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
    blueprintId: Number(campo('TAPPETINO_BLUEPRINT_ID', '623')),
    providerId: Number(campo('TAPPETINO_PROVIDER_ID', '10')),
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

// I file veri sulla cartella, non un manifesto: perla-tappetini-motivi.py
// scrive DUE file per motivo, uno per area di stampa, e li nomina in modo
// prevedibile. Un motivo con un solo file non si carica: meta' tappetino
// stampato bene e meta' adattato dal fornitore e' peggio di niente.
function fileDaCaricare() {
  if (!fs.existsSync(FILE_STAMPA)) {
    throw new Error(
      'Cartella non trovata: ' + FILE_STAMPA + '\n' +
      'Genera prima i file:  python3 scripts/perla-tappetini-motivi.py'
    );
  }
  const perMotivo = {};
  fs.readdirSync(FILE_STAMPA).forEach(function (f) {
    const m = /^tappetino-(piccolo|grande)-(.+)\.jpg$/.exec(f);
    if (!m) return;
    perMotivo[m[2]] = perMotivo[m[2]] || {};
    perMotivo[m[2]][m[1]] = { file: path.join(FILE_STAMPA, f), nomeFile: f };
  });

  const elenco = [];
  Object.keys(perMotivo).sort().forEach(function (chiave) {
    const coppia = perMotivo[chiave];
    const mancanti = GRUPPI.filter(function (g) { return !coppia[g.misura]; })
      .map(function (g) { return g.misura; });
    if (mancanti.length) {
      console.warn('  (saltato "' + chiave + '": manca il file ' + mancanti.join(' e '));
      return;
    }
    elenco.push({ chiave: chiave, titolo: titoloDaChiave(chiave), file: coppia });
  });
  return elenco;
}

// 'ramo-dulivo' -> 'Ramo d\'Ulivo'. La tabella e' corta di proposito: solo i
// nomi in cui la ricostruzione meccanica sbaglierebbe.
const NOMI = {
  // La chiave e' il nome del file, dove l'apostrofo e' diventato un trattino
  // come ogni altro segno non alfanumerico: "Ramo d'Ulivo" -> ramo-d-ulivo.
  'ramo-d-ulivo': "Ramo d'Ulivo",
};

function titoloDaChiave(chiave) {
  if (NOMI[chiave]) return NOMI[chiave];
  return chiave.split('-').map(function (p) {
    return p.charAt(0).toUpperCase() + p.slice(1);
  }).join(' ');
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
  // La chiave e' titolo + tag di mercato, non il titolo da solo: il tappetino
  // e' venduto in due schede con lo STESSO titolo, e il tag e' l'unica cosa
  // che le distingue. Con la sola chiave del titolo, lanciare --mercato usa
  // dopo --mercato eu non avrebbe creato niente.
  const chiavi = new Set();
  let pagina = 1;
  for (;;) {
    const res = await chiamaPrintify(apiKey, 'GET', '/shops/' + shopId + '/products.json?page=' + pagina + '&limit=' + PER_PAGINA);
    const elenco = (res && res.data) || [];
    elenco.forEach(function (p) {
      const titolo = (p.title || '').trim();
      (p.tags || []).forEach(function (t) { chiavi.add(titolo + '|' + t); });
    });
    // Il campo `total` della risposta resta indietro dopo una cancellazione:
    // si contano le pagine, non ci si fida del totale.
    if (elenco.length < PER_PAGINA) break;
    pagina++;
    await attendi(PAUSA_MS);
  }
  return chiavi;
}

function corpoProdotto(cfg, voce, immagini, mercato) {
  const m = MERCATI[mercato];
  const varianti = [];
  const aree = [];
  GRUPPI.forEach(function (g) {
    g.variantIds.forEach(function (id) {
      varianti.push({ id: id, price: m.prezzi[id], is_enabled: true });
    });
    aree.push({
      variant_ids: g.variantIds,
      placeholders: [{
        position: 'front',
        // Il file e' gia' del rapporto esatto della SUA area (1,31 o 1,60,
        // vedi perla-scala-stampa.py): centrato a scala 1.0 la riempie tutta,
        // senza bordi bianchi e senza deformare. E' per questo che ce ne sono
        // due e non uno.
        images: [{ id: immagini[g.misura], x: 0.5, y: 0.5, scale: 1.0, angle: 0 }],
      }],
    });
  });

  return {
    title: 'Tappetino "' + voce.titolo + '"',
    description:
      'Il motivo ' + voce.titolo + ' sul tappetino da pappa, in tinta con la bandana e con il ' +
      'resto della collezione: e\' lo stesso disegno, alla stessa scala.\n\n' +
      'Due forme e due misure: osso 48x36 cm, osso grande 76x46 cm, pesce 48x36 cm. ' +
      'Superficie morbida e base che resta ferma, per tenere in ordine la zona dei pasti.\n\n' +
      'Disegnato in Italia. Stampato dopo l\'ordine, quindi non ci sono rimanenze.\n\n' +
      'Lavabile. Spedizione tracciata. ' + m.consegna,
    blueprint_id: cfg.blueprintId,
    print_provider_id: cfg.providerId,
    variants: varianti,
    print_areas: aree,
    // Il tag del mercato e' obbligatorio, vedi il commento in testa al file.
    // Niente 'personalizzabile': questi hanno un disegno gia' fatto, e quel
    // tag accende l'editor. La base neutra e' un altro prodotto.
    tags: ['perla-italy', 'pet', m.tag, 'tipo-tappetino'],
  };
}

function argomenti() {
  const a = process.argv.slice(2);
  const out = { prova: false, mercato: null };
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--prova' || a[i] === '-n') out.prova = true;
    else if (a[i] === '--mercato') out.mercato = String(a[++i] || '').toLowerCase();
    else if (a[i] === '--help' || a[i] === '-h') {
      console.log(`
Crea su Printify i tappetini a motivo, in bozza.

  --mercato eu|usa   obbligatorio: decide tag, prezzi e tempi di consegna
  --prova, -n        mostra cosa farebbe senza chiamare l'API

Prima serve:  python3 scripts/perla-tappetini-motivi.py
`);
      process.exit(0);
    }
  }
  // Il mercato non ha un predefinito di proposito: sbagliarlo vuol dire
  // pubblicare la scheda europea coi prezzi americani, o peggio col tag
  // sbagliato, e allora il filtro geografico la mostra a chi non deve.
  if (!out.mercato || !MERCATI[out.mercato]) {
    throw new Error('--mercato vuole eu oppure usa (nessun predefinito, e' +
      ' apposta: vedi il commento).');
  }
  return out;
}

async function main() {
  const args = argomenti();
  const daFare = fileDaCaricare();
  const m = MERCATI[args.mercato];

  if (!daFare.length) {
    console.error('Nessun file tappetino-*.jpg in ' + path.relative(ROOT, FILE_STAMPA) + '.');
    console.error('Genera prima i file di stampa:');
    console.error('  python3 scripts/perla-tappetini-motivi.py');
    return 1;
  }

  console.log('\n=== Tappetini a motivo, mercato ' + args.mercato +
    ', ' + daFare.length + ' motivi ===\n');

  if (args.prova) {
    const cfgProva = fs.existsSync(CONFIG_PATH) ? leggiConfig() : null;
    daFare.forEach(function (d) {
      const misure = GRUPPI.map(function (g) {
        return g.misura + ' ' + Math.round(fs.statSync(d.file[g.misura].file).size / 1024) + ' KB';
      }).join(', ');
      console.log('  Tappetino "' + d.titolo + '"  <- ' + misure);
    });
    console.log('\n  prezzi: ' + GRUPPI.map(function (g) {
      return g.misura + ' ' + (m.prezzi[g.variantIds[0]] / 100).toFixed(2);
    }).join(', '));
    console.log('  tag: ' + m.tag);
    if (cfgProva) {
      console.log('  blueprint ' + cfgProva.blueprintId + ', provider ' + cfgProva.providerId);
    }
    console.log('\n  Prova: nessuna chiamata all\'API. Togli --prova per creare davvero.');
    return 0;
  }

  const cfg = leggiConfig();
  console.log('  Negozio Printify ' + cfg.shopId + ', blueprint ' + cfg.blueprintId +
    ', provider ' + cfg.providerId + '\n');

  console.log('  Leggo i prodotti gia\' esistenti, per non crearne di doppi...');
  const esistenti = await titoliEsistenti(cfg.apiKey, cfg.shopId);
  console.log('  ' + esistenti.size + ' prodotti gia\' nel negozio.\n');

  const creati = [];
  let saltati = 0;
  for (const d of daFare) {
    // Il titolo e' lo stesso sui due mercati, com'e' gia' per bandane e
    // ciotole: a distinguerli e' il tag, e nessun cliente ne vede due.
    // Quindi il controllo dei doppi guarda titolo E tag.
    const titolo = 'Tappetino "' + d.titolo + '"';
    const chiaveDoppio = titolo + '|' + m.tag;
    if (esistenti.has(chiaveDoppio)) {
      console.log('  = ' + titolo + ' (' + m.tag + ') esiste gia\', saltato');
      saltati++;
      continue;
    }
    try {
      const immagini = {};
      for (const g of GRUPPI) {
        immagini[g.misura] = await caricaImmagine(
          cfg.apiKey, d.file[g.misura].file, d.file[g.misura].nomeFile);
        await attendi(PAUSA_MS);
      }
      const prodotto = await chiamaPrintify(cfg.apiKey, 'POST',
        '/shops/' + cfg.shopId + '/products.json',
        corpoProdotto(cfg, d, immagini, args.mercato));
      console.log('  + ' + titolo + '  -> printify_product_id = ' + prodotto.id);
      creati.push(prodotto.id);
    } catch (err) {
      // Una riga che fallisce non deve fermare le altre: stesso isolamento
      // degli errori usato dal sync ordini.
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
