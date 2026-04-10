#!/bin/bash

echo "[+] Capture avanzata..."

tshark -i any \
  -b duration:30 \
  -w /pcap/capture.pcap