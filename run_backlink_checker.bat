@echo off
echo ========================================
echo    BACKLINK CHECKER AVANZATO - v2.0
echo ========================================
echo.

:: Controlla se Python è installato
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERRORE: Python non è installato o non è nel PATH
    echo Scarica Python da: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python trovato
echo.

:: Installa le dipendenze
echo 📦 Installazione dipendenze...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ ERRORE: Impossibile installare le dipendenze
    pause
    exit /b 1
)

echo ✅ Dipendenze installate
echo.

:: Chiedi il file CSV
set /p csv_file="📁 Inserisci il nome del file CSV (con estensione): "
if not exist "%csv_file%" (
    echo ❌ ERRORE: File '%csv_file%' non trovato
    pause
    exit /b 1
)

:: Chiedi configurazione avanzata
echo.
echo 🔧 CONFIGURAZIONE AVANZATA (premi INVIO per valori default)
set /p workers="   Thread paralleli [default: 10]: "
set /p timeout="   Timeout richieste in secondi [default: 8]: "

:: Imposta valori default se vuoti
if "%workers%"=="" set workers=10
if "%timeout%"=="" set timeout=8

echo.
echo 🚀 Avvio controllo backlink...
echo    📁 File: %csv_file%
echo    🔧 Thread: %workers%
echo    ⏰ Timeout: %timeout%s
echo.

:: Esegui il script con parametri
python backlink_checker.py "%csv_file%" --workers %workers% --timeout %timeout%

echo.
echo ========================================
echo           CONTROLLO COMPLETATO
echo ========================================
echo.
echo 📊 I risultati sono stati salvati in:
echo    - backlink_report_detailed.csv
echo    - Report dettagliato mostrato sopra
echo.
echo 💡 Per eseguire nuovamente:
echo    python backlink_checker.py "file.csv" --workers 20 --timeout 10
echo.
pause