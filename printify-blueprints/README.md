# Printify Blueprints & Templates

Questa cartella contiene i dati scaricati via API ufficiale Printify (`/v1/catalog/...`).

## Come aggiornare / ottenere nuovi dati

```bash
# Elenca tutti i blueprint
node scripts/fetch-printify-blueprint.js --list

# Cerca
node scripts/fetch-printify-blueprint.js --search "pet bed"

# Scarica dettagli + dimensioni esatte area di stampa per un prodotto
node scripts/fetch-printify-blueprint.js --blueprint 784 --provider 93 --save

# Con mockup di riferimento
node scripts/fetch-printify-blueprint.js -b 562 -p 70 --save --download-mockups
```

I file `<blueprint>_<provider>.json` contengono:
- `blueprint` metadata (title, description, mockup images)
- `providers`
- `variants` con `placeholders[].width` e `.height` → **dimensioni esatte pixel dell'area di stampa**

## Dimensioni attuali note (2026-07)

| Prodotto     | Blueprint | Provider | Variante tipica | Area stampa (px)     | Note |
|--------------|-----------|----------|-----------------|----------------------|------|
| Collar (S)   | 784       | 93       | 74897           | **5764 × 229**       | Striscia lunghissima ~25:1 |
| Collar (M)   | 784       | 93       | -               | **7257 × 338**       | - |
| Bandana      | 562       | 70       | 101403          | **3150 × 1691**      | ~1.86:1 |
| Bandana L    | 562       | 70       | 101404          | 4275 × 2325          | - |
| Pet Tag      | 566       | 70       | 70870           | **810 × 900**        | Quasi quadrato |
| Pet Bed      | 419       | 10       | 61436 (28x18")  | **8850 × 5850**      | Molto alta risoluzione |

## Template PNG con area trasparente

L'API **non** restituisce direttamente il PNG "print file template".

**Metodo ufficiale:**
1. Vai su https://printify.com/app/catalog
2. Apri il prodotto
3. Seleziona la variante
4. Nel Product Creator → sezione Upload → "Download print file template"

Questo PNG ha:
- Dimensioni esatte uguali ai placeholder.width/height
- Area stampabile con sfondo trasparente (o con guide)
- Spesso anche un layer di mockup base

## Uso con Flux (Fal.ai)

Vedi `scripts/generate-flux-design.js`

Esempio:
```bash
node scripts/generate-flux-design.js \
  --product bandana \
  --width 3150 --height 1691 \
  --prompt "motivo elegante con rose e monogramma per bandana di lusso per cani" \
  --model flux-pro
```

Lo script:
1. Arricchisce automaticamente il prompt con le specs tecniche Printify (dye-sublimation ready, dimensioni esatte, tips prodotto)
2. Chiama Fal.ai
3. Salva in `generated-designs/`

Poi usa gli script esistenti (`perla-upload-endpoint.js` ecc.) per caricare su Printify.

## Prossimi passi dopo generazione

- Verifica/riscala l'immagine **esattamente** alle dimensioni del placeholder
- Carica l'immagine come "design file" (non come mockup)
- Quando crei il prodotto Printify, usa la struttura `print_areas` con i placeholder corretti e le coordinate x/y/scale normalizzate (0-1)

## Note

- Provider detail (`/print_providers/{id}.json`) spesso 404 → usa direttamente `/.../variants.json` (contiene i placeholders con dimensioni).
- Alcune blueprint possono cambiare ID nel tempo. Riscarica sempre quando crei nuovi prodotti.
