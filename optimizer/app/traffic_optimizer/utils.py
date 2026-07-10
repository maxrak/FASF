from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')
    tmp.replace(path)


def append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True)
        f.write('\n')


def deep_set(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    cur = config
    parts = dotted_key.split('.')
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def deep_get(config: Dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    cur: Any = config
    for part in dotted_key.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def apply_params(base_config: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_config)
    for key, value in params.items():
        deep_set(candidate, key, value)
    return candidate


def run_command(command: Iterable[str], cwd: Path, timeout_s: Optional[float], log_file: Optional[Path] = None) -> None:
    env = os.environ.copy()
    start = time.time()
    with subprocess.Popen(
        list(command), cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, preexec_fn=os.setsid, env=env
    ) as proc:
        try:
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with log_file.open('a', encoding='utf-8') as log:
                    for line in proc.stdout or []:
                        log.write(line)
                        log.flush()
                        if timeout_s and time.time() - start > timeout_s:
                            raise subprocess.TimeoutExpired(list(command), timeout_s)
            else:
                for _ in proc.stdout or []:
                    if timeout_s and time.time() - start > timeout_s:
                        raise subprocess.TimeoutExpired(list(command), timeout_s)
            rc = proc.wait()
            if rc != 0:
                raise subprocess.CalledProcessError(rc, list(command))
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
            raise
