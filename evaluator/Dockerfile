FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN pip install --no-cache-dir pandas numpy pyvis matplotlib

WORKDIR /app

COPY . .

CMD ["python", "evaluator.py"]
