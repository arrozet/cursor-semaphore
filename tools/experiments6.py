"""Final cross sweep: hybrid (simple local) thresholds x sync cycle.

Usage: python tools/experiments6.py
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


def axis_queues(info):
    queues = info["queues"]
    return queues.get("N", 0) + queues.get("S", 0), queues.get("E", 0) + queues.get("W", 0)


def make_hybrid(cycle=40, ema=0.9, min_share=0.25, low=2.0, high=4.0):
    sync_mem = {"phase": "NS_GREEN", "age": 0, "share": 0.5}
    memory = {}
    mode_mem = {"mode": "sync"}

    def control(state):
        rows, cols = state["map"]["rows"], state["map"]["cols"]

        ns = ew = 0.0
        for info in state["intersections"].values():
            a, b = axis_queues(info)
            ns += a
            ew += b
        total = ns + ew
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - min_share, max(min_share, raw))
        share = sync_mem["share"] * ema + share * (1 - ema)
        sync_mem["share"] = share
        sync_mem["age"] += 1
        if sync_mem["phase"] == "NS_GREEN" and sync_mem["age"] >= share * cycle:
            sync_mem["phase"], sync_mem["age"] = "EW_GREEN", 0
        elif sync_mem["phase"] == "EW_GREEN" and sync_mem["age"] >= (1 - share) * cycle:
            sync_mem["phase"], sync_mem["age"] = "NS_GREEN", 0

        mean_queue = total / max(len(state["intersections"]), 1)
        if mode_mem["mode"] == "sync" and mean_queue < low:
            mode_mem["mode"] = "local"
        elif mode_mem["mode"] == "local" and mean_queue > high:
            mode_mem["mode"] = "sync"
        use_local = mode_mem["mode"] == "local" or (rows == 1 and cols == 1)

        decisions = {}
        for item, info in state["intersections"].items():
            if not use_local:
                decisions[item] = sync_mem["phase"]
                memory[item] = sync_mem["phase"]
                continue
            phase = info["phase"]
            if phase not in ("NS_GREEN", "EW_GREEN"):
                decisions[item] = memory.get(item, "NS_GREEN")
                continue
            other = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"
            a, b = axis_queues(info)
            cur, oth = (a, b) if phase == "NS_GREEN" else (b, a)
            decision = phase
            if info["can_switch"]:
                if cur == 0 and oth > 0:
                    decision = other
                elif oth > cur * 1.35 + 1.0:
                    decision = other
                elif info["phase_age"] >= 45 and oth > 0:
                    decision = other
            decisions[item] = decision
            memory[item] = decision
        return decisions

    return control


def evaluate(factory):
    pub, syn, per_map = [], [], {}
    for scenario in ALL_SCENARIOS:
        cost = run_scenario(scenario, factory(), record_replay=False).metrics.cost
        ratio = cost / baseline_cost(scenario)
        per_map[scenario.id] = ratio
        (pub if scenario.id in PUBLIC_IDS else syn).append(ratio)
    return 0.2 * geo_mean(pub) + 0.8 * geo_mean(syn), geo_mean(pub), geo_mean(syn), max(pub + syn), per_map


def main():
    results = []
    for cycle in (40, 50):
        for low, high in ((1.5, 3.0), (2.0, 4.0), (2.5, 4.5)):
            name = f"c{cycle}-q{low}-{high}"
            comb, pub, syn, worst, per_map = evaluate(lambda: make_hybrid(cycle, low=low, high=high))
            results.append((comb, worst, name, pub, syn, per_map))
            print(f"{name:<18} comb={comb:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")
    results.sort(key=lambda r: (r[0] + 0.3 * max(0, r[1] - 1.0)))
    print("\nbest:", results[0][2])
    for map_id, ratio in results[0][5].items():
        print(f"  {map_id:<22}{ratio:.3f}")


if __name__ == "__main__":
    main()
