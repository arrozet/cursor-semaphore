"""Refine the global-sync family of controllers.

Usage: python tools/experiments2.py
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


def make_global_sync(cycle=40, min_share=0.25, wait_weight=0.0, ema=0.0, deviate=False):
    mem = {"phase": "NS_GREEN", "age": 0, "share": 0.5}

    def control(state):
        ns = ew = 0.0
        for info in state["intersections"].values():
            queues = info["queues"]
            oldest = info["oldest_wait"]
            ns += queues.get("N", 0) + queues.get("S", 0)
            ew += queues.get("E", 0) + queues.get("W", 0)
            if wait_weight:
                ns += wait_weight * math.sqrt(oldest.get("N", 0) + oldest.get("S", 0))
                ew += wait_weight * math.sqrt(oldest.get("E", 0) + oldest.get("W", 0))
        total = ns + ew
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - min_share, max(min_share, raw))
        if ema:
            share = mem["share"] * ema + share * (1 - ema)
        mem["share"] = share
        green_ns = share * cycle
        mem["age"] += 1
        if mem["phase"] == "NS_GREEN" and mem["age"] >= green_ns:
            mem["phase"], mem["age"] = "EW_GREEN", 0
        elif mem["phase"] == "EW_GREEN" and mem["age"] >= cycle - green_ns:
            mem["phase"], mem["age"] = "NS_GREEN", 0

        decisions = {}
        for item, info in state["intersections"].items():
            wanted = mem["phase"]
            if deviate:
                queues = info["queues"]
                ns_local = queues.get("N", 0) + queues.get("S", 0)
                ew_local = queues.get("E", 0) + queues.get("W", 0)
                if wanted == "NS_GREEN" and ns_local == 0 and ew_local >= 3:
                    wanted = "EW_GREEN"
                elif wanted == "EW_GREEN" and ew_local == 0 and ns_local >= 3:
                    wanted = "NS_GREEN"
            decisions[item] = wanted
        return decisions

    return control


def make_adaptive_cycle(base_cycle=30, max_cycle=70, min_share=0.25):
    """Cycle length grows with congestion (per-intersection mean queue)."""
    mem = {"phase": "NS_GREEN", "age": 0}

    def control(state):
        ns = ew = 0.0
        count = len(state["intersections"])
        for info in state["intersections"].values():
            queues = info["queues"]
            ns += queues.get("N", 0) + queues.get("S", 0)
            ew += queues.get("E", 0) + queues.get("W", 0)
        total = ns + ew
        mean_queue = total / max(count, 1)
        cycle = min(max_cycle, base_cycle + 2.5 * mean_queue)
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - min_share, max(min_share, raw))
        green_ns = share * cycle
        mem["age"] += 1
        if mem["phase"] == "NS_GREEN" and mem["age"] >= green_ns:
            mem["phase"], mem["age"] = "EW_GREEN", 0
        elif mem["phase"] == "EW_GREEN" and mem["age"] >= cycle - green_ns:
            mem["phase"], mem["age"] = "NS_GREEN", 0
        return {item: mem["phase"] for item in state["intersections"]}

    return control


def make_corridor_sync(cycle=40, min_share=0.25):
    """Same global schedule, but shares computed per column/row corridor and
    each intersection follows the stronger of its two corridors."""
    mem = {"age": 0, "flip": 0}

    def control(state):
        # Global clock keeps everyone aligned; share from global demand.
        ns = ew = 0.0
        for info in state["intersections"].values():
            queues = info["queues"]
            ns += queues.get("N", 0) + queues.get("S", 0)
            ew += queues.get("E", 0) + queues.get("W", 0)
        total = ns + ew
        share = min(1 - min_share, max(min_share, 0.5 if total == 0 else ns / total))
        period = cycle
        tick_in = state["tick"] % period
        phase = "NS_GREEN" if tick_in < share * period else "EW_GREEN"
        return {item: phase for item in state["intersections"]}

    return control


CANDIDATES = [
    ("sync-c40", lambda: make_global_sync(40)),
    ("sync-c50", lambda: make_global_sync(50)),
    ("sync-c60", lambda: make_global_sync(60)),
    ("sync-c40-share20", lambda: make_global_sync(40, min_share=0.20)),
    ("sync-c40-wait", lambda: make_global_sync(40, wait_weight=1.0)),
    ("sync-c40-ema", lambda: make_global_sync(40, ema=0.9)),
    ("sync-c40-dev", lambda: make_global_sync(40, deviate=True)),
    ("adaptive-cycle", lambda: make_adaptive_cycle()),
    ("clock-c40", lambda: make_corridor_sync(40)),
]


def main():
    names = [name for name, _ in CANDIDATES]
    ratios = {name: {"pub": [], "syn": []} for name in names}
    print(f"{'scenario':<22}" + "".join(f"{name[:15]:>17}" for name in names))
    for scenario in ALL_SCENARIOS:
        row = f"{scenario.id:<22}"
        for name, factory in CANDIDATES:
            cost = run_scenario(scenario, factory(), record_replay=False).metrics.cost
            ratio = cost / baseline_cost(scenario)
            bucket = "pub" if scenario.id in PUBLIC_IDS else "syn"
            ratios[name][bucket].append(ratio)
            row += f"{ratio:>17.3f}"
        print(row)
    print()
    for name in names:
        pub = geo_mean(ratios[name]["pub"])
        syn = geo_mean(ratios[name]["syn"])
        worst = max(ratios[name]["pub"] + ratios[name]["syn"])
        print(f"{name:<20} comb={0.2 * pub + 0.8 * syn:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")


if __name__ == "__main__":
    main()
