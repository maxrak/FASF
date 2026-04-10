FROM python:3.10-slim

RUN apt-get update && apt-get install -y tcpdump
RUN apt-get update && apt-get install -y iproute2
RUN pip install scapy pandas numpy

WORKDIR /app

COPY client_scapy_burst_optimized.py .
COPY flows.csv .

CMD ["python", "client_scapy_burst_optimized.py", "flows.csv", "172.28.0.3", "172.28.0.2"]