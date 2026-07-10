from __future__ import annotations

import argparse
from pathlib import Path

from .algorithms.random_search import run_random_search
from .algorithms.optuna_tpe import run_optuna_tpe
from .runner import SimulationRunner
from .search_space import SearchSpace


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Ottimizzatore per simulazioni Mininet/flussi')
    p.add_argument('test_name', help='Nome del test, es. test5')
    p.add_argument('--project-root', default='.', help='Root progetto con script 2/3/4 e shared/')
    p.add_argument('--base-config', required=True, help='Config base del client')
    p.add_argument('--output-config', required=True, help='Config scritta a ogni trial e letta dal client')
    p.add_argument('--search-space', default=str(Path(__file__).parent / 'config' / 'search_space.json'))
    p.add_argument('--state-root', default='optimizer_state', help='Directory per checkpoint e risultati optimizer')
    p.add_argument('--algorithm', choices=['random', 'optuna'], default='random')
    p.add_argument('--max-trials', type=int, default=30)
    p.add_argument('--max-hours', type=float, default=None)
    p.add_argument('--timeout-s', type=float, default=None, help='Timeout per ogni comando della pipeline')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--resume', action='store_true', help='Mantiene checkpoint esistenti')
    p.add_argument('--dry-run', action='store_true', help='Non lancia gli script, usa sample report se presente')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    state_dir = (project_root / args.state_root / args.test_name).resolve()
    if not args.resume and state_dir.exists():
        print(f'[warn] stato esistente in {state_dir}. Uso comunque i checkpoint presenti. Per azzerare, elimina la directory.')

    space = SearchSpace.from_file(Path(args.search_space).resolve())
    runner = SimulationRunner(
        project_root=project_root,
        test_name=args.test_name,
        base_config_path=Path(args.base_config),
        output_config_path=Path(args.output_config),
        state_dir=state_dir,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
    )

    print(f'[start] test={args.test_name} algorithm={args.algorithm} state={state_dir}')
    print(f'[info] stop-file: {state_dir / "STOP"}')

    if args.algorithm == 'random':
        run_random_search(runner, space, args.max_trials, seed=args.seed, max_hours=args.max_hours)
    elif args.algorithm == 'optuna':
        run_optuna_tpe(runner, space, args.max_trials, seed=args.seed, max_hours=args.max_hours)
    else:
        raise ValueError(args.algorithm)

    print(f'[done] best_score={runner.best_score:.6g}')
    if runner.best_config:
        print(f'[done] best_config={state_dir / "best_config.json"}')


if __name__ == '__main__':
    main()
