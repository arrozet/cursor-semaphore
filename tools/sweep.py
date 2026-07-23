"""Parameter sweep for the controller over public + synthetic scenarios.

Loads the controller module fresh per run, overrides module-level constants,
and reports the robust objective: 0.2*public + 0.8*synthetic geometric cost
ratio vs the fixed-time baseline (lower is better), plus worst case.

Usage: python tools/sweep.py
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
sys.path.insert(0, str(SOURCE))

from traffic_arena.engine import fixed_time_controller, run_scenario  # noqa: E402
from traffic_arena.scenarios import PUBLIC_SCENARIOS  # noqa: E402

from bench import make_synthetic  # noqa: E402

ALL_SCENARIOS = list(PUBLIC_SCENARIOS) + make_synthetic()
BASELINES = {}


def baseline_cost(scenario):
    if scenario.id not in BASELINES:
        BASELINES[scenario.id] = run_scenario(
            scenario, fixed_time_controller, record_replay=False
        ).metrics.cost
    return BASELINES[scenario.id]


def load_module(overrides):
    spec = importlib.util.spec_from_file_location("team_controller", SOURCE / "controller.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for key, value in overrides.items():
        setattr(module, key, value)
    return module


def geo_mean(values):
    return math.exp(sum(math.log(max(v, 1e-9)) for v in values) / len(values))


def evaluate(overrides):
    public, synth = [], []
    for scenario in ALL_SCENARIOS:
        module = load_module(overrides)
        cost = run_scenario(scenario, module.control, record_replay=False).metrics.cost
        ratio = cost / baseline_cost(scenario)
        (public if scenario.id in {s.id for s in PUBLIC_SCENARIOS} else synth).append(ratio)
    combined = 0.2 * geo_mean(public) + 0.8 * geo_mean(synth)
    return combined, geo_mean(public), geo_mean(synth), max(public + synth)


def main():
    configs = []
    for name, overrides in CONFIGS:
        combined, pub, syn, worst = evaluate(overrides)
        configs.append((combined, name, pub, syn, worst))
        print(f"{name:<40} comb={combined:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")
    configs.sort()
    print("\nbest:", configs[0][1])


CONFIGS = [
    ("current", {}),
    ("no-downstream", {"USE_DOWNSTREAM": False}),
    ("ratio-2.0", {"SWITCH_RATIO": 2.0}),
    ("ratio-1.1", {"SWITCH_RATIO": 1.1}),
    ("maxgreen-25", {"MAX_GREEN": 25}),
    ("no-wait", {"WAIT_WEIGHT": 0.0}),
    ("wait-1.5", {"WAIT_WEIGHT": 1.5}),
]

if __name__ == "__main__":
    main()
