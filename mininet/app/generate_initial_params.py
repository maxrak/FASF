#!/usr/bin/env python3
"""
generate_initial_params.py

Genera file di configurazione iniziali per client_scapy_burst_optimized.py
per ogni flow nel CSV CICFlowMeter.

Uso:
    python generate_initial_params.py input.csv output_dir

Note:
- Il CSV deve contenere almeno una riga di flow.
- Le feature temporali CICFlowMeter sono tipicamente in microsecondi.
- Genera un file .config per ogni riga, nominato: basename_sourceip.config
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def choose_column(row: pd.Series, candidates: list[str], default: float = 0.0) -> float:
    for name in candidates:
        if name in row.index:
            return safe_float(row[name], default)
    return default


def derive_pkt_size_scale(fwd_pkt_len_mean: float) -> float:
    """
    Scala iniziale centrata su 1.0, con piccoli aggiustamenti
    per flow molto piccoli o molto grandi.
    """
    if fwd_pkt_len_mean <= 0:
        return 1.0
    if fwd_pkt_len_mean < 80:
        return 0.9
    if fwd_pkt_len_mean > 800:
        return 1.1
    return 1.0


def derive_pkt_size_sigma(fwd_pkt_len_mean: float, fwd_pkt_len_std: float) -> float:
    """
    Usa il coefficiente di variazione std/mean per stimare
    quanto rumorosa debba essere la distribuzione.
    """
    if fwd_pkt_len_mean <= 1e-9:
        return 0.8

    cv = fwd_pkt_len_std / fwd_pkt_len_mean

    if cv < 0.10:
        sigma = 0.55
    elif cv < 0.25:
        sigma = 0.70
    elif cv < 0.50:
        sigma = 0.85
    elif cv < 0.80:
        sigma = 1.00
    else:
        sigma = 1.20

    return clamp(sigma, 0.5, 1.5)


def derive_burst_size_p(active_mean_us: float, idle_mean_us: float, total_fwd_packets: float) -> float:
    """
    p alto -> burst piccoli
    p basso -> burst grandi

    Euristica:
    - se active << idle: traffico sparso -> burst piccoli -> p più alto
    - se active ~ idle o active > idle: traffico più denso -> p più basso
    - aggiusta leggermente in base al numero di pacchetti forward
    """
    active_s = max(active_mean_us / 1_000_000.0, 0.0)
    idle_s = max(idle_mean_us / 1_000_000.0, 0.0)

    if idle_s <= 1e-9 and active_s <= 1e-9:
        base = 0.35
    else:
        ratio = active_s / max(idle_s, 1e-6)

        if ratio < 0.25:
            base = 0.50
        elif ratio < 0.60:
            base = 0.42
        elif ratio < 1.20:
            base = 0.35
        elif ratio < 2.50:
            base = 0.28
        else:
            base = 0.22

    if total_fwd_packets > 1000:
        base -= 0.05
    elif total_fwd_packets < 20:
        base += 0.05

    return clamp(base, 0.1, 0.9)


def derive_idle_scale(idle_mean_us: float) -> float:
    """
    idle_scale in secondi, ma leggermente ridotto rispetto al target
    per evitare un primo replay troppo lento.
    """
    idle_s = max(idle_mean_us / 1_000_000.0, 0.0)

    if idle_s <= 0:
        return 0.10

    scale = idle_s * 0.5
    return clamp(scale, 0.01, 2.0)


def derive_iat_rate(flow_iat_mean_us: float) -> float:
    """
    iat_rate ≈ 1 / Flow IAT Mean(secondi)
    """
    iat_s = flow_iat_mean_us / 1_000_000.0
    if iat_s <= 1e-9:
        return 120.0

    rate = 1.0 / iat_s
    return clamp(rate, 1.0, 10_000.0)


def build_params_from_row(row: pd.Series) -> dict[str, float]:
    fwd_pkt_len_mean = choose_column(row, ["Fwd Packet Length Mean"], 120.0)
    fwd_pkt_len_std = choose_column(row, ["Fwd Packet Length Std"], 20.0)
    flow_iat_mean_us = choose_column(row, ["Flow IAT Mean"], 10_000.0)
    idle_mean_us = choose_column(row, ["Idle Mean"], 200_000.0)
    active_mean_us = choose_column(row, ["Active Mean"], 100_000.0)
    total_fwd_packets = choose_column(row, ["Total Fwd Packets", "total Fwd Packet"], 50.0)

    params = {
        "pkt_size_scale": round(derive_pkt_size_scale(fwd_pkt_len_mean), 4),
        "pkt_size_sigma": round(derive_pkt_size_sigma(fwd_pkt_len_mean, fwd_pkt_len_std), 4),
        "burst_size_p": round(derive_burst_size_p(active_mean_us, idle_mean_us, total_fwd_packets), 4),
        "idle_scale": round(derive_idle_scale(idle_mean_us), 4),
        "iat_rate": round(derive_iat_rate(flow_iat_mean_us), 4),
    }

    return params


def get_source_ip(row: pd.Series) -> str:
    """Estrae l'IP sorgente dalla riga del CSV."""
    candidates = ["Src IP", "Source IP", "Src_IP", "source_ip"]
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            return str(row[col]).strip()
    return "unknown"


def get_dest_ip(row: pd.Series) -> str:
    """Estrae l'IP di destinazione dalla riga del CSV."""
    candidates = ["Dst IP", "Destination IP", "Dst_IP", "dest_ip"]
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            return str(row[col]).strip()
    return "unknown"


def get_source_port(row: pd.Series) -> str:
    """Estrae la porta sorgente dalla riga del CSV."""
    candidates = ["Src Port", "Source Port", "Src_Port", "source_port"]
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            return str(int(row[col])).strip()
    return "0"


def get_dest_port(row: pd.Series) -> str:
    """Estrae la porta destinazione dalla riga del CSV."""
    candidates = ["Dst Port", "Destination Port", "Dst_Port", "dest_port"]
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            return str(int(row[col])).strip()
    return "0"


def sanitize_filename(name: str) -> str:
    """Rimuove caratteri non validi per i nomi di file."""
    return name.replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_").replace(".", "_")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera file di configurazione per ogni flow CICFlowMeter."
    )
    parser.add_argument("input_csv", help="CSV con uno o più flow CICFlowMeter")
    parser.add_argument("output_dir", help="Directory dove salvare i file .config")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"CSV non trovato: {input_path}")

    # Nome base del flusso dal nome del file CSV (senza estensione)
    base_name = input_path.stem

    df = pd.read_csv(input_path)

    if df.empty:
        raise ValueError("Il CSV è vuoto.")

    # Crea la directory di output se non esiste
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[+] Elaborazione di {len(df)} flow da {input_path.name}")
    print(f"[+] Nome base: {base_name}")
    print(f"[+] Directory output: {output_dir}")
    print()

    # Elabora ogni riga del CSV
    for idx, row in df.iterrows():
        # Estrai IP sorgente e destinazione
        source_ip = get_source_ip(row)
        dest_ip = get_dest_ip(row)
        source_port = get_source_port(row)
        dest_port = get_dest_port(row)
        
        source_ip_safe = sanitize_filename(source_ip)
        dest_ip_safe = sanitize_filename(dest_ip)

        # Genera nome file: basename_sourceip_sourceport_destip_destport.config
        # Questo permette di distinguere flussi con stessa coppia IP ma porte diverse
        config_filename = f"{base_name}_{source_ip_safe}_{source_port}_{dest_ip_safe}_{dest_port}.config"
        output_path = output_dir / config_filename

        # Genera parametri dalla riga
        params = build_params_from_row(row)

        # Salva file
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)

        print(f"[{idx + 1}/{len(df)}] {config_filename}")
        print(f"        Src IP: {source_ip} -> Dst IP: {dest_ip}")
        print(f"        Params: {params}")

    print()
    print(f"[✓] Generati {len(df)} file di configurazione in {output_dir}")


if __name__ == "__main__":
    main()