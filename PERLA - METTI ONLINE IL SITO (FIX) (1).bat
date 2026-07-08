@echo off
setlocal enabledelayedexpansion
title PERLA ITALIA - Metti online il sito (versione corretta)
color 0B

REM ===================================================================
REM  PERLA ITALIA - script di pubblicazione del tema Shopify
REM  Codici di uscita:
REM    0 = completato   1 = Node.js mancante/vecchio   2 = download fallito
REM    3 = estrazione/cartella fallita   4 = Shopify CLI non installabile
REM    5 = push del tema fallito   6 = pubblicazione fallita
REM  Log dettagliato: %USERPROFILE%\Desktop\Perla-Sito-Fix-log.txt
REM ===================================================================

set "SCRIPT_DIR=%~dp0"
set "STORE=perlaitaly-store.myshopify.com"
set "WORK=%USERPROFILE%\Desktop\Perla-Sito-Fix"
set "ZIP=%TEMP%\perla-tema-fix.zip"
set "URL=https://storage.googleapis.com/runable-templates/cli-uploads%%2F13CphC5PsGz2m4Q3rGz2JOazJAyY0R6C%%2FAX0DMc3REbGfbgGwdHzaZ%%2Fperla-shopify-theme-fixed.zip"
set "LOG=%USERPROFILE%\Desktop\Perla-Sito-Fix-log.txt"
set "MIN_NODE_MAJOR=18"

call :log "Avvio script"

echo ===================================================
echo        PERLA ITALIA - Sito online (FIX)
echo ===================================================
echo.
echo Questo file carica la versione CORRETTA del tema:
echo   - homepage collegata ai prodotti veri (niente "Prodotto di esempio")
echo   - categorie collegate alle collezioni reali
echo   - footer con menu Negozio / Assistenza / Legale funzionanti
echo   - rimosso il testo conformita' provvisorio
echo   - possibilita' per il cliente di caricare la propria foto
echo     con anteprima live sul prodotto (dove abilitato)
echo.
echo Non devi estrarre niente. Premi un tasto per iniziare.
echo ---------------------------------------------------
pause >nul

REM --- Forza TLS 1.2 per i download (compatibilita' e sicurezza) ---
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12" >nul 2>>"%LOG%"

echo.
echo [1/5] Controllo Node.js...
where node >nul 2>>"%LOG%"
if errorlevel 1 (
  color 0E
  echo.
  echo  [!] NODE.JS NON E' INSTALLATO.
  echo.
  echo  Devi installarlo una volta sola:
  echo    1. Apri il sito   https://nodejs.org
  echo    2. Scarica il pulsante verde "LTS"
  echo    3. Apri il file e clicca Avanti fino a Fine
  echo    4. Poi riapri questo file con doppio click.
  echo.
  call :log "ERRORE: Node.js non trovato"
  start https://nodejs.org
  pause
  exit /b 1
)

set "NODE_MAJOR=0"
for /f "tokens=1 delims=v" %%a in ('node -v') do set "NODE_FULL=%%a"
for /f "tokens=1 delims=." %%a in ("%NODE_FULL%") do set "NODE_MAJOR=%%a"
if %NODE_MAJOR% LSS %MIN_NODE_MAJOR% (
  color 0E
  echo.
  echo  [!] La versione di Node.js installata e' troppo vecchia.
  echo      Serve Node.js %MIN_NODE_MAJOR% o superiore. Aggiornala da https://nodejs.org
  echo.
  call :log "ERRORE: Node.js troppo vecchio (%NODE_MAJOR%)"
  start https://nodejs.org
  pause
  exit /b 1
)
echo     Node.js trovato (versione %NODE_MAJOR%). OK.
call :log "Node.js OK, versione %NODE_MAJOR%"

echo.
echo [2/5] Scarico il tema corretto...
set "DOWNLOAD_OK=0"
for /l %%i in (1,1,3) do (
  if "!DOWNLOAD_OK!"=="0" (
    echo     Tentativo %%i di 3...
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' -UseBasicParsing -TimeoutSec 60; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }" >>"%LOG%" 2>&1
    if not errorlevel 1 (
      set "DOWNLOAD_OK=1"
    ) else (
      call :log "Tentativo %%i di download fallito"
      timeout /t 3 >nul
    )
  )
)
if "%DOWNLOAD_OK%"=="0" (
  echo  [!] Errore nel download dopo 3 tentativi. Controlla la connessione internet e riprova.
  echo      Dettagli nel file di log: %LOG%
  call :log "ERRORE: download fallito dopo 3 tentativi"
  pause
  exit /b 2
)
echo     Tema scaricato.
call :log "Download completato"

echo.
echo [3/5] Preparo i file...
if exist "%WORK%" (
  for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%t"
  set "BACKUP=%WORK%-backup-!TS!"
  echo     Trovata una cartella precedente: la sposto in backup per sicurezza.
  move "%WORK%" "!BACKUP!" >>"%LOG%" 2>&1
  call :log "Backup cartella precedente in !BACKUP!"
)
powershell -NoProfile -Command "try { Expand-Archive -Path '%ZIP%' -DestinationPath '%WORK%' -Force; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }" >>"%LOG%" 2>&1
if errorlevel 1 (
  echo  [!] Errore nell'estrazione. Dettagli nel file di log: %LOG%
  call :log "ERRORE: estrazione fallita"
  pause
  exit /b 3
)
del /q "%ZIP%" >nul 2>>"%LOG%"
echo     File pronti in: %WORK%
call :log "Estrazione completata"

echo.
echo [3b/5] Applico le personalizzazioni PERLA (foto cliente + Printify)...
set "CUSTOM_SRC=%SCRIPT_DIR%src\theme"
if exist "%CUSTOM_SRC%" (
  if not exist "%WORK%\snippets" mkdir "%WORK%\snippets"
  if not exist "%WORK%\assets" mkdir "%WORK%\assets"
  if exist "%CUSTOM_SRC%\snippets" xcopy "%CUSTOM_SRC%\snippets\*" "%WORK%\snippets\" /y >>"%LOG%" 2>&1
  if exist "%CUSTOM_SRC%\assets" xcopy "%CUSTOM_SRC%\assets\*" "%WORK%\assets\" /y >>"%LOG%" 2>&1
  echo     Personalizzazioni copiate nel tema.
  call :log "Personalizzazioni copiate"
) else (
  echo     Nessuna personalizzazione trovata accanto allo script: salto questo passo.
  call :log "Cartella src\theme non trovata, personalizzazione saltata"
)

echo.
echo [3c/5] Installo lo strumento Shopify (puo' metterci 1-2 minuti)...
call npm install -g @shopify/cli@latest
if errorlevel 1 (
  echo  [!] Installazione dello strumento Shopify non riuscita. Riprovo...
  call :log "Primo tentativo npm install fallito, riprovo"
  call npm install -g @shopify/cli@latest
  if errorlevel 1 (
    echo  [!] Impossibile installare lo strumento Shopify.
    echo      Prova ad aprire il Prompt dei comandi come Amministratore e riesegui questo file.
    call :log "ERRORE: npm install fallito dopo 2 tentativi"
    pause
    exit /b 4
  )
)
echo     Strumento Shopify pronto.
call :log "Shopify CLI installato"

echo.
echo ===================================================
echo  [4/5] CARICO IL SITO
echo  Si aprira' il BROWSER: fai LOGIN a Shopify e
echo  clicca CONSENTI / AUTORIZZA. Poi torna qui.
echo ===================================================
echo.
pause

cd /d "%WORK%" 2>>"%LOG%"
if errorlevel 1 (
  echo  [!] Impossibile accedere alla cartella del tema.
  call :log "ERRORE: impossibile entrare nella cartella WORK"
  pause
  exit /b 3
)

call shopify theme push --store %STORE% --unpublished
if errorlevel 1 (
  echo  [!] Errore durante il caricamento del tema. Dettagli nel file di log: %LOG%
  call :log "ERRORE: theme push fallito"
  pause
  exit /b 5
)
echo     Tema caricato come bozza.
call :log "Theme push completato"

echo.
echo ===================================================
echo  [5/5] Il tema corretto e' stato caricato come BOZZA.
echo  Vuoi pubblicarlo ADESSO (renderlo live)?
echo ===================================================
echo.
choice /c SN /n /m "Premi S per pubblicare ora, oppure N per pubblicare dopo: "
if errorlevel 2 goto :not_publish
if errorlevel 1 goto :do_publish

:do_publish
call shopify theme publish --store %STORE%
if errorlevel 1 (
  echo  [!] Errore durante la pubblicazione. Dettagli nel file di log: %LOG%
  call :log "ERRORE: theme publish fallito"
  pause
  exit /b 6
)
color 0A
echo.
echo ===================================================
echo   FATTO! Il tuo sito PERLA e' ONLINE e CORRETTO.
echo ===================================================
call :log "Theme publish completato"
goto :final_steps

:not_publish
echo.
echo Ok. Quando vuoi pubblicarlo riapri questo file e scrivi S,
echo oppure pubblicalo da Shopify Admin (Temi - Pubblica).
call :log "Pubblicazione rimandata dall'utente"

:final_steps
echo.
echo  ULTIMI PASSI nel pannello Shopify (vedi la guida):
echo.
echo  1^) PAGINA SALVATI ^(Preferiti^)
echo     Negozio online -^> Pagine -^> Salvati -^> a destra
echo     "Modello pagina" scegli  page.salvati  -^> Salva.
echo.
echo  2^) MERCATO SOLO USA
echo     Impostazioni -^> Mercati -^> lascia attivo solo
echo     United States. Disattiva gli altri.
echo.
echo  3^) PUBBLICA LE COLLEZIONI
echo     Prodotti -^> Collezioni -^> per ognuna con prodotti
echo     ^(Collari, Bandane, Medagliette, Ciotole^):
echo     Disponibilita' -^> spunta "Negozio online".
echo.
echo  4^) FOTO CLIENTE CON ANTEPRIMA LIVE
echo     Nell'editor del tema, apri il template del prodotto e
echo     aggiungi questa riga prima del pulsante "Aggiungi al carrello":
echo       {%% render 'perla-personalizza-prodotto', product: product %%}
echo     Poi, sui prodotti personalizzabili, aggiungi il tag
echo     "personalizzabile" per attivare il modulo.
echo.
echo  5^) INTEGRAZIONE PRINTIFY
echo     Le cartelle "scripts" e "config" accanto a questo file
echo     preparano l'invio automatico degli ordini personalizzati
echo     a Printify. Vanno avviate e ospitate a parte da un tecnico
echo     ^(non da questo file .bat^): inserisci le chiavi API in
echo     config\printify.local.env, MAI in questo script.
echo.
call :log "Script terminato"
echo.
pause
exit /b 0

:log
echo [%DATE% %TIME%] %~1>>"%LOG%"
exit /b 0
