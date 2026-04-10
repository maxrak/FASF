FROM ubuntu:22.04

RUN apt-get update && apt-get install -y tshark

WORKDIR /app

COPY capture.sh .
RUN chmod +x capture.sh

CMD ["./capture.sh"]