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

LONG_NAMES = {
    "flowId": "Flow ID",
    "srcIP": "Src IP",
    "srcPort": "Src Port",
    "dstIP": "Dst IP",
    "dstPort": "Dst Port",
    "protocol": "Protocol",
    "timestamp": "Timestamp",
    "flowDuration": "Flow Duration",
    "totalFwdPackets": "Total Fwd Packet",
    "totalBackwardPackets": "Total Bwd packets",
    "totalLengthOfFwdPackets": "Total Length of Fwd Packet",
    "totalLengthOfBwdPackets": "Total Length of Bwd Packet",
    "fwdPacketLengthMax": "Fwd Packet Length Max",
    "fwdPacketLengthMin": "Fwd Packet Length Min",
    "fwdPacketLengthMean": "Fwd Packet Length Mean",
    "fwdPacketLengthStd": "Fwd Packet Length Std",
    "bwdPacketLengthMax": "Bwd Packet Length Max",
    "bwdPacketLengthMin": "Bwd Packet Length Min",
    "bwdPacketLengthMean": "Bwd Packet Length Mean",
    "bwdPacketLengthStd": "Bwd Packet Length Std",
    "flowBytesPerSec": "Flow Bytes/s",
    "flowPacketsPerSec": "Flow Packets/s",
    "flowIATMean": "Flow IAT Mean",
    "flowIATStd": "Flow IAT Std",
    "flowIATMax": "Flow IAT Max",
    "flowIATMin": "Flow IAT Min",
    "fwdIATTotal": "Fwd IAT Total",
    "fwdIATMean": "Fwd IAT Mean",
    "fwdIATStd": "Fwd IAT Std",
    "fwdIATMax": "Fwd IAT Max",
    "fwdIATMin": "Fwd IAT Min",
    "bwdIATTotal": "Bwd IAT Total",
    "bwdIATMean": "Bwd IAT Mean",
    "bwdIATStd": "Bwd IAT Std",
    "bwdIATMax": "Bwd IAT Max",
    "bwdIATMin": "Bwd IAT Min",
    "fwdPSHFlags": "Fwd PSH Flags",
    "bwdPSHFlags": "Bwd PSH Flags",
    "fwdURGFlags": "Fwd URG Flags",
    "bwdURGFlags": "Bwd URG Flags",
    "fwdRSTFlags": "Fwd RST Flags",
    "bwdRSTFlags": "Bwd RST Flags",
    "fwdHeaderLength": "Fwd Header Length",
    "bwdHeaderLength": "Bwd Header Length",
    "fwdPacketsPerSec": "Fwd Packets/s",
    "bwdPacketsPerSec": "Bwd Packets/s",
    "minPacketLength": "Packet Length Min",
    "maxPacketLength": "Packet Length Max",
    "packetLengthMean": "Packet Length Mean",
    "packetLengthStd": "Packet Length Std",
    "packetLengthVariance": "Packet Length Variance",
    "finFlagCount": "FIN Flag Count",
    "synFlagCount": "SYN Flag Count",
    "rstFlagCount": "RST Flag Count",
    "pshFlagCount": "PSH Flag Count",
    "ackFlagCount": "ACK Flag Count",
    "urgFlagCount": "URG Flag Count",
    "cwrFlagCount": "CWR Flag Count",
    "eceFlagCount": "ECE Flag Count",
    "downUpRatio": "Down/Up Ratio",
    "averagePacketSize": "Average Packet Size",
    "avgFwdSegmentSize": "Fwd Segment Size Avg",
    "avgBwdSegmentSize": "Bwd Segment Size Avg",
    "fwdAvgBytesPerBulk": "Fwd Bytes/Bulk Avg",
    "fwdAvgPacketsPerBulk": "Fwd Packet/Bulk Avg",
    "fwdAvgBulkRate": "Fwd Bulk Rate Avg",
    "bwdAvgBytesPerBulk": "Bwd Bytes/Bulk Avg",
    "bwdAvgPacketsPerBulk": "Bwd Packet/Bulk Avg",
    "bwdAvgBulkRate": "Bwd Bulk Rate Avg",
    "subflowFwdPackets": "Subflow Fwd Packets",
    "subflowFwdBytes": "Subflow Fwd Bytes",
    "subflowBwdPackets": "Subflow Bwd Packets",
    "subflowBwdBytes": "Subflow Bwd Bytes",
    "initWinBytesForward": "FWD Init Win Bytes",
    "initWinBytesBackward": "Bwd Init Win Bytes",
    "actDataPktForward": "Fwd Act Data Pkts",
    "actDataPktBackward": "Bwd Act Data Pkts",
    "minSegSizeForward": "Fwd Seg Size Min",
    "minSegSizeBackward": "Bwd Seg Size Min",
    "activeMean": "Active Mean",
    "activeStd": "Active Std",
    "activeMax": "Active Max",
    "activeMin": "Active Min",
    "idleMean": "Idle Mean",
    "idleStd": "Idle Std",
    "idleMax": "Idle Max",
    "idleMin": "Idle Min",
    "icmpCode": "ICMP Code",
    "icmpType": "ICMP Type",
    "fwdTcpRetransmissions": "Fwd TCP Retrans. Count",
    "bwdTcpRetransmissions": "Bwd TCP Retrans. Count",
    "totalTcpRetransmissions": "Total TCP Retrans. Count",
    "cumulativeConnectionDuration": "Total Connection Flow Time",
    "label": "Label",
}

def now_epoch_ms():
    return int(time.time() * 1000)

def to_long_name(name):
    return LONG_NAMES.get(name, name)

def open_socket(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s

def ensure_writer(csv_file, header, writer_state, write_header):
    if writer_state.get("header") != header:
        writer = csv.DictWriter(csv_file, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        if write_header:
            writer.writeheader()
            csv_file.flush()
        writer_state["header"] = header
        writer_state["writer"] = writer
    return writer_state["writer"]

def snapshot_rows(event, received_at_ms):
    flows = event.get("flows", [])
    if not isinstance(flows, list) or not flows:
        return [], None

    json_names = list(flows[0].keys())
    csv_names = [to_long_name(n) for n in json_names]
    header = ["Snapshot Received At Ms"] + csv_names

    rows = []
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        row = {"Snapshot Received At Ms": received_at_ms}
        for json_name, csv_name in zip(json_names, csv_names):
            row[csv_name] = flow.get(json_name, "")
        rows.append(row)

    return rows, header

def main():
    parser = argparse.ArgumentParser(description="Salva snapshot CICFlowMeter NDJSON su CSV con nomi lunghi.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-o", "--output", default=DEFAULT_OUT)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    mode = "a" if args.append else "w"
    file_exists = os.path.exists(args.output) and os.path.getsize(args.output) > 0
    write_header = not (args.append and file_exists)

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
                    continue

                rows, header = snapshot_rows(event, received_at_ms)
                if not rows:
                    continue

                writer = ensure_writer(csv_file, header, writer_state, write_header)
                writer.writerows(rows)
                csv_file.flush()
                write_header = True

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
