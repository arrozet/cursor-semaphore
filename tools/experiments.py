"""Structural experiments: compare controller architectures quickly.

Each candidate is a factory returning a fresh `control(state)` per map.
Reports cost ratio vs fixed baseline per scenario plus robust aggregates.

Usage: python tools/experiments.py
"""

from __future__ import annotations

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
PUBLIC_IDS = {s.id for s in PUBLIC_SCENARIOS}
BASELINES = {}


def baseline_cost(scenario):
    if scenario.id not in BASELINES:
        BASELINES[scenario.id] = run_scenario(
            scenario, fixed_time_controller, record_replay=False
        ).metrics.cost
    return BASELINES[scenario.id]


def geo_mean(values):
    return math.exp(sum(math.log(max(v, 1e-9)) for v in values) / len(values))


# ---------------------------------------------------------------- candidates

def make_current():
    import importlib.util

    spec = importlib.util.spec_from_file_location("team_controller", SOURCE / "controller.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.control


def make_global_sync(cycle=30, min_share=0.25):
    """All intersections share one phase; split adapts to global queues."""
    state_mem = {"phase": "NS_GREEN", "age": 0}

    def control(state):
        ns = ew = 0
        for info in state["intersections"].values():
            queues = info["queues"]
            ns += queues.get("N", 0) + queues.get("S", 0)
            ew += queues.get("E", 0) + queues.get("W", 0)
        total = ns + ew
        share_ns = 0.5 if total == 0 else min(1 - min_share, max(min_share, ns / total))
        green_ns = share_ns * cycle
        state_mem["age"] += 1
        if state_mem["phase"] == "NS_GREEN" and state_mem["age"] >= green_ns:
            state_mem["phase"], state_mem["age"] = "EW_GREEN", 0
        elif state_mem["phase"] == "EW_GREEN" and state_mem["age"] >= cycle - green_ns:
            state_mem["phase"], state_mem["age"] = "NS_GREEN", 0
        return {item: state_mem["phase"] for item in state["intersections"]}

    return control


def make_local_inertia(min_green=12, ratio=1.5, margin=2.0, max_green=40):
    """Local queue pressure, but with a long self-imposed minimum green."""
    memory = {}

    def control(state):
        decisions = {}
        for item, info in state["intersections"].items():
            phase = info["phase"]
            if phase not in ("NS_GREEN", "EW_GREEN"):
                decisions[item] = memory.get(item, "NS_GREEN")
                continue
            other = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"
            queues = info["queues"]
            ns = queues.get("N", 0) + queues.get("S", 0)
            ew = queues.get("E", 0) + queues.get("W", 0)
            cur, oth = (ns, ew) if phase == "NS_GREEN" else (ew, ns)
            decision = phase
            if info["can_switch"] and info["phase_age"] >= min_green:
                if cur == 0 and oth > 0:
                    decision = other
                elif info["phase_age"] >= max_green and oth > 0:
                    decision = other
                elif oth > cur * ratio + margin:
                    decision = other
            decisions[item] = decision
            memory[item] = decision
        return decisions

    return control


def make_sync_offsetless(base=15):
    """Baseline-like alternation, but skip switch when own axis still busy and
    other side empty (cheap adaptivity on top of full sync)."""
    memory = {}

    def control(state):
        decisions = {}
        target = "NS_GREEN" if state["tick"] % (2 * base) < base else "EW_GREEN"
        for item, info in state["intersections"].items():
            queues = info["queues"]
            ns = queues.get("N", 0) + queues.get("S", 0)
            ew = queues.get("E", 0) + queues.get("W", 0)
            wanted = target
            if target == "NS_GREEN" and ns == 0 and ew > 0:
                wanted = "EW_GREEN"
            elif target == "EW_GREEN" and ew == 0 and ns > 0:
                wanted = "NS_GREEN"
            decisions[item] = wanted
            memory[item] = wanted
        return decisions

    return control


CANDIDATES = [
    ("current-backpressure", make_current),
    ("global-sync-c30", lambda: make_global_sync(30)),
    ("global-sync-c40", lambda: make_global_sync(40)),
    ("local-inertia-12", lambda: make_local_inertia(12)),
    ("local-inertia-8", lambda: make_local_inertia(8)),
    ("sync-skip-empty", make_sync_offsetless),
]


def main():
    names = [name for name, _ in CANDIDATES]
    print(f"{'scenario':<22}" + "".join(f"{name[:14]:>16}" for name in names))
    ratios = {name: {"pub": [], "syn": []} for name in names}
    for scenario in ALL_SCENARIOS:
        row = f"{scenario.id:<22}"
        for name, factory in CANDIDATES:
            cost = run_scenario(scenario, factory(), record_replay=False).metrics.cost
            ratio = cost / baseline_cost(scenario)
            bucket = "pub" if scenario.id in PUBLIC_IDS else "syn"
            ratios[name][bucket].append(ratio)
            row += f"{ratio:>16.3f}"
        print(row)
    print()
    for name in names:
        pub = geo_mean(ratios[name]["pub"])
        syn = geo_mean(ratios[name]["syn"])
        worst = max(ratios[name]["pub"] + ratios[name]["syn"])
        print(f"{name:<24} comb={0.2 * pub + 0.8 * syn:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")


if __name__ == "__main__":
    main()
