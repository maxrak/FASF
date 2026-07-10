FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Installazione pacchetti
RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    openvswitch-common \
    python3 \
    python3-pip \
    tcpdump \
    iproute2 \
    iputils-ping \
    netcat-openbsd \
    openjdk-11-jre \
    kmod \
    procps \
    && rm -rf /var/lib/apt/lists/*

# "python" -> python3
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Librerie Python
RUN pip3 install --no-cache-dir \
    scapy \
    pandas \
    numpy

WORKDIR /app

# Entrypoint
RUN cat > /entrypoint.sh <<'EOF'
#!/bin/bash
set -e

echo "=== Cleanup Mininet ==="

# Pulizia di eventuali reti precedenti
mn -c >/dev/null 2>&1 || true

# Chiudi eventuali processi OVS rimasti
pkill ovs-vswitchd 2>/dev/null || true
pkill ovsdb-server 2>/dev/null || true

rm -f /var/run/openvswitch/*.pid
rm -f /var/run/openvswitch/*.sock

mkdir -p /var/run/openvswitch
mkdir -p /etc/openvswitch
mkdir -p /var/log/openvswitch

# Crea il database OVS se non esiste
if [ ! -f /etc/openvswitch/conf.db ]; then
    ovsdb-tool create \
        /etc/openvswitch/conf.db \
        /usr/share/openvswitch/vswitch.ovsschema
fi

echo "=== Starting ovsdb-server ==="

ovsdb-server \
    --remote=punix:/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --pidfile \
    --detach \
    --log-file

ovs-vsctl --no-wait init

echo "=== Starting ovs-vswitchd ==="

ovs-vswitchd \
    unix:/var/run/openvswitch/db.sock \
    --pidfile \
    --detach \
    --log-file

echo "=== Open vSwitch ==="
ovs-vsctl show

exec "$@"
EOF

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["bash"]