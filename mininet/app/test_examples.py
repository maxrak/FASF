#!/usr/bin/env python3
"""
Esempio di uso programmatico del test framework

Mostra come:
- Importare e usare il test framework
- Customizzare parametri
- Processare risultati
- Creare test personalizzati
"""

import sys
from pathlib import Path

# Aggiungi path per import
sys.path.insert(0, str(Path(__file__).parent))

from test_implementations import (
    ImplementationTester,
    TestRunner,
    Colors
)


def test_custom_parameters():
    """Test con parametri personalizzati"""
    
    print(f"{Colors.BOLD}=== Test con Parametri Personalizzati ==={Colors.RESET}\n")
    
    # Crea tester con parametri custom
    impl_path = Path(__file__).parent / "implementations" / "tcp_simple"
    tester = ImplementationTester("tcp_simple", impl_path, verbose=True)
    
    # Modifica parametri
    tester.test_port = 8888  # Porta diversa
    tester.test_duration = 10  # Durata più lunga
    
    print(f"Test con porta: {tester.test_port}, durata: {tester.test_duration}s\n")
    
    # Esegui test
    result = tester.run_test()
    
    # Processa risultato
    if result["success"]:
        print(f"\n{Colors.GREEN}✓ Test completato con successo{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}✗ Test fallito: {result['error']}{Colors.RESET}")
    
    return result


def test_selective_implementations():
    """Testa solo implementazioni specifiche"""
    
    print(f"\n{Colors.BOLD}=== Test Selettivo ==={Colors.RESET}\n")
    
    runner = TestRunner(verbose=False)
    
    # Lista implementazioni da testare
    implementations_to_test = ["tcp_simple", "scapy_burst"]
    
    for impl_name in implementations_to_test:
        impl_path = runner.implementations_dir / impl_name
        
        if impl_path.exists():
            print(f"Testing {impl_name}...")
            result = runner.test_implementation(impl_name, impl_path)
            runner.results.append(result)
        else:
            print(f"{Colors.YELLOW}⚠ {impl_name} non trovata{Colors.RESET}")
    
    # Stampa riepilogo
    runner.print_summary()
    
    return runner.results


def analyze_results():
    """Analizza risultati salvati"""
    
    print(f"\n{Colors.BOLD}=== Analisi Risultati ==={Colors.RESET}\n")
    
    import json
    results_file = Path(__file__).parent / "test_results.json"
    
    if not results_file.exists():
        print(f"{Colors.YELLOW}Nessun file risultati trovato{Colors.RESET}")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    print(f"Timestamp: {data['timestamp']}")
    print(f"Totale: {data['total']}, Passati: {data['passed']}, Falliti: {data['failed']}\n")
    
    # Analizza dettagli
    for result in data["results"]:
        name = result["name"]
        success = result["success"]
        
        status = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
        print(f"{status} {name}")
        
        if not success:
            print(f"  Errore: {result.get('error', 'N/A')}")
            
            # Mostra stage fallito
            for stage, passed in result["stages"].items():
                if not passed:
                    print(f"  Stage fallito: {stage}")


def custom_test_logic():
    """Test con logica personalizzata"""
    
    print(f"\n{Colors.BOLD}=== Test con Logica Personalizzata ==={Colors.RESET}\n")
    
    # Crea un tester custom
    class CustomTester(ImplementationTester):
        """Tester con logica aggiuntiva"""
        
        def check_performance(self):
            """Verifica performance aggiuntive"""
            # Qui potresti aggiungere check su latenza, throughput, etc.
            self.log("Verifica performance...", "INFO")
            return True
        
        def run_test(self):
            """Override con check aggiuntivi"""
            result = super().run_test()
            
            if result["success"]:
                # Aggiungi check performance
                result["performance_ok"] = self.check_performance()
            
            return result
    
    # Usa custom tester
    impl_path = Path(__file__).parent / "implementations" / "tcp_simple"
    tester = CustomTester("tcp_simple_custom", impl_path, verbose=True)
    
    result = tester.run_test()
    
    print(f"\nPerformance OK: {result.get('performance_ok', False)}")
    
    return result


def main():
    """Esegue tutti gli esempi"""
    
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}Esempi di Uso Programmatico{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    examples = [
        ("Parametri personalizzati", test_custom_parameters),
        ("Test selettivo", test_selective_implementations),
        ("Analisi risultati", analyze_results),
        ("Logica personalizzata", custom_test_logic)
    ]
    
    for name, func in examples:
        try:
            print(f"\n{Colors.BLUE}► {name}{Colors.RESET}")
            func()
        except Exception as e:
            print(f"{Colors.RED}Errore in {name}: {e}{Colors.RESET}")
        
        print("\n" + "─" * 60)
    
    print(f"\n{Colors.GREEN}Esempi completati!{Colors.RESET}")


if __name__ == "__main__":
    main()
