#!/bin/bash

# Estrae il numero della colonna FIN Flag Count
fin_col=$(head -1 shared/input_flows/test6.csv | tr ',' '\n' | grep -n "^FIN Flag Count$" | cut -d: -f1)
echo "FIN Flag Count è nella colonna $fin_col\n"

# Estrae il numero della colonna Flow ID (o usa le colonne di identificazione)
flow_id_col=$(head -1 shared/input_flows/test6.csv | tr ',' '\n' | grep -n "^Flow ID$" | cut -d: -f1)

if [ -z "$flow_id_col" ]; then
    # Usa le prime colonne per identificare il flusso
    echo "Usando Src IP, Src Port, Dst IP, Dst Port per identificare flussi"
    # Crea un file temporaneo con flow_key | fin_count
    
    echo "=== FILE ORIGINALE ==="
    awk -F',' 'NR>1 {
        # Colonne: Src IP, Src Port, Dst IP, Dst Port, FIN Flag Count
        # Cerca le colonne
        for(i=1; i<=NF; i++) {
            if ($i ~ /Src IP/ || i==1) src_ip=i
            if ($i ~ /Src Port/ || i==2) src_port=i
            if ($i ~ /Dst IP/ || i==3) dst_ip=i
            if ($i ~ /Dst Port/ || i==4) dst_port=i
        }
        print $1":"$2"→"$3":"$4
    }' <(head -2 shared/input_flows/test6.csv) | head -5
fi

# Semplice: estrai le colonne rilevanti da entrambi i file
echo "=== FLUSSI CON FIN FLAG COUNT ORIGINALE ==="
tail -n +2 shared/input_flows/test6.csv | awk -F',' -v col="$fin_col" '{print $1":"$2"→"$3":"$4" | FIN="$col}' | head -20

echo ""
echo "=== FLUSSI CON FIN FLAG COUNT REGENERATED ==="
tail -n +2 shared/output_flows/regenerated_test6_clean.csv | awk -F',' -v col="$fin_col" '{print $1":"$2"→"$3":"$4" | FIN="$col}' | head -20

