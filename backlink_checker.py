#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backlink Checker Script
Controlla tutti i link nella colonna 'Backlink' del file CSV
Verifica status HTTP, redirect e funzionalità dei link
"""

import csv
import requests
import time
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disabilita i warning SSL per una migliore esperienza utente
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BacklinkChecker:
    def __init__(self, csv_file_path, max_workers=10):
        self.csv_file_path = csv_file_path
        self.results = []
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.timeout = 8  # Timeout default
        
        # Configura sessione con retry strategy e connection pooling
        self.session = requests.Session()
        # Disabilita verifica SSL per considerare accessibili anche link con certificati non validi
        self.session.verify = False
        
        # Strategia di retry più robusta per Railway
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            retry_strategy = Retry(
                total=5,  # Più tentativi su Railway
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                connect=3,  # Retry per errori di connessione
                read=3,     # Retry per errori di lettura
            )
        else:
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers ottimizzati
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def check_url(self, url, timeout=8):
        """
        Controlla un singolo URL e restituisce informazioni dettagliate
        """
        if not url or str(url).strip() == '' or str(url).lower() == 'nan':
            return {
                'url': url,
                'status': 'INVALID',
                'status_code': None,
                'redirect_chain': [],
                'final_url': None,
                'error': 'URL vuoto o non valido',
                'response_time': None,
                'redirect_count': 0,
                'has_redirects': False
            }
            
        # Pulisci e normalizza l'URL
        original_url = str(url).strip()
        if not original_url.startswith(('http://', 'https://')):
            if original_url.startswith('www.'):
                original_url = 'https://' + original_url
            else:
                original_url = 'https://' + original_url
            
        start_time = time.time()
        redirect_chain = []
        
        try:
            # Su Railway usa timeout più generoso per evitare falsi negativi
            if 'RAILWAY_ENVIRONMENT' in os.environ:
                actual_timeout = 15  # Timeout più generoso su Railway
            else:
                actual_timeout = timeout
            
            # Prima richiesta HEAD per velocità
            try:
                response = self.session.head(original_url, timeout=actual_timeout, allow_redirects=True)
                
                # Se HEAD fallisce o restituisce errore, prova sempre GET
                if response.status_code >= 400:
                    response = self.session.get(original_url, timeout=actual_timeout, allow_redirects=True)
                    
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Se HEAD fallisce completamente, prova direttamente GET
                response = self.session.get(original_url, timeout=actual_timeout, allow_redirects=True)
            
            response_time = round(time.time() - start_time, 3)
            
            # Traccia la catena di redirect
            if response.history:
                for resp in response.history:
                    redirect_chain.append({
                        'from_url': resp.url,
                        'status_code': resp.status_code,
                        'reason': resp.reason
                    })
            
            # Determina lo status più preciso
            has_redirects = len(redirect_chain) > 0
            redirect_count = len(redirect_chain)
            
            if response.status_code == 200:
                status = 'ONLINE_WITH_REDIRECTS' if has_redirects else 'ONLINE'
            elif 300 <= response.status_code < 400:
                status = 'REDIRECT_ERROR'
            elif 400 <= response.status_code < 500:
                status = 'CLIENT_ERROR'
            elif response.status_code >= 500:
                status = 'SERVER_ERROR'
            else:
                status = 'UNKNOWN_ERROR'
                    
            result = {
                'url': original_url,
                'status': status,
                'status_code': response.status_code,
                'redirect_chain': redirect_chain,
                'final_url': response.url,
                'error': None if response.status_code == 200 else f'HTTP {response.status_code}: {response.reason}',
                'response_time': response_time,
                'redirect_count': redirect_count,
                'has_redirects': has_redirects
            }
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                'url': original_url,
                'status': 'TIMEOUT',
                'status_code': None,
                'redirect_chain': [],
                'final_url': None,
                'error': f'Timeout dopo {timeout}s',
                'response_time': timeout,
                'redirect_count': 0,
                'has_redirects': False
            }
            
        except requests.exceptions.ConnectionError:
            return {
                'url': original_url,
                'status': 'CONNECTION_ERROR',
                'status_code': None,
                'redirect_chain': [],
                'final_url': None,
                'error': 'Connessione fallita - Sito offline o irraggiungibile',
                'response_time': round(time.time() - start_time, 3),
                'redirect_count': 0,
                'has_redirects': False
            }
            
        # Gli errori SSL sono ora gestiti automaticamente (verifica disabilitata)
            
        except Exception as e:
            return {
                'url': original_url,
                'status': 'ERROR',
                'status_code': None,
                'redirect_chain': [],
                'final_url': None,
                'error': f'Errore: {str(e)[:100]}',
                'response_time': round(time.time() - start_time, 3),
                'redirect_count': 0,
                'has_redirects': False
            }
            
    def check_url_wrapper(self, url_data, timeout=8):
        """Wrapper per il controllo URL con threading"""
        index, url = url_data
        
        try:
            result = self.check_url(url, timeout=timeout)
            result['row_index'] = index
            return result
            
        except Exception as e:
            return {
                'url': url,
                'status': 'ERROR',
                'status_code': None,
                'redirect_chain': [],
                'final_url': url,
                'error': str(e),
                'response_time': 0,
                'redirect_count': 0,
                'has_redirects': False,
                'row_index': index
            }
    
    def process_csv(self):
        """
        Processa il file CSV e controlla tutti i backlink in parallelo
        """
        print(f"Inizio controllo backlink dal file: {self.csv_file_path}")
        print("=" * 60)
        
        try:
            # Leggi il CSV
            df = pd.read_csv(self.csv_file_path, encoding='utf-8')
            
            # Trova la colonna 'Backlink'
            backlink_column = None
            for col in df.columns:
                if col.strip().lower() == 'backlink':
                    backlink_column = col
                    break
            
            # Se non trova 'Backlink', cerca altre varianti
            if backlink_column is None:
                for col in df.columns:
                    if 'backlink' in col.lower() and 'target' not in col.lower() and 'n.' not in col.lower():
                        backlink_column = col
                        break
                    
            if backlink_column is None:
                print("ERRORE: Colonna 'Backlink' non trovata nel CSV")
                return
                
            print(f"Trovata colonna backlink: '{backlink_column}'")
            
            # Filtra solo le righe con backlink non vuoti
            # Converti la colonna in stringa e rimuovi spazi
            df[backlink_column] = df[backlink_column].astype(str).str.strip()
            df_with_backlinks = df[
                (df[backlink_column].notna()) & 
                (df[backlink_column] != '') & 
                (df[backlink_column] != 'nan') &
                (df[backlink_column].str.startswith(('http', 'www.')))
            ]
            
            total_links = len(df_with_backlinks)
            print(f"Trovati {total_links} backlink da controllare")
            print(f"🚀 Controllo parallelo con {self.max_workers} thread")
            print("=" * 60)
            
            if total_links == 0:
                print("Nessun backlink trovato nel file CSV")
                return
                
            # Prepara i dati per il processing parallelo
            url_data = [(index, str(row[backlink_column]).strip()) for index, row in df_with_backlinks.iterrows()]
            
            # Controlla gli URL in parallelo
            completed = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Invia tutti i task con timeout personalizzato
                future_to_url = {executor.submit(self.check_url_wrapper, data, timeout=self.timeout): data for data in url_data}
                
                # Processa i risultati man mano che arrivano
                for future in as_completed(future_to_url):
                    try:
                        result = future.result()
                        
                        # Aggiungi informazioni aggiuntive dalla riga CSV
                        row = df_with_backlinks.loc[result['row_index']]
                        result.update({
                            'nome_azienda': row.get('Nome Azienda', ''),
                            'sito_pubblicazione': row.get('Sito di pubblicazione', ''),
                            'titolo': row.get('Titolo', ''),
                            'data_pubblicazione': row.get('Data di pubblicazione', '')
                        })
                        
                        with self.lock:
                            self.results.append(result)
                            completed += 1
                        
                        # Mostra progresso
                        url = result['url']
                        print(f"\n[{completed}/{total_links}] {url[:60]}{'...' if len(url) > 60 else ''}")
                        
                        # Emoji per status
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
                        }.get(result['status'], '❓')
                        
                        print(f"  {status_emoji} {result['status']} ({result['status_code']}) - {result['response_time']}s")
                        
                        if result['has_redirects']:
                            print(f"  🔄 {result['redirect_count']} redirect: {result['final_url'][:50]}{'...' if len(result['final_url']) > 50 else ''}")
                        
                        if result['error']:
                            print(f"  ⚠️  {result['error'][:60]}{'...' if len(result['error']) > 60 else ''}")
                            
                    except Exception as e:
                        print(f"❌ Errore nel controllo URL: {e}")
            
            # Ordina i risultati per row_index
            self.results.sort(key=lambda x: x['row_index'])
                
        except Exception as e:
            print(f"ERRORE durante la lettura del CSV: {str(e)}")
            return
            
    def generate_report(self):
        """Genera un report dettagliato dei risultati"""
        if not self.results:
            print("Nessun risultato da mostrare")
            return
            
        print("\n" + "=" * 80)
        print("📊 REPORT FINALE BACKLINK CHECKER")
        print("=" * 80)
        
        # Statistiche generali
        total = len(self.results)
        online = len([r for r in self.results if r['status'] in ['ONLINE', 'ONLINE_WITH_REDIRECTS']])
        online_clean = len([r for r in self.results if r['status'] == 'ONLINE'])
        online_redirects = len([r for r in self.results if r['status'] == 'ONLINE_WITH_REDIRECTS'])
        errors = len([r for r in self.results if r['status'] not in ['ONLINE', 'ONLINE_WITH_REDIRECTS']])
        
        print(f"\n📈 STATISTICHE GENERALI:")
        print(f"  • Totale link controllati: {total}")
        print(f"  • ✅ Link funzionanti: {online} ({online/total*100:.1f}%)")
        print(f"    ├─ 🟢 Senza redirect: {online_clean} ({online_clean/total*100:.1f}%)")
        print(f"    └─ 🔄 Con redirect: {online_redirects} ({online_redirects/total*100:.1f}%)")
        print(f"  • ❌ Link con problemi: {errors} ({errors/total*100:.1f}%)")
        
        # Tempo medio di risposta
        response_times = [r['response_time'] for r in self.results if r['response_time'] is not None]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            print(f"  • ⏱️  Tempo medio risposta: {avg_time:.2f}s")
        
        # Dettaglio per status
        status_count = {}
        for result in self.results:
            status = result['status']
            status_count[status] = status_count.get(status, 0) + 1
            
        print(f"\n📋 DETTAGLIO PER STATUS:")
        status_order = ['ONLINE', 'ONLINE_WITH_REDIRECTS', 'CLIENT_ERROR', 'SERVER_ERROR', 'TIMEOUT', 'CONNECTION_ERROR', 'REDIRECT_ERROR', 'INVALID', 'ERROR']
        
        for status in status_order:
            if status in status_count:
                count = status_count[status]
                percentage = count/total*100
                emoji = {
                    'ONLINE': '🟢',
                    'ONLINE_WITH_REDIRECTS': '🔄',
                    'CLIENT_ERROR': '🔴',
                    'SERVER_ERROR': '🔥',
                    'TIMEOUT': '⏰',
                    'CONNECTION_ERROR': '🔌',
                    'REDIRECT_ERROR': '🔄❌',
                    'INVALID': '❓',
                    'ERROR': '❌'
                }.get(status, '❓')
                print(f"  {emoji} {status}: {count} ({percentage:.1f}%)")
        
        # Analisi redirect
        redirected = [r for r in self.results if r['has_redirects']]
        if redirected:
            redirect_counts = {}
            for r in redirected:
                count = r['redirect_count']
                redirect_counts[count] = redirect_counts.get(count, 0) + 1
            
            print(f"\n🔄 ANALISI REDIRECT ({len(redirected)} link):")
            for count in sorted(redirect_counts.keys()):
                num_links = redirect_counts[count]
                print(f"  • {count} redirect: {num_links} link")
                
        # Link con problemi
        problematic = [r for r in self.results if r['status'] not in ['ONLINE', 'ONLINE_WITH_REDIRECTS']]
        if problematic:
            print(f"\n🚨 LINK CON PROBLEMI ({len(problematic)}):")
            for result in problematic[:8]:  # Mostra solo i primi 8
                print(f"  ❌ Riga {result['row_index']}: {result['url'][:55]}{'...' if len(result['url']) > 55 else ''}")
                print(f"     🔸 {result['status']} - {result['error'][:50]}{'...' if len(result['error']) > 50 else ''}")
                print()
                
            if len(problematic) > 8:
                print(f"  ... e altri {len(problematic) - 8} link con problemi")
                
        # Esempi di redirect più comuni
        if redirected:
            print(f"\n🔄 ESEMPI DI REDIRECT:")
            for result in redirected[:4]:  # Mostra solo i primi 4
                print(f"  🔗 Riga {result['row_index']}: {result['redirect_count']} redirect")
                print(f"     Da: {result['url'][:50]}{'...' if len(result['url']) > 50 else ''}")
                print(f"     A:  {result['final_url'][:50]}{'...' if len(result['final_url']) > 50 else ''}")
                print()
                
        print("\n" + "=" * 80)
                    
    def save_detailed_report(self):
        """
        Salva un report dettagliato in formato CSV
        """
        if not self.results:
            print("Nessun risultato da salvare")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"backlink_report_{timestamp}.csv"
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'row_index', 'url', 'status', 'status_code', 'final_url', 
                    'has_redirects', 'redirect_count', 'redirect_chain_details',
                    'response_time', 'error', 'check_timestamp',
                    'nome_azienda', 'sito_pubblicazione', 'titolo', 'data_pubblicazione'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.results:
                    # Prepara dettagli redirect per CSV
                    redirect_details = ""
                    if result['redirect_chain']:
                        redirect_parts = []
                        for i, redirect in enumerate(result['redirect_chain']):
                            redirect_parts.append(f"{i+1}. {redirect['from_url']} ({redirect['status_code']})")
                        redirect_details = " | ".join(redirect_parts)
                    
                    # Prepara i dati per il CSV
                    row_data = {
                        'row_index': result['row_index'],
                        'url': result['url'],
                        'status': result['status'],
                        'status_code': result['status_code'],
                        'final_url': result['final_url'],
                        'has_redirects': 'Sì' if result['has_redirects'] else 'No',
                        'redirect_count': result['redirect_count'],
                        'redirect_chain_details': redirect_details,
                        'response_time': result['response_time'],
                        'error': result['error'] or '',
                        'check_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'nome_azienda': result.get('nome_azienda', ''),
                        'sito_pubblicazione': result.get('sito_pubblicazione', ''),
                        'titolo': result.get('titolo', ''),
                        'data_pubblicazione': result.get('data_pubblicazione', '')
                    }
                    
                    writer.writerow(row_data)
                    
            print(f"\n✅ Report dettagliato salvato in: {output_file}")
            
            # Statistiche del file salvato
            total = len(self.results)
            online = len([r for r in self.results if r['status'] in ['ONLINE', 'ONLINE_WITH_REDIRECTS']])
            with_redirects = len([r for r in self.results if r['has_redirects']])
            
            print(f"📄 Contenuto del report:")
            print(f"  • {total} link analizzati")
            print(f"  • {online} link funzionanti")
            print(f"  • {with_redirects} link con redirect")
            print(f"  • {total - online} link con problemi")
            
        except Exception as e:
            print(f"❌ Errore nel salvare il report: {e}")
        
    def run(self):
        """
        Esegue il controllo completo dei backlink
        """
        print("🔍 BACKLINK CHECKER")
        print(f"Data/Ora inizio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.process_csv()
        self.generate_report()
        self.save_detailed_report()
        
        print("\n✅ Controllo completato!")

def main():
    """Funzione principale"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Backlink Checker - Verifica lo stato dei backlink in un file CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python backlink_checker.py file.csv
  python backlink_checker.py file.csv --workers 20
  python backlink_checker.py file.csv --workers 5 --timeout 15

Il sistema controlla automaticamente:
  ✅ Link online (status 200)
  🔄 Redirect (automatici e funzionanti)
  ❌ Link offline o con errori
  ⏰ Timeout di connessione
  🔒 Errori SSL
        """
    )
    
    parser.add_argument('csv_file', help='File CSV contenente i backlink da controllare')
    parser.add_argument('--workers', '-w', type=int, default=10, 
                       help='Numero di thread paralleli (default: 10, max: 50)')
    parser.add_argument('--timeout', '-t', type=int, default=8,
                       help='Timeout in secondi per ogni richiesta (default: 8)')
    
    args = parser.parse_args()
    
    # Validazione parametri
    if not os.path.exists(args.csv_file):
        print(f"❌ Errore: File '{args.csv_file}' non trovato")
        sys.exit(1)
    
    if args.workers < 1 or args.workers > 50:
        print(f"❌ Errore: Il numero di workers deve essere tra 1 e 50")
        sys.exit(1)
        
    if args.timeout < 1 or args.timeout > 60:
        print(f"❌ Errore: Il timeout deve essere tra 1 e 60 secondi")
        sys.exit(1)
        
    print(f"🚀 BACKLINK CHECKER AVANZATO")
    print(f"📁 File CSV: {args.csv_file}")
    print(f"🔧 Configurazione:")
    print(f"   • Thread paralleli: {args.workers}")
    print(f"   • Timeout richieste: {args.timeout}s")
    print(f"⏰ Inizio controllo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 60)
    
    try:
        checker = BacklinkChecker(args.csv_file, max_workers=args.workers)
        checker.timeout = args.timeout  # Salva il timeout nell'istanza
        checker.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Controllo interrotto dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Errore critico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()