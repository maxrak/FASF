#!/usr/bin/env python3
"""
flow_compare_html.py
Legge report_data.json e genera un report.html completamente statico e portatile.
Esempio: python flow_compare_html.py report_output/report_data.json -o report_output/report.html

Versione estesa:
- aggiunge una vista dedicata alle 24 feature chiave;
- mostra valori medi originali/simulati, errori medi e bias;
- mostra i valori per singolo flusso solo per le feature chiave.
"""

import argparse
import json
from pathlib import Path

KEY_FEATURES = [
    "Flow Duration",
    "Total Length of Fwd Packet",
    "Fwd Packet Length Max",
    "Fwd Packet Length Min",
    "Bwd Packet Length Max",
    "Bwd Packet Length Min",
    "Flow Bytes/s",
    "Flow IAT Min",
    "Fwd IAT Min",
    "Bwd IAT Min",
    "Fwd URG Flags",
    "Bwd URG Flags",
    "Fwd RST Flags",
    "Bwd RST Flags",
    "Packet Length Std",
    "FIN Flag Count",
    "SYN Flag Count",
    "CWR Flag Count",
    "ECE Flag Count",
    "Down/Up Ratio",
    "Bwd Init Win Bytes",
    "Bwd Seg Size Min",
    "Fwd TCP Retrans. Count",
    "Bwd TCP Retrans. Count",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", help="Path al file report_data.json")
    ap.add_argument("-o", "--output", default="report.html", help="Path del file HTML in uscita")
    args = ap.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Errore: Il file {json_path} non esiste. Esegui prima flow_compare_data.py")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    # Inseriamo nel JSON anche la lista delle feature chiave, così il report resta self-contained.
    report_data["key_features"] = KEY_FEATURES
    json_string = json.dumps(report_data, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Report Analitico di Confronto Flussi</title>
<link href='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css' rel='stylesheet'>
<link href='https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css' rel='stylesheet'>
<style>
    body {{ margin: 20px; font-family: system-ui, sans-serif; background-color: #f8f9fa; }}
    .container-fluid {{ background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .table-wrapper {{ margin-top: 20px; padding-top: 20px; }}
    table.dataTable thead th {{ background-color: #343a40; color: white; }}
    .nav-tabs .nav-link {{ font-weight: 600; color: #495057; }}
    .metric-card {{ border: 1px solid #dee2e6; border-radius: 8px; padding: 14px; background: #f8f9fa; }}
    .metric-label {{ color: #6c757d; font-size: 0.9rem; }}
    .metric-value {{ font-size: 1.25rem; font-weight: 700; }}
    .small-note {{ color: #6c757d; font-size: 0.9rem; }}
    .nowrap {{ white-space: nowrap; }}
</style>
</head>
<body>
<div class='container-fluid'>
    <h2 class='mb-4 text-primary'>Report Analitico di Confronto Flussi (Statico)</h2>

    <div class='alert alert-info'>
        Coppie abbinate: <b id="matched-count">-</b> |
        Flussi originali mancanti: <b id="missing-count">-</b> |
        Flussi simulati extra: <b id="extra-count">-</b>
    </div>

    <ul class='nav nav-tabs' id='reportTabs' role='tablist'>
        <li class='nav-item'><button class='nav-link active' data-bs-toggle='tab' data-bs-target='#keyfeatures' type='button'>24 Feature Chiave</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#summary' type='button'>Media Errori (Feature)</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#flow' type='button'>Dettaglio Flusso per Flusso</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#missing' type='button'>Flussi Mancanti</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#extra' type='button'>Flussi Extra</button></li>
    </ul>

    <div class='tab-content' id='reportTabsContent'>
        <div class='tab-pane fade show active table-wrapper' id='keyfeatures'>
            <div class='row g-3 mb-3'>
                <div class='col-md-3'><div class='metric-card'><div class='metric-label'>Feature chiave trovate</div><div class='metric-value' id='key-found'>-</div></div></div>
                <div class='col-md-3'><div class='metric-card'><div class='metric-label'>MAE medio chiave</div><div class='metric-value' id='key-mae'>-</div></div></div>
                <div class='col-md-3'><div class='metric-card'><div class='metric-label'>Errore relativo medio</div><div class='metric-value' id='key-rel'>-</div></div></div>
                <div class='col-md-3'><div class='metric-card'><div class='metric-label'>Feature mancanti</div><div class='metric-value' id='key-missing'>-</div></div></div>
            </div>
            <p class='small-note'>Questa vista considera solo le 24 feature indicate come prioritarie per l'ottimizzazione.</p>
            <h5 class='mt-4'>Valori medi delle feature chiave</h5>
            <table id="key-summary-table" class="table table-striped table-hover w-100 nowrap"></table>
            <h5 class='mt-5'>Valori per singolo flusso</h5>
            <table id="key-flow-table" class="table table-striped table-hover w-100 nowrap"></table>
        </div>
        <div class='tab-pane fade table-wrapper' id='summary'><table id="summary-table" class="table table-striped table-hover w-100"></table></div>
        <div class='tab-pane fade table-wrapper' id='flow'><table id="flow-table" class="table table-striped table-hover w-100"></table></div>
        <div class='tab-pane fade table-wrapper' id='missing'><div id="missing-table-container"></div></div>
        <div class='tab-pane fade table-wrapper' id='extra'><div id="extra-table-container"></div></div>
    </div>
</div>

<script src='https://code.jquery.com/jquery-3.7.0.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js'></script>
<script src='https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js'></script>
<script src='https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js'></script>

<script>
const reportData = {json_string};

$(document).ready(function() {{
    function numOrNull(x) {{
        return (typeof x === 'number' && Number.isFinite(x)) ? x : null;
    }}

    function formatNum(data) {{
        if (typeof data === 'number' && Number.isFinite(data)) {{
            if (Math.abs(data) >= 1000000) return data.toExponential(4);
            return data.toFixed(4);
        }}
        return (data === null || data === undefined) ? '-' : data;
    }}

    function formatPct(data) {{
        const n = numOrNull(data);
        return n === null ? '-' : n.toFixed(2) + '%';
    }}

    function mean(values) {{
        const nums = values.filter(v => typeof v === 'number' && Number.isFinite(v));
        if (nums.length === 0) return null;
        return nums.reduce((a, b) => a + b, 0) / nums.length;
    }}

    function buildKeySummaryRows() {{
        const details = reportData.flow_details || [];
        const summary = reportData.summary || [];
        const keyFeatures = reportData.key_features || [];

        return keyFeatures.map(feature => {{
            const rows = details.filter(r => r.feature === feature);
            const summaryRow = summary.find(r => r.feature === feature) || {{}};
            return {{
                feature: feature,
                flows_count: rows.length,
                original_mean: mean(rows.map(r => numOrNull(r.original_value))),
                simulated_mean: mean(rows.map(r => numOrNull(r.simulated_value))),
                mean_absolute_error: rows.length ? mean(rows.map(r => numOrNull(r.absolute_error))) : numOrNull(summaryRow.mae),
                mean_relative_error_pct: rows.length ? mean(rows.map(r => numOrNull(r.relative_error_pct))) : numOrNull(summaryRow.mean_relative_error_pct),
                mean_signed_error: rows.length ? mean(rows.map(r => numOrNull(r.signed_error))) : numOrNull(summaryRow.mean_signed_error),
                group: rows.length ? rows[0].group : (summaryRow.group || '-')
            }};
        }});
    }}

    function buildKeyFlowRows() {{
        const keySet = new Set(reportData.key_features || []);
        return (reportData.flow_details || [])
            .filter(r => keySet.has(r.feature))
            .map(r => ({{
                pair_id: r.pair_id,
                endpoint: r['Endpoint Flusso'] || '',
                feature: r.feature,
                group: r.group,
                original_value: r.original_value,
                simulated_value: r.simulated_value,
                absolute_error: r.absolute_error,
                relative_error_pct: r.relative_error_pct,
                signed_error: r.signed_error
            }}));
    }}

    $('#matched-count').text(reportData.metadata?.matched_count ?? '-');
    $('#missing-count').text(reportData.metadata?.missing_count ?? '-');
    $('#extra-count').text(reportData.metadata?.extra_count ?? '-');

    const keySummaryRows = buildKeySummaryRows();
    const foundRows = keySummaryRows.filter(r => r.flows_count > 0 || r.mean_absolute_error !== null || r.mean_relative_error_pct !== null);
    const missingFeatures = keySummaryRows.filter(r => r.flows_count === 0 && r.mean_absolute_error === null && r.mean_relative_error_pct === null).map(r => r.feature);

    $('#key-found').text(foundRows.length + ' / ' + keySummaryRows.length);
    $('#key-mae').text(formatNum(mean(foundRows.map(r => numOrNull(r.mean_absolute_error)))));
    $('#key-rel').text(formatPct(mean(foundRows.map(r => numOrNull(r.mean_relative_error_pct)))));
    $('#key-missing').text(missingFeatures.length);

    $('#key-summary-table').DataTable({{
        data: keySummaryRows,
        columns: [
            {{ data: 'feature', title: 'Feature chiave' }},
            {{ data: 'group', title: 'Gruppo' }},
            {{ data: 'flows_count', title: 'Flussi' }},
            {{ data: 'original_mean', title: 'Media Originale', render: formatNum }},
            {{ data: 'simulated_mean', title: 'Media Simulata', render: formatNum }},
            {{ data: 'mean_absolute_error', title: 'MAE', render: formatNum }},
            {{ data: 'mean_relative_error_pct', title: 'Errore Rel. Medio', render: formatPct }},
            {{ data: 'mean_signed_error', title: 'Bias Medio', render: formatNum }}
        ],
        scrollX: true,
        pageLength: 24,
        order: [[6, 'desc']],
        language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }}
    }});

    $('#key-flow-table').DataTable({{
        data: buildKeyFlowRows(),
        columns: [
            {{ data: 'pair_id', title: 'ID Coppia' }},
            {{ data: 'endpoint', title: 'Endpoint' }},
            {{ data: 'feature', title: 'Feature chiave' }},
            {{ data: 'original_value', title: 'Orig.', render: formatNum }},
            {{ data: 'simulated_value', title: 'Sim.', render: formatNum }},
            {{ data: 'absolute_error', title: 'Err Assoluto', render: formatNum }},
            {{ data: 'relative_error_pct', title: 'Err Relativo', render: formatPct }},
            {{ data: 'signed_error', title: 'Bias', render: formatNum }}
        ],
        scrollX: true,
        pageLength: 50,
        order: [[0, 'asc'], [2, 'asc']],
        language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }}
    }});

    if ((reportData.summary || []).length > 0) {{
        $('#summary-table').DataTable({{
            data: reportData.summary,
            columns: [
                {{ data: 'feature', title: 'Feature' }},
                {{ data: 'group', title: 'Gruppo' }},
                {{ data: 'mae', title: 'Errore Assoluto Medio', render: formatNum }},
                {{ data: 'mean_relative_error_pct', title: 'Errore Relativo Medio (%)', render: formatNum }},
                {{ data: 'mean_signed_error', title: 'Bias Medio (Segno)', render: formatNum }}
            ],
            pageLength: 50, language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }}
        }});
    }}

    if ((reportData.flow_details || []).length > 0) {{
        $('#flow-table').DataTable({{
            data: reportData.flow_details,
            columns: [
                {{ data: 'pair_id', title: 'ID Coppia' }},
                {{ data: 'Endpoint Flusso', title: 'Endpoint' }},
                {{ data: 'feature', title: 'Feature' }},
                {{ data: 'original_value', title: 'Orig.', render: formatNum }},
                {{ data: 'simulated_value', title: 'Sim.', render: formatNum }},
                {{ data: 'absolute_error', title: 'Err Assoluto', render: formatNum }},
                {{ data: 'relative_error_pct', title: 'Err Relativo (%)', render: formatNum }}
            ],
            pageLength: 50, language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }}
        }});
    }}

    function renderDynamicTable(containerId, dataset) {{
        if (!dataset || dataset.length === 0) {{ $('#' + containerId).html('<p>Nessun dato.</p>'); return; }}
        let cols = Object.keys(dataset[0]).map(k => ({{ data: k, title: k, defaultContent: "-" }}));
        let tableId = containerId + '-dt';
        $('#' + containerId).html('<table id="' + tableId + '" class="table table-striped table-hover w-100" style="white-space: nowrap;"></table>');
        $('#' + tableId).DataTable({{ data: dataset, columns: cols, scrollX: true, pageLength: 50, language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/it-IT.json' }} }});
    }}

    renderDynamicTable('missing-table-container', reportData.missing_flows);
    renderDynamicTable('extra-table-container', reportData.extra_flows);
}});
</script>
</body></html>
"""
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"✅ Report HTML statico generato con successo: {args.output}")


if __name__ == "__main__":
    main()
