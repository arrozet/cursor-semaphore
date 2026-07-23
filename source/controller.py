"""This is the only file you need to change.

Hybrid traffic controller selected by benchmarking against the fixed-time
baseline on the public maps plus a synthetic battery of unseen-style maps
(different grids, biases, demand windows, bursts, capacities).

Two regimes, chosen by network congestion (mean queued vehicles per
intersection, with hysteresis so the mode does not flap):

- Congested (sync mode): every intersection follows one shared clock that
  alternates NS/EW with a green split proportional to network-wide demand
  (EMA-smoothed). Keeping the whole grid in phase preserves platoons and
  avoids spillback gridlock; local greedy control measurably collapses here.

- Light traffic (local mode): each intersection greedily serves the axis
  with more queued vehicles, with hysteresis so a switch (2 yellow + 1
  all-red dead ticks) is only paid when the other axis is clearly better,
  plus a maximum green so no approach starves.

Single-intersection maps always use local mode: there is nothing to
synchronize and reacting to queues immediately is strictly better.
No map identification: decisions depend only on the state interface.
"""

# Sync mode: shared clock.
CYCLE = 40               # full NS+EW period in ticks
MIN_SHARE = 0.25         # each axis always keeps at least this green share
SHARE_EMA = 0.9          # smoothing of the demand-driven split

# Mode selection: mean queued vehicles per intersection, with hysteresis.
LOCAL_BELOW = 2.0        # enter local mode under this congestion level
SYNC_ABOVE = 4.0         # return to sync mode above this level

# Local mode: greedy with switch hysteresis.
SWITCH_RATIO = 1.35      # other axis must beat current by this factor...
SWITCH_MARGIN = 1.0      # ...plus this margin, to justify a switch
MAX_GREEN = 45           # force rotation if the other axis has demand

_state = {
    "phase": "NS_GREEN",  # sync-mode shared phase
    "age": 0,             # ticks since the shared phase changed
    "share": 0.5,         # EMA of the NS demand share
    "mode": "sync",
    "last": {},           # last request per intersection (kept in transitions)
}


def _axis_queues(info):
    queues = info["queues"]
    ns = queues.get("N", 0) + queues.get("S", 0)
    ew = queues.get("E", 0) + queues.get("W", 0)
    return ns, ew


def _advance_sync_clock(ns_total, ew_total):
    total = ns_total + ew_total
    raw = 0.5 if total == 0 else ns_total / total
    share = min(1 - MIN_SHARE, max(MIN_SHARE, raw))
    share = _state["share"] * SHARE_EMA + share * (1 - SHARE_EMA)
    _state["share"] = share

    _state["age"] += 1
    if _state["phase"] == "NS_GREEN" and _state["age"] >= share * CYCLE:
        _state["phase"], _state["age"] = "EW_GREEN", 0
    elif _state["phase"] == "EW_GREEN" and _state["age"] >= (1 - share) * CYCLE:
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
        _state.update(phase="NS_GREEN", age=0, share=0.5, mode="sync", last={})

    intersections = state["intersections"]
    ns_total = ew_total = 0
    for info in intersections.values():
        ns, ew = _axis_queues(info)
        ns_total += ns
        ew_total += ew

    _advance_sync_clock(ns_total, ew_total)

    mean_queue = (ns_total + ew_total) / max(len(intersections), 1)
    if _state["mode"] == "sync" and mean_queue < LOCAL_BELOW:
        _state["mode"] = "local"
    elif _state["mode"] == "local" and mean_queue > SYNC_ABOVE:
        _state["mode"] = "sync"

    single = state["map"]["rows"] == 1 and state["map"]["cols"] == 1
    use_local = single or _state["mode"] == "local"

    decisions = {}
    for item, info in intersections.items():
        decision = _local_decision(item, info) if use_local else _state["phase"]
        decisions[item] = decision
        _state["last"][item] = decision
    return decisions
