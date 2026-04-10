FROM openjdk:11

WORKDIR /app

COPY CICFlowMeter.jar .

CMD ["bash", "-c", "\
while true; do \
  for f in /pcap/*.pcap; do \
    java -jar CICFlowMeter.jar $f /features/$(basename $f).csv; \
  done; \
  sleep 10; \
done"]