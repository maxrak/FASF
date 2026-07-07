#!/usr/bin/env python3
import argparse
import csv
import json
import os
import socket
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9099
DEFAULT_OUT = "flow_snapshots.csv"


def now_epoch_ms():
    return int(time.time() * 1000)


def open_socket(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def ensure_writer(csv_file, header, writer_state):
    """
    Crea/sostituisce il writer se l'header cambia.
    Il file CSV resta append-only, ma se cambiano le feature durante l'esecuzione
    viene scritta una nuova intestazione.
    """
    if writer_state.get("header") != header:
        writer = csv.DictWriter(csv_file, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        csv_file.flush()
        writer_state["header"] = header
        writer_state["writer"] = writer

    return writer_state["writer"]


def snapshot_rows(event, received_at_ms):
    flows = event.get("flows", [])
    if not isinstance(flows, list) or not flows:
        return [], None

    # Feature compatte: usa l'ordine del primo flow ricevuto dal JSON.
    # Python 3.7+ conserva l'ordine delle chiavi.
    feature_names = list(flows[0].keys())
    header = ["snapshot_received_at_ms"] + feature_names

    rows = []
    for flow in flows:
        if not isinstance(flow, dict):
            continue

        row = {"snapshot_received_at_ms": received_at_ms}
        for name in feature_names:
            row[name] = flow.get(name, "")
        rows.append(row)

    return rows, header


def main():
    parser = argparse.ArgumentParser(
        description="TCP CICFlowMeter snapshot viewer/logger: salva snapshots NDJSON su CSV compatto."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host exporter TCP, default {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Porta exporter TCP, default {DEFAULT_PORT}")
    parser.add_argument("-o", "--output", default=DEFAULT_OUT, help=f"File CSV output, default {DEFAULT_OUT}")
    parser.add_argument("--append", action="store_true", help="Appende al CSV esistente invece di sovrascriverlo")
    parser.add_argument("--quiet", action="store_true", help="Non stampa statistiche su stdout")
    args = parser.parse_args()

    mode = "a" if args.append else "w"
    file_exists = os.path.exists(args.output) and os.path.getsize(args.output) > 0

    snapshots = 0
    rows_written = 0
    buffer = b""
    writer_state = {"header": None, "writer": None}

    s = None
    csv_file = None

    try:
        s = open_socket(args.host, args.port)
        csv_file = open(args.output, mode, newline="", encoding="utf-8")

        if not args.quiet:
            print(f"Connesso a {args.host}:{args.port}")
            print(f"Scrivo snapshots su: {args.output}")
            print("Premi Ctrl+C per terminare.")

        # In append mode, non possiamo sapere l'header precedente in modo affidabile
        # senza leggerlo; per semplicità, appena arriva il primo snapshot scriviamo header
        # solo se il file è nuovo/vuoto. Se è già presente, il writer verrà inizializzato
        # senza writeheader.
        if args.append and file_exists:
            writer_state["header"] = "__existing_unknown__"

        while True:
            data = s.recv(65536)
            if not data:
                if not args.quiet:
                    print("Connessione chiusa dal server.")
                break

            buffer += data

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()

                if not line:
                    continue

                received_at_ms = now_epoch_ms()

                try:
                    event = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    if not args.quiet:
                        print(f"[{received_at_ms}] Riga non JSON ignorata")
                    continue

                if event.get("type") != "snapshot":
                    # Modalità compatta: ignora flow_update e flow_end.
                    continue

                rows, header = snapshot_rows(event, received_at_ms)
                if not rows:
                    continue

                if args.append and file_exists and writer_state["header"] == "__existing_unknown__":
                    writer = csv.DictWriter(csv_file, fieldnames=header, extrasaction="ignore", lineterminator="\n")
                    writer_state["header"] = header
                    writer_state["writer"] = writer
                else:
                    writer = ensure_writer(csv_file, header, writer_state)

                writer.writerows(rows)
                csv_file.flush()

                snapshots += 1
                rows_written += len(rows)

                if not args.quiet:
                    print(f"[{received_at_ms}] snapshot={snapshots} flows={len(rows)} rows_total={rows_written}")

    except KeyboardInterrupt:
        if not args.quiet:
            print("\nCtrl+C ricevuto: chiusura ordinata...")
    finally:
        if csv_file is not None:
            try:
                csv_file.flush()
                csv_file.close()
            except Exception:
                pass

        if s is not None:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                s.close()
            except Exception:
                pass

        if not args.quiet:
            print(f"Terminato. snapshots={snapshots}, righe_csv={rows_written}")


if __name__ == "__main__":
    main()
