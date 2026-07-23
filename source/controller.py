"""Strategy D: Occupancy Travel-Time + Floor Guard (synchronized).

Network-wide phase. Infer effective travel from link occupancy/capacity (fallback 5).
Green = f(travel, corridor hops, max queue). Compact single-hop grids hold in-link
platoons and apply a late completion bias. Non-compact maps get a starve floor.
"""

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


def _link_axis(frm, to):
    if frm[0] == to[0]:
        return "EW"
    if frm[1:] == to[1:]:
        return "NS"
    return None


def control(state):
    """Coordinate every junction with one adaptive network-wide phase."""
    global _planned_axis, _planned_green, _target_phase, _ema

    intersections = state["intersections"]
    if not intersections:
        return {}

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

    # Occupancy-inferred travel; fall back toward 5. Capacity scales for private maps.
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
