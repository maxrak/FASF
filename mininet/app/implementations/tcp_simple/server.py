#!/usr/bin/env python3
"""
Server TCP semplice usando socket nativi Python
Più affidabile di scapy per gestire l'handshake TCP
"""

import socket
import threading
import sys

SERVER_PORT = 9000
BUFFER_SIZE = 65535


def handle_client(client_socket, client_address):
    """Gestisce un singolo client"""
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break
            # Echo back (ACK implicito nel TCP stack)
            # Non serve rispondere, basta ricevere
    except Exception as e:
        pass
    finally:
        # Chiusura corretta TCP con FIN
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            client_socket.close()
        except:
            pass


def start_server(port=SERVER_PORT):
    """Avvia il server TCP"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(('0.0.0.0', port))
        server.listen(100)  # Backlog di 100 connessioni
        print(f"[+] Server TCP in ascolto su porta {port}")
        
        while True:
            client_socket, client_address = server.accept()
            # Gestisci ogni client in un thread separato
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
            
    except Exception as e:
        print(f"[!] Errore server: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SERVER_PORT
    start_server(port)
