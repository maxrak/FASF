from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ..runner import SimulationRunner
from ..search_space import SearchSpace


def run_optuna_tpe(
    runner: SimulationRunner,
    space: SearchSpace,
    max_trials: int,
    seed: int = 42,
    max_hours: Optional[float] = None,
) -> None:
    try:
        import optuna
    except ImportError as exc:
        raise RuntimeError('Optuna non installato. Esegui: pip install optuna') from exc

    storage_path = runner.state_dir / 'optuna.db'
    storage = f'sqlite:///{storage_path}'
    sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True, group=True, n_startup_trials=5)
    study = optuna.create_study(
        study_name=f'traffic-optimizer-{runner.test_name}',
        direction='minimize',
        sampler=sampler,
        storage=storage,
        load_if_exists=True,
    )

    deadline = None if max_hours is None else time.time() + max_hours * 3600.0

    def objective(trial):
        if runner.should_stop():
            raise optuna.exceptions.TrialPruned('stop-file trovato')
        if deadline is not None and time.time() >= deadline:
            raise optuna.exceptions.TrialPruned('limite di tempo raggiunto')
        params = space.suggest_optuna(trial)
        result = runner.evaluate(params, algorithm='optuna-tpe')
        trial.set_user_attr('optimizer_trial_no', result['trial_no'])
        trial.set_user_attr('status', result['status'])
        trial.set_user_attr('improved', result['improved'])
        if result['status'] != 'ok':
            return float('inf')
        print(
            f"[trial {result['trial_no']}] score={result['score']:.6g} "
            f"status={result['status']} improved={result['improved']} duration={result['duration_s']:.1f}s"
        )
        return float(result['score'])

    completed_before = len(study.trials)
    remaining = max(0, max_trials - completed_before)
    if remaining == 0:
        print('[optuna] max_trials gia raggiunto nello studio esistente')
        return

    try:
        study.optimize(objective, n_trials=remaining, gc_after_trial=True)
    except KeyboardInterrupt:
        print('[stop] KeyboardInterrupt: stato salvato, puoi riprendere con --resume')
    print(f'[optuna] best_value={study.best_value if study.best_trial else None}')
