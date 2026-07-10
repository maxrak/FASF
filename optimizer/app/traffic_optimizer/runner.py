from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .objective import score_report
from .utils import apply_params, append_jsonl, load_json, run_command, save_json


class SimulationRunner:
    def __init__(
        self,
        project_root: Path,
        test_name: str,
        base_config_path: Path,
        output_config_path: Path,
        state_dir: Path,
        timeout_s: Optional[float] = None,
        dry_run: bool = False,
    ):
        self.project_root = project_root.resolve()
        self.test_name = test_name
        self.base_config_path = base_config_path.resolve()
        self.output_config_path = output_config_path.resolve()
        self.state_dir = state_dir.resolve()
        self.timeout_s = timeout_s
        self.dry_run = dry_run
        self.report_path = self.project_root / 'shared' / 'results' / test_name / 'report_data.json'
        self.stop_file = self.state_dir / 'STOP'
        self.base_config = load_json(self.base_config_path)
        self.best_score = float('inf')
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_config: Optional[Dict[str, Any]] = None
        self.trial_no = 0
        self._load_checkpoint()

    def should_stop(self) -> bool:
        return self.stop_file.exists()

    def _load_checkpoint(self) -> None:
        ckpt = self.state_dir / 'checkpoint.json'
        if ckpt.exists():
            data = load_json(ckpt)
            self.best_score = float(data.get('best_score', float('inf')))
            self.best_params = data.get('best_params')
            self.best_config = data.get('best_config')
            self.trial_no = int(data.get('trial_no', 0))

    def _save_checkpoint(self) -> None:
        save_json(self.state_dir / 'checkpoint.json', {
            'trial_no': self.trial_no,
            'best_score': self.best_score,
            'best_params': self.best_params,
            'best_config': self.best_config,
            'test_name': self.test_name,
            'updated_at': time.time(),
        })

    def evaluate(self, params: Dict[str, Any], algorithm: str) -> Dict[str, Any]:
        self.trial_no += 1
        started = time.time()
        candidate_config = apply_params(self.base_config, params)
        save_json(self.output_config_path, candidate_config)

        trial_dir = self.state_dir / 'trials' / f'{self.trial_no:05d}'
        trial_dir.mkdir(parents=True, exist_ok=True)
        save_json(trial_dir / 'candidate_config.json', candidate_config)
        save_json(trial_dir / 'params.json', params)
        log_file = trial_dir / 'commands.log'

        status = 'ok'
        error = None
        score_data: Dict[str, Any]
        report: Optional[Dict[str, Any]] = None
        try:
            if not self.dry_run:
                run_command(['./2.replicate_slow.sh', self.test_name], self.project_root, self.timeout_s, log_file)
                run_command(['./3.regenerate_flows.sh', self.test_name], self.project_root, self.timeout_s, log_file)
                run_command(['./4.compare_flows', self.test_name], self.project_root, self.timeout_s, log_file)
                if not self.report_path.exists():
                    raise FileNotFoundError(f'report non trovato: {self.report_path}')
                report = load_json(self.report_path)
            else:
                sample = Path(__file__).resolve().parent / 'sample_report_data.json'
                if not sample.exists():
                    sample = Path(__file__).resolve().parents[1] / 'sample_report_data.json'
                report = load_json(sample) if sample.exists() else {'summary': []}
            score_data = score_report(report)
        except Exception as exc:
            status = 'failed'
            error = repr(exc)
            score_data = {'score': float('inf'), 'top_features': []}

        score = float(score_data['score'])
        improved = score < self.best_score
        if improved:
            self.best_score = score
            self.best_params = params
            self.best_config = candidate_config
            save_json(self.state_dir / 'best_config.json', candidate_config)
            save_json(self.state_dir / 'best_params.json', params)
            if report is not None:
                save_json(self.state_dir / 'best_report_data.json', report)

        if report is not None:
            save_json(trial_dir / 'report_data.json', report)
            if not self.dry_run and self.report_path.exists():
                try:
                    shutil.copy2(self.report_path, trial_dir / 'report_data.source.json')
                except OSError:
                    pass

        result = {
            'trial_no': self.trial_no,
            'algorithm': algorithm,
            'status': status,
            'error': error,
            'score': score,
            'improved': improved,
            'duration_s': time.time() - started,
            'params': params,
            'top_features': score_data.get('top_features', []),
            'timestamp': time.time(),
        }
        save_json(trial_dir / 'result.json', result)
        append_jsonl(self.state_dir / 'trials.jsonl', result)
        self._save_checkpoint()
        return result
