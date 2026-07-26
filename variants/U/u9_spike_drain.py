"""Variant U9: U2 soft-hold + spike-gated drain-extend.

Drain-extend only when late density spikes vs early-episode mean — hits
windows-endgame-flood without overholding steady city-rush.
"""

MIN_GREEN = 5
YELLOW_PLUS_ALLRED = 3
LINK_TRAVEL_TICKS = 5

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

HYSTERESIS = 1.0
HYSTERESIS_RATIO = 0.0
DOWNSTREAM_WEIGHT = 0.0
GAP_OUT_QUEUE = 0
GAP_OUT_TRAVEL = 0
MAX_GREEN = 50
OLDEST_WAIT_WEIGHT = 0.0
QUEUE_BONUS_IN_PLAN = 1.15
DENSITY_SOFTEN = 8.0
SOFT_BONUS = 1.0
REQUIRE_PRESSURE_TO_SWITCH = True
TRAVEL_IN_PRESSURE = 0.0

LATE_FREEZE_TICKS = YELLOW_PLUS_ALLRED + MIN_GREEN
ENDGAME_TICKS = 80
ENDGAME_SWITCH_MARGIN = 1.5
ENDGAME_HOLD_RATIO = 1.0
ENDGAME_NO_MAXOUT = 100
LARGE_GRID_CELLS = 9

# Spike-gated drain (flood detector).
DRAIN_TICKS = 200
DRAIN_DENSITY = 5.5
DRAIN_MIN_ACTIVE = 40
DRAIN_SPIKE_RATIO = 1.45
DRAIN_MAX_GREEN = 68
DRAIN_DEMAND_BOOST = 1.15

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN
_early_density_sum = 0.0
_early_density_n = 0


def _parse_id(item: str) -> tuple[int, int] | None:
    if len(item) < 2 or not item[0].isalpha():
        return None
    try:
        return ord(item[0].upper()) - 65, int(item[1:]) - 1
    except ValueError:
        return None


def _link_axis(link: dict) -> str | None:
    a = _parse_id(link.get("from", ""))
    b = _parse_id(link.get("to", ""))
    if a is None or b is None:
        return None
    if a[1] == b[1] and a[0] != b[0]:
        return "NS"
    if a[0] == b[0] and a[1] != b[1]:
        return "EW"
    return None


def _neighbor(item: str, direction: str, rows: int, cols: int) -> str | None:
    parsed = _parse_id(item)
    if parsed is None:
        return None
    row, col = parsed
    if direction == "N":
        row -= 1
    elif direction == "S":
        row += 1
    elif direction == "E":
        col += 1
    elif direction == "W":
        col -= 1
    else:
        return None
    if row < 0 or row >= rows or col < 0 or col >= cols:
        return None
    return f"{chr(65 + row)}{col + 1}"


def _queue_totals(intersections: dict) -> dict[str, int]:
    totals = {"NS": 0, "EW": 0}
    for intersection in intersections.values():
        for axis, dirs in AXIS_DIRECTIONS.items():
            totals[axis] += sum(intersection["queues"][d] for d in dirs)
    return totals


def _travel_totals(links: dict) -> dict[str, int]:
    totals = {"NS": 0, "EW": 0}
    for link in (links or {}).values():
        axis = _link_axis(link)
        if axis:
            totals[axis] += int(link.get("vehicles") or 0)
    return totals


def _max_junction_queue(intersections: dict, axis: str) -> int:
    dirs = AXIS_DIRECTIONS[axis]
    best = 0
    for intersection in intersections.values():
        best = max(best, sum(intersection["queues"][d] for d in dirs))
    return best


def _axis_pressure(state: dict, axis: str, travel_totals: dict[str, int]) -> float:
    intersections = state["intersections"]
    links = state.get("links") or {}
    rows = state["map"]["rows"]
    cols = state["map"]["cols"]
    pressure = TRAVEL_IN_PRESSURE * travel_totals.get(axis, 0)
    for item, intersection in intersections.items():
        for direction in AXIS_DIRECTIONS[axis]:
            q = intersection["queues"][direction]
            oldest = (intersection.get("oldest_wait") or {}).get(direction, 0)
            pressure += q + OLDEST_WAIT_WEIGHT * oldest
            if DOWNSTREAM_WEIGHT <= 0:
                continue
            nxt = _neighbor(item, direction, rows, cols)
            if nxt is None:
                continue
            link = links.get(f"{item}->{nxt}")
            if not link:
                continue
            capacity = max(1, int(link.get("capacity") or 1))
            occ = int(link.get("vehicles") or 0)
            pressure -= DOWNSTREAM_WEIGHT * (occ / capacity) * max(q, 1)
    return pressure


def control(state):
    """Sync max-pressure + spike-gated unfinished drain."""
    global _target_phase, _planned_axis, _planned_green
    global _early_density_sum, _early_density_n

    intersections = state["intersections"]
    if not intersections:
        return {}

    reference = next(iter(intersections.values()))
    current_phase = reference["phase"]

    if current_phase not in ("NS_GREEN", "EW_GREEN"):
        return {iid: _target_phase for iid in intersections}

    current_axis = current_phase[:2]
    other_axis = "EW" if current_axis == "NS" else "NS"
    age = reference["phase_age"]
    remaining = int(state.get("remaining_ticks", 10**9))
    n_cells = len(intersections)
    large_grid = n_cells >= LARGE_GRID_CELLS

    queues = _queue_totals(intersections)
    travel = _travel_totals(state.get("links") or {})
    q_cur, q_oth = queues[current_axis], queues[other_axis]
    t_cur, t_oth = travel[current_axis], travel[other_axis]
    active = q_cur + q_oth + t_cur + t_oth
    density = active / max(1, n_cells)

    # Track early/mid density baseline (before late window).
    if remaining > DRAIN_TICKS + 50:
        _early_density_sum += density
        _early_density_n += 1

    early_mean = (
        _early_density_sum / _early_density_n if _early_density_n > 20 else density
    )
    spiked = density >= max(DRAIN_DENSITY, early_mean * DRAIN_SPIKE_RATIO)

    drain_mode = (
        large_grid
        and remaining <= DRAIN_TICKS
        and active >= DRAIN_MIN_ACTIVE
        and spiked
    )

    max_green_now = DRAIN_MAX_GREEN if drain_mode else MAX_GREEN
    soft_window = DRAIN_TICKS if drain_mode else ENDGAME_TICKS

    if age == 0 or _planned_axis != current_axis:
        rows = state["map"]["rows"]
        cols = state["map"]["cols"]
        corridor_length = rows if current_axis == "NS" else cols
        traversal = LINK_TRAVEL_TICKS * max(0, corridor_length - 1)
        scale = QUEUE_BONUS_IN_PLAN
        if density >= DENSITY_SOFTEN:
            scale = min(scale, SOFT_BONUS)
        demand = int(scale * _max_junction_queue(intersections, current_axis))
        if drain_mode and (q_cur + t_cur) >= (q_oth + t_oth):
            demand = int(demand * DRAIN_DEMAND_BOOST)
        _planned_green = max(MIN_GREEN, min(max_green_now, traversal + demand))
        _planned_axis = current_axis

    p_cur = _axis_pressure(state, current_axis, travel)
    p_oth = _axis_pressure(state, other_axis, travel)

    margin = HYSTERESIS
    if remaining <= soft_window:
        margin = max(margin, ENDGAME_SWITCH_MARGIN)

    pressure_leads = p_oth > p_cur + margin

    gap_out = (
        age >= MIN_GREEN
        and q_cur <= GAP_OUT_QUEUE
        and t_cur <= GAP_OUT_TRAVEL
        and q_oth > 0
    )

    allow_max_out = True
    if remaining <= ENDGAME_NO_MAXOUT and (large_grid or remaining <= LATE_FREEZE_TICKS + 20):
        allow_max_out = False
    if drain_mode:
        allow_max_out = False
    max_out = allow_max_out and age >= max_green_now and q_oth > 0

    plan_ready = age >= _planned_green and q_oth > 0
    plan_switch = plan_ready and pressure_leads if REQUIRE_PRESSURE_TO_SWITCH else plan_ready
    if plan_ready and HYSTERESIS > 0 and not pressure_leads and p_oth + margin < p_cur:
        plan_switch = False

    should_switch = False
    if reference["can_switch"] and q_oth > 0:
        cur_work = q_cur + t_cur
        oth_work = q_oth + t_oth

        if remaining <= LATE_FREEZE_TICKS:
            should_switch = q_cur <= 0 and t_cur <= 0
        elif remaining <= soft_window:
            current_clear = q_cur <= GAP_OUT_QUEUE and t_cur <= GAP_OUT_TRAVEL
            other_dominates = oth_work > cur_work * ENDGAME_HOLD_RATIO
            useful = current_clear or other_dominates
            should_switch = useful and (gap_out or plan_switch)
        else:
            should_switch = gap_out or plan_switch or max_out

    requested = other_axis if should_switch else current_axis
    _target_phase = f"{requested}_GREEN"
    return {iid: _target_phase for iid in intersections}
