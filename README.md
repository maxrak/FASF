# 🚀 FASF - Flow Analyzer Simulation Framework

[![Docker](https://img.shields.io/badge/docker-ready-blue)]()
[![Mininet](https://img.shields.io/badge/network-mininet-orange)]()
[![Python](https://img.shields.io/badge/python-3.10+-green)]()
[![License](https://img.shields.io/badge/license-research-lightgrey)]()

---

## 📑 Table of Contents

- Overview
- Architecture
- Project Structure
- Requirements
- Quick Start
- How It Works
- Advanced Usage
- Configuration
- Outputs
- Validation
- Limitations
- Extensions

---

# 🧠 Overview

Framework for synthetic traffic generation based on CICFlowMeter and Mininet.

---

# 🏗️ Architecture

optimizer → Mininet → PCAP → CICFlowMeter → features → evaluator

---

# 📁 Project Structure

project/
├── docker-compose.yml
├── mininet/
├── app/
├── cicflowmeter/
├── optimizer/
├── evaluator/
├── pcap/
├── features/
├── results/
└── shared/

---

# ⚙️ Requirements

- Docker + Docker Compose
- Linux
- RAM ≥ 4GB

---

# 🚀 Quick Start

```bash
docker-compose up --build
```

---

# 🔄 How It Works

1. The optimizer generates parameters
2. Mininet generates traffic
3. A probe captures PCAP files
4. CICFlowMeter extracts features
5. The evaluator computes the loss

---

# 🧪 Advanced Usage

```bash
docker-compose run --rm mininet
```

---

# 📊 Outputs

- `pcap/capture.pcap`
- `features/*.csv`
- `results/loss.txt`

---

# 🎯 Use Cases

- IDS testing
- ML dataset generation
- Network simulation

---

# 📌 Conclusion

A complete framework for traffic synthesis and network emulation.
