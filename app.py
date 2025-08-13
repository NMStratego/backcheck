from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import os
import threading
import time
from datetime import datetime
from backlink_checker import BacklinkChecker
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
app.config['SECRET_KEY'] = 'backlink_checker_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Variabili globali per il controllo dell'analisi
analysis_running = False
analysis_thread = None
checker = None
stop_analysis = False
analysis_logs = []
analysis_progress = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Il file deve essere in formato CSV'}), 400
    
    # Salva il file temporaneamente
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    filepath = os.path.join(upload_folder, file.filename)
    file.save(filepath)
    
    # Analizza il CSV per trovare le colonne
    try:
        df = pd.read_csv(filepath)
        columns = list(df.columns)
        
        # Trova automaticamente la colonna backlink
        backlink_column = None
        possible_columns = ['backlink', 'url', 'link', 'sito web', 'website', 'target']
        
        for col in columns:
            if any(keyword in col.lower() for keyword in possible_columns):
                backlink_column = col
                break
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'filepath': filepath,
            'columns': columns,
            'suggested_column': backlink_column,
            'total_rows': len(df)
        })
    
    except Exception as e:
        return jsonify({'error': f'Errore nell\'analisi del file: {str(e)}'}), 400

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    global analysis_running, analysis_thread, checker, stop_analysis
    
    if analysis_running:
        return jsonify({'error': 'Analisi già in corso'}), 400
    
    data = request.json
    filepath = data.get('filepath')
    max_workers = data.get('max_workers', 10)
    timeout = data.get('timeout', 10)
    backlink_column = data.get('backlink_column')
    
    # Limita risorse su Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        max_workers = min(max_workers, 3)  # Massimo 3 worker su Railway
        timeout = max(timeout, 15)  # Timeout più generoso per Railway per evitare falsi negativi
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File non trovato'}), 400
    
    analysis_running = True
    stop_analysis = False
    
    # Avvia l'analisi in un thread separato
    analysis_thread = threading.Thread(
        target=run_backlink_analysis,
        args=(filepath, max_workers, timeout, backlink_column)
    )
    analysis_thread.start()
    
    return jsonify({'success': True, 'message': 'Analisi avviata'})

@app.route('/stop_analysis', methods=['POST'])
def stop_analysis_route():
    global stop_analysis
    stop_analysis = True
    return jsonify({'success': True, 'message': 'Richiesta di stop inviata'})

@app.route('/download_report/<filename>')
def download_report(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Errore nel download: {str(e)}'}), 400

@app.route('/get_logs')
def get_logs():
    """Endpoint per ottenere i log dell'analisi (per Railway)"""
    global analysis_logs
    return jsonify({'logs': analysis_logs})

@app.route('/get_progress')
def get_progress():
    """Endpoint per ottenere il progresso dell'analisi (per Railway)"""
    global analysis_progress, analysis_running
    return jsonify({
        'progress': analysis_progress,
        'running': analysis_running
    })

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """Endpoint per pulire i log (per Railway)"""
    global analysis_logs
    analysis_logs = []
    return jsonify({'success': True})

def emit_log(message, log_type='info'):
    """Funzione universale per logging che funziona sia con SocketIO che senza"""
    global analysis_logs
    
    log_entry = {
        'message': message,
        'type': log_type,
        'timestamp': datetime.now().isoformat()
    }
    
    # Aggiungi ai log per Railway
    analysis_logs.append(log_entry)
    
    # Se SocketIO è disponibile (ambiente locale), usa anche quello
    if not os.environ.get('RAILWAY_ENVIRONMENT'):
        try:
            socketio.emit('log', log_entry)
        except:
            pass  # Ignora errori SocketIO su Railway

def emit_progress(completed, total, percentage, current_url, status):
    """Funzione universale per aggiornamenti di progresso"""
    global analysis_progress
    
    progress_data = {
        'completed': completed,
        'total': total,
        'percentage': round(percentage, 1),
        'current_url': current_url,
        'status': status
    }
    
    # Aggiorna progresso per Railway
    analysis_progress = progress_data
    
    # Se SocketIO è disponibile (ambiente locale), usa anche quello
    if not os.environ.get('RAILWAY_ENVIRONMENT'):
        try:
            socketio.emit('progress', progress_data)
        except:
            pass  # Ignora errori SocketIO su Railway

def emit_analysis_complete(report_filename, total_analyzed, statistics):
    """Funzione universale per completamento analisi"""
    complete_data = {
        'report_filename': report_filename,
        'total_analyzed': total_analyzed,
        'statistics': statistics
    }
    
    # Se SocketIO è disponibile (ambiente locale), usa anche quello
    if not os.environ.get('RAILWAY_ENVIRONMENT'):
        try:
            socketio.emit('analysis_complete', complete_data)
        except:
            pass  # Ignora errori SocketIO su Railway

def run_backlink_analysis(filepath, max_workers, timeout, backlink_column):
    global analysis_running, checker, stop_analysis, analysis_progress
    
    try:
        print(f"[DEBUG] Starting analysis with filepath: {filepath}")
        print(f"[DEBUG] max_workers: {max_workers}, timeout: {timeout}, column: {backlink_column}")
        
        emit_log('🚀 Avvio analisi backlink...', 'info')
        emit_log(f'📁 File: {os.path.basename(filepath)}', 'info')
        emit_log(f'🚀 Thread paralleli: {max_workers}', 'info')
        emit_log(f'⏱️ Timeout: {timeout}s', 'info')
        
        # Leggi il CSV
        print(f"[DEBUG] Reading CSV file: {filepath}")
        df = pd.read_csv(filepath)
        print(f"[DEBUG] CSV loaded, shape: {df.shape}")
        print(f"[DEBUG] Available columns: {list(df.columns)}")
        
        if not backlink_column or backlink_column not in df.columns:
            print(f"[DEBUG] Invalid backlink column: {backlink_column}")
            emit_log('❌ Colonna backlink non valida', 'error')
            return
        
        emit_log(f'✅ Colonna backlink: {backlink_column}', 'success')
        
        # Filtra backlink validi
        df[backlink_column] = df[backlink_column].astype(str).str.strip()
        df_with_backlinks = df[
            (df[backlink_column].notna()) & 
            (df[backlink_column] != '') & 
            (df[backlink_column] != 'nan') &
            (df[backlink_column].str.startswith(('http', 'www.'), na=False))
        ]
        
        total_links = len(df_with_backlinks)
        emit_log(f'🔍 Trovati {total_links} backlink da controllare', 'info')
        
        if total_links == 0:
            emit_log('❌ Nessun backlink valido trovato!', 'error')
            return
        
        # Crea il checker
        print(f"[DEBUG] Creating BacklinkChecker with {max_workers} workers")
        try:
            checker = BacklinkChecker(filepath, max_workers)
            checker.timeout = timeout
            print(f"[DEBUG] BacklinkChecker created successfully")
        except Exception as e:
            print(f"[DEBUG] Error creating BacklinkChecker: {str(e)}")
            emit_log(f'❌ Errore nella creazione del checker: {str(e)}', 'error')
            return
        
        # Prepara i dati per l'analisi
        url_data = [(index, str(row[backlink_column]).strip()) 
                   for index, row in df_with_backlinks.iterrows()]
        
        results = []
        completed = 0
        
        # Analizza gli URL in parallelo con batch processing per Railway
        print(f"Starting URL analysis, Railway environment: {bool(os.environ.get('RAILWAY_ENVIRONMENT'))}")
        
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            batch_size = 50  # Processa 50 URL alla volta su Railway
            print(f"Using Railway batch processing with batch_size: {batch_size}")
            
            for i in range(0, len(url_data), batch_size):
                if stop_analysis:
                    print(f"[DEBUG] Analysis stopped by user at batch {i}")
                    break
                    
                batch = url_data[i:i+batch_size]
                print(f"Processing batch {i//batch_size + 1}, URLs: {len(batch)}")
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {
                        executor.submit(checker.check_url_wrapper, data, timeout=timeout): data 
                        for data in batch
                    }
                    
                    for future in as_completed(future_to_url):
                        if stop_analysis:
                            print(f"[DEBUG] Analysis stopped during batch processing")
                            break
                        
                        try:
                            result = future.result()
                            results.append(result)
                            
                            completed += 1
                            progress = (completed / total_links) * 100
                            
                            if completed % 10 == 0:  # Log every 10th completion
                                print(f"Completed {completed}/{total_links} URLs")
                            emit_progress(completed, total_links, progress, result['url'], result['status'])
                            
                            if completed % 10 == 0 or completed == total_links:
                                emit_log(f'📊 Progresso: {completed}/{total_links} ({progress:.1f}%)', 'info')
                        
                        except Exception as e:
                            print(f"[DEBUG] Error processing URL: {str(e)}")
                            emit_log(f'❌ Errore nell\'analisi: {str(e)}', 'error')
                
                # Pausa tra i batch per non sovraccaricare Railway
                if i + batch_size < len(url_data):
                    print(f"Sleeping 1 second between batches")
                    time.sleep(1)
                    
        else:
            # Ambiente locale: processa tutto insieme
            print(f"Using local processing for {len(url_data)} URLs")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {
                    executor.submit(checker.check_url_wrapper, data, timeout=timeout): data 
                    for data in url_data
                }
                
                for future in as_completed(future_to_url):
                    if stop_analysis:
                        print(f"[DEBUG] Analysis stopped by user")
                        emit_log('⏹️ Analisi interrotta dall\'utente', 'warning')
                        break
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        completed += 1
                        progress = (completed / total_links) * 100
                        
                        if completed % 10 == 0:  # Log every 10th completion
                            print(f"Completed {completed}/{total_links} URLs")
                        emit_progress(completed, total_links, progress, result['url'], result['status'])
                        
                        if completed % 10 == 0 or completed == total_links:
                            emit_log(f'📊 Progresso: {completed}/{total_links} ({progress:.1f}%)', 'info')
                    
                    except Exception as e:
                        emit_log(f'❌ Errore nell\'analisi: {str(e)}', 'error')
        
        if not stop_analysis and results:
            # Genera il report
            emit_log('📝 Generazione report...', 'info')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f'backlink_report_{timestamp}.csv'
            
            # Crea DataFrame con i risultati
            report_data = []
            for result in results:
                row = df_with_backlinks.loc[result['row_index']]
                report_data.append({
                    'URL': result['url'],
                    'Status': result['status'],
                    'Response_Time': result.get('response_time', ''),
                    'Status_Code': result.get('status_code', ''),
                    'Final_URL': result.get('final_url', ''),
                    'Error': result.get('error', ''),
                    'Nome_Azienda': row.get('Nome Azienda', ''),
                    'Referente': row.get('Referente', ''),
                    'Target_Backlink': row.get('Target backlink (URL)', '')
                })
            
            report_df = pd.DataFrame(report_data)
            report_df.to_csv(report_filename, index=False)
            
            # Statistiche finali
            status_counts = report_df['Status'].value_counts().to_dict()
            
            emit_analysis_complete(report_filename, len(results), status_counts)
            
            emit_log(f'✅ Analisi completata! Report salvato: {report_filename}', 'success')
        
    except Exception as e:
        emit_log(f'❌ Errore critico: {str(e)}', 'error')
    
    finally:
        analysis_running = False
        stop_analysis = False

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Usa SocketIO sia per Railway che per sviluppo locale
    socketio.run(app, debug=False, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)