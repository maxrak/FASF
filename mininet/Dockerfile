FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    python3 \
    python3-pip \
    tcpdump \
    iproute2 \
    iputils-ping \
    netcat-openbsd \
    openjdk-11-jre

RUN pip install scapy pandas numpy

WORKDIR /app

COPY run_experiment.py /app/

# Create entrypoint script to start OVS
RUN echo '#!/bin/bash\n\
service openvswitch-switch start\n\
# Start ovs-vswitchd manually since the module is not available\n\
ovs-vswitchd unix:/var/run/openvswitch/db.sock --pidfile --detach --log-file 2>/dev/null || true\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "run_experiment.py"]