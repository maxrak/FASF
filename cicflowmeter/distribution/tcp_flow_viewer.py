#!/usr/bin/env python3
import socket
import json

HOST = "127.0.0.1"
PORT = 9099

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connesso a {HOST}:{PORT}")

        buffer = b""

        while True:
            data = s.recv(4096)
            if not data:
                print("Connessione chiusa dal server.")
                break

            buffer += data

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()

                if not line:
                    continue

                try:
                    event = json.loads(line.decode("utf-8"))
                    print(json.dumps(event, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print("Riga non JSON:", line.decode("utf-8", errors="replace"))

if __name__ == "__main__":
    main()
