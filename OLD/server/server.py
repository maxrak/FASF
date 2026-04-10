import socket
import threading

HOST = "0.0.0.0"
PORT = 9000

def handle_client(conn, addr):
    print(f"[+] Connessione da {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            # Simula traffico backward (echo)
            conn.sendall(b"ACK")

    except Exception as e:
        print(f"[!] Errore: {e}")
    finally:
        conn.close()
        print(f"[-] Connessione chiusa {addr}")


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        print(f"[+] Server in ascolto su {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()


if __name__ == "__main__":
    start_server()