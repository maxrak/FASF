#!/usr/bin/env python3
"""
Demo completa delle funzionalità dell'applicazione di test

Mostra tutte le features in un unico script dimostrativo
"""

import sys
from pathlib import Path

# Aggiungi path per import
sys.path.insert(0, str(Path(__file__).parent))

from test_implementations import Colors
import test_utils


def print_header(title):
    """Stampa header decorato"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def demo_check_dependencies():
    """Demo: Verifica dipendenze"""
    print_header("1. VERIFICA DIPENDENZE")
    
    deps = test_utils.check_dependencies()
    
    print("Dipendenze installate:\n")
    for dep, installed in deps.items():
        status = f"{Colors.GREEN}✓ installata{Colors.RESET}" if installed else f"{Colors.RED}✗ mancante{Colors.RESET}"
        print(f"  {dep:10s}: {status}")
    
    all_installed = all(deps.values())
    
    if all_installed:
        print(f"\n{Colors.GREEN}✓ Tutte le dipendenze sono soddisfatte{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}⚠ Alcune dipendenze sono mancanti{Colors.RESET}")
        print(f"  Installa con: python3 test_utils.py install-deps")


def demo_list_implementations():
    """Demo: Lista implementazioni"""
    print_header("2. IMPLEMENTAZIONI DISPONIBILI")
    
    implementations = test_utils.list_implementations()
    
    print(f"Trovate {len(implementations)} implementazioni:\n")
    test_utils.print_implementations_table(implementations)
    
    # Dettagli per implementazione
    print("Dettagli implementazioni:\n")
    for impl in implementations:
        print(f"{Colors.BOLD}{impl['name']}{Colors.RESET}")
        print(f"  Path: {impl['path']}")
        print(f"  Client: {impl['client_lines']} linee")
        print(f"  Server: {impl['server_lines']} linee")
        print(f"  README: {'Presente' if impl['has_readme'] else 'Assente'}")
        print()


def demo_check_port():
    """Demo: Verifica porta"""
    print_header("3. VERIFICA DISPONIBILITÀ PORTA")
    
    test_ports = [9000, 9001, 8080, 3000]
    
    print("Controllo porte:\n")
    for port in test_ports:
        available = test_utils.check_port_available(port)
        status = f"{Colors.GREEN}disponibile{Colors.RESET}" if available else f"{Colors.RED}in uso{Colors.RESET}"
        print(f"  Porta {port:5d}: {status}")
    
    # Trova porta libera
    print("\nCerca porta libera nell'intervallo 9000-9100:")
    free_port = test_utils.get_free_port(9000, 9100)
    if free_port:
        print(f"  {Colors.GREEN}✓ Porta libera trovata: {free_port}{Colors.RESET}")
    else:
        print(f"  {Colors.RED}✗ Nessuna porta libera trovata{Colors.RESET}")


def demo_load_config():
    """Demo: Carica configurazione"""
    print_header("4. CONFIGURAZIONE TEST")
    
    config = test_utils.load_test_config()
    
    if config:
        print("Configurazione caricata da test_config.json:\n")
        
        if "test_config" in config:
            print(f"{Colors.BOLD}Parametri Test:{Colors.RESET}")
            for key, value in config["test_config"].items():
                if key != "comment":
                    print(f"  {key:20s}: {value}")
        
        print()
        
        if "implementations" in config:
            print(f"{Colors.BOLD}Implementazioni Configurate:{Colors.RESET}")
            for impl, settings in config["implementations"].items():
                enabled = settings.get("enabled", False)
                status = f"{Colors.GREEN}✓{Colors.RESET}" if enabled else f"{Colors.RED}✗{Colors.RESET}"
                desc = settings.get("description", "N/A")
                print(f"  {status} {impl:15s}: {desc}")
        
        print()
        
        if "output" in config:
            print(f"{Colors.BOLD}Configurazione Output:{Colors.RESET}")
            for key, value in config["output"].items():
                print(f"  {key:15s}: {value}")
    else:
        print(f"{Colors.YELLOW}Nessuna configurazione trovata{Colors.RESET}")
        print("Usa parametri di default")


def demo_test_commands():
    """Demo: Comandi di test disponibili"""
    print_header("5. COMANDI DISPONIBILI")
    
    commands = [
        ("test_implementations.py", "Test runner principale", [
            ("", "Testa tutte le implementazioni"),
            ("tcp_simple", "Testa solo tcp_simple"),
            ("--list", "Lista implementazioni"),
            ("-v", "Output verboso"),
        ]),
        ("test_utils.py", "Utility helper", [
            ("check-deps", "Verifica dipendenze"),
            ("install-deps", "Installa dipendenze"),
            ("list-impls", "Lista implementazioni"),
            ("check-port --port 9000", "Verifica porta"),
            ("kill-port --port 9000", "Uccidi processo su porta"),
            ("cleanup", "Pulisci artefatti"),
        ]),
        ("test_examples.py", "Esempi programmatici", [
            ("", "Esegue tutti gli esempi"),
        ]),
        ("quick_test_implementations.sh", "Script bash rapido", [
            ("", "Test con check dipendenze automatico"),
        ]),
    ]
    
    for cmd, desc, subcmds in commands:
        print(f"{Colors.BOLD}{cmd}{Colors.RESET}")
        print(f"  {desc}\n")
        
        for subcmd, subdesc in subcmds:
            full_cmd = f"python3 {cmd} {subcmd}".strip()
            if cmd.endswith('.sh'):
                full_cmd = f"./{cmd} {subcmd}".strip()
            print(f"  $ {Colors.CYAN}{full_cmd:50s}{Colors.RESET} # {subdesc}")
        print()


def demo_workflow():
    """Demo: Workflow tipico"""
    print_header("6. WORKFLOW TIPICO")
    
    workflow_steps = [
        ("1. Verifica dipendenze", "python3 test_utils.py check-deps"),
        ("2. Lista implementazioni", "python3 test_implementations.py --list"),
        ("3. Test singola implementazione", "python3 test_implementations.py tcp_simple -v"),
        ("4. Test tutte le implementazioni", "python3 test_implementations.py"),
        ("5. Analizza risultati", "cat test_results.json | jq"),
        ("6. Cleanup", "python3 test_utils.py cleanup"),
    ]
    
    print("Workflow standard per testare implementazioni:\n")
    for step, cmd in workflow_steps:
        print(f"{Colors.BOLD}{step}{Colors.RESET}")
        print(f"  $ {Colors.CYAN}{cmd}{Colors.RESET}\n")


def demo_features():
    """Demo: Features principali"""
    print_header("7. FEATURES PRINCIPALI")
    
    features = [
        ("✅ Test Automatici", "Test tutte le implementazioni automaticamente"),
        ("✅ Verifica Connettività", "Controlla che server/client comunicano"),
        ("✅ Report Dettagliati", "JSON + console con colori"),
        ("✅ Parametri Configurabili", "Via test_config.json"),
        ("✅ Uso Programmatico", "Import e uso come libreria"),
        ("✅ Utilità Helper", "Check dipendenze, porte, cleanup"),
        ("✅ Multi-implementazione", "Testa diverse implementazioni"),
        ("✅ Exit Code", "Per integrazione CI/CD"),
    ]
    
    for feature, desc in features:
        print(f"{Colors.GREEN}{feature:25s}{Colors.RESET} {desc}")


def demo_file_structure():
    """Demo: Struttura file"""
    print_header("8. STRUTTURA FILE")
    
    files = [
        ("test_implementations.py", "⭐ Main application - test runner"),
        ("test_utils.py", "🔧 Funzioni utilità"),
        ("test_examples.py", "📚 Esempi uso programmatico"),
        ("test_demo.py", "🎨 Questo file - demo features"),
        ("quick_test_implementations.sh", "🚀 Script bash quick"),
        ("test_config.json", "⚙️ Configurazione"),
        ("TEST_README.md", "📖 README compatto"),
        ("TEST_APP_README.md", "📖 Documentazione completa"),
        ("QUICK_START.py", "⚡ Guida rapida"),
    ]
    
    print("File creati per l'applicazione di test:\n")
    for filename, desc in files:
        print(f"{desc:45s} {Colors.CYAN}{filename}{Colors.RESET}")


def demo_summary():
    """Demo: Riepilogo"""
    print_header("RIEPILOGO")
    
    print(f"{Colors.BOLD}Applicazione di Test per Implementations{Colors.RESET}\n")
    print("Hai a disposizione un'applicazione completa per:")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Testare automaticamente implementazioni client/server")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Verificare connettività e funzionamento")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Generare report dettagliati")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Gestire dipendenze e porte")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Integrare in workflow di sviluppo")
    
    print(f"\n{Colors.CYAN}Quick Start:{Colors.RESET}")
    print(f"  $ python3 test_implementations.py")
    
    print(f"\n{Colors.CYAN}Documentazione:{Colors.RESET}")
    print(f"  - Completa: TEST_APP_README.md")
    print(f"  - Quick: TEST_README.md")
    print(f"  - Guide: QUICK_START.py")
    
    print(f"\n{Colors.GREEN}✓ Applicazione pronta all'uso!{Colors.RESET}\n")


def main():
    """Main entry point"""
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔" + "═" * 68 + "╗")
    print("║" + "DEMO - Test Implementations Application".center(68) + "║")
    print("║" + "Panoramica completa delle funzionalità".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"{Colors.RESET}")
    
    demos = [
        demo_check_dependencies,
        demo_list_implementations,
        demo_check_port,
        demo_load_config,
        demo_test_commands,
        demo_workflow,
        demo_features,
        demo_file_structure,
        demo_summary,
    ]
    
    for demo in demos:
        try:
            demo()
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Demo interrotta{Colors.RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{Colors.RED}Errore: {e}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Per iniziare:{Colors.RESET}")
    print(f"  python3 test_implementations.py --list")
    print(f"  python3 test_implementations.py tcp_simple -v")
    print(f"  python3 test_implementations.py\n")


if __name__ == "__main__":
    main()
