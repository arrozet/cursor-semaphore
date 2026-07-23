"""Fine sweep over the global-sync controller: cycle x EMA x min_share,
plus wait-weight and an endgame variant.

Usage: python tools/experiments3.py
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


def make_sync(cycle=50, min_share=0.25, ema=0.9, wait_weight=0.0):
    mem = {"phase": "NS_GREEN", "age": 0, "share": 0.5}

    def control(state):
        ns = ew = 0.0
        for info in state["intersections"].values():
            queues = info["queues"]
            ns += queues.get("N", 0) + queues.get("S", 0)
            ew += queues.get("E", 0) + queues.get("W", 0)
            if wait_weight:
                oldest = info["oldest_wait"]
                ns += wait_weight * math.sqrt(oldest.get("N", 0) + oldest.get("S", 0))
                ew += wait_weight * math.sqrt(oldest.get("E", 0) + oldest.get("W", 0))
        total = ns + ew
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - min_share, max(min_share, raw))
        share = mem["share"] * ema + share * (1 - ema)
        mem["share"] = share
        green_ns = share * cycle
        mem["age"] += 1
        if mem["phase"] == "NS_GREEN" and mem["age"] >= green_ns:
            mem["phase"], mem["age"] = "EW_GREEN", 0
        elif mem["phase"] == "EW_GREEN" and mem["age"] >= cycle - green_ns:
            mem["phase"], mem["age"] = "NS_GREEN", 0
        return {item: mem["phase"] for item in state["intersections"]}

    return control


def evaluate(factory):
    pub, syn = [], []
    for scenario in ALL_SCENARIOS:
        cost = run_scenario(scenario, factory(), record_replay=False).metrics.cost
        ratio = cost / baseline_cost(scenario)
        (pub if scenario.id in PUBLIC_IDS else syn).append(ratio)
    return 0.2 * geo_mean(pub) + 0.8 * geo_mean(syn), geo_mean(pub), geo_mean(syn), max(pub + syn)


def main():
    results = []
    for cycle in (40, 50, 60, 70):
        for ema in (0.85, 0.9, 0.95):
            for min_share in (0.25, 0.3):
                name = f"c{cycle}-e{ema}-s{min_share}"
                comb, pub, syn, worst = evaluate(lambda: make_sync(cycle, min_share, ema))
                results.append((comb, worst, name, pub, syn))
                print(f"{name:<22} comb={comb:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")
    for wait_weight in (0.5, 1.0):
        name = f"c60-e0.9-w{wait_weight}"
        comb, pub, syn, worst = evaluate(lambda: make_sync(60, 0.25, 0.9, wait_weight))
        results.append((comb, worst, name, pub, syn))
        print(f"{name:<22} comb={comb:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")

    results.sort(key=lambda r: (r[0], r[1]))
    print("\ntop 5:")
    for comb, worst, name, pub, syn in results[:5]:
        print(f"  {name:<20} comb={comb:.3f} worst={worst:.3f} pub={pub:.3f} syn={syn:.3f}")


if __name__ == "__main__":
    main()
