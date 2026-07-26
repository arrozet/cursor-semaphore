"""Strategy C: Demand-Ratio Adaptive Split (synchronized).

Network-wide phase. Green length mixes corridor traversal, peak junction
queue, mean axis queue, and an EMA demand-share bonus so asymmetric maps
(NS-heavy) get longer greens without scenario-id hardcoding.
"""

MIN_GREEN = 5
MAX_GREEN = 50
LINK_TRAVEL = 5
EMA_ALPHA = 0.055
SHARE_BONUS = 7.0

# Small grids: blend peak with mean demand. Larger grids: peak-dominated.
SMALL_PEAK_W = 0.7
SMALL_AVG_W = 0.3
LARGE_PEAK_W = 0.86
LARGE_AVG_W = 0.14
SMALL_MAX_JUNCTIONS = 4

TRANSITION_TICKS = 3
USEFUL_SERVICE = 5

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN
_ema = {"NS": 0.0, "EW": 0.0}
_ema_ready = False


def _queues(intersections):
    totals = {"NS": 0, "EW": 0}
    peaks = {"NS": 0, "EW": 0}
    for intersection in intersections.values():
        for axis, directions in AXIS_DIRECTIONS.items():
            q = sum(intersection["queues"][d] for d in directions)
            totals[axis] += q
            peaks[axis] = max(peaks[axis], q)
    return totals, peaks


def _touch_ema(totals):
    global _ema, _ema_ready
    if not _ema_ready:
        _ema = {"NS": float(totals["NS"]), "EW": float(totals["EW"])}
        _ema_ready = True
        return
    for axis in ("NS", "EW"):
        _ema[axis] = (1.0 - EMA_ALPHA) * _ema[axis] + EMA_ALPHA * float(totals[axis])


def _demand_share(axis):
    total = _ema["NS"] + _ema["EW"]
    if total <= 1e-9:
        return 0.5
    return _ema[axis] / total


def control(state):
    """Allocate synchronized green proportional to observed demand ratio."""
    global _planned_axis, _planned_green, _target_phase

    intersections = state["intersections"]
    if not intersections:
        return {}

    reference = next(iter(intersections.values()))
    phase = reference["phase"]
    if phase not in ("NS_GREEN", "EW_GREEN"):
        return {iid: _target_phase for iid in intersections}

    current = phase[:2]
    other = "EW" if current == "NS" else "NS"
    totals, peaks = _queues(intersections)
    _touch_ema(totals)

    rows = state["map"]["rows"]
    cols = state["map"]["cols"]
    n_junctions = max(1, len(intersections))
    remaining = int(state["remaining_ticks"])
    age = reference["phase_age"]

    if age == 0 or _planned_axis != current:
        corridor = rows if current == "NS" else cols
        traversal = LINK_TRAVEL * max(0, corridor - 1)
        avg_queue = totals[current] / n_junctions
        share = _demand_share(current)

        if n_junctions <= SMALL_MAX_JUNCTIONS:
            peak_w, avg_w = SMALL_PEAK_W, SMALL_AVG_W
        else:
            peak_w, avg_w = LARGE_PEAK_W, LARGE_AVG_W

        # Demand-ratio term: heavy EMA axis keeps green longer (asymmetric maps).
        green = (
            traversal
            + peak_w * peaks[current]
            + avg_w * avg_queue
            + SHARE_BONUS * (share - 0.5)
        )
        _planned_green = max(MIN_GREEN, min(MAX_GREEN, int(round(green))))
        _planned_axis = current

    rival_q = totals[other]
    # Late-episode: avoid burning a transition unless enough ticks remain to serve.
    can_afford_switch = remaining >= TRANSITION_TICKS + USEFUL_SERVICE
    should_switch = (
        reference["can_switch"]
        and rival_q > 0
        and can_afford_switch
        and age >= _planned_green
    )

    requested = other if should_switch else current
    _target_phase = f"{requested}_GREEN"
    return {iid: _target_phase for iid in intersections}
