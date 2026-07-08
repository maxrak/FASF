# Suggerimenti per migliorare il simulatore


## Aree piu' critiche

- TCP/flag/window: errore relativo medio 1254.80% su 17 feature.
- dimensioni/lunghezze: errore relativo medio 841.42% su 8 feature.
- altro: errore relativo medio 556.27% su 10 feature.
- conteggi pacchetti: errore relativo medio 449.64% su 27 feature.
- throughput/rate: errore relativo medio 421.73% su 1 feature.

## Feature peggiori

- Fwd Act Data Pkts (altro): errore relativo medio 3849.09%, sovrastima.
- Fwd PSH Flags (TCP/flag/window): errore relativo medio 3849.09%, sovrastima.
- Bwd Header Length (dimensioni/lunghezze): errore relativo medio 2981.90%, sovrastima.
- Bwd Packets/s (conteggi pacchetti): errore relativo medio 2043.07%, sovrastima.
- Total Bwd packets (conteggi pacchetti): errore relativo medio 1938.15%, sovrastima.
- PSH Flag Count (TCP/flag/window): errore relativo medio 1810.28%, sovrastima.
- Fwd Header Length (dimensioni/lunghezze): errore relativo medio 1754.16%, sovrastima.
- ACK Flag Count (TCP/flag/window): errore relativo medio 1569.42%, sovrastima.
- Flow Packets/s (conteggi pacchetti): errore relativo medio 1497.84%, sovrastima.
- Fwd Packets/s (conteggi pacchetti): errore relativo medio 1253.43%, sovrastima.

## Lettura diagnostica

- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.
- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.
- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.
- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.
