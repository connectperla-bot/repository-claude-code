# Esempi di Prompt Eccellenti per Flux (basati su Printify specs)

Usa sempre lo script:
node scripts/generate-flux-design.js --product <name> --prompt "..." [--width W --height H] [--model flux-pro]

Lo script aggiunge automaticamente:
- "high resolution print-ready design for dye-sublimation on fabric..."
- Tips specifici del prodotto
- "designed exactly for a printable area of WxH pixels"
- Per collar: "very wide panoramic composition, long horizontal layout, seamless..."

## Collar (5764×229 per taglia S)

Prompt base:
"motivo damascato elegante con monogramma Perla Italy in oro su sfondo bordeaux profondo, stile luxury italiano, pattern continuo e seamless lungo tutta la fascia del collare, dettagli raffinati, alta leggibilità"

Prompt completo generato:
motivo damascato elegante con monogramma Perla Italy in oro su sfondo bordeaux profondo, stile luxury italiano, pattern continuo e seamless lungo tutta la fascia del collare, dettagli raffinati, alta leggibilità, high resolution print-ready design for dye-sublimation on fabric, crisp sharp lines, vibrant colors, professional pet product quality, no text overflow, excellent contrast, Design must be extremely wide panoramic strip. Use repeating patterns, long text, or continuous artwork that wraps around the collar. High detail on the thin band. Dye-sublimation friendly, vector-like or crisp illustration., designed exactly for a printable area of 5764 by 229 pixels, very wide panoramic composition, long horizontal layout, seamless or continuous pattern across the full width, 8k detail, intricate, best quality, award winning design

## Bandana (3150×1691)

"elegant floral monogram pattern for luxury pet bandana, delicate roses and leaves in soft pink, sage green and cream, sophisticated Italian style, high detail, clean vector art suitable for dye sublimation, seamless tileable where appropriate, premium pet accessory quality"

## Pet Tag (810×900)

"minimalist elegant pet tag design with name 'LUNA' and small paw, luxury gold foil effect on white, very high contrast, simple readable typography, perfect for small metal tag"

## Dopo la generazione

1. Controlla che l'immagine abbia le giuste proporzioni.
2. Se Flux ha generato a risoluzione diversa, usa un editor (o ImageMagick / sharp) per portare esattamente a WxH.
3. Carica su Printify (usa l'upload endpoint del progetto).
4. Nel create product, specifica print_areas con il placeholder "front" e le coordinate di posizionamento (x,y normalizzate, scale).

Per i template trasparenti scaricali manualmente una tantum dal Product Creator di Printify per avere la maschera esatta da usare come reference durante il prompt engineering.
