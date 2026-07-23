"""Strategy D-opt: Strategy D + measured link travel + strict gap-out.

Network-wide synchronized phase (as strategy D). Two additions:

1. Measured travel: watch links carrying exactly one vehicle; the tick span
   from 0->1 to 1->0 is the exact link travel time. The mode of recent samples
   replaces the occupancy-EMA guess, fixing fast-travel (2) and slow-travel
   (8-10) maps where the guess was clamped to ~4.5-7.
2. Strict gap-out: when the green axis is completely empty (no queued cars and
   nothing on its links) and the other axis waits, switch at MIN_GREEN instead
   of holding the planned green. Helps sparse maps and dying-demand tails.

Compact platoon hold and late completion guard from strategy D are kept: they
are worth ~4k on the public geometric mean.
"""

from collections import deque

MIN_GREEN = 5
MAX_GREEN = 50
DEFAULT_TRAVEL = 5

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN
_ema = {"NS": 0.0, "EW": 0.0}
_solo_entry = {}
_travel_samples = deque(maxlen=25)
_prev_link_counts = {}


def _link_axis(frm, to):
    if frm[0] == to[0]:
        return "EW"
    if frm[1:] == to[1:]:
        return "NS"
    return None


def _measured_travel(state):
    """Exact travel time from links that carried a single vehicle end to end."""
    tick = state["tick"]
    links = state.get("links") or {}
    seen = set()
    for lid, link in links.items():
        seen.add(lid)
        cur = link.get("vehicles") or 0
        prev = _prev_link_counts.get(lid, 0)
        if prev == 0 and cur == 1:
            _solo_entry[lid] = tick
        elif cur != 1:
            if prev == 1 and cur == 0 and lid in _solo_entry:
                _travel_samples.append(tick - _solo_entry.pop(lid))
            else:
                _solo_entry.pop(lid, None)
        _prev_link_counts[lid] = cur
    # Links absent from the payload have zero vehicles.
    for lid in list(_prev_link_counts):
        if lid not in seen:
            if _prev_link_counts[lid] == 1 and lid in _solo_entry:
                _travel_samples.append(tick - _solo_entry.pop(lid))
            else:
                _solo_entry.pop(lid, None)
            _prev_link_counts[lid] = 0
    if len(_travel_samples) >= 3:
        counts = {}
        for v in _travel_samples:
            counts[v] = counts.get(v, 0) + 1
        mode = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        return float(max(1, min(15, mode)))
    return None


def control(state):
    """Coordinate every junction with one adaptive network-wide phase."""
    global _planned_axis, _planned_green, _target_phase

    intersections = state["intersections"]
    if not intersections:
        return {}

    measured = _measured_travel(state)

    reference = next(iter(intersections.values()))
    phase = reference["phase"]
    if phase not in ("NS_GREEN", "EW_GREEN"):
        return {i: _target_phase for i in intersections}

    cur = phase[:2]
    other = "EW" if cur == "NS" else "NS"
    qt = {"NS": 0, "EW": 0}
    mq = {"NS": 0, "EW": 0}
    ow = {"NS": 0, "EW": 0}
    for inter in intersections.values():
        for ax, dirs in AXIS_DIRECTIONS.items():
            aq = sum(inter["queues"][d] for d in dirs)
            qt[ax] += aq
            mq[ax] = max(mq[ax], aq)
            for d in dirs:
                ow[ax] = max(ow[ax], inter["oldest_wait"][d])

    link_veh = {"NS": 0, "EW": 0}
    ratios = {"NS": [], "EW": []}
    capacities = []
    for link in (state.get("links") or {}).values():
        ax = _link_axis(link["from"], link["to"])
        if not ax:
            continue
        veh = link.get("vehicles") or 0
        link_veh[ax] += veh
        cap = link.get("capacity") or 0
        if cap > 0:
            capacities.append(cap)
            ratios[ax].append(min(1.0, veh / float(cap)))
    for a in ("NS", "EW"):
        r = (sum(ratios[a]) / len(ratios[a])) if ratios[a] else 0.0
        _ema[a] = 0.9 * _ema[a] + 0.1 * r

    if measured is not None:
        travel = measured
    else:
        # Fallback until enough solo-car samples exist.
        travel = max(4.5, min(7.0, DEFAULT_TRAVEL * (1.0 + 0.2 * _ema[cur])))
        if capacities:
            avg_cap = sum(capacities) / len(capacities)
            travel = max(3.5, min(10.0, travel * max(0.85, min(1.25, avg_cap / 8.0))))

    ns_hops = state["map"]["rows"] - 1
    ew_hops = state["map"]["cols"] - 1
    hops = ns_hops if cur == "NS" else ew_hops
    compact = max(ns_hops, ew_hops) <= 1

    if reference["phase_age"] == 0 or _planned_axis != cur:
        _planned_green = max(
            MIN_GREEN,
            min(MAX_GREEN, int(round(travel * max(0, hops) + mq[cur]))),
        )
        _planned_axis = cur

    age = reference["phase_age"]
    can = reference["can_switch"]
    rem = state.get("remaining_ticks", 10**9)
    dem = {a: qt[a] + 0.5 * link_veh[a] for a in ("NS", "EW")}

    should = can and age >= _planned_green and dem[other] > 0

    # Gap-out: the green axis is fully served; do not burn ticks on it.
    if can and age >= MIN_GREEN and qt[cur] == 0 and link_veh[cur] == 0 and qt[other] > 0:
        should = True

    # Compact platoon hold: finish vehicles still on links before switching.
    if (
        compact
        and can
        and age >= _planned_green
        and dem[other] > 0
        and dem[cur] > dem[other] * 1.1
        and link_veh[cur] > 0
    ):
        should = False
        _planned_green = min(MAX_GREEN, age + 2)

    # Completion guard on compact grids (late episode unfinished risk).
    if rem <= 100 and compact:
        if dem[cur] >= dem[other] and qt[cur] > 0 and age < _planned_green + 10:
            should = False
        elif dem[other] > dem[cur] * 1.3 and can and age >= MIN_GREEN + 3:
            should = True

    # Floor guard: non-compact starve after planned green.
    if (
        (not compact)
        and can
        and qt[other] > 0
        and ow[other] >= 55
        and age >= _planned_green
    ):
        should = True

    if should and rem < 8:
        should = False

    req = other if should else cur
    _target_phase = f"{req}_GREEN"
    return {i: _target_phase for i in intersections}
