'use strict';

// LA PROVA CHE MANCAVA: una riga personalizzata entra nel carrello E CI RESTA.
//
// LA DOMANDA
// "verifica che quando un cliente aggiunge un prodotto avendolo personalizzato
// al carrello questo rimanga e non scompaia."
//
// PERCHE' NON BASTAVANO LE PROVE CHE C'ERANO
// tests/guardia-carrello.test.js copre benissimo il momento del CLIC: finge il
// DOM e verifica trenta casi. Ma si ferma un istante prima di /cart/add.
// E tests/perla-come-si-ordina.py credeva di provarlo: al passo 7 cercava
// "[data-add-to-cart]", "button[name='add']", ".product__add" -- nessuno dei
// tre esiste nel markup, che usa [data-add-btn] / .product__atc. Quel passo non
// ha mai cliccato niente: l'aggiunta al carrello non era mai stata provata da
// nessuno, ne' qui ne' altrove.
//
// PERCHE' NON C'E' UN BROWSER
// Ci ho provato: Playwright con il Chromium del contenitore non esce su
// internet da qui. L'uscita passa dal proxy della sessione, che ri-termina la
// TLS, e il tunnel muore a meta' scambio -- non solo verso il negozio, anche
// verso example.com. E' un limite del contenitore, non del negozio.
//
// Quindi si fa la stessa cosa un piano piu' sotto: si parla con il negozio con
// le STESSE chiamate che fa il browser (POST /cart/add.js, GET /cart.js),
// tenendo i cookie come li terrebbe lui. E la personalizzazione non e'
// inventata: si manda un file di stampa vero al servizio che compone, e si
// mette in carrello la risposta che darebbe lo studio.
//
// COSA PROVA, E COSA NO
//   prova   che Shopify tiene la riga e le proprieta' nascoste (_Personalizzazione)
//           dopo l'aggiunta, dopo una rilettura, e che due personalizzazioni
//           diverse restano due righe invece di fondersi;
//   prova   che una riga con personalizzazione VUOTA -- il caso in cui il
//           servizio fallisce -- si fonde con un'altra vuota, cioe' una riga
//           sparisce davvero. E' l'unico modo in cui il carrello perde una
//           riga, ed e' esattamente cio' che la guardia in
//           assets/perla-guardia-carrello.js esiste per impedire;
//   NON prova  il pezzo dentro assets/global.js (il cassetto del carrello, il
//           cambio quantita'): quel file e' minificato, fuori dal repository, e
//           da qui non e' raggiungibile ne' leggibile.
//
// NESSUN ORDINE VIENE COMPLETATO: ci si ferma al carrello.
//
// PERCHE' NON E' IN `npm test`
// Chiama il negozio vero e il servizio di composizione, che sta su un piano
// gratuito e si addormenta (12,6 s misurati a freddo). Una prova che dipende
// dalla rete non puo' stare in una suite che deve girare in pochi secondi.
//
//     node tests/carrello-dal-vivo.test.js
//     node tests/carrello-dal-vivo.test.js --prodotto collare-damasco

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const NEGOZIO = 'https://perlaitaly.com';
const COMPONI = 'https://perla-upload-endpoint-yizy.onrender.com/upload';
const RADICE = path.join(__dirname, '..');

function argomento(nome, predefinito) {
  const i = process.argv.indexOf('--' + nome);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : predefinito;
}

const esiti = [];
function verifica(titolo, condizione, dettaglio) {
  esiti.push({ titolo, ok: !!condizione });
  console.log('  %s %s%s', condizione ? 'ok  ' : 'NO  ', titolo,
    dettaglio ? '  (' + dettaglio + ')' : '');
}

// Un barattolo di cookie per tutta la prova: senza, ogni chiamata sarebbe un
// carrello diverso -- cioe' sempre vuoto, cioe' un falso allarme.
const BARATTOLO = '/tmp/perla-carrello-cookie.txt';

function curl(args) {
  return execFileSync('curl', ['-sS', '-m', '90', '-b', BARATTOLO, '-c', BARATTOLO,
    '-H', 'Accept: application/json', ...args], { encoding: 'utf8', maxBuffer: 32e6 });
}

function carrello() {
  return JSON.parse(curl([NEGOZIO + '/cart.js']));
}

function aggiungi(varianteId, proprieta) {
  const corpo = { id: Number(varianteId), quantity: 1, properties: proprieta };
  return JSON.parse(curl(['-X', 'POST', NEGOZIO + '/cart/add.js',
    '-H', 'Content-Type: application/json', '-d', JSON.stringify(corpo)]));
}

// Il composito vero: si manda un file di stampa al servizio che lo ospita, e si
// riceve {id, url}. E' esattamente cio' che lo studio mette nel campo nascosto.
function componiDavvero(file) {
  const r = JSON.parse(execFileSync('curl', ['-sS', '-m', '300', '-X', 'POST',
    COMPONI, '-F', 'photo=@' + file], { encoding: 'utf8', maxBuffer: 32e6 }));
  if (!r.id) throw new Error('il servizio non ha restituito un id: ' + JSON.stringify(r).slice(0, 120));
  return r;
}

function main() {
  const handle = argomento('prodotto', 'collare-barocco');
  const nome = argomento('nome', 'Rocky');
  try { fs.unlinkSync(BARATTOLO); } catch (e) {}

  console.log('\n=== Carrello dal vivo: %s ===\n', handle);

  const prodotto = JSON.parse(curl([NEGOZIO + '/products/' + handle + '.json'])).product;
  const variante = prodotto.variants[0].id;
  verifica('il prodotto esiste e ha una variante', !!variante, prodotto.title + ' / ' + prodotto.variants[0].title);

  // Un file di stampa vero, gia' sul disco: e' lo stesso che il cliente
  // otterrebbe scrivendo un nome.
  const stampa = path.join(RADICE, 'out-foto-nome',
    'collare-eu-barocco-navy-oro-fornitore-europeo-stampa.jpg');
  verifica('c\'e\' un file di stampa vero da mandare', fs.existsSync(stampa));

  const composito = componiDavvero(stampa);
  verifica('il servizio compone e restituisce un id', !!composito.id, composito.id);

  const datiUno = JSON.stringify({
    printify_image_id: composito.id, preview_url: composito.url,
    product_type: 'collare_eu', x: 0.5, y: 0.5, scale: 1, angle: 0,
  });

  const r1 = aggiungi(variante, {
    'Foto Personalizzata': composito.url,
    '_Personalizzazione': datiUno,
    'Nome inciso': nome,
  });
  verifica('la riga entra nel carrello', !!r1.id || !!r1.key, r1.key || r1.status || '');

  let c = carrello();
  verifica('il carrello riporta una riga', c.item_count === 1, 'item_count = ' + c.item_count);
  const riga = c.items[0];
  const dati = (riga.properties || {})._Personalizzazione || '';
  verifica('_Personalizzazione non e\' vuota', dati.length > 0, dati.length + ' caratteri');
  verifica('porta il printify_image_id', dati.indexOf(composito.id) !== -1);
  verifica('«Nome inciso» riporta il nome', riga.properties['Nome inciso'] === nome);

  // IL PUNTO: si rilegge il carrello, come farebbe una ricarica di pagina.
  const dopo = carrello();
  verifica('rileggendo, la riga c\'e\' ancora', dopo.item_count === 1,
    'item_count = ' + dopo.item_count);
  verifica('rileggendo, _Personalizzazione e\' intatta',
    ((dopo.items[0].properties || {})._Personalizzazione || '') === dati);

  // Una SECONDA personalizzazione, diversa: devono restare due righe. Shopify
  // fonde le righe con la stessa variante SOLO se hanno le stesse proprieta',
  // e due compositi diversi hanno id diversi.
  const compositoDue = componiDavvero(path.join(RADICE, 'out-foto-nome',
    'collare-eu-damasco-bordeaux-oro-fornitore-europeo-stampa.jpg'));
  aggiungi(variante, {
    'Foto Personalizzata': compositoDue.url,
    '_Personalizzazione': JSON.stringify({
      printify_image_id: compositoDue.id, preview_url: compositoDue.url,
      product_type: 'collare_eu', x: 0.5, y: 0.5, scale: 1, angle: 0,
    }),
    'Nome inciso': nome + 'due',
  });
  const due = carrello();
  verifica('due personalizzazioni diverse restano due righe',
    due.items.length === 2 && due.item_count === 2,
    due.items.length + ' righe, ' + due.item_count + ' pezzi');

  // E adesso il caso che fa sparire una riga per davvero: due aggiunte con la
  // personalizzazione VUOTA hanno proprieta' identiche, quindi Shopify le
  // fonde. Il cliente vede una riga da due pezzi invece di due righe.
  const vuote = { 'Foto Personalizzata': '', '_Personalizzazione': '', 'Nome inciso': '' };
  aggiungi(variante, vuote);
  const primaDelDoppione = carrello().items.length;
  aggiungi(variante, vuote);
  const conDoppione = carrello();
  const fuse = conDoppione.items.length === primaDelDoppione;
  verifica('DUE aggiunte VUOTE si fondono in una riga sola (per questo esiste la guardia)',
    fuse, fuse ? 'confermato: righe ' + primaDelDoppione + ' -> ' + conDoppione.items.length
               : 'non si sono fuse, righe ' + conDoppione.items.length);

  // Si lascia il carrello come lo si e' trovato. /cart/clear.js vuole un corpo
  // JSON anche se e' vuoto: senza, Shopify risponde ma non svuota.
  curl(['-X', 'POST', NEGOZIO + '/cart/clear.js',
        '-H', 'Content-Type: application/json', '-d', '{}']);
  const finale = carrello();
  verifica('il carrello di prova viene svuotato', finale.item_count === 0,
    'item_count = ' + finale.item_count);

  const rotte = esiti.filter((e) => !e.ok);
  console.log('\n%d verifiche, %d fallite\n', esiti.length, rotte.length);
  process.exit(rotte.length ? 1 : 0);
}

try { main(); }
catch (e) {
  console.error('\nProva interrotta:', String(e.message).slice(0, 300));
  process.exit(1);
}
