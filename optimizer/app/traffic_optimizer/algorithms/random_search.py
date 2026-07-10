from __future__ import annotations

import random
import time
from typing import Optional

from ..runner import SimulationRunner
from ..search_space import SearchSpace


def run_random_search(
    runner: SimulationRunner,
    space: SearchSpace,
    max_trials: int,
    seed: int = 42,
    max_hours: Optional[float] = None,
    exploit_probability: float = 0.65,
) -> None:
    rng = random.Random(seed)
    deadline = None if max_hours is None else time.time() + max_hours * 3600.0

    for _ in range(max_trials):
        if runner.should_stop():
            print(f'[stop] stop-file trovato: {runner.stop_file}')
            break
        if deadline is not None and time.time() >= deadline:
            print('[stop] limite di tempo raggiunto')
            break

        if runner.best_params and rng.random() < exploit_probability:
            params = space.mutate_around_best(rng, runner.best_params, strength=rng.uniform(0.12, 0.45))
            mode = 'mutate-best'
        else:
            params = space.sample_random(rng)
            mode = 'explore'

        result = runner.evaluate(params, algorithm=f'random:{mode}')
        print(
            f"[trial {result['trial_no']}] score={result['score']:.6g} "
            f"status={result['status']} improved={result['improved']} duration={result['duration_s']:.1f}s"
        )
