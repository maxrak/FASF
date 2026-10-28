# 🏗️ FASF Architecture Diagrams

## 📊 Complete Workflow Pipeline

```
INPUT
  ↓
  ├─ shared/input_flows/test6.csv (87 features × N flows)
  │
  ↓
[STEP 1: Generate Topology]
  ├─ Script: 1.generate_topology.sh
  ├─ Input: CSV file
  ├─ Process: Parse flows → identify hosts/links → generate topology
  └─ Output: shared/topologies/test6.csv.json
       │
       ├─ Hosts: [h1, h2, ..., hN]
       ├─ Switches: [s1, s2, ...]
       └─ Links: [h1-s1, h2-s1, ...]
  │
  ↓
[STEP 2: Replicate Flows]
  ├─ Script: 2.replicate_flow.sh <test> [implementation]
  ├─ Input: Topology JSON + CSV parameters
  ├─ Process:
  │   ├─ Docker spawn Mininet container
  │   ├─ Create virtual hosts/switches
  │   ├─ Generate traffic flow per flow:
  │   │   ├─ Connect src → dst via routing
  │   │   ├─ Generate TCP/UDP packets (Scapy/raw socket)
  │   │   ├─ Respect timing (inter-packet delay)
  │   │   ├─ Respect sizes (payload length)
  │   │   └─ Respect flags (FIN, SYN, RST, etc.)
  │   └─ Probe tcpdump captures all packets
  └─ Output: shared/pcap/test6.pcap
       │
       ├─ Binary PCAP format
       ├─ Size: 100KB - 10MB (depends on flows)
       └─ Contains: All packets from all flows
  │
  ↓
[STEP 3: Regenerate Flows]
  ├─ Script: 3.regenerate_flows.sh <test>
  ├─ Input: PCAP file
  ├─ Process:
  │   ├─ Docker spawn CICFlowMeter container
  │   ├─ Read PCAP packets
  │   ├─ Identify flows (4-tuple: src_ip, src_port, dst_ip, dst_port)
  │   ├─ For each flow, calculate 87 features:
  │   │   ├─ Duration, packet counts, bytes
  │   │   ├─ Min/Max/Mean/Std of packet sizes
  │   │   ├─ IAT (inter-arrival time) statistics
  │   │   ├─ TCP flags count (FIN, SYN, RST, ACK)
  │   │   ├─ Throughput (bytes/s, packets/s)
  │   │   └─ Active/Idle time
  │   └─ Aggregate into CSV
  └─ Output: shared/output_flows/regenerated_test6_clean.csv
       │
       ├─ Format: Same as input CSV
       ├─ Rows: Number of flows extracted from PCAP
       └─ May differ from input (filtering, timing issues)
  │
  ↓
[STEP 4: Compare Flows]
  ├─ Script: 4.compare_flows.sh <test>
  ├─ Input: Original CSV + Regenerated CSV
  ├─ Process:
  │   ├─ Normalize both CSVs (convert IPs/ports to strings)
  │   ├─ Match flows on 4-tuple key
  │   ├─ For each matched flow and each feature:
  │   │   ├─ Calculate absolute error: |regenerated - original|
  │   │   ├─ Calculate relative error: abs_error / |original|
  │   │   │   (Special handling when original = 0)
  │   │   └─ Classify: group by feature type
  │   ├─ Aggregate by feature across all flows:
  │   │   ├─ MAE (Mean Absolute Error)
  │   │   ├─ Mean Relative Error (%)
  │   │   └─ Count of errors per category
  │   └─ Identify missing/extra flows
  └─ Output: shared/results/test6/report_data.json
       │
       ├─ metadata:
       │   ├─ matched_count: N
       │   ├─ missing_count: M (in original, not in regenerated)
       │   └─ extra_count: K (in regenerated, not in original)
       │
       ├─ summary:
       │   └─ For each feature:
       │       ├─ feature: "FIN Flag Count"
       │       ├─ group: "TCP/flag/window"
       │       ├─ mae: 0.98
       │       └─ mean_relative_error_pct: 43.18
       │
       ├─ flow_details:
       │   └─ For each (flow, feature) pair:
       │       ├─ pair_id, feature, group
       │       ├─ original_value, simulated_value
       │       ├─ absolute_error, relative_error_pct
       │       └─ Src IP, Src Port, Dst IP, Dst Port
       │
       └─ missing_flows, extra_flows
  │
  ↓
[STEP 5: OPTIONAL - Optimize Simulation]
  ├─ Script: 5.optimize_flow_simulation.sh <test> [max_trials]
  ├─ Input: Baseline score from step 4
  ├─ Process (Bayesian Optimization loop):
  │   └─ For each trial (1 to max_trials):
  │       ├─ Suggest new parameters:
  │       │   ├─ Traffic generation timeout
  │       │   ├─ Packet inter-arrival time
  │       │   ├─ Payload size distribution
  │       │   └─ TCP window size
  │       ├─ Re-run steps 2-4 with new parameters
  │       ├─ Calculate new score (mean error across features)
  │       ├─ Update Bayesian model with (params → score)
  │       └─ Log trial results
  │       
  │   Trial N/10: Score = 14.87 (vs baseline 15.34) ✓ Improvement!
  │
  └─ Output: optimizer_state/test6/trials.jsonl
       │
       ├─ Line 1: {trial_id: 0, params: {...}, score: 15.34}
       ├─ Line 2: {trial_id: 1, params: {...}, score: 15.12}
       ├─ ...
       └─ Line N: {trial_id: 9, params: {...}, score: 14.56} ← BEST
  │
  ↓
[STEP 6: Evaluate Results]
  ├─ Script: 6.evaluate_optimization.sh <test>
  ├─ Input: report_data.json (from step 4)
  ├─ Process:
  │   ├─ Extract 24 key features from summary
  │   ├─ Calculate mean error for each:
  │   │   ├─ FIN Flag Count: 43.18%
  │   │   ├─ SYN Flag Count: 37.50%
  │   │   ├─ Flow Duration: 23.50%
  │   │   └─ ... (21 more features)
  │   │
  │   ├─ Sort by error (worst → best)
  │   ├─ Color-code by severity:
  │   │   ├─ 🟢 Green < 10%
  │   │   ├─ 🟡 Yellow 10-20%
  │   │   ├─ 🟠 Orange 20-50%
  │   │   └─ 🔴 Red > 50%
  │   │
  │   └─ Generate visualizations:
  │       ├─ Horizontal bar chart (error vs feature)
  │       ├─ Optimization progress curve (trial → score)
  │       └─ Export to PNG + CSV
  │
  └─ Output:
       ├─ shared/results/test6/test6_keyfeatures.png
       │   └─ Bar chart showing error % for each of 24 features
       │
       ├─ shared/results/test6/test6_keyfeatures.csv
       │   └─ CSV with feature, label, error%, missing_flag
       │
       ├─ shared/results/test6/optimization_progress.png
       │   └─ Curve showing score improvement over trials
       │
       └─ shared/results/test6/optimization_summary.json
           └─ Metadata: baseline score, best score, improvement %
  │
  ↓
ANALYSIS & REPORTING
```

---

## 🔄 Data Flow Transformation

```
┌─ ORIGINAL CSV (test6.csv)
│  ├─ Columns: 87 features (Duration, Fwd bytes, FIN count, etc.)
│  ├─ Rows: 45 flows
│  ├─ Format: CSV with header row
│  └─ Example row:
│     192.168.1.100,1234,8.8.8.8,80,6,5.2,245,512,...,2,2,0,0
│
├─────────────────────────────────────────────
│
├─ TOPOLOGY JSON (test6.csv.json)
│  ├─ Hosts: [{name: h1, ip: 192.168.1.100}, ...]
│  ├─ Switches: [{name: s1}, ...]
│  ├─ Links: [{src: h1, dst: s1}, ...]
│  └─ Flows: [{src: h1, dst: h2, params: {...}}, ...]
│
├─────────────────────────────────────────────
│
├─ PCAP FILE (test6.pcap)
│  ├─ Binary packets captured from Mininet
│  ├─ Contains all TCP/UDP packets from all flows
│  └─ Example:
│     Frame 1: h1(192.168.1.100:1234) → h2(8.8.8.8:80) [SYN]
│     Frame 2: h2(8.8.8.8:80) → h1(192.168.1.100:1234) [SYN-ACK]
│     Frame 3: h1(192.168.1.100:1234) → h2(8.8.8.8:80) [ACK]
│     ... (many packets)
│     Frame N: h1 → h2 [FIN]
│     Frame N+1: h2 → h1 [FIN-ACK]
│
├─────────────────────────────────────────────
│
├─ REGENERATED CSV (regenerated_test6_clean.csv)
│  ├─ Columns: 87 features (calculated from PCAP)
│  ├─ Rows: Flow extracted from PCAP (may differ from input)
│  ├─ Format: Same as input CSV
│  └─ Example row (calculated):
│     192.168.1.100,1234,8.8.8.8,80,6,5.15,243,510,...,2,2,0,0
│     │                                                      │
│     │                                                      └─ Changed: 5.2 → 5.15
│
├─────────────────────────────────────────────
│
├─ REPORT JSON (report_data.json)
│  ├─ metadata:
│  │   └─ {matched: 42, missing: 3, extra: 2}
│  │
│  ├─ summary:
│  │   ├─ {feature: "FIN Flag Count", mae: 0.98, error%: 43.18}
│  │   ├─ {feature: "Flow Duration", mae: 0.15, error%: 23.50}
│  │   └─ ... (87 total)
│  │
│  ├─ flow_details:
│  │   └─ {pair_id: 1, feature: "Duration", original: 5.2, simulated: 5.15, error%: 0.96}
│  │       {pair_id: 1, feature: "FIN Flag Count", original: 2, simulated: 2, error%: 0.0}
│  │       ... (42 flows × 87 features = 3654 rows)
│  │
│  └─ missing_flows, extra_flows
│
├─────────────────────────────────────────────
│
└─ KEY FEATURES CSV (test6_keyfeatures.csv)
   └─ {feature: "FIN Flag Count", error%: 43.18}
       {feature: "SYN Flag Count", error%: 37.50}
       {feature: "Flow Duration", error%: 23.50}
       ... (24 selected features)
```

---

## 🎯 Feature Calculation (Step 3 Detail)

```
PCAP Packet Stream:
┌─────────────────────────────────────────────────────────┐
│ Frame 1: Time=0.000s, Src=192.168.1.100:1234           │
│          Dst=8.8.8.8:80, Flags=SYN, Len=20             │
│                                                         │
│ Frame 2: Time=0.050s, Src=8.8.8.8:80                   │
│          Dst=192.168.1.100:1234, Flags=SYN-ACK, Len=20 │
│                                                         │
│ Frame 3: Time=0.052s, Src=192.168.1.100:1234           │
│          Dst=8.8.8.8:80, Flags=ACK, Len=512            │
│                                                         │
│ ... (many more frames)                                  │
│                                                         │
│ Frame N: Time=5.245s, Src=192.168.1.100:1234           │
│          Dst=8.8.8.8:80, Flags=FIN, Len=20             │
│                                                         │
│ Frame N+1: Time=5.300s, Src=8.8.8.8:80                 │
│            Dst=192.168.1.100:1234, Flags=FIN-ACK, Len=20│
└─────────────────────────────────────────────────────────┘
        ↓
CICFlowMeter Analysis:
        ↓
Flow: 192.168.1.100:1234 → 8.8.8.8:80
  ├─ Protocol: 6 (TCP)
  ├─ Duration: 5.245 - 0.000 = 5.245 seconds
  ├─ Total Fwd Packet: 42 (frames with src=192.168.1.100)
  ├─ Total Bwd packets: 43 (frames with dst=192.168.1.100)
  ├─ Total Length of Fwd Packet: 12,450 bytes (sum fwd payload)
  ├─ Total Length of Bwd Packet: 15,330 bytes
  ├─ Fwd Packet Length Max: 1,460 bytes
  ├─ Fwd Packet Length Min: 20 bytes
  ├─ FIN Flag Count: 2 (1 client FIN + 1 server FIN-ACK)
  ├─ SYN Flag Count: 2 (1 client SYN + 1 server SYN-ACK)
  ├─ RST Flag Count: 0
  ├─ ACK Flag Count: 83
  ├─ Flow Bytes/s: (12,450 + 15,330) / 5.245 = 5,280 bytes/s
  ├─ Active Time: 5.245s
  ├─ Idle Time: 0s
  └─ ... (79 more features)
        ↓
CSV Row: 192.168.1.100,1234,8.8.8.8,80,6,5.245,42,43,12450,15330,...,2,2,0,83,...
```

---

## ⚙️ Optimization Loop (Step 5 Detail)

```
ITERATION 1
└─ Current params:
   ├─ timeout: 10s
   ├─ pkt_delay: 0.05ms
   ├─ payload_size: 512 bytes
   └─ tcp_window: 65536
   └─ Baseline Score: 15.34

   → Execute steps 2-4 with these params
   → Calculate new score: 15.34 (no change)
   → Bayesian: record (params → 15.34)

ITERATION 2
└─ Bayesian suggests:
   ├─ timeout: 12s (increased)
   ├─ pkt_delay: 0.04ms (decreased)
   ├─ payload_size: 600 bytes
   └─ tcp_window: 65536
   └─ Predicted Score: 15.1 (better!)

   → Execute steps 2-4 with these params
   → Calculate new score: 15.12 ✓ Improvement!
   → Bayesian: record (new_params → 15.12)

ITERATION 3
└─ Bayesian suggests:
   ├─ timeout: 11s
   ├─ pkt_delay: 0.043ms
   ├─ payload_size: 580 bytes
   └─ tcp_window: 65536
   └─ Predicted Score: 15.0

   → Execute steps 2-4 with these params
   → Calculate new score: 14.95 ✓✓ Better!
   → Bayesian: record (new_params → 14.95)

... (continue up to max_trials)

FINAL RESULT
└─ Best Score Found: 14.56 (Trial 4)
   ├─ Best params:
   │   ├─ timeout: 11.5s
   │   ├─ pkt_delay: 0.042ms
   │   ├─ payload_size: 570 bytes
   │   └─ tcp_window: 65536
   │
   └─ Improvement: (15.34 - 14.56) / 15.34 = 5.1%
```

---

## 📦 File Organization

```
FASF/
│
├── Workflow Scripts (Numbered)
│   ├── 1.generate_topology.sh          [CSV → Topology JSON]
│   ├── 2.replicate_flow.sh             [Topology → PCAP]
│   ├── 3.regenerate_flows.sh           [PCAP → CSV Features]
│   ├── 4.compare_flows.sh              [CSV Comparison → Report JSON]
│   ├── 5.optimize_flow_simulation.sh   [Report → Optimized Params]
│   └── 6.evaluate_optimization.sh      [Report → Charts/CSV]
│
├── Utility Scripts
│   ├── aggregate_bursts.sh
│   └── compare_fin_flags.sh
│
├── Docker Containers
│   ├── mininet/                [Network simulation]
│   ├── evaluator/              [CICFlowMeter + Analysis]
│   ├── optimizer/              [Bayesian Optimization]
│   └── docker-compose.yml      [Orchestration]
│
└── Data Directories
    └── shared/
        ├── input_flows/                    [Original CSV]
        ├── topologies/                     [Generated topology JSON]
        ├── pcap/                           [PCAP captures]
        ├── output_flows/                   [Regenerated CSV]
        ├── results/
        │   ├── test6/
        │   │   ├── report_data.json        [Detailed comparison]
        │   │   ├── report.html             [Interactive report]
        │   │   ├── test6_keyfeatures.png   [Error chart]
        │   │   ├── test6_keyfeatures.csv   [Feature errors]
        │   │   └── optimization_*.png      [Progress charts]
        │   │
        │   └── tmp/                        [Intermediate files]
        │       ├── bidir_dataset_*.csv
        │       ├── burst_dataset_*.csv
        │       ├── flows_adapted_*.csv
        │       └── server_*.log
        │
        └── optimizer_state/
            └── test6/
                └── trials.jsonl            [Optimization history]
```

---

## 🔐 Error Flow (When Things Go Wrong)

```
Step 1: Generate Topology
  ├─ Error: CSV not found
  │   └─ Solution: Check shared/input_flows/
  │
  └─ Error: Invalid CSV format
      └─ Solution: Ensure 87 columns, valid IPs

Step 2: Replicate Flows
  ├─ Error: Docker not running
  │   └─ Solution: docker daemon start
  │
  ├─ Error: Out of memory
  │   └─ Solution: Reduce flows or increase Docker RAM
  │
  └─ Error: PCAP empty
      └─ Solution: Increase timeout, check implementation

Step 3: Regenerate Flows
  ├─ Error: PCAP not found
  │   └─ Solution: Re-run step 2
  │
  └─ Error: CICFlowMeter timeout
      └─ Solution: Reduce PCAP size or increase timeout

Step 4: Compare Flows
  ├─ Error: CSV mismatch
  │   └─ Solution: Check flow count, IP format
  │
  └─ Error: All flows missing/extra
      └─ Solution: Debug step 2 or 3

Step 5: Optimize
  ├─ Error: Very high error > 100%
  │   └─ Solution: Try different implementation
  │
  └─ Error: Optimization stuck
      └─ Solution: Reduce search space or increase trials

Step 6: Evaluate
  └─ Error: Report JSON not found
      └─ Solution: Re-run step 4
```

---

**Last Updated**: 2026-10-28
**Version**: 1.0
