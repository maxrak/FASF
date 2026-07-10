from __future__ import annotations

import argparse
import random
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .objective import score_report
from .search_space import SearchSpace
from .utils import apply_params, append_jsonl, load_json, save_json


def _state_dir(state_root: Path, test_name: str) -> Path:
    d = (state_root / test_name).resolve()
    d.mkdir(parents=True, exist_ok=True)
    (d / 'trials').mkdir(parents=True, exist_ok=True)
    return d


def _load_checkpoint(state_dir: Path) -> Dict[str, Any]:
    p = state_dir / 'checkpoint.json'
    if p.exists():
        return load_json(p)
    return {
        'trial_no': 0,
        'best_score': float('inf'),
        'best_params': None,
        'best_config': None,
    }


def _save_checkpoint(state_dir: Path, data: Dict[str, Any]) -> None:
    data = dict(data)
    data['updated_at'] = time.time()
    save_json(state_dir / 'checkpoint.json', data)


def _make_optuna_study(state_dir: Path, test_name: str, seed: int):
    try:
        import optuna
    except ImportError as exc:
        raise RuntimeError('Optuna non installato nel container optimizer. Installa requirements.txt.') from exc
    storage = f"sqlite:///{state_dir / 'optuna.db'}"
    sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True, group=True)
    return optuna.create_study(
        study_name=f'traffic-optimizer-{test_name}',
        direction='minimize',
        sampler=sampler,
        storage=storage,
        load_if_exists=True,
    )


def _sample_random(space: SearchSpace, ckpt: Dict[str, Any], seed: int, trial_no: int, exploit_probability: float) -> Dict[str, Any]:
    # Deterministico per trial: utile quando il processo viene riavviato spesso.
    rng = random.Random(seed + trial_no * 1000003)
    best_params = ckpt.get('best_params')
    if best_params and rng.random() < exploit_probability:
        return space.mutate_around_best(rng, best_params, strength=rng.uniform(0.12, 0.45))
    return space.sample_random(rng)


def cmd_propose(args: argparse.Namespace) -> int:
    state_dir = _state_dir(Path(args.state_root), args.test_name)
    stop_file = state_dir / 'STOP'
    if stop_file.exists():
        print(f'[stop] stop-file trovato: {stop_file}')
        return 20

    ckpt = _load_checkpoint(state_dir)
    current_trial = int(ckpt.get('trial_no', 0))
    if args.max_trials is not None and current_trial >= args.max_trials:
        print(f'[stop] max-trials raggiunto: {current_trial}/{args.max_trials}')
        return 21

    pending = state_dir / 'pending_trial.json'
    if pending.exists() and not args.overwrite_pending:
        data = load_json(pending)
        print(f"[pending] trial {data.get('trial_no')} gia proposto. Usa observe o --overwrite-pending.")
        return 22

    trial_no = current_trial + 1
    base_config = load_json(Path(args.base_config))
    space = SearchSpace.from_file(Path(args.search_space))

    optuna_trial_number: Optional[int] = None
    if args.algorithm == 'random':
        params = _sample_random(space, ckpt, args.seed, trial_no, args.exploit_probability)
        algorithm_label = 'random-host'
    elif args.algorithm == 'optuna':
        study = _make_optuna_study(state_dir, args.test_name, args.seed)
        trial = study.ask()
        optuna_trial_number = trial.number
        params = space.suggest_optuna(trial)
        algorithm_label = 'optuna-tpe-host'
    else:
        raise ValueError(args.algorithm)

    candidate_config = apply_params(base_config, params)
    output_config = Path(args.output_config)
    save_json(output_config, candidate_config)

    trial_dir = state_dir / 'trials' / f'{trial_no:05d}'
    trial_dir.mkdir(parents=True, exist_ok=True)
    save_json(trial_dir / 'candidate_config.json', candidate_config)
    save_json(trial_dir / 'params.json', params)

    pending_data = {
        'trial_no': trial_no,
        'test_name': args.test_name,
        'algorithm': algorithm_label,
        'algorithm_kind': args.algorithm,
        'optuna_trial_number': optuna_trial_number,
        'params': params,
        'candidate_config': candidate_config,
        'output_config': str(output_config),
        'started_at': time.time(),
    }
    save_json(pending, pending_data)
    print(f'[propose] trial={trial_no} algorithm={algorithm_label} config={output_config}')
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    state_dir = _state_dir(Path(args.state_root), args.test_name)
    pending_path = state_dir / 'pending_trial.json'
    if not pending_path.exists():
        print(f'[error] pending_trial.json non trovato in {state_dir}')
        return 30

    pending = load_json(pending_path)
    trial_no = int(pending['trial_no'])
    trial_dir = state_dir / 'trials' / f'{trial_no:05d}'
    trial_dir.mkdir(parents=True, exist_ok=True)

    report_path = Path(args.report_path)
    status = 'ok'
    error = None
    report: Optional[Dict[str, Any]] = None
    try:
        if not report_path.exists():
            raise FileNotFoundError(f'report non trovato: {report_path}')
        report = load_json(report_path)
        score_data = score_report(report)
    except Exception as exc:
        status = 'failed'
        error = repr(exc)
        score_data = {'score': float('inf'), 'top_features': []}

    score = float(score_data['score'])
    ckpt = _load_checkpoint(state_dir)
    best_score = float(ckpt.get('best_score', float('inf')))
    improved = score < best_score

    if improved:
        ckpt['best_score'] = score
        ckpt['best_params'] = pending.get('params')
        ckpt['best_config'] = pending.get('candidate_config')
        save_json(state_dir / 'best_config.json', pending.get('candidate_config'))
        save_json(state_dir / 'best_params.json', pending.get('params'))
        if report is not None:
            save_json(state_dir / 'best_report_data.json', report)

    ckpt['trial_no'] = max(int(ckpt.get('trial_no', 0)), trial_no)
    ckpt['test_name'] = args.test_name
    _save_checkpoint(state_dir, ckpt)

    if report is not None:
        save_json(trial_dir / 'report_data.json', report)
        try:
            shutil.copy2(report_path, trial_dir / 'report_data.source.json')
        except OSError:
            pass

    result = {
        'trial_no': trial_no,
        'algorithm': pending.get('algorithm'),
        'status': status,
        'error': error,
        'score': score,
        'improved': improved,
        'duration_s': time.time() - float(pending.get('started_at', time.time())),
        'params': pending.get('params'),
        'top_features': score_data.get('top_features', []),
        'timestamp': time.time(),
    }
    save_json(trial_dir / 'result.json', result)
    append_jsonl(state_dir / 'trials.jsonl', result)

    if pending.get('algorithm_kind') == 'optuna':
        try:
            study = _make_optuna_study(state_dir, args.test_name, args.seed)
            trial_number = pending.get('optuna_trial_number')
            if trial_number is not None:
                study.tell(int(trial_number), score)
        except Exception as exc:
            # Non rendere inutilizzabile il trial se Optuna tell fallisce: storico e checkpoint sono gia salvi.
            result['optuna_tell_error'] = repr(exc)
            save_json(trial_dir / 'result.json', result)

    pending_path.unlink(missing_ok=True)
    print(
        f"[observe] trial={trial_no} score={score:.6g} status={status} "
        f"improved={improved} best={float(ckpt.get('best_score', score)):.6g}"
    )
    return 0 if status == 'ok' else 31


def cmd_status(args: argparse.Namespace) -> int:
    state_dir = _state_dir(Path(args.state_root), args.test_name)
    ckpt = _load_checkpoint(state_dir)
    print(f"test={args.test_name}")
    print(f"state_dir={state_dir}")
    print(f"trial_no={ckpt.get('trial_no', 0)}")
    print(f"best_score={ckpt.get('best_score', float('inf'))}")
    print(f"stop_file={state_dir / 'STOP'}")
    print(f"pending={(state_dir / 'pending_trial.json').exists()}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Host-driven optimizer stepper')
    sub = p.add_subparsers(dest='command', required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('test_name')
    common.add_argument('--state-root', default='/optimizer_state')
    common.add_argument('--seed', type=int, default=42)

    pp = sub.add_parser('propose', parents=[common])
    pp.add_argument('--algorithm', choices=['random', 'optuna'], default='random')
    pp.add_argument('--base-config', required=True)
    pp.add_argument('--output-config', required=True)
    pp.add_argument('--search-space', default=str(Path(__file__).parent / 'config' / 'search_space.json'))
    pp.add_argument('--max-trials', type=int, default=None)
    pp.add_argument('--exploit-probability', type=float, default=0.65)
    pp.add_argument('--overwrite-pending', action='store_true')

    op = sub.add_parser('observe', parents=[common])
    op.add_argument('--report-path', required=True)

    sp = sub.add_parser('status', parents=[common])

    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == 'propose':
        raise SystemExit(cmd_propose(args))
    if args.command == 'observe':
        raise SystemExit(cmd_observe(args))
    if args.command == 'status':
        raise SystemExit(cmd_status(args))
    raise ValueError(args.command)


if __name__ == '__main__':
    main()
