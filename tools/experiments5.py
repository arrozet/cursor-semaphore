"""Refine the hybrid controller: mode signal, local policy, thresholds.

Usage: python tools/experiments5.py
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

_NEXT_DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


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


def downstream(item, direction, rows, cols):
    row = ord(item[0]) - 65
    col = int(item[1:]) - 1
    d_row, d_col = _NEXT_DELTA[direction]
    row, col = row + d_row, col + d_col
    if 0 <= row < rows and 0 <= col < cols:
        return chr(65 + row) + str(col + 1)
    return None


def make_local_full():
    """The original backpressure local policy (wait + downstream discount)."""
    memory = {}

    def control(state):
        rows, cols = state["map"]["rows"], state["map"]["cols"]
        decisions = {}
        for item, info in state["intersections"].items():
            phase = info["phase"]
            if phase not in ("NS_GREEN", "EW_GREEN"):
                decisions[item] = memory.get(item, "NS_GREEN")
                continue
            other = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"

            def axis_pressure(green):
                directions = ("N", "S") if green == "NS_GREEN" else ("E", "W")
                total, servable = 0.0, False
                for direction in directions:
                    queue = info["queues"].get(direction, 0)
                    oldest = info["oldest_wait"].get(direction, 0)
                    target = downstream(item, direction, rows, cols)
                    free = 1.0
                    if target is not None:
                        link = state["links"].get(f"{item}->{target}")
                        in_flight = link["vehicles"] if link else 0
                        capacity = link["capacity"] if link else 8
                        receiving = state["intersections"][target]["queues"].get(direction, 0)
                        free = max(0.0, 1.0 - (in_flight + receiving) / max(capacity, 1))
                    total += queue * free
                    if queue > 0:
                        total += 0.6 * math.sqrt(oldest)
                    servable = servable or (queue > 0 and free > 0)
                return total, servable

            cur_pressure, cur_servable = axis_pressure(phase)
            oth_pressure, oth_servable = axis_pressure(other)
            decision = phase
            if info["can_switch"] and oth_servable:
                if not cur_servable:
                    decision = other
                elif info["phase_age"] >= 45:
                    decision = other
                elif oth_pressure > cur_pressure * 1.35 + 1.0:
                    decision = other
            decisions[item] = decision
            memory[item] = decision
        return decisions

    return control


def make_local_simple():
    memory = {}

    def control(state):
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

    return control


def make_sync():
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


def mean_queue_signal(state):
    total = 0
    for info in state["intersections"].values():
        ns, ew = axis_queues(info)
        total += ns + ew
    return total / max(len(state["intersections"]), 1)


def saturation_signal(state):
    links = state["links"]
    if not links:
        return 0.0
    saturated = sum(1 for link in links.values() if link["vehicles"] >= link["capacity"] - 1)
    return saturated / len(links)


def make_hybrid(local_factory, signal, low, high, single_local=True):
    sync = make_sync()
    local = local_factory()
    mem = {"mode": "sync"}

    def control(state):
        rows, cols = state["map"]["rows"], state["map"]["cols"]
        sync_decisions = sync(state)
        local_decisions = local(state)
        if single_local and rows == 1 and cols == 1:
            return local_decisions
        value = signal(state)
        if mem["mode"] == "sync" and value < low:
            mem["mode"] = "local"
        elif mem["mode"] == "local" and value > high:
            mem["mode"] = "sync"
        return local_decisions if mem["mode"] == "local" else sync_decisions

    return control


CANDIDATES = [
    ("hyb-simple-q1.5-3", lambda: make_hybrid(make_local_simple, mean_queue_signal, 1.5, 3.0)),
    ("hyb-full-q1.5-3", lambda: make_hybrid(make_local_full, mean_queue_signal, 1.5, 3.0)),
    ("hyb-full-q2-4", lambda: make_hybrid(make_local_full, mean_queue_signal, 2.0, 4.0)),
    ("hyb-full-q3-5", lambda: make_hybrid(make_local_full, mean_queue_signal, 3.0, 5.0)),
    ("hyb-full-sat10-25", lambda: make_hybrid(make_local_full, saturation_signal, 0.10, 0.25)),
    ("hyb-full-sat15-35", lambda: make_hybrid(make_local_full, saturation_signal, 0.15, 0.35)),
]


def main():
    names = [name for name, _ in CANDIDATES]
    ratios = {name: {"pub": [], "syn": []} for name in names}
    print(f"{'scenario':<22}" + "".join(f"{name[:17]:>19}" for name in names))
    for scenario in ALL_SCENARIOS:
        row = f"{scenario.id:<22}"
        for name, factory in CANDIDATES:
            cost = run_scenario(scenario, factory(), record_replay=False).metrics.cost
            ratio = cost / baseline_cost(scenario)
            bucket = "pub" if scenario.id in PUBLIC_IDS else "syn"
            ratios[name][bucket].append(ratio)
            row += f"{ratio:>19.3f}"
        print(row)
    print()
    for name in names:
        pub = geo_mean(ratios[name]["pub"])
        syn = geo_mean(ratios[name]["syn"])
        worst = max(ratios[name]["pub"] + ratios[name]["syn"])
        print(f"{name:<22} comb={0.2 * pub + 0.8 * syn:.3f} pub={pub:.3f} syn={syn:.3f} worst={worst:.3f}")


if __name__ == "__main__":
    main()
