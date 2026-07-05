#!/usr/bin/env python3
"""
Test Application per Client/Server Implementations

Testa tutte le implementazioni disponibili di client e server
nella cartella implementations/, verificando connettività e
funzionamento corretto.

Uso:
    python test_implementations.py [implementation_name] [--verbose]
    
    - Senza parametri: testa tutte le implementazioni
    - Con nome: testa solo quella implementazione
    - --verbose: output dettagliato
"""

import os
import sys
import time
import socket
import subprocess
import signal
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class Colors:
    """Colori ANSI per output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class ImplementationTester:
    """Testa una singola implementazione client/server"""
    
    def __init__(self, impl_name: str, impl_path: Path, verbose: bool = False):
        self.name = impl_name
        self.path = impl_path
        self.verbose = verbose
        self.server_process = None
        self.client_process = None
        
        # Parametri di test
        self.test_port = 9000
        self.test_duration = 5  # secondi
        self.localhost = "127.0.0.1"
        
    def log(self, message: str, level: str = "INFO"):
        """Stampa messaggio con livello"""
        colors = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW
        }
        color = colors.get(level, Colors.RESET)
        
        if self.verbose or level in ["SUCCESS", "ERROR"]:
            print(f"{color}[{level}]{Colors.RESET} {message}")
    
    def check_files(self) -> bool:
        """Verifica esistenza file client e server"""
        client_file = self.path / "client.py"
        server_file = self.path / "server.py"
        
        if not client_file.exists():
            self.log(f"client.py non trovato in {self.path}", "ERROR")
            return False
        
        if not server_file.exists():
            self.log(f"server.py non trovato in {self.path}", "ERROR")
            return False
        
        self.log(f"File client.py e server.py trovati", "INFO")
        return True
    
    def is_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Verifica se una porta è aperta"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def start_server(self) -> bool:
        """Avvia il server in background"""
        server_script = self.path / "server.py"
        
        try:
            self.log(f"Avvio server su porta {self.test_port}...", "INFO")
            
            # Avvia server con stdout/stderr catturati
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script), str(self.test_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Attendi che il server sia pronto (max 5 secondi)
            for i in range(10):
                time.sleep(0.5)
                if self.is_port_open(self.localhost, self.test_port):
                    self.log(f"Server avviato con successo (PID: {self.server_process.pid})", "SUCCESS")
                    return True
            
            self.log("Server non ha aperto la porta in tempo", "ERROR")
            return False
            
        except Exception as e:
            self.log(f"Errore avvio server: {e}", "ERROR")
            return False
    
    def stop_server(self):
        """Ferma il server"""
        if self.server_process:
            try:
                self.log("Fermo il server...", "INFO")
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.log("Server fermato", "INFO")
            except subprocess.TimeoutExpired:
                self.log("Timeout fermando server, forzo kill", "WARNING")
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                self.log(f"Errore fermando server: {e}", "ERROR")
    
    def run_client(self) -> Tuple[bool, str]:
        """Esegue il client e verifica output"""
        client_script = self.path / "client.py"
        
        try:
            self.log(f"Avvio client (durata: {self.test_duration}s)...", "INFO")
            
            # Prepara comando client
            # Formato standard: client.py <dst_ip> <dst_port> [duration]
            cmd = [
                sys.executable,
                str(client_script),
                self.localhost,
                str(self.test_port),
                str(self.test_duration)
            ]
            
            # Esegui client
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.test_duration + 10  # Margine di sicurezza
            )
            
            # Analizza risultato
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            if success:
                self.log("Client completato con successo", "SUCCESS")
            else:
                self.log(f"Client terminato con errore (code: {result.returncode})", "ERROR")
            
            return success, output
            
        except subprocess.TimeoutExpired:
            self.log("Client timeout", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.log(f"Errore esecuzione client: {e}", "ERROR")
            return False, str(e)
    
    def run_test(self) -> Dict:
        """Esegue test completo"""
        result = {
            "name": self.name,
            "success": False,
            "stages": {
                "files_check": False,
                "server_start": False,
                "client_run": False
            },
            "error": None,
            "client_output": ""
        }
        
        try:
            # 1. Verifica file
            if not self.check_files():
                result["error"] = "File mancanti"
                return result
            result["stages"]["files_check"] = True
            
            # 2. Avvia server
            if not self.start_server():
                result["error"] = "Server non avviato"
                return result
            result["stages"]["server_start"] = True
            
            # Pausa breve
            time.sleep(1)
            
            # 3. Esegui client
            client_success, client_output = self.run_client()
            result["stages"]["client_run"] = client_success
            result["client_output"] = client_output
            
            if not client_success:
                result["error"] = "Client fallito"
                return result
            
            # Test completato con successo
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            self.log(f"Errore durante test: {e}", "ERROR")
        
        finally:
            # Ferma sempre il server
            self.stop_server()
        
        return result


class TestRunner:
    """Gestisce l'esecuzione di tutti i test"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.implementations_dir = Path(__file__).parent / "implementations"
        self.results = []
    
    def discover_implementations(self) -> List[Tuple[str, Path]]:
        """Scopre tutte le implementazioni disponibili"""
        implementations = []
        
        if not self.implementations_dir.exists():
            print(f"{Colors.RED}Directory implementations non trovata!{Colors.RESET}")
            return implementations
        
        for item in self.implementations_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Verifica che abbia client.py e server.py
                if (item / "client.py").exists() and (item / "server.py").exists():
                    implementations.append((item.name, item))
        
        return sorted(implementations)
    
    def test_implementation(self, name: str, path: Path) -> Dict:
        """Testa una singola implementazione"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Testing: {name}{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        tester = ImplementationTester(name, path, self.verbose)
        result = tester.run_test()
        
        # Mostra riepilogo
        if result["success"]:
            print(f"\n{Colors.GREEN}✓ {name}: SUCCESSO{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}✗ {name}: FALLITO{Colors.RESET}")
            if result["error"]:
                print(f"  Errore: {result['error']}")
        
        return result
    
    def test_all(self):
        """Testa tutte le implementazioni"""
        implementations = self.discover_implementations()
        
        if not implementations:
            print(f"{Colors.RED}Nessuna implementazione trovata!{Colors.RESET}")
            return
        
        print(f"{Colors.CYAN}Trovate {len(implementations)} implementazioni:{Colors.RESET}")
        for name, _ in implementations:
            print(f"  - {name}")
        
        # Esegui test
        for name, path in implementations:
            result = self.test_implementation(name, path)
            self.results.append(result)
    
    def test_single(self, impl_name: str):
        """Testa una singola implementazione"""
        impl_path = self.implementations_dir / impl_name
        
        if not impl_path.exists():
            print(f"{Colors.RED}Implementazione '{impl_name}' non trovata!{Colors.RESET}")
            return
        
        result = self.test_implementation(impl_name, impl_path)
        self.results.append(result)
    
    def print_summary(self):
        """Stampa riepilogo finale"""
        if not self.results:
            return
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}RIEPILOGO TEST{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        print(f"Totale: {total} | {Colors.GREEN}Passati: {passed}{Colors.RESET} | {Colors.RED}Falliti: {failed}{Colors.RESET}\n")
        
        # Dettaglio per implementazione
        for result in self.results:
            name = result["name"]
            success = result["success"]
            
            status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
            print(f"{status_icon} {name:20s}", end="")
            
            # Mostra stage completati
            stages = result["stages"]
            stage_str = f"[files: {'✓' if stages['files_check'] else '✗'}, "
            stage_str += f"server: {'✓' if stages['server_start'] else '✗'}, "
            stage_str += f"client: {'✓' if stages['client_run'] else '✗'}]"
            print(f" {stage_str}", end="")
            
            if not success and result["error"]:
                print(f" - {result['error']}")
            else:
                print()
        
        # Salva risultati in JSON
        self.save_results()
    
    def save_results(self):
        """Salva risultati in JSON"""
        results_file = Path(__file__).parent / "test_results.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if r["success"]),
                    "failed": sum(1 for r in self.results if not r["success"]),
                    "results": self.results
                }, f, indent=2)
            
            print(f"\n{Colors.CYAN}Risultati salvati in: {results_file}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.YELLOW}Impossibile salvare risultati: {e}{Colors.RESET}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Testa implementazioni client/server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python test_implementations.py                    # Testa tutte le implementazioni
  python test_implementations.py tcp_simple         # Testa solo tcp_simple
  python test_implementations.py --verbose          # Output dettagliato
  python test_implementations.py scapy_burst -v     # Testa scapy_burst con verbosità
        """
    )
    
    parser.add_argument(
        'implementation',
        nargs='?',
        help='Nome implementazione da testare (opzionale, default: tutte)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Output dettagliato'
    )
    
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='Elenca implementazioni disponibili'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    # Lista implementazioni
    if args.list:
        implementations = runner.discover_implementations()
        print(f"{Colors.CYAN}Implementazioni disponibili:{Colors.RESET}")
        for name, path in implementations:
            print(f"  - {name} ({path})")
        return
    
    # Esegui test
    try:
        if args.implementation:
            runner.test_single(args.implementation)
        else:
            runner.test_all()
        
        runner.print_summary()
        
        # Exit code basato sui risultati
        failed = sum(1 for r in runner.results if not r["success"])
        sys.exit(failed)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrotti dall'utente{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
