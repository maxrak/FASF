#!/usr/bin/env python3
"""
Utilità per l'applicazione di test implementations
Fornisce funzioni helper comuni
"""

import os
import sys
import json
import socket
from pathlib import Path
from typing import List, Dict, Optional

# Psutil è opzionale
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Verifica se una porta è libera"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def kill_process_on_port(port: int) -> bool:
    """Uccidi tutti i processi in ascolto su una porta"""
    if not HAS_PSUTIL:
        print("Warning: psutil not installed, cannot kill processes")
        print("Install with: pip3 install psutil")
        return False
    
    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.info['connections'] or []:
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['pid']} ({proc.info['name']}) on port {port}")
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def get_free_port(start: int = 9000, end: int = 9100) -> Optional[int]:
    """Trova una porta libera nell'intervallo specificato"""
    for port in range(start, end):
        if check_port_available(port):
            return port
    return None


def load_test_config(config_file: str = "test_config.json") -> Dict:
    """Carica configurazione test"""
    config_path = Path(__file__).parent / config_file
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config from {config_file}: {e}")
        return {}


def check_dependencies() -> Dict[str, bool]:
    """Verifica dipendenze Python installate"""
    dependencies = {
        'scapy': False,
        'pandas': False,
        'numpy': False,
        'psutil': False
    }
    
    for dep in dependencies.keys():
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            dependencies[dep] = False
    
    return dependencies


def install_missing_dependencies(auto_install: bool = False) -> bool:
    """Installa dipendenze mancanti"""
    deps = check_dependencies()
    missing = [dep for dep, installed in deps.items() if not installed]
    
    if not missing:
        print("✓ All dependencies installed")
        return True
    
    print(f"Missing dependencies: {', '.join(missing)}")
    
    if not auto_install:
        response = input("Install missing dependencies? (y/n): ")
        if response.lower() != 'y':
            return False
    
    try:
        import subprocess
        for dep in missing:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        
        print("✓ All dependencies installed successfully")
        return True
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False


def get_implementation_info(impl_path: Path) -> Dict:
    """Estrae informazioni da un'implementazione"""
    info = {
        "name": impl_path.name,
        "path": str(impl_path),
        "has_client": False,
        "has_server": False,
        "has_readme": False,
        "client_lines": 0,
        "server_lines": 0
    }
    
    client_file = impl_path / "client.py"
    server_file = impl_path / "server.py"
    readme_file = impl_path / "README.md"
    
    if client_file.exists():
        info["has_client"] = True
        with open(client_file) as f:
            info["client_lines"] = len(f.readlines())
    
    if server_file.exists():
        info["has_server"] = True
        with open(server_file) as f:
            info["server_lines"] = len(f.readlines())
    
    if readme_file.exists():
        info["has_readme"] = True
    
    return info


def list_implementations(implementations_dir: str = "implementations") -> List[Dict]:
    """Lista tutte le implementazioni con info"""
    impl_dir = Path(__file__).parent / implementations_dir
    
    if not impl_dir.exists():
        return []
    
    implementations = []
    for item in impl_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            info = get_implementation_info(item)
            if info["has_client"] and info["has_server"]:
                implementations.append(info)
    
    return sorted(implementations, key=lambda x: x["name"])


def print_implementations_table(implementations: List[Dict]):
    """Stampa tabella formattata delle implementazioni"""
    if not implementations:
        print("No implementations found")
        return
    
    print("\n┌" + "─" * 70 + "┐")
    print("│{:^70}│".format("AVAILABLE IMPLEMENTATIONS"))
    print("├" + "─" * 20 + "┬" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 17 + "┤")
    print("│{:^20}│{:^10}│{:^10}│{:^10}│{:^17}│".format(
        "Name", "Client", "Server", "README", "Lines (C/S)"
    ))
    print("├" + "─" * 20 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 17 + "┤")
    
    for impl in implementations:
        client_status = "✓" if impl["has_client"] else "✗"
        server_status = "✓" if impl["has_server"] else "✗"
        readme_status = "✓" if impl["has_readme"] else "✗"
        lines = f"{impl['client_lines']}/{impl['server_lines']}"
        
        print("│{:<20}│{:^10}│{:^10}│{:^10}│{:^17}│".format(
            impl["name"][:20], client_status, server_status, readme_status, lines
        ))
    
    print("└" + "─" * 20 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 17 + "┘\n")


def cleanup_test_artifacts():
    """Pulisci artefatti di test"""
    artifacts = [
        "test_results.json",
        "__pycache__",
        "*.pyc",
        ".pytest_cache"
    ]
    
    base_path = Path(__file__).parent
    
    for pattern in artifacts:
        for file in base_path.glob(pattern):
            try:
                if file.is_file():
                    file.unlink()
                    print(f"Removed: {file}")
                elif file.is_dir():
                    import shutil
                    shutil.rmtree(file)
                    print(f"Removed directory: {file}")
            except Exception as e:
                print(f"Could not remove {file}: {e}")


def main():
    """CLI per utilità"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test utilities")
    parser.add_argument('command', choices=[
        'check-deps', 'install-deps', 'list-impls',
        'check-port', 'kill-port', 'cleanup'
    ])
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--auto', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'check-deps':
        deps = check_dependencies()
        print("\nDependencies:")
        for dep, installed in deps.items():
            status = "✓ installed" if installed else "✗ missing"
            print(f"  {dep}: {status}")
    
    elif args.command == 'install-deps':
        install_missing_dependencies(args.auto)
    
    elif args.command == 'list-impls':
        impls = list_implementations()
        print_implementations_table(impls)
    
    elif args.command == 'check-port':
        available = check_port_available(args.port)
        status = "available" if available else "in use"
        print(f"Port {args.port}: {status}")
    
    elif args.command == 'kill-port':
        killed = kill_process_on_port(args.port)
        if killed:
            print(f"✓ Killed process on port {args.port}")
        else:
            print(f"No process found on port {args.port}")
    
    elif args.command == 'cleanup':
        cleanup_test_artifacts()
        print("✓ Cleanup complete")


if __name__ == "__main__":
    main()
