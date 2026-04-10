FROM python:3.10-slim

RUN pip install scapy

WORKDIR /app

COPY server_scapy.py .

CMD ["python", "server_scapy.py"]