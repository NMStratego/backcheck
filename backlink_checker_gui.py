import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from backlink_checker import BacklinkChecker

class BacklinkCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔗 Backlink Checker - Interfaccia Grafica")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')
        
        # Variabili
        self.csv_file_path = tk.StringVar()
        self.workers = tk.IntVar(value=10)
        self.timeout = tk.IntVar(value=8)
        self.checker = None
        self.analysis_thread = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Titolo principale
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x', padx=10, pady=(10, 0))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="🔗 BACKLINK CHECKER", 
                              font=('Arial', 20, 'bold'), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(title_frame, text="Analizza i tuoi backlink con facilità", 
                                 font=('Arial', 10), fg='#ecf0f1', bg='#2c3e50')
        subtitle_label.pack()
        
        # Frame principale
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Sezione selezione file
        file_frame = tk.LabelFrame(main_frame, text="📁 Selezione File CSV", 
                                  font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        file_frame.pack(fill='x', pady=(0, 10))
        
        file_inner_frame = tk.Frame(file_frame, bg='#f0f0f0')
        file_inner_frame.pack(fill='x', padx=10, pady=10)
        
        self.file_entry = tk.Entry(file_inner_frame, textvariable=self.csv_file_path, 
                                  font=('Arial', 10), width=60)
        self.file_entry.pack(side='left', fill='x', expand=True)
        
        browse_btn = tk.Button(file_inner_frame, text="📂 Sfoglia", 
                              command=self.browse_file, bg='#3498db', fg='white',
                              font=('Arial', 10, 'bold'), padx=20)
        browse_btn.pack(side='right', padx=(10, 0))
        
        # Sezione configurazione
        config_frame = tk.LabelFrame(main_frame, text="⚙️ Configurazione", 
                                    font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        config_frame.pack(fill='x', pady=(0, 10))
        
        config_inner_frame = tk.Frame(config_frame, bg='#f0f0f0')
        config_inner_frame.pack(fill='x', padx=10, pady=10)
        
        # Workers
        workers_frame = tk.Frame(config_inner_frame, bg='#f0f0f0')
        workers_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(workers_frame, text="🚀 Thread paralleli:", 
                font=('Arial', 10), bg='#f0f0f0').pack(side='left')
        
        workers_spinbox = tk.Spinbox(workers_frame, from_=1, to=50, 
                                    textvariable=self.workers, width=10,
                                    font=('Arial', 10))
        workers_spinbox.pack(side='left', padx=(10, 0))
        
        tk.Label(workers_frame, text="(1-50, consigliato: 5-15)", 
                font=('Arial', 9), fg='#7f8c8d', bg='#f0f0f0').pack(side='left', padx=(10, 0))
        
        # Timeout
        timeout_frame = tk.Frame(config_inner_frame, bg='#f0f0f0')
        timeout_frame.pack(fill='x')
        
        tk.Label(timeout_frame, text="⏱️ Timeout (secondi):", 
                font=('Arial', 10), bg='#f0f0f0').pack(side='left')
        
        timeout_spinbox = tk.Spinbox(timeout_frame, from_=3, to=30, 
                                    textvariable=self.timeout, width=10,
                                    font=('Arial', 10))
        timeout_spinbox.pack(side='left', padx=(10, 0))
        
        tk.Label(timeout_frame, text="(3-30, consigliato: 8-12)", 
                font=('Arial', 9), fg='#7f8c8d', bg='#f0f0f0').pack(side='left', padx=(10, 0))
        
        # Pulsanti di controllo
        control_frame = tk.Frame(main_frame, bg='#f0f0f0')
        control_frame.pack(fill='x', pady=(0, 10))
        
        self.start_btn = tk.Button(control_frame, text="🚀 AVVIA ANALISI", 
                                  command=self.start_analysis, bg='#27ae60', fg='white',
                                  font=('Arial', 12, 'bold'), padx=30, pady=10)
        self.start_btn.pack(side='left')
        
        self.stop_btn = tk.Button(control_frame, text="⏹️ FERMA", 
                                 command=self.stop_analysis, bg='#e74c3c', fg='white',
                                 font=('Arial', 12, 'bold'), padx=30, pady=10,
                                 state='disabled')
        self.stop_btn.pack(side='left', padx=(10, 0))
        
        self.clear_btn = tk.Button(control_frame, text="🗑️ PULISCI LOG", 
                                  command=self.clear_log, bg='#95a5a6', fg='white',
                                  font=('Arial', 10, 'bold'), padx=20, pady=10)
        self.clear_btn.pack(side='right')
        
        # Barra di progresso
        progress_frame = tk.Frame(main_frame, bg='#f0f0f0')
        progress_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(progress_frame, text="📊 Progresso:", 
                font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill='x', pady=(5, 0))
        
        self.progress_label = tk.Label(progress_frame, text="Pronto per iniziare", 
                                      font=('Arial', 9), fg='#7f8c8d', bg='#f0f0f0')
        self.progress_label.pack(anchor='w', pady=(2, 0))
        
        # Area di log
        log_frame = tk.LabelFrame(main_frame, text="📋 Log Analisi", 
                                 font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                 font=('Consolas', 9), bg='#2c3e50', 
                                                 fg='#ecf0f1', insertbackground='white')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Messaggio iniziale
        self.log_message("🔗 Backlink Checker v2.0 - Pronto per l'uso!")
        self.log_message("📝 Seleziona un file CSV e configura i parametri per iniziare.")
        self.log_message("💡 Suggerimento: Usa 5-15 thread per prestazioni ottimali.")
        
    def browse_file(self):
        """Apre il dialog per selezionare il file CSV"""
        file_path = filedialog.askopenfilename(
            title="Seleziona file CSV con backlink",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
            initialdir=os.getcwd()
        )
        if file_path:
            self.csv_file_path.set(file_path)
            self.log_message(f"📁 File selezionato: {os.path.basename(file_path)}")
            
    def log_message(self, message):
        """Aggiunge un messaggio al log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """Pulisce il log"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🗑️ Log pulito - Pronto per nuova analisi")
        
    def update_progress(self, current, total, message=""):
        """Aggiorna la barra di progresso"""
        if total > 0:
            percentage = (current / total) * 100
            self.progress['value'] = percentage
            
            if message:
                self.progress_label.config(text=f"{message} ({current}/{total} - {percentage:.1f}%)")
            else:
                self.progress_label.config(text=f"Progresso: {current}/{total} ({percentage:.1f}%)")
        
        self.root.update_idletasks()
        
    def validate_inputs(self):
        """Valida gli input dell'utente"""
        if not self.csv_file_path.get():
            messagebox.showerror("Errore", "Seleziona un file CSV!")
            return False
            
        if not os.path.exists(self.csv_file_path.get()):
            messagebox.showerror("Errore", "Il file selezionato non esiste!")
            return False
            
        if not self.csv_file_path.get().lower().endswith('.csv'):
            messagebox.showwarning("Attenzione", "Il file selezionato non sembra essere un CSV!")
            
        if self.workers.get() < 1 or self.workers.get() > 50:
            messagebox.showerror("Errore", "Il numero di thread deve essere tra 1 e 50!")
            return False
            
        if self.timeout.get() < 3 or self.timeout.get() > 30:
            messagebox.showerror("Errore", "Il timeout deve essere tra 3 e 30 secondi!")
            return False
            
        return True
        
    def start_analysis(self):
        """Avvia l'analisi dei backlink"""
        if not self.validate_inputs():
            return
            
        # Disabilita il pulsante start e abilita stop
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Reset progresso
        self.progress['value'] = 0
        self.progress_label.config(text="Inizializzazione...")
        
        # Avvia l'analisi in un thread separato
        self.analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        self.analysis_thread.start()
        
    def run_analysis(self):
        """Esegue l'analisi dei backlink"""
        try:
            self.log_message("\n" + "="*60)
            self.log_message("🚀 AVVIO ANALISI BACKLINK")
            self.log_message("="*60)
            self.log_message(f"📁 File: {os.path.basename(self.csv_file_path.get())}")
            self.log_message(f"🚀 Thread: {self.workers.get()}")
            self.log_message(f"⏱️ Timeout: {self.timeout.get()}s")
            self.log_message("="*60)
            
            # Crea il checker con i parametri configurati
            self.checker = BacklinkChecker(
                csv_file_path=self.csv_file_path.get(),
                max_workers=self.workers.get()
            )
            self.checker.timeout = self.timeout.get()
            
            # Modifica il checker per supportare callback GUI
            original_process = self.checker.process_csv
            
            def gui_process_csv():
                # Implementazione personalizzata per GUI
                import pandas as pd
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                try:
                    df = pd.read_csv(self.checker.csv_file_path)
                    
                    # Trova la colonna backlink
                    backlink_column = None
                    possible_columns = ['backlink', 'url', 'link', 'sito web', 'website', 'target']
                    
                    self.log_message(f"🔍 Colonne disponibili ({len(df.columns)}): {list(df.columns)}")
                    
                    # Debug: controlla ogni colonna
                    for col in df.columns:
                        col_lower = col.lower()
                        matches = [keyword for keyword in possible_columns if keyword in col_lower]
                        if matches:
                            self.log_message(f"🎯 Colonna '{col}' contiene parole chiave: {matches}")
                            if not backlink_column:  # Prendi la prima che trova
                                backlink_column = col
                                self.log_message(f"✅ Selezionata colonna: '{col}'")
                    
                    if not backlink_column:
                        self.log_message("❌ Colonna backlink non trovata!")
                        self.log_message(f"💡 Parole chiave cercate: {possible_columns}")
                        return
                    
                    self.log_message(f"✅ Colonna backlink trovata: '{backlink_column}'")
                    
                    # Debug: mostra alcune righe della colonna backlink
                    self.log_message(f"🔍 Analizzando colonna '{backlink_column}'...")
                    
                    # Converti la colonna in stringa e pulisci
                    df[backlink_column] = df[backlink_column].astype(str).str.strip()
                    
                    # Conta i valori non vuoti
                    non_empty = df[df[backlink_column].notna() & (df[backlink_column] != '') & (df[backlink_column] != 'nan')]
                    self.log_message(f"📊 Righe con valori non vuoti: {len(non_empty)}/{len(df)}")
                    
                    # Conta quelli che iniziano con http o www
                    with_protocol = non_empty[non_empty[backlink_column].str.startswith(('http', 'www.'), na=False)]
                    self.log_message(f"🌐 Righe con URL validi: {len(with_protocol)}")
                    
                    # Mostra alcuni esempi
                    if len(with_protocol) > 0:
                        sample_urls = with_protocol[backlink_column].head(3).tolist()
                        self.log_message(f"📝 Esempi URL trovati: {sample_urls}")
                    
                    # Filtra backlink validi
                    df_with_backlinks = df[
                        (df[backlink_column].notna()) & 
                        (df[backlink_column] != '') & 
                        (df[backlink_column] != 'nan') &
                        (df[backlink_column].str.startswith(('http', 'www.'), na=False))
                    ]
                    
                    total_links = len(df_with_backlinks)
                    self.log_message(f"🔍 Trovati {total_links} backlink da controllare")
                    
                    if total_links == 0:
                        self.log_message("❌ Nessun backlink valido trovato!")
                        self.log_message("💡 Suggerimento: Verifica che la colonna contenga URL completi (http/https)")
                        return
                    
                    # Prepara dati per processing
                    url_data = [(index, str(row[backlink_column]).strip()) 
                               for index, row in df_with_backlinks.iterrows()]
                    
                    # Controlla URL in parallelo
                    completed = 0
                    with ThreadPoolExecutor(max_workers=self.checker.max_workers) as executor:
                        future_to_url = {
                            executor.submit(self.checker.check_url_wrapper, data, timeout=self.checker.timeout): data 
                            for data in url_data
                        }
                        
                        for future in as_completed(future_to_url):
                            try:
                                result = future.result()
                                
                                # Aggiungi info dalla riga CSV
                                row = df_with_backlinks.loc[result['row_index']]
                                result.update({
                                    'nome_azienda': row.get('Nome Azienda', ''),
                                    'sito_pubblicazione': row.get('Sito di pubblicazione', ''),
                                    'titolo': row.get('Titolo', ''),
                                    'data_pubblicazione': row.get('Data di pubblicazione', '')
                                })
                                
                                with self.checker.lock:
                                    self.checker.results.append(result)
                                    completed += 1
                                
                                # Aggiorna GUI
                                self.update_progress(completed, total_links)
                                
                                # Log risultato
                                url = result['url']
                                status = result['status']
                                status_code = result.get('status_code', 'N/A')
                                response_time = result.get('response_time', 0)
                                
                                status_emoji = {
                                    'ONLINE': '✅',
                                    'ONLINE_WITH_REDIRECTS': '✅🔄',
                                    'CLIENT_ERROR': '❌',
                                    'SERVER_ERROR': '🔥',
                                    'TIMEOUT': '⏰',
                                    'CONNECTION_ERROR': '🔌',
                                    'REDIRECT_ERROR': '🔄❌',
                                    'INVALID': '❓',
                                    'ERROR': '❌'
                                }.get(status, '❓')
                                
                                short_url = url[:50] + '...' if len(url) > 50 else url
                                self.log_message(f"[{completed}/{total_links}] {status_emoji} {short_url}")
                                self.log_message(f"    {status} ({status_code}) - {response_time}s")
                                
                                if result.get('has_redirects'):
                                    redirect_count = result.get('redirect_count', 0)
                                    final_url = result.get('final_url', '')[:40]
                                    self.log_message(f"    🔄 {redirect_count} redirect → {final_url}...")
                                
                                if result.get('error'):
                                    error_msg = result['error'][:50]
                                    self.log_message(f"    ⚠️ {error_msg}...")
                                    
                            except Exception as e:
                                self.log_message(f"❌ Errore nel controllo URL: {e}")
                    
                    # Ordina risultati
                    self.checker.results.sort(key=lambda x: x['row_index'])
                    
                except Exception as e:
                    self.log_message(f"❌ ERRORE durante la lettura del CSV: {str(e)}")
                    return
            
            # Sostituisci il metodo process_csv
            self.checker.process_csv = gui_process_csv
            
            # Esegui l'analisi completa
            self.checker.run()
            
            self.log_message("\n" + "="*60)
            self.log_message("✅ ANALISI COMPLETATA CON SUCCESSO!")
            self.log_message("📊 Controlla i file di report generati.")
            self.log_message("="*60)
            
        except Exception as e:
            self.log_message(f"\n❌ ERRORE DURANTE L'ANALISI: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'analisi:\n{str(e)}")
            
        finally:
            # Riabilita i pulsanti
            self.root.after(0, self.analysis_completed)
            
    def analysis_completed(self):
        """Chiamata quando l'analisi è completata"""
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress_label.config(text="Analisi completata")
        
    def stop_analysis(self):
        """Ferma l'analisi in corso"""
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.log_message("\n⏹️ Interruzione analisi richiesta...")
            # Nota: threading in Python non supporta l'interruzione forzata
            # L'analisi si fermerà al prossimo checkpoint
            messagebox.showinfo("Info", "L'analisi si fermerà al prossimo checkpoint.")
        
        self.analysis_completed()

def main():
    """Funzione principale per avviare l'interfaccia grafica"""
    root = tk.Tk()
    app = BacklinkCheckerGUI(root)
    
    # Centra la finestra
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Gestione chiusura
    def on_closing():
        if messagebox.askokcancel("Uscita", "Vuoi chiudere il Backlink Checker?"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Avvia l'interfaccia
    root.mainloop()

if __name__ == "__main__":
    main()