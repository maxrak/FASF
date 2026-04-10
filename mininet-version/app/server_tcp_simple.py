#!/usr/bin/env python3
"""Server TCP semplice che risponde su porta 9000 - per test"""
import socket
import threading

SERVER_PORT = 9000

def handle_client(conn, addr):
    """Gestisce connessione client"""
    print(f"[+] Connessione da {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            # Echo back
            conn.sendall(data)
    except:
        pass
    finally:
        conn.close()
        print(f"[-] Chiusura connessione da {addr}")

def start_server():
    """Avvia server TCP"""
    print(f"[+] Server TCP in ascolto su porta {SERVER_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', SERVER_PORT))
    sock.listen(10)
    
    while True:
        conn, addr = sock.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == '__main__':
    start_server()
