# 🚀FASF - Flow Analyzer Simulation Framework

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

Framework per generazione traffico sintetico basato su CICFlowMeter con Mininet.

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
├── shared/

---

# ⚙️ Requirements

- Docker + Docker Compose
- Linux
- RAM ≥ 4GB

---

# 🚀 Quick Start

docker-compose up --build

---

# 🔄 How It Works

1. Optimizer genera parametri  
2. Mininet genera traffico  
3. Probe cattura PCAP  
4. CICFlowMeter estrae feature  
5. Evaluator calcola loss  

---

# 🧪 Advanced Usage

docker-compose run --rm mininet

---

# 📊 Outputs

- pcap/capture.pcap
- features/*.csv
- results/loss.txt

---

# 🎯 Use Cases

- IDS testing  
- ML dataset generation  
- Network simulation  

---

# 📌 Conclusion

Framework completo per traffic synthesis e network emulation.
