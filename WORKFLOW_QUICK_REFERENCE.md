# 📋 FASF Workflow Quick Reference

## The 6-Step Workflow

```
[1] Generate   [2] Replicate   [3] Regenerate   [4] Compare   [5] Optimize   [6] Evaluate
Topology       Flows           Flows            Flows        Parameters    Results
   ↓              ↓                ↓               ↓             ↓            ↓
Input CSV    Mininet Sim      CICFlowMeter   Report JSON   Bayesian Opt  Graphs/CSV
```

---

## 🎯 Standard Workflow

```bash
# Setup: Prepare CSV file
cp shared/input_flows/test6.csv shared/input_flows/mytest.csv

# Step 1: Generate Topology
./1.generate_topology.sh mytest
# Output: shared/topologies/mytest.csv.json

# Step 2: Replicate Flows (Mininet simulation)
./2.replicate_flow.sh mytest
# Output: shared/pcap/mytest.pcap (~10-30s)

# Step 3: Extract Features (CICFlowMeter)
./3.regenerate_flows.sh mytest
# Output: shared/output_flows/regenerated_mytest_clean.csv

# Step 4: Compare Flows
./4.compare_flows.sh mytest
# Output: shared/results/mytest/report_data.json

# Step 5: OPTIONAL - Optimize Parameters
./5.optimize_flow_simulation.sh mytest 10
# Output: optimizer_state/mytest/trials.jsonl (~30-50 min for 10 trials)

# Step 6: Generate Report & Charts
./6.evaluate_optimization.sh mytest
# Output: shared/results/mytest/mytest_keyfeatures.png/.csv
```

---

## ⚡ Quick Commands

### Test Single Implementation
```bash
# Test scapy_burst implementation
./1.generate_topology.sh test6
./2.replicate_flow.sh test6 scapy_burst
./3.regenerate_flows.sh test6
./4.compare_flows.sh test6
./6.evaluate_optimization.sh test6

# View results
cat shared/results/test6/test6_keyfeatures.csv | head -20
```

### Test Multiple Implementations
```bash
for impl in scapy_burst tcp_burst flow_emulator; do
  ./2.replicate_flow.sh test6 $impl
  ./3.regenerate_flows.sh test6
  ./4.compare_flows.sh test6
  echo "=== $impl ==="
  head -2 shared/results/test6/test6_keyfeatures.csv | tail -1
done
```

### Batch Test Multiple Datasets
```bash
for test in test1 test2 test3 test6; do
  echo "Processing $test..."
  ./1.generate_topology.sh $test
  ./2.replicate_flow.sh $test
  ./3.regenerate_flows.sh $test
  ./4.compare_flows.sh $test
  ./6.evaluate_optimization.sh $test
done
```

### Optimize with Multiple Trials
```bash
# Run optimization with 20 trials (long, ~2-3 hours)
./5.optimize_flow_simulation.sh test6 20

# View optimization progress
cat shared/results/test6/optimization_summary.json | python3 -m json.tool
```

---

## 📊 Quick Analysis

### Check Overall Error
```bash
echo "=== Error Summary ==="
cat shared/results/test6/test6_keyfeatures.csv | \
  awk -F',' 'NR>1 {sum+=$3; count++} END {print "Mean Error: " sum/count "% (" count " features)"}'
```

### Check Specific Features
```bash
echo "=== TCP Flags ==="
grep -E "FIN|SYN|RST|ACK" shared/results/test6/test6_keyfeatures.csv

echo "=== Timing Features ==="
grep -E "Duration|IAT|Active|Idle" shared/results/test6/test6_keyfeatures.csv

echo "=== Size Features ==="
grep -E "Length|Bytes" shared/results/test6/test6_keyfeatures.csv
```

### Visualize Results
```bash
# Open PNG charts
open shared/results/test6/test6_keyfeatures.png
open shared/results/test6/optimization_progress.png

# Or view HTML report
open shared/results/test6/report.html
```

---

## 🐛 Debug Commands

### View Matched Flows Count
```bash
python3 << 'EOF'
import json
with open('shared/results/test6/report_data.json') as f:
    r = json.load(f)
print(f"Matched: {r['metadata']['matched_count']}")
print(f"Missing: {r['metadata']['missing_count']}")  
print(f"Extra: {r['metadata']['extra_count']}")
EOF
```

### Compare Specific Flow
```bash
python3 << 'EOF'
import json
target_src = "192.168.1.100"
target_dst = "8.8.8.8"

with open('shared/results/test6/report_data.json') as f:
    r = json.load(f)
    
for detail in r['flow_details']:
    if detail['Src IP'] == target_src and detail['Dst IP'] == target_dst:
        print(f"{detail['feature']}: {detail['original_value']} -> {detail['simulated_value']} "
              f"(error: {detail['relative_error_pct']:.2f}%)")
EOF
```

### Extract High-Error Features
```bash
python3 << 'EOF'
import json
with open('shared/results/test6/report_data.json') as f:
    r = json.load(f)
    
high_error = [(s['feature'], s['mean_relative_error_pct']) 
              for s in r['summary'] 
              if s['mean_relative_error_pct'] and s['mean_relative_error_pct'] > 50]

for feature, error in sorted(high_error, key=lambda x: -x[1]):
    print(f"{feature:<40} {error:>8.2f}%")
EOF
```

---

## 🔍 File Locations

| File | Location | Purpose |
|------|----------|---------|
| Input CSV | `shared/input_flows/{test}.csv` | Original flows (87 features) |
| Topology JSON | `shared/topologies/{test}.csv.json` | Network topology |
| PCAP Capture | `shared/pcap/{test}.pcap` | Traffic capture (binary) |
| Regenerated CSV | `shared/output_flows/regenerated_{test}_clean.csv` | Extracted features |
| Report Data | `shared/results/{test}/report_data.json` | Error metrics |
| Report HTML | `shared/results/{test}/report.html` | Interactive report |
| Key Features PNG | `shared/results/{test}/{test}_keyfeatures.png` | Error chart |
| Key Features CSV | `shared/results/{test}/{test}_keyfeatures.csv` | Error data |
| Intermediate Files | `shared/results/tmp/` | Temp files (bidir, burst, flows_adapted, etc.) |
| Optimization State | `optimizer_state/{test}/trials.jsonl` | Bayesian optimization trials |

---

## ✅ Success Criteria

✓ All steps complete without errors
✓ Error on key features < 20% (good) or < 50% (acceptable)
✓ FIN Flag Count error < 50%
✓ Flow Duration error < 30%
✓ PCAP file size > 1KB

---

## 📈 Typical Results

```
test6 Results (default scapy_burst implementation):
  Matched Flows: 42/42 ✓
  Mean Error: 22.3% (acceptable)
  Best Features (< 10%): SYN Flag Count, Packet Length Min
  Worst Features (> 50%): ACK Flag Count, Flow IAT Min
  
After Optimization (10 trials):
  Best Score: 14.56 (vs baseline 15.34)
  Improvement: 5.1%
```

---

## 🚀 Performance Tips

1. **Faster First Run**: Use `scapy_burst` (default, fastest)
2. **Longer Simulation**: Increase timeout in CSV (Duration column)
3. **Batch Processing**: Run on Linux with 8GB+ RAM
4. **Parallel Execution**: Run different tests on separate terminals
5. **Skip Optimization**: If time-limited, skip step 5 (optional)

---

## ⚠️ Common Issues

| Issue | Solution |
|-------|----------|
| Docker not found | Install Docker, add user to docker group |
| Out of memory | Reduce flows in CSV or increase Docker memory |
| PCAP not created | Check step 2 logs, increase timeout |
| No features extracted | PCAP might be empty, check step 3 logs |
| High error (>80%) | Try different implementation or adjust timing |
| Optimization slow | Reduce max_trials or use fewer features |

---

## 📞 Getting Help

```bash
# View script help
./1.generate_topology.sh -h
./2.replicate_flow.sh -h
./3.regenerate_flows.sh -h
./4.compare_flows.sh -h
./5.optimize_flow_simulation.sh -h
./6.evaluate_optimization.sh -h

# Check logs
docker logs <container_id>

# View generated files
ls -lah shared/results/test6/
ls -lah shared/pcap/
ls -lah shared/results/tmp/
```

---

**Last Updated**: 2026-10-28
