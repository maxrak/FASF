# Suggerimenti per migliorare il simulatore


## Aree piu' critiche

- dimensioni/lunghezze: errore relativo medio 54020.67% su 8 feature.
- throughput/rate: errore relativo medio 858.71% su 1 feature.
- TCP/flag/window: errore relativo medio 568.57% su 17 feature.
- conteggi pacchetti: errore relativo medio 556.53% su 27 feature.
- altro: errore relativo medio 296.82% su 10 feature.

## Feature peggiori

- Bwd Bulk Rate Avg (dimensioni/lunghezze): errore relativo medio 321904.45%, sovrastima.
- Bwd Packets/s (conteggi pacchetti): errore relativo medio 3810.86%, sovrastima.
- Flow Packets/s (conteggi pacchetti): errore relativo medio 3244.37%, sovrastima.
- Fwd Packets/s (conteggi pacchetti): errore relativo medio 3066.36%, sovrastima.
- Bwd Header Length (dimensioni/lunghezze): errore relativo medio 1149.66%, sovrastima.
- Fwd Act Data Pkts (altro): errore relativo medio 1149.66%, sovrastima.
- Fwd PSH Flags (TCP/flag/window): errore relativo medio 1149.66%, sovrastima.
- Fwd Header Length (dimensioni/lunghezze): errore relativo medio 918.17%, sovrastima.
- Flow Bytes/s (throughput/rate): errore relativo medio 858.71%, sovrastima.
- PSH Flag Count (TCP/flag/window): errore relativo medio 817.20%, sovrastima.

## Lettura diagnostica

- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.
- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.
- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.
- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.
