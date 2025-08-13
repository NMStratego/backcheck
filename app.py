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

def run_backlink_analysis(filepath, max_workers, timeout, backlink_column):
    global analysis_running, checker, stop_analysis
    
    try:
        socketio.emit('log', {'message': '🚀 Avvio analisi backlink...', 'type': 'info'})
        socketio.emit('log', {'message': f'📁 File: {os.path.basename(filepath)}', 'type': 'info'})
        socketio.emit('log', {'message': f'🚀 Thread paralleli: {max_workers}', 'type': 'info'})
        socketio.emit('log', {'message': f'⏱️ Timeout: {timeout}s', 'type': 'info'})
        
        # Leggi il CSV
        df = pd.read_csv(filepath)
        
        if not backlink_column or backlink_column not in df.columns:
            socketio.emit('log', {'message': '❌ Colonna backlink non valida', 'type': 'error'})
            return
        
        socketio.emit('log', {'message': f'✅ Colonna backlink: {backlink_column}', 'type': 'success'})
        
        # Filtra backlink validi
        df[backlink_column] = df[backlink_column].astype(str).str.strip()
        df_with_backlinks = df[
            (df[backlink_column].notna()) & 
            (df[backlink_column] != '') & 
            (df[backlink_column] != 'nan') &
            (df[backlink_column].str.startswith(('http', 'www.'), na=False))
        ]
        
        total_links = len(df_with_backlinks)
        socketio.emit('log', {'message': f'🔍 Trovati {total_links} backlink da controllare', 'type': 'info'})
        
        if total_links == 0:
            socketio.emit('log', {'message': '❌ Nessun backlink valido trovato!', 'type': 'error'})
            return
        
        # Crea il checker
        checker = BacklinkChecker(filepath, max_workers)
        checker.timeout = timeout
        
        # Prepara i dati per l'analisi
        url_data = [(index, str(row[backlink_column]).strip()) 
                   for index, row in df_with_backlinks.iterrows()]
        
        results = []
        completed = 0
        
        # Analizza gli URL in parallelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(checker.check_url_wrapper, data, timeout=timeout): data 
                for data in url_data
            }
            
            for future in as_completed(future_to_url):
                if stop_analysis:
                    socketio.emit('log', {'message': '⏹️ Analisi interrotta dall\'utente', 'type': 'warning'})
                    break
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    completed += 1
                    progress = (completed / total_links) * 100
                    
                    # Emetti aggiornamento progresso
                    socketio.emit('progress', {
                        'completed': completed,
                        'total': total_links,
                        'percentage': round(progress, 1),
                        'current_url': result['url'],
                        'status': result['status']
                    })
                    
                    # Log periodico
                    if completed % 10 == 0 or completed == total_links:
                        socketio.emit('log', {
                            'message': f'📊 Progresso: {completed}/{total_links} ({progress:.1f}%)',
                            'type': 'info'
                        })
                
                except Exception as e:
                    socketio.emit('log', {
                        'message': f'❌ Errore nell\'analisi: {str(e)}',
                        'type': 'error'
                    })
        
        if not stop_analysis and results:
            # Genera il report
            socketio.emit('log', {'message': '📝 Generazione report...', 'type': 'info'})
            
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
            
            socketio.emit('analysis_complete', {
                'report_filename': report_filename,
                'total_analyzed': len(results),
                'statistics': status_counts
            })
            
            socketio.emit('log', {
                'message': f'✅ Analisi completata! Report salvato: {report_filename}',
                'type': 'success'
            })
        
    except Exception as e:
        socketio.emit('log', {
            'message': f'❌ Errore critico: {str(e)}',
            'type': 'error'
        })
    
    finally:
        analysis_running = False
        stop_analysis = False

if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)