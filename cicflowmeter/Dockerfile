FROM --platform=linux/amd64 eclipse-temurin:11-jre

RUN apt-get update && apt-get install -y libpcap0.8 libpcap-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY distribution/ ./distribution/
COPY cicflowmeter.sh .

RUN chmod +x cicflowmeter.sh

CMD ["bash", "-c", "\
while true; do \
  if ls /pcap/*.pcap 1> /dev/null 2>&1; then \
    for f in /pcap/*.pcap; do \
      ./cicflowmeter.sh $f /flows/$(basename $f).csv; \
    done; \
  else \
    echo 'No pcap files found, waiting...'; \
  fi; \
  sleep 10; \
done"]