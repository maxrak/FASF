# Suggerimenti per migliorare il simulatore

- Priorita' alta: il simulatore non riproduce 2 flussi originali. Verifica le regole di generazione/sessionizzazione e le condizioni di terminazione dei flussi.

## Aree piu' critiche

- TCP/flag/window: errore relativo medio 405.26% su 17 feature.
- dimensioni/lunghezze: errore relativo medio 339.20% su 8 feature.
- altro: errore relativo medio 259.52% su 10 feature.
- throughput/rate: errore relativo medio 188.45% su 1 feature.
- conteggi pacchetti: errore relativo medio 187.20% su 27 feature.

## Feature peggiori

- Fwd Act Data Pkts (altro): errore relativo medio 1142.86%, sovrastima.
- Fwd PSH Flags (TCP/flag/window): errore relativo medio 1142.86%, sovrastima.
- Bwd Header Length (dimensioni/lunghezze): errore relativo medio 1054.88%, sovrastima.
- Total Bwd packets (conteggi pacchetti): errore relativo medio 650.83%, sovrastima.
- Fwd Header Length (dimensioni/lunghezze): errore relativo medio 643.96%, sovrastima.
- Bwd Packets/s (conteggi pacchetti): errore relativo medio 641.08%, sovrastima.
- ACK Flag Count (TCP/flag/window): errore relativo medio 503.41%, sovrastima.
- Bwd Init Win Bytes (altro): errore relativo medio 493.61%, sovrastima.
- PSH Flag Count (TCP/flag/window): errore relativo medio 485.28%, sovrastima.
- Flow Packets/s (conteggi pacchetti): errore relativo medio 451.72%, sovrastima.

## Lettura diagnostica

- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.
- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.
- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.
- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.
