#!/usr/bin/env python3
"""
Plot optimization progress from traffic optimizer trials.jsonl.

Usage:
  python3 plot_optimization.py shared/results/test5/optimizer_state/trials.jsonl
  python3 plot_optimization.py shared/results/test5/optimizer_state/trials.jsonl --out-dir plots
  python3 plot_optimization.py shared/results/test5/optimizer_state/trials.jsonl --title test5

Outputs:
  optimization_progress.png
  optimization_summary.json
  optimization_trials.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt


def load_trials(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")

    trials: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON non valido alla riga {line_no}: {exc}") from exc
            if "score" not in item:
                continue
            try:
                item["score"] = float(item["score"])
            except (TypeError, ValueError):
                continue
            if math.isfinite(item["score"]):
                trials.append(item)

    if not trials:
        raise ValueError(f"Nessun trial valido trovato in {path}")
    return trials


def get_trial_id(trial: Dict[str, Any], index: int) -> int:
    for key in ("trial_id", "trial", "iteration", "n"):
        if key in trial:
            try:
                return int(trial[key])
            except (TypeError, ValueError):
                pass
    return index


def compute_best_so_far(scores: List[float]) -> List[float]:
    best: List[float] = []
    current = float("inf")
    for score in scores:
        current = min(current, score)
        best.append(current)
    return best


def write_csv(path: Path, trials: List[Dict[str, Any]], ids: List[int], best_so_far: List[float]) -> None:
    fieldnames = ["index", "trial_id", "score", "best_so_far", "algorithm", "is_best"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, (trial, trial_id, best) in enumerate(zip(trials, ids, best_so_far), start=1):
            writer.writerow({
                "index": idx,
                "trial_id": trial_id,
                "score": trial.get("score"),
                "best_so_far": best,
                "algorithm": trial.get("algorithm", ""),
                "is_best": trial.get("is_best", ""),
            })


def write_summary(path: Path, trials: List[Dict[str, Any]], ids: List[int], scores: List[float], best_so_far: List[float]) -> Dict[str, Any]:
    baseline = scores[0]
    best_score = min(scores)
    best_index = scores.index(best_score)
    last_score = scores[-1]
    improvement_abs = baseline - best_score
    improvement_pct: Optional[float]
    if baseline != 0:
        improvement_pct = improvement_abs / abs(baseline) * 100.0
    else:
        improvement_pct = None

    summary = {
        "num_trials": len(trials),
        "baseline_score": baseline,
        "last_score": last_score,
        "best_score": best_score,
        "best_trial_id": ids[best_index],
        "best_trial_index": best_index + 1,
        "improvement_abs_vs_baseline": improvement_abs,
        "improvement_pct_vs_baseline": improvement_pct,
        "lower_score_is_better": True,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


def plot_progress(path: Path, ids: List[int], scores: List[float], best_so_far: List[float], title: str) -> None:
    plt.figure(figsize=(11, 6))
    plt.plot(ids, scores, marker="o", linewidth=1, label="Score trial")
    plt.plot(ids, best_so_far, marker="", linewidth=2.5, label="Best so far")
    
    # Imposta limiti assi seguendo best practice:
    # - origine a 0 per entrambi gli assi
    # - curve occupano circa 3/4 del grafico
    max_score = max(max(scores), max(best_so_far))
    max_id = max(ids)
    plt.xlim(0, max_id * 1.33)  # curve a ~3/4 sull'asse x
    plt.ylim(0, max_score * 1.33)  # curve a ~3/4 sull'asse y
    
    plt.xlabel("Trial")
    plt.ylabel("Score, più basso è meglio")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_improvement(path: Path, ids: List[int], scores: List[float], title: str) -> None:
    baseline = scores[0]
    improvements = []
    for score in scores:
        if baseline == 0:
            improvements.append(0.0)
        else:
            improvements.append((baseline - score) / abs(baseline) * 100.0)

    plt.figure(figsize=(11, 6))
    plt.plot(ids, improvements, marker="o", linewidth=1.5)
    plt.axhline(0, linewidth=1)
    plt.xlabel("Trial")
    plt.ylabel("Miglioramento vs baseline (%)")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera grafici andamento ottimizzazione da trials.jsonl")
    parser.add_argument("trials_jsonl", type=Path, help="Path a optimizer_state/trials.jsonl")
    parser.add_argument("--out-dir", type=Path, default=None, help="Directory output. Default: stessa directory di trials.jsonl")
    parser.add_argument("--title", default=None, help="Titolo grafico")
    args = parser.parse_args()

    trials = load_trials(args.trials_jsonl)
    ids = [get_trial_id(trial, i) for i, trial in enumerate(trials, start=1)]
    scores = [float(trial["score"]) for trial in trials]
    best_so_far = compute_best_so_far(scores)

    out_dir = args.out_dir or args.trials_jsonl.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    title_prefix = args.title or args.trials_jsonl.parent.parent.name or "Optimization"

    progress_png = out_dir / "optimization_progress.png"
    improvement_png = out_dir / "optimization_improvement.png"
    summary_json = out_dir / "optimization_summary.json"
    trials_csv = out_dir / "optimization_trials.csv"

    plot_progress(progress_png, ids, scores, best_so_far, f"{title_prefix}: andamento score")
    plot_improvement(improvement_png, ids, scores, f"{title_prefix}: miglioramento vs baseline")
    summary = write_summary(summary_json, trials, ids, scores, best_so_far)
    write_csv(trials_csv, trials, ids, best_so_far)

    print("Output generati:")
    print(f"  {progress_png}")
    print(f"  {improvement_png}")
    print(f"  {summary_json}")
    print(f"  {trials_csv}")
    print()
    print("Riepilogo:")
    print(f"  trial totali      : {summary['num_trials']}")
    print(f"  baseline score    : {summary['baseline_score']:.6g}")
    print(f"  best score        : {summary['best_score']:.6g}")
    print(f"  best trial id     : {summary['best_trial_id']}")
    if summary["improvement_pct_vs_baseline"] is not None:
        print(f"  miglioramento     : {summary['improvement_pct_vs_baseline']:.2f}%")
    else:
        print("  miglioramento     : n/d, baseline score = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
