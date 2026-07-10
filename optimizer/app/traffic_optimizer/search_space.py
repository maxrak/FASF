from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional

from .utils import load_json


class SearchSpace:
    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.parameters: Dict[str, Dict[str, Any]] = spec.get('parameters', {})
        if not self.parameters:
            raise ValueError('search space senza parameters')

    @classmethod
    def from_file(cls, path):
        return cls(load_json(path))

    def sample_random(self, rng: random.Random) -> Dict[str, Any]:
        return {name: self._sample_one(rng, cfg) for name, cfg in self.parameters.items()}

    def mutate_around_best(self, rng: random.Random, best: Dict[str, Any], strength: float = 0.35) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, cfg in self.parameters.items():
            if rng.random() < 0.25 or name not in best:
                out[name] = self._sample_one(rng, cfg)
            else:
                out[name] = self._mutate_one(rng, cfg, best[name], strength)
        return out

    def _sample_one(self, rng: random.Random, cfg: Dict[str, Any]) -> Any:
        typ = cfg.get('type')
        if typ == 'categorical':
            return rng.choice(cfg['choices'])
        if typ in ('nullable_float', 'nullable_int') and rng.random() < float(cfg.get('null_probability', 0.2)):
            return None
        if typ in ('float', 'nullable_float'):
            low, high = float(cfg['low']), float(cfg['high'])
            if cfg.get('log'):
                return math.exp(rng.uniform(math.log(low), math.log(high)))
            return rng.uniform(low, high)
        if typ in ('int', 'nullable_int'):
            low, high = int(cfg['low']), int(cfg['high'])
            if cfg.get('log'):
                value = int(round(math.exp(rng.uniform(math.log(low), math.log(high)))))
            else:
                value = rng.randint(low, high)
            step = int(cfg.get('step', 1))
            if step > 1:
                value = low + round((value - low) / step) * step
            return int(max(low, min(high, value)))
        raise ValueError(f'tipo parametro non supportato: {typ}')

    def _mutate_one(self, rng: random.Random, cfg: Dict[str, Any], value: Any, strength: float) -> Any:
        typ = cfg.get('type')
        if value is None:
            return self._sample_one(rng, cfg)
        if typ == 'categorical':
            if rng.random() < 0.15:
                return rng.choice(cfg['choices'])
            return value
        if typ in ('nullable_float', 'nullable_int') and rng.random() < float(cfg.get('null_probability', 0.2)) * 0.25:
            return None
        low, high = float(cfg['low']), float(cfg['high'])
        span = high - low
        if cfg.get('log'):
            lv = math.log(max(float(value), low))
            ll, lh = math.log(low), math.log(high)
            nv = math.exp(rng.gauss(lv, (lh - ll) * strength))
        else:
            nv = rng.gauss(float(value), span * strength)
        nv = max(low, min(high, nv))
        if typ in ('int', 'nullable_int'):
            step = int(cfg.get('step', 1))
            iv = int(round(nv))
            if step > 1:
                iv = int(low) + round((iv - int(low)) / step) * step
            return int(max(int(low), min(int(high), iv)))
        return float(nv)

    def suggest_optuna(self, trial) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        for name, cfg in self.parameters.items():
            typ = cfg.get('type')
            if typ == 'categorical':
                params[name] = trial.suggest_categorical(name, cfg['choices'])
            elif typ == 'float':
                params[name] = trial.suggest_float(name, float(cfg['low']), float(cfg['high']), log=bool(cfg.get('log', False)))
            elif typ == 'int':
                params[name] = trial.suggest_int(name, int(cfg['low']), int(cfg['high']), step=int(cfg.get('step', 1)), log=bool(cfg.get('log', False)))
            elif typ == 'nullable_float':
                use_null = trial.suggest_float(name + '.__null_prob', 0.0, 1.0) < float(cfg.get('null_probability', 0.2))
                params[name] = None if use_null else trial.suggest_float(name, float(cfg['low']), float(cfg['high']), log=bool(cfg.get('log', False)))
            elif typ == 'nullable_int':
                use_null = trial.suggest_float(name + '.__null_prob', 0.0, 1.0) < float(cfg.get('null_probability', 0.2))
                params[name] = None if use_null else trial.suggest_int(name, int(cfg['low']), int(cfg['high']), step=int(cfg.get('step', 1)), log=bool(cfg.get('log', False)))
            else:
                raise ValueError(f'tipo parametro non supportato: {typ}')
        return params
