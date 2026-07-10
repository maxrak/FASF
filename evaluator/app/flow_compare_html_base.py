#!/usr/bin/env python3
"""
flow_compare_html.py
Legge report_data.json e genera un report.html completamente statico e portatile.
Esempio: python flow_compare_html.py report_output/report_data.json -o report_output/report.html
"""

import argparse
import json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", help="Path al file report_data.json")
    ap.add_argument("-o", "--output", default="report.html", help="Path del file HTML in uscita")
    args = ap.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Errore: Il file {json_path} non esiste. Esegui prima flow_compare_data.py")
        return

    # Leggiamo il JSON come stringa grezza per iniettarlo nel JS
    with open(json_path, "r", encoding="utf-8") as f:
        json_string = f.read()

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
        <li class='nav-item'><button class='nav-link active' data-bs-toggle='tab' data-bs-target='#summary' type='button'>Media Errori (Feature)</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#flow' type='button'>Dettaglio Flusso per Flusso</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#missing' type='button'>Flussi Mancanti</button></li>
        <li class='nav-item'><button class='nav-link' data-bs-toggle='tab' data-bs-target='#extra' type='button'>Flussi Extra</button></li>
    </ul>

    <div class='tab-content' id='reportTabsContent'>
        <div class='tab-pane fade show active table-wrapper' id='summary'><table id="summary-table" class="table table-striped table-hover w-100"></table></div>
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
// INIEZIONE DIRETTA DEL JSON NEL CODICE JAVASCRIPT
const reportData = {json_string};

$(document).ready(function() {{
    function formatNum(data) {{
        return (typeof data === 'number') ? data.toFixed(4) : (data === null ? '-' : data);
    }}

    $('#matched-count').text(reportData.metadata.matched_count);
    $('#missing-count').text(reportData.metadata.missing_count);
    $('#extra-count').text(reportData.metadata.extra_count);

    if (reportData.summary.length > 0) {{
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

    if (reportData.flow_details.length > 0) {{
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