FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       jq \
       procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then pip install -r /tmp/requirements.txt; fi \
    && pip install optuna numpy pandas pyyaml

CMD ["python3", "-m", "traffic_optimizer.host_step", "--help"]
