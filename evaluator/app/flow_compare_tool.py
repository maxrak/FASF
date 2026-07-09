#!/usr/bin/env python3
"""
flow_compare_tool.py

Confronta due CSV di descrizione flussi: originale vs simulato.

Chiave logica del flusso:
    Src IP, Src Port, Dst IP, Dst Port

Poiche' i timestamp assoluti non sono confrontabili, lo script NON usa Timestamp
per il matching. Se ci sono piu' flussi con la stessa quadrupla, li abbina
all'interno dello stesso gruppo minimizzando una distanza normalizzata sulle
feature numeriche selezionate.

Output principali:
    - matched_flows.csv: coppie originale/simulato abbinate
    - missing_original_flows.csv: flussi originali non riprodotti
    - extra_simulated_flows.csv: flussi simulati non presenti nell'originale
    - feature_error_summary.csv: errori aggregati per feature
    - cell_differences.csv: differenze feature-per-feature per ogni coppia
    - suggestions.md: indicazioni pratiche su dove intervenire nel simulatore
    - report.html: report HTML sintetico interattivo

Esempio:
    python flow_compare_tool.py original.csv simulated.csv -o comparison_report
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover
    linear_sum_assignment = None

KEY_COLS_DEFAULT = ["Src IP", "Src Port", "Dst IP", "Dst Port"]
EXCLUDE_DEFAULT = {"Flow ID", "Timestamp"}
EPS = 1e-12

FEATURE_GROUPS = {
    "identita/topologia": ["Protocol"],
    "durata/timing": ["Duration", "IAT", "Active", "Idle"],
    "conteggi pacchetti": ["Total Fwd Packet", "Total Bwd packets", "Packet", "Subflow"],
    "dimensioni/lunghezze": ["Length", "Header", "Segment", "Bytes/Bulk", "Bulk Rate"],
    "throughput/rate": ["Bytes/s", "Packets/s", "Rate"],
    "TCP/flag/window": ["Flag", "Window", "TCP", "PSH", "URG", "ECE", "CWR", "ACK", "RST", "SYN", "FIN"],
}


def read_csv(path: str, sep: str | None = None) -> pd.DataFrame:
    if sep is None:
        return pd.read_csv(path, sep=None, engine="python")
    return pd.read_csv(path, sep=sep)


def normalize_keys(df: pd.DataFrame, key_cols: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    for c in key_cols:
        if c not in out.columns:
            raise ValueError(f"Colonna chiave mancante: {c}")
        if "IP" in c:
            out[c] = out[c].astype(str).str.strip()
        else:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64").astype(str)
    return out


def common_numeric_features(
    original: pd.DataFrame,
    simulated: pd.DataFrame,
    exclude_cols: Iterable[str],
    key_cols: Sequence[str],
) -> List[str]:
    exclude = set(exclude_cols).union(key_cols)
    common = [c for c in original.columns if c in simulated.columns and c not in exclude]
    features = []
    for c in common:
        o = pd.to_numeric(original[c], errors="coerce")
        s = pd.to_numeric(simulated[c], errors="coerce")
        if o.notna().any() or s.notna().any():
            features.append(c)
    return features


def infer_group(feature: str) -> str:
    f = feature.lower()
    for group, needles in FEATURE_GROUPS.items():
        for n in needles:
            if n.lower() in f:
                return group
    return "altro"


def robust_scale(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 1.0
    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    if abs(iqr) > EPS:
        return float(iqr)
    std = np.std(values)
    if std > EPS:
        return float(std)
    mx = np.max(np.abs(values))
    return float(mx) if mx > EPS else 1.0


def build_cost_matrix(
    o_group: pd.DataFrame,
    s_group: pd.DataFrame,
    features: Sequence[str],
    weights: Dict[str, float],
) -> np.ndarray:
    n, m = len(o_group), len(s_group)
    cost = np.zeros((n, m), dtype=float)
    used = 0

    for f in features:
        ov = pd.to_numeric(o_group[f], errors="coerce").to_numpy(dtype=float)
        sv = pd.to_numeric(s_group[f], errors="coerce").to_numpy(dtype=float)
        joined = np.concatenate([ov, sv])
        scale = robust_scale(joined)
        w = weights.get(f, 1.0)

        diff = np.abs(ov[:, None] - sv[None, :]) / scale
        both_nan = np.isnan(ov[:, None]) & np.isnan(sv[None, :])
        one_nan = np.isnan(ov[:, None]) ^ np.isnan(sv[None, :])
        diff = np.where(both_nan, 0.0, diff)
        diff = np.where(one_nan, 10.0, diff)
        diff = np.nan_to_num(diff, nan=10.0, posinf=10.0, neginf=10.0)
        cost += w * diff
        used += 1

    if used == 0:
        return cost
    return cost / used


def greedy_assignment(cost: np.ndarray) -> List[Tuple[int, int]]:
    pairs = []
    used_i, used_j = set(), set()
    flat = [(cost[i, j], i, j) for i in range(cost.shape[0]) for j in range(cost.shape[1])]
    for _, i, j in sorted(flat):
        if i not in used_i and j not in used_j:
            pairs.append((i, j))
            used_i.add(i)
            used_j.add(j)
    return pairs


def assign_pairs(cost: np.ndarray) -> List[Tuple[int, int]]:
    if cost.size == 0:
        return []
    if linear_sum_assignment is not None:
        rows, cols = linear_sum_assignment(cost)
        return list(zip(rows.tolist(), cols.tolist()))
    return greedy_assignment(cost)


def compare_cells(o_row: pd.Series, s_row: pd.Series, features: Sequence[str]) -> List[dict]:
    rows = []
    for f in features:
        ov = pd.to_numeric(pd.Series([o_row[f]]), errors="coerce").iloc[0]
        sv = pd.to_numeric(pd.Series([s_row[f]]), errors="coerce").iloc[0]
        abs_err = np.nan if pd.isna(ov) or pd.isna(sv) else abs(float(ov) - float(sv))
        signed_err = np.nan if pd.isna(ov) or pd.isna(sv) else float(sv) - float(ov)
        rel_err = np.nan
        if not pd.isna(abs_err) and abs(float(ov)) > EPS:
            rel_err = abs_err / abs(float(ov))
        rows.append(
            {
                "feature": f,
                "group": infer_group(f),
                "original_value": ov,
                "simulated_value": sv,
                "signed_error_sim_minus_orig": signed_err,
                "absolute_error": abs_err,
                "relative_error": rel_err,
            }
        )
    return rows


def summarize_feature_errors(cell_df: pd.DataFrame) -> pd.DataFrame:
    if cell_df.empty:
        return pd.DataFrame()
    g = cell_df.groupby(["feature", "group"], dropna=False)
    out = g.agg(
        matched_pairs=("absolute_error", "count"),
        mae=("absolute_error", "mean"),
        rmse=("absolute_error", lambda x: math.sqrt(np.nanmean(np.square(x))) if len(x) else np.nan),
        median_abs_error=("absolute_error", "median"),
        max_abs_error=("absolute_error", "max"),
        mean_relative_error=("relative_error", "mean"),
        median_relative_error=("relative_error", "median"),
        mean_signed_error=("signed_error_sim_minus_orig", "mean"),
    ).reset_index()
    out["mean_relative_error_pct"] = out["mean_relative_error"] * 100
    return out.sort_values(["mean_relative_error", "mae"], ascending=False, na_position="last")


def make_suggestions(summary: pd.DataFrame, missing_count: int, extra_count: int) -> str:
    lines = ["# Suggerimenti per migliorare il simulatore", ""]
    if missing_count:
        lines.append(f"- Priorita' alta: il simulatore non riproduce {missing_count} flussi originali. Verifica le regole di generazione/sessionizzazione e le condizioni di terminazione dei flussi.")
    if extra_count:
        lines.append(f"- Il simulatore genera {extra_count} flussi extra. Controlla duplicazioni, apertura/chiusura connessioni e criteri di aggregazione.")
    if summary.empty:
        lines.append("- Nessuna coppia confrontabile trovata: controlla chiavi, direzione dei flussi e normalizzazione delle porte.")
        return "\n".join(lines) + "\n"

    group_summary = summary.groupby("group").agg(
        n_features=("feature", "count"),
        mean_rel=("mean_relative_error", "mean"),
        max_rel=("mean_relative_error", "max"),
        mean_mae=("mae", "mean"),
    ).reset_index().sort_values(["mean_rel", "mean_mae"], ascending=False, na_position="last")

    lines += ["", "## Aree piu' critiche", ""]
    for _, r in group_summary.head(5).iterrows():
        pct = "n/d" if pd.isna(r["mean_rel"]) else f"{r['mean_rel']*100:.2f}%"
        lines.append(f"- {r['group']}: errore relativo medio {pct} su {int(r['n_features'])} feature.")

    lines += ["", "## Feature peggiori", ""]
    for _, r in summary.head(10).iterrows():
        pct = "n/d" if pd.isna(r["mean_relative_error_pct"]) else f"{r['mean_relative_error_pct']:.2f}%"
        bias = r["mean_signed_error"]
        direction = "sovrastima" if pd.notna(bias) and bias > 0 else "sottostima" if pd.notna(bias) and bias < 0 else "nessun bias medio"
        lines.append(f"- {r['feature']} ({r['group']}): errore relativo medio {pct}, {direction}.")

    lines += ["", "## Lettura diagnostica", ""]
    lines.append("- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.")
    lines.append("- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.")
    lines.append("- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.")
    lines.append("- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.")
    return "\n".join(lines) + "\n"


def write_html_report(out_dir: Path, matched: pd.DataFrame, missing: pd.DataFrame, extra: pd.DataFrame, summary: pd.DataFrame, cell_df: pd.DataFrame, key_cols: List[str]) -> None:
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Report di Confronto Flussi</title>",
        "<link href='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css' rel='stylesheet'>",
        "<link href='https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css' rel='stylesheet'>",
        "<style>",
        "body { margin: 20px; font-family: system-ui, -apple-system, sans-serif; background-color: #f8f9fa; }",
        ".container-fluid { background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }",
        ".table-wrapper { margin-top: 20px; padding-top: 20px; }",
        "table.dataTable thead th { background-color: #343a40; color: white; }",
        ".nav-tabs .nav-link { font-weight: 600; color: #495057; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='container-fluid'>",
        "<h2 class='mb-4 text-primary'>Report Analitico di Confronto Flussi</h2>",
        f"<div class='alert alert-info'>Coppie abbinate: <b>{len(matched)}</b> | Flussi originali mancanti: <b>{len(missing)}</b> | Flussi simulati extra: <b>{len(extra)}</b></div>"
    ]

    # Tabs navigation
    html.extend([
        "<ul class='nav nav-tabs' id='reportTabs' role='tablist'>",
        "<li class='nav-item' role='presentation'><button class='nav-link active' id='summary-tab' data-bs-toggle='tab' data-bs-target='#summary' type='button' role='tab'>Media Errori (Feature)</button></li>",
        "<li class='nav-item' role='presentation'><button class='nav-link' id='flow-tab' data-bs-toggle='tab' data-bs-target='#flow' type='button' role='tab'>Dettaglio Flusso per Flusso</button></li>",
        "<li class='nav-item' role='presentation'><button class='nav-link' id='missing-tab' data-bs-toggle='tab' data-bs-target='#missing' type='button' role='tab'>Flussi Mancanti</button></li>",
        "<li class='nav-item' role='presentation'><button class='nav-link' id='extra-tab' data-bs-toggle='tab' data-bs-target='#extra' type='button' role='tab'>Flussi Extra</button></li>",
        "</ul>",
        "<div class='tab-content' id='reportTabsContent'>"
    ])

    # TAB 1: Media Errori (Summary)
    html.append("<div class='tab-pane fade show active table-wrapper' id='summary' role='tabpanel'>")
    html.append("<h4 class='mb-3'>Errori Medi Aggregati sulle Feature</h4>")
    if not summary.empty:
        sum_disp = summary[['feature', 'group', 'mae', 'mean_relative_error_pct', 'mean_signed_error']].copy()
        sum_disp = sum_disp.rename(columns={
            'feature': 'Feature', 'group': 'Gruppo', 'mae': 'Errore Assoluto Medio (MAE)',
            'mean_relative_error_pct': 'Errore Relativo Medio (%)', 'mean_signed_error': 'Errore Medio con Segno'
        })
        html.append(sum_disp.to_html(index=False, classes='table table-striped table-hover datatable', float_format="%.4f", na_rep="-"))
    else:
        html.append("<p>Nessuna feature confrontabile trovata.</p>")
    html.append("</div>")

    # TAB 2: Dettaglio Flusso per Flusso
    html.append("<div class='tab-pane fade table-wrapper' id='flow' role='tabpanel'>")
    html.append("<h4 class='mb-3'>Dettaglio Errori per Singolo Flusso</h4>")
    if not cell_df.empty:
        flow_disp = cell_df.copy()
        
        # Genera il nome del flusso unendo le chiavi (es. IP:Port -> IP:Port se si usano le classiche 4 tuple)
        def make_flow_name(r):
            if len(key_cols) == 4:
                return f"{r.get(key_cols[0], '')}:{r.get(key_cols[1], '')} &rarr; {r.get(key_cols[2], '')}:{r.get(key_cols[3], '')}"
            return " | ".join(str(r.get(k, '')) for k in key_cols)
            
        flow_disp['Endpoint Flusso'] = flow_disp.apply(make_flow_name, axis=1)
        flow_disp['relative_error_pct'] = flow_disp['relative_error'] * 100
        
        cols_to_show = ['pair_id', 'Endpoint Flusso', 'feature', 'original_value', 'simulated_value', 'absolute_error', 'relative_error_pct']
        cols_to_show = [c for c in cols_to_show if c in flow_disp.columns]
        
        flow_disp = flow_disp[cols_to_show].rename(columns={
            'pair_id': 'ID Coppia', 'feature': 'Feature',
            'original_value': 'Valore Originale', 'simulated_value': 'Valore Simulato',
            'absolute_error': 'Errore Assoluto', 'relative_error_pct': 'Errore Relativo (%)'
        })
        
        html.append(flow_disp.to_html(index=False, classes='table table-striped table-hover datatable', float_format="%.4f", na_rep="-", escape=False))
    else:
        html.append("<p>Nessun dettaglio disponibile.</p>")
    html.append("</div>")

    # TAB 3: Flussi Mancanti
    html.append("<div class='tab-pane fade table-wrapper' id='missing' role='tabpanel'>")
    html.append("<h4 class='mb-3'>Flussi Originali Non Riprodotti (Primi 1000)</h4>")
    html.append(missing.head(1000).to_html(index=False, classes='table table-striped table-hover datatable') if not missing.empty else "<p>Tutti i flussi originali sono stati abbinati!</p>")
    html.append("</div>")

    # TAB 4: Flussi Extra
    html.append("<div class='tab-pane fade table-wrapper' id='extra' role='tabpanel'>")
    html.append("<h4 class='mb-3'>Flussi Simulati in Eccesso (Primi 1000)</h4>")
    html.append(extra.head(1000).to_html(index=False, classes='table table-striped table-hover datatable') if not extra.empty else "<p>Nessun flusso simulato in eccesso!</p>")
    html.append("</div>")

    # Script JS per attivare i tab e le DataTables
    html.extend([
        "</div>", # Fine tab-content
        "</div>", # Fine container
        "<script src='https://code.jquery.com/jquery-3.7.0.min.js'></script>",
        "<script src='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js'></script>",
        "<script src='https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js'></script>",
        "<script src='https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js'></script>",
        "<script>",
        "$(document).ready(function() {",
        "    $('.datatable').DataTable({",
        "        pageLength: 50,",
        "        language: { url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }",
        "    });",
        "});",
        "</script>",
        "</body></html>"
    ])
    
    (out_dir / "report.html").write_text("\n".join(html), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Confronta CSV di flussi originali e simulati.")
    ap.add_argument("original_csv")
    ap.add_argument("simulated_csv")
    ap.add_argument("-o", "--output-dir", default="flow_comparison_report")
    ap.add_argument("--sep", default=None, help="Separatore CSV. Default: auto-detect.")
    ap.add_argument("--key-cols", nargs=4, default=KEY_COLS_DEFAULT)
    ap.add_argument("--exclude", nargs="*", default=list(EXCLUDE_DEFAULT), help="Colonne da escludere dal confronto/matching.")
    ap.add_argument("--match-features", nargs="*", default=None, help="Feature numeriche da usare per abbinare duplicati della stessa quadrupla. Default: tutte le numeriche comuni.")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original = normalize_keys(read_csv(args.original_csv, args.sep), args.key_cols)
    simulated = normalize_keys(read_csv(args.simulated_csv, args.sep), args.key_cols)

    features = common_numeric_features(original, simulated, args.exclude, args.key_cols)
    if args.match_features:
        missing_features = [f for f in args.match_features if f not in features]
        if missing_features:
            raise ValueError(f"Feature di matching non numeriche o mancanti: {missing_features}")
        match_features = args.match_features
    else:
        match_features = features

    matched_rows, diff_rows = [], []
    missing_indices, extra_indices = set(original.index), set(simulated.index)
    all_keys = pd.concat([original[args.key_cols], simulated[args.key_cols]], ignore_index=True).drop_duplicates()

    for _, key_row in all_keys.iterrows():
        mask_o = np.logical_and.reduce([(original[c] == key_row[c]) for c in args.key_cols])
        mask_s = np.logical_and.reduce([(simulated[c] == key_row[c]) for c in args.key_cols])
        og = original.loc[mask_o]
        sg = simulated.loc[mask_s]
        if og.empty or sg.empty:
            continue

        cost = build_cost_matrix(og, sg, match_features, weights={})
        local_pairs = assign_pairs(cost)
        o_idx_list = og.index.to_list()
        s_idx_list = sg.index.to_list()
        for oi_local, si_local in local_pairs:
            oi = o_idx_list[oi_local]
            si = s_idx_list[si_local]
            missing_indices.discard(oi)
            extra_indices.discard(si)
            pair_id = len(matched_rows) + 1
            o_row = original.loc[oi]
            s_row = simulated.loc[si]
            row = {"pair_id": pair_id, "match_cost": cost[oi_local, si_local]}
            for c in args.key_cols:
                row[c] = o_row[c]
            row["original_index"] = oi
            row["simulated_index"] = si
            if "Flow ID" in original.columns:
                row["original_Flow ID"] = o_row["Flow ID"]
            if "Flow ID" in simulated.columns:
                row["simulated_Flow ID"] = s_row["Flow ID"]
            matched_rows.append(row)
            for d in compare_cells(o_row, s_row, features):
                d.update({"pair_id": pair_id, "original_index": oi, "simulated_index": si})
                for c in args.key_cols:
                    d[c] = o_row[c]
                diff_rows.append(d)

    matched = pd.DataFrame(matched_rows)
    missing = original.loc[sorted(missing_indices)].copy()
    extra = simulated.loc[sorted(extra_indices)].copy()
    cell_df = pd.DataFrame(diff_rows)
    summary = summarize_feature_errors(cell_df)

    matched.to_csv(out_dir / "matched_flows.csv", index=False)
    missing.to_csv(out_dir / "missing_original_flows.csv", index=False)
    extra.to_csv(out_dir / "extra_simulated_flows.csv", index=False)
    cell_df.to_csv(out_dir / "cell_differences.csv", index=False)
    summary.to_csv(out_dir / "feature_error_summary.csv", index=False)
    (out_dir / "suggestions.md").write_text(make_suggestions(summary, len(missing), len(extra)), encoding="utf-8")
    
    # Chiamata alla funzione HTML aggiornata
    write_html_report(out_dir, matched, missing, extra, summary, cell_df, args.key_cols)

    print(f"Report scritto in: {out_dir.resolve()}")
    print(f"Coppie abbinate: {len(matched)}")
    print(f"Flussi originali mancanti: {len(missing)}")
    print(f"Flussi simulati extra: {len(extra)}")
    if not summary.empty:
        print("\nTop 10 feature peggiori:")
        cols = ["feature", "group", "mae", "mean_relative_error_pct", "mean_signed_error"]
        print(summary[cols].head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())