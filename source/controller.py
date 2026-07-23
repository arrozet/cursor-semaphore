"""Adaptive, network-synchronised traffic controller.

All connected intersections share a phase so platoons can cross successive
junctions without meeting conflicting signals.  The green split follows
network-wide queue demand, while the cycle length grows with network size and
is smoothed to avoid oscillation.  Under heavy congestion the split reacts
more slowly but cycle changes settle faster, preserving throughput.

A single junction is controlled locally because it has no platoons to
coordinate.  Every decision is derived from the provided state; no scenario
identification is used.
"""

MIN_SHARE = 0.22
LIGHT_QUEUE = 1.5
DENSE_QUEUE = 5.5
NORMAL_SHARE_EMA = 0.95
DENSE_SHARE_EMA = 0.958
NORMAL_CYCLE_EMA = 0.95
DENSE_CYCLE_EMA = 0.90
MIN_CYCLE = 18.0
MAX_CYCLE = 55.0
INITIAL_CYCLE = 25.0

SWITCH_RATIO = 1.35
SWITCH_MARGIN = 1.0
MAX_GREEN = 45

_state = {
    "phase": "NS_GREEN",
    "age": 0,
    "share": 0.5,
    "cycle": INITIAL_CYCLE,
    "last": {},
}


def _axis_queues(info):
    queues = info["queues"]
    ns = queues.get("N", 0) + queues.get("S", 0)
    ew = queues.get("E", 0) + queues.get("W", 0)
    return ns, ew


def _advance_sync_clock(ns_total, ew_total, intersection_count):
    total = ns_total + ew_total
    raw = 0.5 if total == 0 else ns_total / total
    share = min(1 - MIN_SHARE, max(MIN_SHARE, raw))
    mean_queue = total / max(intersection_count, 1)

    share_ema = DENSE_SHARE_EMA if mean_queue >= DENSE_QUEUE else NORMAL_SHARE_EMA
    cycle_ema = DENSE_CYCLE_EMA if mean_queue >= DENSE_QUEUE else NORMAL_CYCLE_EMA

    share = _state["share"] * share_ema + share * (1 - share_ema)
    _state["share"] = share

    if mean_queue < LIGHT_QUEUE:
        target_cycle = 20.0 + 3.0 * mean_queue
    else:
        target_cycle = 14.0 + 3.5 * intersection_count
    target_cycle = min(MAX_CYCLE, max(MIN_CYCLE, target_cycle))
    _state["cycle"] = _state["cycle"] * cycle_ema + target_cycle * (1 - cycle_ema)

    _state["age"] += 1
    if _state["phase"] == "NS_GREEN" and _state["age"] >= share * _state["cycle"]:
        _state["phase"], _state["age"] = "EW_GREEN", 0
    elif _state["phase"] == "EW_GREEN" and _state["age"] >= (1 - share) * _state["cycle"]:
        _state["phase"], _state["age"] = "NS_GREEN", 0


def _local_decision(item, info):
    phase = info["phase"]
    if phase not in ("NS_GREEN", "EW_GREEN"):
        return _state["last"].get(item, "NS_GREEN")

    other = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"
    ns, ew = _axis_queues(info)
    current, opposing = (ns, ew) if phase == "NS_GREEN" else (ew, ns)

    if not info["can_switch"]:
        return phase
    if current == 0 and opposing > 0:
        return other
    if opposing > current * SWITCH_RATIO + SWITCH_MARGIN:
        return other
    if info["phase_age"] >= MAX_GREEN and opposing > 0:
        return other
    return phase


def control(state):
    """Return the requested green phase for every intersection."""
    if state["tick"] == 0:
        _state.update(
            phase="NS_GREEN",
            age=0,
            share=0.5,
            cycle=INITIAL_CYCLE,
            last={},
        )

    intersections = state["intersections"]
    ns_total = ew_total = 0
    for info in intersections.values():
        ns, ew = _axis_queues(info)
        ns_total += ns
        ew_total += ew

    _advance_sync_clock(ns_total, ew_total, len(intersections))

    single = state["map"]["rows"] == 1 and state["map"]["cols"] == 1

    decisions = {}
    for item, info in intersections.items():
        decision = _local_decision(item, info) if single else _state["phase"]
        decisions[item] = decision
        _state["last"][item] = decision
    return decisions
