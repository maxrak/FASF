# Suggerimenti per migliorare il simulatore


## Aree piu' critiche

- durata/timing: errore relativo medio 207.79% su 23 feature.
- dimensioni/lunghezze: errore relativo medio 137.41% su 8 feature.
- TCP/flag/window: errore relativo medio 129.55% su 17 feature.
- altro: errore relativo medio 102.51% su 10 feature.
- conteggi pacchetti: errore relativo medio 68.84% su 27 feature.

## Feature peggiori

- Active Std (durata/timing): errore relativo medio 1158.25%, sovrastima.
- Active Max (durata/timing): errore relativo medio 994.14%, sovrastima.
- Bwd IAT Min (durata/timing): errore relativo medio 871.05%, sottostima.
- Active Mean (durata/timing): errore relativo medio 597.27%, sovrastima.
- Bwd Init Win Bytes (altro): errore relativo medio 493.61%, sovrastima.
- Bwd Header Length (dimensioni/lunghezze): errore relativo medio 302.78%, sovrastima.
- Flow IAT Min (durata/timing): errore relativo medio 221.70%, sottostima.
- Fwd Header Length (dimensioni/lunghezze): errore relativo medio 208.17%, sovrastima.
- Bwd Packets/s (conteggi pacchetti): errore relativo medio 207.60%, sovrastima.
- Bwd PSH Flags (TCP/flag/window): errore relativo medio 199.29%, sottostima.

## Lettura diagnostica

- Errori su Duration/IAT/Active/Idle indicano problemi nel modello temporale, non nei timestamp assoluti.
- Errori su Total Fwd/Bwd Packet o Total Length indicano problemi nella generazione dei pacchetti o nella direzione client/server.
- Errori su Bytes/s o Packets/s spesso sono conseguenza di Duration o byte/packet count errati; correggi prima le feature primitive.
- Errori su Flag/Window/Header indicano limiti nella simulazione TCP o nella ricostruzione dello stack/protocollo.
