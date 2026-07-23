"""Hybrid traffic controller: synchronised waves under load, local otherwise.

Two complementary strategies run side by side and a density gate picks one:

* **Sync mode** (heavy traffic): all junctions share one phase so platoons
  cross consecutive junctions without hitting red.  The green split follows
  network-wide demand and the cycle grows with network size.
* **Local mode** (light or spatially skewed traffic): each junction runs
  max-pressure on its own queues, weighted by waiting age and discounted
  when the downstream link is blocked.

The mode gate uses the smoothed mean queue per junction with hysteresis, so
maps that ramp up switch to sync once waves matter and quiet maps stay
responsive.  No scenario identification is used.
"""

# ---- sync mode (shared phase) ----
MIN_SHARE = 0.22
LIGHT_QUEUE = 1.5
DENSE_QUEUE = 5.5
NORMAL_SHARE_EMA = 0.95
DENSE_SHARE_EMA = 0.958
NORMAL_CYCLE_EMA = 0.95
DENSE_CYCLE_EMA = 0.90
MIN_CYCLE = 18.0
MAX_CYCLE = 110.0
INITIAL_CYCLE = 25.0
DENSE_BASE = 14.0
DENSE_SLOPE = 3.5
OVERLOAD_GAIN = 2.0   # extra cycle ticks per unit of mean queue beyond OVERLOAD_START
OVERLOAD_START = 15.0

# ---- local mode (per-junction max-pressure) ----
AGE_WEIGHT = 0.08
AGE_CAP = 120
DOWNSTREAM_WEIGHT = 0.50
BLOCKED_FACTOR = 0.12
SWITCH_RATIO = 1.30
SWITCH_MARGIN = 1.2
MAX_GREEN = 55
STARVE_WAIT = 60

# ---- green wave (sync mode) ----
WAVE_K = 0          # ticks of clock lag per junction step along dominant flow
WAVE_HISTORY = 400
DOM_EMA = 0.97

# ---- mode gate ----
MODE_EMA = 0.90
WARMUP_TICKS = 40  # faster density tracking early on
WARMUP_EMA = 0.70
SYNC_ENTER = 3.0   # mean queue per junction to enter sync mode
SYNC_EXIT = 2.0    # mean queue per junction to fall back to local mode

_state = {
    "phase": "NS_GREEN",
    "age": 0,
    "share": 0.5,
    "cycle": INITIAL_CYCLE,
    "mode": "local",
    "density": 0.0,
    "history": [],
    "ns_bias": 0.0,  # >0 means southbound dominates, <0 northbound
    "ew_bias": 0.0,  # >0 means eastbound dominates, <0 westbound
    "last": {},
}


def _parse(item):
    return ord(item[0]) - 65, int(item[1:]) - 1


def _neighbor(item, direction, rows, cols):
    row, col = _parse(item)
    if direction == "N":
        row -= 1
    elif direction == "S":
        row += 1
    elif direction == "E":
        col += 1
    else:
        col -= 1
    if 0 <= row < rows and 0 <= col < cols:
        return chr(65 + row) + str(col + 1)
    return None


# ---------------------------------------------------------------- sync mode

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
        target_cycle = DENSE_BASE + DENSE_SLOPE * intersection_count
        target_cycle += OVERLOAD_GAIN * max(0.0, mean_queue - OVERLOAD_START)
    target_cycle = min(MAX_CYCLE, max(MIN_CYCLE, target_cycle))
    _state["cycle"] = _state["cycle"] * cycle_ema + target_cycle * (1 - cycle_ema)

    _state["age"] += 1
    if _state["phase"] == "NS_GREEN" and _state["age"] >= share * _state["cycle"]:
        _state["phase"], _state["age"] = "EW_GREEN", 0
    elif _state["phase"] == "EW_GREEN" and _state["age"] >= (1 - share) * _state["cycle"]:
        _state["phase"], _state["age"] = "NS_GREEN", 0

    history = _state["history"]
    history.append(_state["phase"])
    if len(history) > WAVE_HISTORY:
        del history[: len(history) - WAVE_HISTORY]


def _wave_phase(item, rows, cols):
    if WAVE_K <= 0:
        return _state["phase"]
    row, col = _parse(item)
    row_progress = row if _state["ns_bias"] >= 0 else rows - 1 - row
    col_progress = col if _state["ew_bias"] >= 0 else cols - 1 - col
    offset = WAVE_K * (row_progress + col_progress)
    history = _state["history"]
    if offset <= 0 or not history:
        return _state["phase"]
    return history[max(len(history) - 1 - offset, 0)]


# --------------------------------------------------------------- local mode

def _direction_pressure(item, direction, info, state, rows, cols):
    queue = info["queues"].get(direction, 0)
    if queue == 0:
        return 0.0, False

    pressure = queue + AGE_WEIGHT * min(info["oldest_wait"].get(direction, 0), AGE_CAP)

    target = _neighbor(item, direction, rows, cols)
    movable = True
    if target is not None:
        link = state["links"].get(f"{item}->{target}")
        occupancy = link["vehicles"] if link else 0
        capacity = link["capacity"] if link else 8
        downstream_queue = state["intersections"][target]["queues"].get(direction, 0)
        pressure -= DOWNSTREAM_WEIGHT * downstream_queue
        if occupancy >= capacity or downstream_queue + occupancy >= capacity:
            movable = False
            pressure *= BLOCKED_FACTOR
    return max(pressure, 0.0), movable


def _axis_stats(item, directions, info, state, rows, cols):
    total = 0.0
    movable_count = 0
    queued = 0
    for direction in directions:
        pressure, movable = _direction_pressure(item, direction, info, state, rows, cols)
        total += pressure
        queued += info["queues"].get(direction, 0)
        if movable and info["queues"].get(direction, 0) > 0:
            movable_count += 1
    return total, movable_count, queued


def _local_decision(item, info, state, rows, cols):
    phase = info["phase"]
    if phase not in ("NS_GREEN", "EW_GREEN"):
        return _state["last"].get(item, "NS_GREEN")
    if not info["can_switch"]:
        return phase

    ns = _axis_stats(item, ("N", "S"), info, state, rows, cols)
    ew = _axis_stats(item, ("E", "W"), info, state, rows, cols)
    current, other = (ns, ew) if phase == "NS_GREEN" else (ew, ns)
    other_phase = "EW_GREEN" if phase == "NS_GREEN" else "NS_GREEN"

    cur_pressure, cur_movable, _cur_queued = current
    oth_pressure, oth_movable, oth_queued = other

    if oth_queued == 0:
        return phase
    if cur_movable == 0 and oth_movable > 0:
        return other_phase
    directions = ("E", "W") if phase == "NS_GREEN" else ("N", "S")
    oldest = max(info["oldest_wait"].get(direction, 0) for direction in directions)
    if oldest >= STARVE_WAIT:
        return other_phase
    if oth_pressure > cur_pressure * SWITCH_RATIO + SWITCH_MARGIN:
        return other_phase
    if info["phase_age"] >= MAX_GREEN:
        return other_phase
    return phase


# -------------------------------------------------------------------- gate

def _update_mode(total_queued, intersection_count, tick, intersections):
    mean_queue = total_queued / max(intersection_count, 1)
    ema = WARMUP_EMA if tick < WARMUP_TICKS else MODE_EMA
    _state["density"] = _state["density"] * ema + mean_queue * (1 - ema)
    if _state["mode"] == "local" and _state["density"] >= SYNC_ENTER:
        _state["mode"] = "sync"
    elif _state["mode"] == "sync" and _state["density"] <= SYNC_EXIT:
        _state["mode"] = "local"


def control(state):
    """Return the requested green phase for every intersection."""
    if state["tick"] == 0:
        _state.update(
            phase="NS_GREEN",
            age=0,
            share=0.5,
            cycle=INITIAL_CYCLE,
            mode="local",
            density=0.0,
            history=[],
            ns_bias=0.0,
            ew_bias=0.0,
            last={},
        )

    intersections = state["intersections"]
    rows = state["map"]["rows"]
    cols = state["map"]["cols"]

    n_total = s_total = e_total = w_total = 0
    for info in intersections.values():
        queues = info["queues"]
        n_total += queues.get("N", 0)
        s_total += queues.get("S", 0)
        e_total += queues.get("E", 0)
        w_total += queues.get("W", 0)
    ns_total = n_total + s_total
    ew_total = e_total + w_total

    if ns_total:
        _state["ns_bias"] = _state["ns_bias"] * DOM_EMA + (
            (s_total - n_total) / ns_total
        ) * (1 - DOM_EMA)
    if ew_total:
        _state["ew_bias"] = _state["ew_bias"] * DOM_EMA + (
            (e_total - w_total) / ew_total
        ) * (1 - DOM_EMA)

    _advance_sync_clock(ns_total, ew_total, len(intersections))
    _update_mode(ns_total + ew_total, len(intersections), state["tick"], intersections)

    single = rows == 1 and cols == 1
    use_local = single or _state["mode"] == "local"

    decisions = {}
    for item, info in intersections.items():
        if use_local:
            decision = _local_decision(item, info, state, rows, cols)
        else:
            decision = _wave_phase(item, rows, cols)
        decisions[item] = decision
        _state["last"][item] = decision
    return decisions
