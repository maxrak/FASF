#!/usr/bin/env python3
import socket
import json
from datetime import datetime, timezone

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
                    received_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
                    event = json.loads(line.decode("utf-8"))

                    # Timestamp locale del viewer: momento di ricezione/parsing del JSON
                    event["_viewer_received_at"] = received_at

                    print(json.dumps(event, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    received_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
                    print(f"[{received_at}] Riga non JSON:", line.decode("utf-8", errors="replace"))

if __name__ == "__main__":
    main()
