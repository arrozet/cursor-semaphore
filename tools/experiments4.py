"""Structural upgrades on top of the global-sync base (c40, ema 0.9, s 0.25):

- aligned-local: shared cycle clock, per-intersection green split.
- hybrid: local backpressure when traffic is light, global sync otherwise.
- endgame: extra weight for vehicles at their final intersection near the end.

Usage: python tools/experiments4.py
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

CYCLE = 40
EMA = 0.9
MIN_SHARE = 0.25


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
    ns = queues.get("N", 0) + queues.get("S", 0)
    ew = queues.get("E", 0) + queues.get("W", 0)
    return ns, ew


def make_base_sync():
    mem = {"phase": "NS_GREEN", "age": 0, "share": 0.5}

    def control(state):
        ns = ew = 0.0
        for info in state["intersections"].values():
            a, b = axis_queues(info)
            ns += a
            ew += b
        total = ns + ew
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - MIN_SHARE, max(MIN_SHARE, raw))
        share = mem["share"] * EMA + share * (1 - EMA)
        mem["share"] = share
        mem["age"] += 1
        if mem["phase"] == "NS_GREEN" and mem["age"] >= share * CYCLE:
            mem["phase"], mem["age"] = "EW_GREEN", 0
        elif mem["phase"] == "EW_GREEN" and mem["age"] >= (1 - share) * CYCLE:
            mem["phase"], mem["age"] = "NS_GREEN", 0
        return {item: mem["phase"] for item in state["intersections"]}

    return control


def make_aligned_local():
    """Common cycle clock; each intersection picks its own NS share (EMA)."""
    shares = {}

    def control(state):
        tick_in = state["tick"] % CYCLE
        decisions = {}
        for item, info in state["intersections"].items():
            ns, ew = axis_queues(info)
            total = ns + ew
            raw = 0.5 if total == 0 else ns / total
            raw = min(1 - MIN_SHARE, max(MIN_SHARE, raw))
            share = shares.get(item, 0.5) * EMA + raw * (1 - EMA)
            shares[item] = share
            decisions[item] = "NS_GREEN" if tick_in < share * CYCLE else "EW_GREEN"
        return decisions

    return control


def make_hybrid(light_threshold=1.5, heavy_threshold=3.0):
    """Local greedy when mean queue is small; global sync when congested."""
    sync = make_base_sync()
    mem = {"mode": "sync"}
    memory = {}

    def local(state):
        decisions = {}
        for item, info in state["intersections"].items():
            phase = info["phase"]
            if phase not in ("NS_GREEN", "EW_GREEN"):
                decisions[item] = memory.get(item, "NS_GREEN")
                continue
            other = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"
            ns, ew = axis_queues(info)
            cur, oth = (ns, ew) if phase == "NS_GREEN" else (ew, ns)
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

    def control(state):
        total = 0
        count = len(state["intersections"])
        for info in state["intersections"].values():
            ns, ew = axis_queues(info)
            total += ns + ew
        mean_queue = total / max(count, 1)
        if mem["mode"] == "sync" and mean_queue < light_threshold:
            mem["mode"] = "local"
        elif mem["mode"] == "local" and mean_queue > heavy_threshold:
            mem["mode"] = "sync"
        sync_decisions = sync(state)  # keep sync clock/EMA state warm
        return local(state) if mem["mode"] == "local" else sync_decisions

    return control


def make_endgame(window=60, weight=4.0):
    """Base sync, but near the end weight terminal-intersection queues."""
    mem = {"phase": "NS_GREEN", "age": 0, "share": 0.5}

    def control(state):
        rows = state["map"]["rows"]
        cols = state["map"]["cols"]
        endgame = state["remaining_ticks"] <= window
        ns = ew = 0.0
        for item, info in state["intersections"].items():
            row = ord(item[0]) - 65
            col = int(item[1:]) - 1
            queues = info["queues"]
            for direction, value in queues.items():
                boost = 1.0
                if endgame:
                    terminal = (
                        (direction == "N" and row == 0)
                        or (direction == "S" and row == rows - 1)
                        or (direction == "E" and col == cols - 1)
                        or (direction == "W" and col == 0)
                    )
                    boost = weight if terminal else 0.5
                if direction in ("N", "S"):
                    ns += value * boost
                else:
                    ew += value * boost
        total = ns + ew
        raw = 0.5 if total == 0 else ns / total
        share = min(1 - MIN_SHARE, max(MIN_SHARE, raw))
        ema = 0.5 if endgame else EMA
        share = mem["share"] * ema + share * (1 - ema)
        mem["share"] = share
        mem["age"] += 1
        if mem["phase"] == "NS_GREEN" and mem["age"] >= share * CYCLE:
            mem["phase"], mem["age"] = "EW_GREEN", 0
        elif mem["phase"] == "EW_GREEN" and mem["age"] >= (1 - share) * CYCLE:
            mem["phase"], mem["age"] = "NS_GREEN", 0
        return {item: mem["phase"] for item in state["intersections"]}

    return control


CANDIDATES = [
    ("base-sync", make_base_sync),
    ("aligned-local", make_aligned_local),
    ("hybrid-1.5-3.0", lambda: make_hybrid(1.5, 3.0)),
    ("hybrid-1.0-2.0", lambda: make_hybrid(1.0, 2.0)),
    ("endgame-60", lambda: make_endgame(60)),
    ("endgame-100", lambda: make_endgame(100)),
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
