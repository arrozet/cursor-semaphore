"""Synchronized Max-Pressure Hybrid controller (Strategy B)."""

MIN_GREEN = 5
YELLOW_PLUS_ALLRED = 3
LINK_TRAVEL_TICKS = 5

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

# Winning public tunables (geom ~22983). See RESULTS.md.
HYSTERESIS = 1.0
HYSTERESIS_RATIO = 0.0
DOWNSTREAM_WEIGHT = 0.0
GAP_OUT_QUEUE = 0
GAP_OUT_TRAVEL = 0
MAX_GREEN = 50
ENDGAME_TICKS = 0
ENDGAME_SWITCH_MARGIN = 1.0
OLDEST_WAIT_WEIGHT = 0.0
QUEUE_BONUS_IN_PLAN = 1.15
DENSITY_SOFTEN = 8.0
SOFT_BONUS = 1.0
REQUIRE_PRESSURE_TO_SWITCH = True
TRAVEL_IN_PRESSURE = 0.35

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN


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
    """Sync max-pressure hybrid: locked corridor green + pressure switch."""
    global _target_phase, _planned_axis, _planned_green

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

    queues = _queue_totals(intersections)
    travel = _travel_totals(state.get("links") or {})
    q_cur, q_oth = queues[current_axis], queues[other_axis]
    t_cur, t_oth = travel[current_axis], travel[other_axis]

    if age == 0 or _planned_axis != current_axis:
        rows = state["map"]["rows"]
        cols = state["map"]["cols"]
        corridor_length = rows if current_axis == "NS" else cols
        traversal = LINK_TRAVEL_TICKS * max(0, corridor_length - 1)
        n = max(1, len(intersections))
        active = q_cur + q_oth + t_cur + t_oth
        density = active / n
        scale = QUEUE_BONUS_IN_PLAN
        if density >= DENSITY_SOFTEN:
            scale = min(scale, SOFT_BONUS)
        demand = int(scale * _max_junction_queue(intersections, current_axis))
        _planned_green = max(MIN_GREEN, min(MAX_GREEN, traversal + demand))
        _planned_axis = current_axis

    p_cur = _axis_pressure(state, current_axis, travel)
    p_oth = _axis_pressure(state, other_axis, travel)

    margin = HYSTERESIS
    if remaining <= ENDGAME_TICKS:
        margin = max(margin, ENDGAME_SWITCH_MARGIN)

    pressure_leads = p_oth > p_cur + margin
    if HYSTERESIS_RATIO > 0:
        pressure_leads = pressure_leads and (
            p_oth > p_cur * (1.0 + HYSTERESIS_RATIO) or p_cur <= 0
        )

    # Gap-out only when queues AND in-flight corridor traffic are gone.
    gap_out = (
        age >= MIN_GREEN
        and q_cur <= GAP_OUT_QUEUE
        and t_cur <= GAP_OUT_TRAVEL
        and q_oth > 0
    )
    max_out = age >= MAX_GREEN and q_oth > 0
    plan_ready = age >= _planned_green and q_oth > 0

    if REQUIRE_PRESSURE_TO_SWITCH:
        plan_switch = plan_ready and pressure_leads
    else:
        plan_switch = plan_ready

    if plan_ready and HYSTERESIS > 0 and not pressure_leads and p_oth + margin < p_cur:
        plan_switch = False

    should_switch = False
    if reference["can_switch"] and q_oth > 0:
        if remaining <= YELLOW_PLUS_ALLRED + MIN_GREEN:
            should_switch = q_cur <= 0 and t_cur <= 0
        elif ENDGAME_TICKS > 0 and remaining <= ENDGAME_TICKS:
            cur_work = q_cur + t_cur
            oth_work = q_oth + t_oth
            useful = oth_work >= cur_work or (
                q_cur <= GAP_OUT_QUEUE and t_cur <= GAP_OUT_TRAVEL
            )
            should_switch = useful and (gap_out or plan_switch or max_out)
        else:
            should_switch = gap_out or plan_switch or max_out

    requested = other_axis if should_switch else current_axis
    _target_phase = f"{requested}_GREEN"
    return {iid: _target_phase for iid in intersections}
