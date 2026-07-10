# Nuovi Design Generati - Collezione Perla Italy (Lusso Pet)

**Data**: 2026-07-10
**Prodotto principale**: Collare (unico collar trovato su Printify: Blueprint 784 / Provider 93 - C4)

**IMPORTANTE**:
- Questi sono **solo file immagine di design**.
- **NON** sono stati creati, modificati o cancellati prodotti su Printify o Shopify.
- Usa questi PNG come base per caricare manualmente su Printify (upload) quando sei pronto.
- Per il collare usa le dimensioni esatte dell'area di stampa.

## Dimensioni Printify di riferimento (dal catalogo)

**Collare (Dog Collar - 784/93)**:
- S (es. 74897 Black Onyx): **5764 × 229 px**
- M: 7257 × 338 px
- Usa sempre la risoluzione esatta o multipli per la migliore qualità.

**Bandana (562/70)**:
- 20"×10": **3150 × 1691 px**

**Medaglietta / Pet Tag (566/70)**:
- **810 × 900 px**

**Cuccia / Pet Bed (419/10)**:
- 28"×18" (61436): **8850 × 5850 px** (usa scaled per generazione)

**Tappetino / Pet Mat** (approssimato, in attesa ID esatto):
- Esempio usato: **2400 × 1600 px** (o 12x18" equivalente ~3600x2400)

## File generati (coordinati in stile luxury Italian)

### Collari (2 design nuovi - stile simile/coordinato)
1. **collar-damask-gold-burgundy.jpg**
   - Target: 5764 × 229 px (S)
   - Stile: Damasco elegante ripetuto + monogramma Perla Italy sottile in foglia oro su sfondo borgogna profondo.
   - Prompt ottimizzato Flux: "elegant repeating damask pattern with subtle Perla Italy monogram in luxurious gold foil on deep burgundy background, sophisticated Italian luxury pet style, continuous seamless design across the entire collar length..."

2. **collar-botanical-olive-gold.jpg**
   - Target: 5764 × 229 px (S)
   - Stile: Motivo botanico delicato (rami di ulivo) in verde salvia, crema e accenti oro, minimal luxury.
   - Prompt ottimizzato Flux: "delicate botanical olive branch and leaves pattern in soft sage green and cream with elegant gold accents, minimalist luxury, seamless long horizontal repeat..."

### Bandana
- **bandana-damask-monogram.jpg**
  - Target: 3150 × 1691 px
  - Stile coordinato: damasco + monogramma oro/borgogna/crema.

### Medaglietta (Tag)
- **medaglietta-tag-luxury.jpg**
  - Target: 810 × 900 px
  - Stile: Monogramma Perla minimal + elemento sottile (zampa o foglia), alto contrasto, leggibile su piccolo metallo.

### Cuccia (Pet Bed)
- **cuccia-bed-damask.jpg**
  - Target: ~8850 × 5850 px (o scaled)
  - Stile full coverage coordinato damasco/botanico luxury.

### Tappetino (Pet Mat)
- **tappetino-mat-luxury.jpg**
  - Target: 2400 × 1600 px (o la dimensione reale del tuo blueprint)
  - Stile: damasco + foglie, palette oro/borgogna, aspetto premium e durevole.

## Come usarli (prossimi passi - senza toccare prodotti esistenti)

1. Verifica/riscala le immagini alle dimensioni **esatte** del placeholder Printify per la variante desiderata (usa Photoshop, GIMP, o sharp/ImageMagick).
2. Carica il PNG come immagine di design su Printify:
   - Usa `scripts/perla-upload-endpoint.js` (avvia il server)
   - O POST diretto all'Uploads API.
3. Quando crei il prodotto manualmente nel pannello Printify o via API, usa:
   - blueprint_id: 784 (per collari)
   - print_provider_id: 93
   - La print_area corretta con il placeholder "front" + le coordinate di posizionamento.
4. Non creare nuovi prodotti qui a meno che non ti chieda esplicitamente.

## Prompt completi (pronti per Fal.ai flux-pro quando hai credito)

Vedi anche EXAMPLE-PROMPTS.md e i dry-run eseguiti.

**Per rigenerare con Fal (dopo top-up):**
```powershell
cd ruflo-test
node scripts/generate-flux-design.js --product collar --width 5764 --height 229 `
  --prompt "elegant repeating damask pattern with subtle Perla Italy monogram..." `
  --model flux-pro --name "collar-damask-v2"
```

## Nota su Tappetino
L'ID 855 del config attuale non ha restituito risultati validi. Quando vuoi, dimmi il blueprint ID corretto del tappetino che usi su Printify e riscaricherò le dimensioni esatte.

Tutti i design sono stati generati in stile coerente per creare una collezione coordinata Perla Italy.

Non è stato toccato alcun prodotto esistente.
