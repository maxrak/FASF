FROM python:3.10-slim

RUN pip install pandas numpy

WORKDIR /app

COPY . .

CMD ["python", "optimizer.py"]