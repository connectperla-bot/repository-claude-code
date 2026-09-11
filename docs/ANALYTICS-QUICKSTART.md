# Analytics & Clarity — Quick Start (5 minuti)

## Setup Immediato

### 1️⃣ Microsoft Clarity

1. clarity.microsoft.com → **Add project** → incolla URL negozio
2. Settings > Overview → copia **Project ID**
3. Shopify admin → Personalizza Tema → Marketing & Analytics → incolla in **"Microsoft Clarity — ID progetto"**
4. Salva

### 2️⃣ Google Analytics 4 (Opzione Consigliata: Pixel)

1. analytics.google.com → **Crea proprietà** → nome "Perla Shop" → Timezone Italy → Salva
2. Amministrazione → Flussi dati → clicca il flusso → copia **ID misurazione** (G-...)
3. Shopify admin → Impostazioni → **Eventi cliente**
4. **Aggiungi pixel personalizzato** → Nome: "GA4"
5. Apri `docs/analytics-pixel-ga4.js` → Sostituisci `'G-XXXXXXXXXX'` con il tuo ID
6. Copia tutto il codice → Incolla in Shopify → Salva → Connetti

### 3️⃣ Meta Pixel

1. business.facebook.com → Strumenti → Gestione evento → **Crea** → Pixel da sito web
2. Nome "Perla Shop" → Crea
3. Impostazioni → copia **ID Pixel**
4. Shopify admin → Personalizza Tema → Marketing & Analytics → incolla in **"Meta Pixel ID"**
5. Salva

## ✅ Verifica (Finestra Incognito)

1. Apri negozio in **incognito** (Ctrl+Shift+N / Cmd+Shift+N)
2. Accetta i cookie
3. F12 (Console) — niente errori rossi? ✅
4. clarity.microsoft.com → Dashboard → vedi visite?
5. analytics.google.com → Tempo reale → vedi "1 utente"?
6. Meta Business Suite → Test Events → "Connected"?

## 🚨 GA4: Pixel OR Tema, non Entrambi

- ✅ Se usi il **pixel** → lascia vuoto il campo "Measurement ID" del tema
- ✅ Se usi solo il **tema** → GA4 traccia solo il negozio (non il checkout)
- ❌ Se riempi ENTRAMBI → conti doppi, sessioni sbagliate

## 📞 Problemi?

| Problema | Soluzione |
|----------|-----------|
| Clarity non carica | Verifica l'ID, accetta cookie, incognito |
| GA4 non vede acquisiti | Usa il pixel, non l'ID nel tema |
| Meta Pixel dice "not connected" | Verifica l'ID, test dopo 10 min |
| Errori in console | Controlla che gli ID non abbiano spazi/caratteri extra |

---

Guida completa: [`docs/SETUP-ANALYTICS-CLARITY.md`](./SETUP-ANALYTICS-CLARITY.md)
