# Suggerimenti per migliorare il simulatore


## Aree piu' critiche

- dimensioni/lunghezze: errore relativo medio 7036.20% su 8 feature.
- throughput/rate: errore relativo medio 1135.72% su 1 feature.
- conteggi pacchetti: errore relativo medio 663.06% su 27 feature.
- TCP/flag/window: errore relativo medio 545.88% su 17 feature.
- altro: errore relativo medio 289.69% su 10 feature.

## Feature peggiori

- Bwd Bulk Rate Avg (dimensioni/lunghezze): errore relativo medio 40133.39%, sovrastima.
- Bwd Packets/s (conteggi pacchetti): errore relativo medio 4664.81%, sovrastima.
- Flow Packets/s (conteggi pacchetti): errore relativo medio 3956.74%, sovrastima.
- Fwd Packets/s (conteggi pacchetti): errore relativo medio 3710.12%, sovrastima.
- Fwd Act Data Pkts (altro): errore relativo medio 1146.49%, sovrastima.
- Fwd PSH Flags (TCP/flag/window): errore relativo medio 1146.49%, sovrastima.
- Flow Bytes/s (throughput/rate): errore relativo medio 1135.72%, sovrastima.
- Bwd Header Length (dimensioni/lunghezze): errore relativo medio 1075.32%, sovrastima.
- Fwd Header Length (dimensioni/lunghezze): errore relativo medio 874.25%, sovrastima.
- PSH Flag Count (TCP/flag/window): errore relativo medio 785.06%, sovrastima.

## Lettura diagnostica

- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.
- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.
- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.
- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.
