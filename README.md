# Backlink Checker Avanzato v2.0

Un sistema automatizzato ad alte prestazioni per verificare lo stato dei backlink in file CSV con elaborazione parallela e analisi dettagliata dei redirect.

## 🚀 Nuove Caratteristiche v2.0

- ⚡ **Elaborazione parallela** con thread configurabili
- 🎯 **Analisi granulare** dei redirect e status code
- 🔧 **Configurazione avanzata** tramite parametri CLI
- 📊 **Report dettagliati** con statistiche complete
- 🛡️ **Gestione errori robusta** con retry automatici
- ⏱️ **Timeout personalizzabili** per ogni richiesta
- 🔍 **Rilevamento intelligente** delle colonne backlink

## Caratteristiche Principali

- ✅ Verifica se i link sono online (status 200)
- 🔄 Rileva e analizza redirect automatici (301, 302, etc.)
- ❌ Identifica link offline, errori client/server
- 🔒 Gestisce errori SSL e certificati
- ⏱️ Misura tempi di risposta precisi
- 📊 Genera report CSV dettagliati
- 🚀 Elaborazione veloce con controllo parallelo
- 🎛️ Configurazione flessibile via linea di comando

## Requisiti

- Python 3.7 o superiore
- Connessione internet attiva
- File CSV con colonna contenente URL

## 🎯 Installazione e Uso Rapido

### Metodo 1: Automatico (Raccomandato)

1. **Doppio click su:**
   ```
   run_backlink_checker.bat
   ```
   
2. **Segui le istruzioni:**
   - Inserisci il nome del file CSV
   - Configura thread paralleli (default: 10)
   - Imposta timeout (default: 8s)

### Metodo 2: Linea di Comando

1. **Installa dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Uso base:**
   ```bash
   python backlink_checker.py "mio_file.csv"
   ```

3. **Uso avanzato:**
   ```bash
   python backlink_checker.py "file.csv" --workers 20 --timeout 10
   ```

## 📋 Parametri di Configurazione

| Parametro | Descrizione | Default | Range |
|-----------|-------------|---------|-------|
| `csv_file` | File CSV da analizzare | - | Obbligatorio |
| `--workers` / `-w` | Thread paralleli | 10 | 1-50 |
| `--timeout` / `-t` | Timeout richieste (sec) | 8 | 1-60 |

### Esempi di Uso

```bash
# Controllo veloce con molti thread
python backlink_checker.py "links.csv" --workers 30

# Controllo conservativo per siti lenti
python backlink_checker.py "links.csv" --workers 5 --timeout 15

# Configurazione bilanciata
python backlink_checker.py "links.csv" --workers 15 --timeout 10
```

## 📁 Formato File di Input

Il sistema rileva automaticamente colonne con nomi:
- "Backlink"
- "backlink" 
- "URL"
- "url"
- "Link"
- "link"

**Esempio CSV:**
```csv
Titolo,Backlink,Data
Articolo 1,https://example.com/page1,2024-01-01
Articolo 2,https://example.com/page2,2024-01-02
```

## 📊 Output e Report

### 1. Report Console in Tempo Reale
```
🚀 BACKLINK CHECKER AVANZATO
📁 File CSV: links.csv
🔧 Configurazione:
   • Thread paralleli: 15
   • Timeout richieste: 8s
⏰ Inizio controllo: 2024-01-15 10:30:00

🔍 Progresso: 150/200 (75.0%) - Ultimo: ONLINE - https://example.com...

📊 RISULTATI FINALI:
✅ Link Online: 145 (72.5%)
   • Senza redirect: 98
   • Con redirect: 47
🔄 Redirect funzionanti: 47
❌ Link problematici: 55 (27.5%)
   • Errori client (4xx): 12
   • Errori server (5xx): 8
   • Timeout: 15
   • Errori SSL: 5
   • Altri errori: 15
```

### 2. File CSV Dettagliato
**Nome:** `backlink_report_detailed_YYYYMMDD_HHMMSS.csv`

**Colonne principali:**
- `url`: URL originale
- `status`: Categoria di status dettagliata
- `status_code`: Codice HTTP finale
- `response_time`: Tempo di risposta (secondi)
- `final_url`: URL finale dopo redirect
- `has_redirects`: True/False
- `redirect_count`: Numero di redirect
- `redirect_chain_details`: Catena completa JSON
- `check_timestamp`: Timestamp del controllo
- `error`: Descrizione errore (se presente)
- `row_index`: Riga nel file originale

## 🎯 Interpretazione Risultati

### Status Dettagliati

| Status | Significato | Azione |
|--------|-------------|--------|
| `ONLINE` ✅ | Link perfetto, nessun redirect | Nessuna |
| `ONLINE_WITH_REDIRECTS` 🔄 | Link funzionante con redirect | Normale |
| `CLIENT_ERROR` ⚠️ | Errori 4xx (404, 403, etc.) | Verificare URL |
| `SERVER_ERROR` 🔴 | Errori 5xx (500, 502, etc.) | Problema server |
| `TIMEOUT` ⏱️ | Timeout connessione | Sito lento/irraggiungibile |
| `CONNECTION_ERROR` 🔌 | Errore di rete | Verificare connessione |
| `SSL_ERROR` 🔒 | Problema certificato SSL | Certificato non valido |

### 🔄 Comprensione dei Redirect

**I redirect sono NORMALI e non errori!**

Esempi comuni e legittimi:
- `http://sito.com` → `https://sito.com` (sicurezza HTTPS)
- `www.sito.com` → `sito.com` (standardizzazione dominio)
- `sito.com/vecchia-pagina` → `sito.com/nuova-pagina` (SEO)
- `sito.com` → `sito.com/it/` (localizzazione)

**Regola:** Se status finale = 200, il link funziona perfettamente!

## ⚙️ Ottimizzazione Prestazioni

### Configurazioni Consigliate

| Scenario | Workers | Timeout | Descrizione |
|----------|---------|---------|-------------|
| **Veloce** | 25-30 | 6-8s | Siti veloci, connessione buona |
| **Bilanciato** | 15-20 | 8-10s | Uso generale |
| **Conservativo** | 5-10 | 12-15s | Siti lenti, connessione instabile |
| **Debug** | 1-3 | 20s | Analisi dettagliata errori |

### Fattori di Performance

- **Più workers** = più veloce, ma maggior carico di rete
- **Timeout alto** = meno falsi negativi, ma più lento
- **Connessione internet** = fattore limitante principale

## 🛠️ Risoluzione Problemi

### Errori Comuni

**"File non trovato"**
```bash
# Usa percorso completo
python backlink_checker.py "C:\path\to\file.csv"

# O sposta il file nella cartella dello script
```

**"Colonna backlink non trovata"**
- Verifica nomi colonne nel CSV
- Supportati: Backlink, URL, Link (case-insensitive)

**Molti timeout**
```bash
# Aumenta timeout e riduci workers
python backlink_checker.py "file.csv" --workers 5 --timeout 15
```

**Errori SSL frequenti**
- Normale per siti con certificati scaduti/non validi
- Non indica problema dello script

### Debug Avanzato

```bash
# Modalità debug (1 thread, timeout alto)
python backlink_checker.py "file.csv" --workers 1 --timeout 30
```

## 🔮 Roadmap Futura

- [ ] **GUI Desktop** con interfaccia grafica
- [ ] **Supporto Excel** (.xlsx, .xls)
- [ ] **Scheduling** controlli automatici
- [ ] **API REST** per integrazioni
- [ ] **Dashboard web** con grafici
- [ ] **Notifiche email** per cambi status
- [ ] **Analisi SEO** avanzata (PageRank, DA, etc.)
- [ ] **Export multipli** (JSON, XML, PDF)
- [ ] **Confronto storico** tra controlli
- [ ] **Filtri avanzati** per domini/pattern

## 📞 Supporto

### Checklist Problemi

1. ✅ Python 3.7+ installato?
2. ✅ Dipendenze installate? (`pip install -r requirements.txt`)
3. ✅ File CSV nel formato corretto?
4. ✅ Connessione internet attiva?
5. ✅ Parametri nei range validi?

### Informazioni Sistema

```bash
# Verifica versione Python
python --version

# Verifica dipendenze
pip list | findstr "requests pandas"

# Test connessione
python -c "import requests; print(requests.get('https://google.com').status_code)"
```

---

**Backlink Checker v2.0** - Sistema professionale per analisi backlink

*Sviluppato per massima velocità, precisione e facilità d'uso*