# Configurare Analytics e Clarity — Guida Completa

Il tema Perla supporta tre strumenti di misurazione: **Microsoft Clarity**, **Google Analytics 4** e **Meta Pixel**. Tutti richiedono il consenso del cliente ai cookie di analisi prima di partire (GDPR compliant).

## Sommario

1. [Microsoft Clarity](#microsoft-clarity-mappe-di-calore--riproduzione-sessioni)
2. [Google Analytics 4](#google-analytics-4-tracciamento-visite--ecommerce)
3. [Meta Pixel](#meta-pixel-tracciamento-facebook--instagram)
4. [Verifica e Test](#verifica-e-test)
5. [Domande Frequenti](#domande-frequenti)

---

## Microsoft Clarity — Mappe di Calore + Riproduzione Sessioni

Clarity registra il comportamento dei visitatori: dove cliccano, come scorrono, quanto tempo passano su ogni elemento. Perfetto per capire i punti deboli del negozio.

### Passaggio 1: Creare un Progetto Clarity

1. Vai su [**clarity.microsoft.com**](https://clarity.microsoft.com)
2. Accedi con un account Microsoft (crea uno se non l'hai)
3. Clicca **"Add a new project"**
4. Incolla l'URL del tuo negozio (es. `https://perlagrandezampa.com`)
5. Clicca **"Create"**
6. Aspetta che Clarity crei il progetto

### Passaggio 2: Copiare l'ID Progetto

1. Vai in **Settings > Overview**
2. Guarda il campo **"Project ID"** — è un numero lungo
3. Copia l'ID intero (es. `r4u5v8w2k9j3`)

### Passaggio 3: Incollare l'ID nel Tema

1. Vai in Shopify admin: **Negozio online > Personalizzazione**
2. Clicca il tema Perla (se non lo vedi, clicca **"Sfoglia"** e selezionalo)
3. Clicca il bottone **"Personalizza tema"**
4. Nel menu a sinistra, scorri fino a **"Marketing & Analytics"**
5. Incolla l'ID nel campo **"Microsoft Clarity — ID progetto"**
6. Clicca **"Salva"**

✅ Fatto! Clarity partirà non appena un cliente accetterà i cookie di analisi.

---

## Google Analytics 4 — Tracciamento Visite + Ecommerce

Google Analytics 4 misura:
- Visite, visualizzazioni di pagina, tempo di permanenza
- Visualizzazioni prodotto, aggiunte al carrello, acquisti
- Fonte del traffico (organico, pubblicitario, etc.)

### Scelta: Tema vs. Pixel

Scegli **uno solo** di questi metodi:

| Metodo | Pro | Contro |
|--------|-----|--------|
| **Pixel (consigliato)** | Traccia anche il checkout | Richiede un passaggio manuale in Shopify |
| **ID nel tema** | Automatico, niente da fare | Non traccia il checkout |

#### Opzione A: Pixel (Consigliato)

##### A1: Creare una Proprietà GA4

1. Vai su [**analytics.google.com**](https://analytics.google.com)
2. Clicca **"Crea account"** (oppure accedi se ne hai uno)
3. Nome account: `Perla` (o quello che vuoi)
4. Clicca **"Avanti"**
5. Nome proprietà: `Perla Shop`
6. Timezone: `Italy (Ora dell'Europa centrale)`
7. Valuta: `EUR`
8. Clicca **"Crea"**
9. Seleziona il tuo settore: `Retail / E-commerce`
10. Clicca **"Crea"**

##### A2: Ottenere l'ID Misurazione

1. In Google Analytics, vai in **Amministrazione** (in basso a sinistra)
2. Nella colonna **Proprietà**, clicca **"Flussi di dati"**
3. Clicca il flusso che hai appena creato (es. "Perla Shop")
4. Guarda in alto a destra: troverai **"ID misurazione"** (es. `G-XXXXXXXXXX`)
5. **Copia questo ID**

##### A3: Creare il Pixel Personalizzato in Shopify

1. Vai in Shopify admin: **Impostazioni > Eventi cliente**
2. Clicca **"Aggiungi pixel personalizzato"**
3. Nome: `GA4`
4. Apri il file `docs/analytics-pixel-ga4.js` del tema
5. Sostituisci `'G-XXXXXXXXXX'` con il tuo ID misurazione (conserva le virgolette)
6. Copia **tutto il contenuto modificato**
7. Torna in Shopify e incolla il codice nel campo **"Codice"**
8. Clicca **"Salva"**
9. Clicca **"Connetti"** quando viene offerto

✅ Fatto! GA4 traccia adesso visite, prodotti, carrello e acquisti (incluso checkout).

#### Opzione B: ID nel Tema (Solo Tracciamento Visite)

Se non vuoi usare il pixel:

1. Segui i passaggi **A1 e A2** sopra per ottenere l'ID misurazione
2. Vai in Shopify admin: **Negozio online > Personalizzazione**
3. Clicca il tema Perla > **"Personalizza tema"**
4. Menu a sinistra: **"Marketing & Analytics"**
5. Incolla l'ID nel campo **"Google Analytics 4 — Measurement ID"**
6. Clicca **"Salva"**

⚠️ **Nota**: Con questo metodo, il checkout non viene tracciato (vedi qui perché nella sezione **Domande Frequenti**).

---

## Meta Pixel — Tracciamento Facebook + Instagram

Il Meta Pixel traccia i visitatori del tuo negozio per fargli pubblicità mirata su Facebook e Instagram, e misura le conversioni delle tue campagne.

### Passaggio 1: Creare un Pixel in Meta Business Suite

1. Vai su [**business.facebook.com**](https://business.facebook.com)
2. Accedi con l'account Meta / Facebook aziendale (creane uno se non l'hai)
3. Nel menu a sinistra, vai a **"Strumenti > Gestione evento"**
4. Clicca **"Crea"** (in alto a destra)
5. Seleziona **"Pixel da sito web"**
6. Dai un nome: `Perla Shop`
7. Clicca **"Crea"**
8. Completa la domanda sulla posizione (scegli il tuo negozio, se lo trovi) oppure salta
9. Clicca **"Continua"**

### Passaggio 2: Copiare l'ID Pixel

1. Vai in **"Strumenti > Gestione evento"**
2. Clicca sul pixel che hai appena creato
3. Vai in **"Impostazioni"** (in basso a sinistra)
4. Guarda il campo **"ID Pixel"** — è un numero lungo (es. `987654321098765`)
5. **Copia questo ID**

### Passaggio 3: Incollare l'ID nel Tema

1. Vai in Shopify admin: **Negozio online > Personalizzazione**
2. Clicca il tema Perla > **"Personalizza tema"**
3. Menu a sinistra: **"Marketing & Analytics"**
4. Incolla l'ID nel campo **"Meta Pixel ID"**
5. Clicca **"Salva"**

✅ Fatto! Meta Pixel traccia ora visite e eventi dal tuo negozio.

### Passaggio 4 (Facoltativo): Testare il Pixel

1. Torna in Meta Business Suite > **"Strumenti > Gestione evento"**
2. Clicca il tuo pixel
3. Clicca **"Test Events"** (in basso a sinistra)
4. Incolla l'URL del tuo negozio nel campo **"URL del sito web"**
5. Clicca **"Test"**
6. **Se vedi "Connected"** in verde: il pixel funziona ✅

---

## Verifica e Test

### Verificare che Tutto Funziona

1. Apri il negozio in una **finestra in incognito** (per resettare i cookie)
2. Accetta i cookie di analisi quando ti viene chiesto
3. Apri gli strumenti di sviluppo del browser (**F12** o **Cmd+Opt+I**)
4. Vai alla scheda **Console**

Dovresti vedere **senza errori in rosso**:

```
✅ Clarity caricato
✅ GA4 caricato (se configurato)
✅ Meta Pixel caricato (se configurato)
```

### Verificare in Clarity

1. Vai in **clarity.microsoft.com**
2. Apri il tuo progetto
3. Clicca **"Dashboard"**
4. Dovresti vedere visite in tempo reale

### Verificare in Google Analytics

1. Vai in **analytics.google.com**
2. Apri la tua proprietà
3. Vai in **Tempo reale > Panoramica**
4. Fai un'azione nel negozio: dovresti vedere **1 utente attivo**

### Verificare in Meta Pixel

1. Vai in Meta Business Suite > **"Strumenti > Gestione evento"**
2. Clicca il tuo pixel
3. Clicca **"Test Events"**
4. Dovresti vedere **"Connected"** in verde

---

## Domande Frequenti

### D: Perché il checkout non appare in Google Analytics con il metodo "ID nel tema"?

**R:** L'ID nel tema funziona solo sul negozio (il tema Perla), non sul checkout. Shopify espone il checkout su un dominio diverso, che il tema non controlla. Per tracciare il checkout, serve il **pixel personalizzato** (Opzione A, Passaggio A3).

### D: Uso GA4 dal tema E il pixel? Non è doppio?

**R:** Sì, diventerebbero doppie le visite. **Scegli uno solo:**
- **Pixel** (consigliato): Shopify carica il pixel sul negozio + checkout
- **ID nel tema**: Manuale, solo negozio, niente checkout

Se usi il pixel, **LASCIA VUOTO** il campo "Google Analytics 4 — Measurement ID" del tema.

### D: Clarity non registra niente. Che faccio?

**R:** Verifica:
1. L'ID del progetto è corretto (copiato da clarity.microsoft.com > Settings > Overview)
2. Il cliente ha accettato i cookie di analisi (il banner in basso della pagina)
3. Usa una finestra in incognito per resettare i cookie e testare di nuovo

Se il problema persiste, controlla la **Console del browser** (F12) per errori rossi.

### D: Posso usare Clarity, GA4 e Meta Pixel tutti insieme?

**R:** Sì, non ci sono conflitti. Configura i tre ID nei campi corrispondenti e tutti e tre partiranno (dopo il consenso ai cookie).

### D: Il tema carica qualcos'altro senza che lo chieda?

**R:** No. Se un campo è vuoto, lo script non viene caricato. Zero richieste, zero cookie, zero errori. Solo consenso → avvio.

### D: Dove posso modificare le impostazioni dopo?

**R:** Sempre in Shopify: **Negozio online > Personalizzazione > Tema Perla > Personalizza > Marketing & Analytics**. Cambi un ID, salvi, e il tema la prossima visita carica il nuovo script.

---

## Recap: Checklist di Configurazione

- [ ] Microsoft Clarity
  - [ ] Crea progetto su clarity.microsoft.com
  - [ ] Copia l'ID del progetto
  - [ ] Incolla in Shopify > Marketing & Analytics
  
- [ ] Google Analytics 4
  - [ ] Crea proprietà su analytics.google.com
  - [ ] Copia l'ID misurazione
  - [ ] **Scegli uno:**
    - [ ] Crea pixel personalizzato in Shopify (consigliato)
    - [ ] Oppure incolla ID nel tema
  
- [ ] Meta Pixel
  - [ ] Crea pixel in Meta Business Suite
  - [ ] Copia l'ID Pixel
  - [ ] Incolla in Shopify > Marketing & Analytics
  
- [ ] Test
  - [ ] Visita il negozio in incognito
  - [ ] Accetta i cookie
  - [ ] Verifica in Clarity, GA4, Meta Pixel

---

## Note Tecniche

- **Ubicazione dello snippet**: `theme/snippets/perla-analytics.liquid`
- **Pixel GA4**: `docs/analytics-pixel-ga4.js`
- **File di impostazioni**: `theme/config/settings_schema.json`
- **Dichiarazioni di consenso**: La Customer Privacy API di Shopify gestisce il consenso. Nessun tracker parte prima del consenso.
- **Privacy**: Nessun cookie viene creato finché il cliente non accetta l'analisi.

