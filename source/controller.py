"""Synchronized Max-Pressure Hybrid controller (Strategy B)."""

from collections import deque

MIN_GREEN = 5
YELLOW_PLUS_ALLRED = 3
LINK_TRAVEL_TICKS = 5
MIN_TRAVEL_SAMPLES = 1
SLOW_TRAVEL_SAMPLES = 3
FAST_TRAVEL_FACTOR = 1.0
SLOW_TRAVEL_FACTOR = 1.0

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

# Winning public tunables (geom ~22983). See RESULTS.md.
HYSTERESIS = 1.0
COMPACT_HYSTERESIS = 2.0
COMPACT_MAX_JUNCTIONS = 2
HYSTERESIS_RATIO = 0.0
DOWNSTREAM_WEIGHT = 0.0
GAP_OUT_QUEUE = 0
GAP_OUT_TRAVEL = 0
MAX_GREEN = 60
ENDGAME_TICKS = 0
ENDGAME_SWITCH_MARGIN = 1.0
OLDEST_WAIT_WEIGHT = 0.0
QUEUE_BONUS_IN_PLAN = 1.15
FAST_QUEUE_BONUS_IN_PLAN = QUEUE_BONUS_IN_PLAN
SLOW_QUEUE_BONUS_IN_PLAN = 0.90
DENSITY_SOFTEN = 8.0
SMALL_MAP_DENSITY_SOFTEN = 10.0
SMALL_MAP_MAX_JUNCTIONS = 2
DENSITY_RAMP = 0.0
SOFT_BONUS = 1.06
REQUIRE_PRESSURE_TO_SWITCH = True
TRAVEL_IN_PRESSURE = 0.0
EMA_ALPHA = 0.05
EMA_SHARE_BONUS = 2.0
CAPACITY_PLAN_WEIGHT = 0.25
STARVATION_WAIT = 0
EXIT_BIAS_TICKS = 0
EXIT_QUEUE_WEIGHT = 0.0
SAFE_FREEZE_TICKS = YELLOW_PLUS_ALLRED + MIN_GREEN
LARGE_SAFE_FREEZE_TICKS = SAFE_FREEZE_TICKS
LARGE_FREEZE_MIN_JUNCTIONS = 7
SLOW_PRESSURE_GATE = True

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN
_solo_entry = {}
_travel_samples = deque(maxlen=31)
_prev_link_counts = {}
_demand_ema = {"NS": 0.0, "EW": 0.0}
_ema_ready = False
_observed_capacity = 8.0


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


def _measured_travel(state: dict) -> float:
    """Infer link travel ticks from isolated one-vehicle occupancy runs."""
    tick = int(state.get("tick", 0))
    links = state.get("links") or {}
    seen = set()

    for link_id, link in links.items():
        seen.add(link_id)
        current = int(link.get("vehicles") or 0)
        previous = _prev_link_counts.get(link_id, 0)
        if previous == 0 and current == 1:
            _solo_entry[link_id] = tick
        elif current != 1:
            if previous == 1 and current == 0 and link_id in _solo_entry:
                elapsed = tick - _solo_entry[link_id]
                if 1 <= elapsed <= 15:
                    _travel_samples.append(elapsed)
            _solo_entry.pop(link_id, None)
        _prev_link_counts[link_id] = current

    # Unoccupied links are omitted from the controller payload.
    for link_id in tuple(_prev_link_counts):
        if link_id in seen:
            continue
        if _prev_link_counts[link_id] == 1 and link_id in _solo_entry:
            elapsed = tick - _solo_entry[link_id]
            if 1 <= elapsed <= 15:
                _travel_samples.append(elapsed)
        _solo_entry.pop(link_id, None)
        _prev_link_counts[link_id] = 0

    shortest = min(_travel_samples, default=LINK_TRAVEL_TICKS)
    needed = MIN_TRAVEL_SAMPLES if shortest <= LINK_TRAVEL_TICKS else SLOW_TRAVEL_SAMPLES
    if len(_travel_samples) < needed:
        return float(LINK_TRAVEL_TICKS)
    # A sustained single-count run can hide back-to-back replacements and
    # become a multiple of the real duration. The shortest valid run is exact.
    factor = FAST_TRAVEL_FACTOR if shortest < LINK_TRAVEL_TICKS else SLOW_TRAVEL_FACTOR
    return max(1.0, LINK_TRAVEL_TICKS + factor * (shortest - LINK_TRAVEL_TICKS))


def _max_junction_queue(intersections: dict, axis: str) -> int:
    dirs = AXIS_DIRECTIONS[axis]
    best = 0
    for intersection in intersections.values():
        best = max(best, sum(intersection["queues"][d] for d in dirs))
    return best


def _max_oldest_wait(intersections: dict, axis: str) -> int:
    dirs = AXIS_DIRECTIONS[axis]
    return max(
        (
            (intersection.get("oldest_wait") or {}).get(direction, 0)
            for intersection in intersections.values()
            for direction in dirs
        ),
        default=0,
    )


def _exit_queue_totals(state: dict) -> dict[str, int]:
    rows = state["map"]["rows"]
    cols = state["map"]["cols"]
    totals = {"NS": 0, "EW": 0}
    for item, intersection in state["intersections"].items():
        parsed = _parse_id(item)
        if parsed is None:
            continue
        row, col = parsed
        queues = intersection["queues"]
        if row == 0:
            totals["NS"] += queues["N"]
        if row == rows - 1:
            totals["NS"] += queues["S"]
        if col == 0:
            totals["EW"] += queues["W"]
        if col == cols - 1:
            totals["EW"] += queues["E"]
    return totals


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
    global _ema_ready, _observed_capacity

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
    measured_travel = _measured_travel(state)
    capacities = [
        float(link.get("capacity") or 0)
        for link in (state.get("links") or {}).values()
        if float(link.get("capacity") or 0) > 0
    ]
    if capacities:
        _observed_capacity = sum(capacities) / len(capacities)

    work = {axis: queues[axis] + travel[axis] for axis in ("NS", "EW")}
    if not _ema_ready:
        _demand_ema.update({axis: float(work[axis]) for axis in ("NS", "EW")})
        _ema_ready = True
    else:
        for axis in ("NS", "EW"):
            _demand_ema[axis] = (
                (1.0 - EMA_ALPHA) * _demand_ema[axis] + EMA_ALPHA * work[axis]
            )
    q_cur, q_oth = queues[current_axis], queues[other_axis]
    t_cur, t_oth = travel[current_axis], travel[other_axis]

    if age == 0 or _planned_axis != current_axis:
        rows = state["map"]["rows"]
        cols = state["map"]["cols"]
        corridor_length = rows if current_axis == "NS" else cols
        traversal = measured_travel * max(0, corridor_length - 1)
        n = max(1, len(intersections))
        active = q_cur + q_oth + t_cur + t_oth
        density = active / n
        if measured_travel < LINK_TRAVEL_TICKS:
            scale = FAST_QUEUE_BONUS_IN_PLAN
        elif measured_travel > LINK_TRAVEL_TICKS:
            scale = SLOW_QUEUE_BONUS_IN_PLAN
        else:
            scale = QUEUE_BONUS_IN_PLAN
        density_threshold = (
            SMALL_MAP_DENSITY_SOFTEN
            if n <= SMALL_MAP_MAX_JUNCTIONS
            else DENSITY_SOFTEN
        )
        if DENSITY_RAMP > 0:
            softened = max(
                0.0,
                min(
                    1.0,
                    (density - (density_threshold - DENSITY_RAMP / 2.0))
                    / DENSITY_RAMP,
                ),
            )
            scale += softened * (min(scale, SOFT_BONUS) - scale)
        elif density >= density_threshold:
            scale = min(scale, SOFT_BONUS)
        capacity_scale = max(
            0.5,
            min(
                1.5,
                1.0 + CAPACITY_PLAN_WEIGHT * (_observed_capacity / 8.0 - 1.0),
            ),
        )
        ema_total = _demand_ema["NS"] + _demand_ema["EW"]
        share = _demand_ema[current_axis] / ema_total if ema_total > 0 else 0.5
        demand = int(
            scale
            * capacity_scale
            * _max_junction_queue(intersections, current_axis)
        )
        demand += int(round(EMA_SHARE_BONUS * (share - 0.5)))
        _planned_green = max(MIN_GREEN, min(MAX_GREEN, traversal + demand))
        _planned_axis = current_axis

    p_cur = _axis_pressure(state, current_axis, travel)
    p_oth = _axis_pressure(state, other_axis, travel)
    if EXIT_BIAS_TICKS > 0 and remaining <= EXIT_BIAS_TICKS:
        exit_queues = _exit_queue_totals(state)
        p_cur += EXIT_QUEUE_WEIGHT * exit_queues[current_axis]
        p_oth += EXIT_QUEUE_WEIGHT * exit_queues[other_axis]

    margin = (
        COMPACT_HYSTERESIS
        if len(intersections) <= COMPACT_MAX_JUNCTIONS
        else HYSTERESIS
    )
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
    starvation = (
        STARVATION_WAIT > 0
        and plan_ready
        and _max_oldest_wait(intersections, other_axis) >= STARVATION_WAIT
    )

    require_gate = REQUIRE_PRESSURE_TO_SWITCH and (
        SLOW_PRESSURE_GATE or measured_travel <= LINK_TRAVEL_TICKS
    )
    if require_gate:
        plan_switch = plan_ready and pressure_leads
    else:
        plan_switch = plan_ready

    if require_gate and plan_ready and margin > 0 and not pressure_leads and p_oth + margin < p_cur:
        plan_switch = False

    should_switch = False
    if reference["can_switch"] and q_oth > 0:
        freeze_ticks = (
            LARGE_SAFE_FREEZE_TICKS
            if len(intersections) >= LARGE_FREEZE_MIN_JUNCTIONS
            else SAFE_FREEZE_TICKS
        )
        if remaining <= freeze_ticks:
            should_switch = q_cur <= 0 and t_cur <= 0
        elif ENDGAME_TICKS > 0 and remaining <= ENDGAME_TICKS:
            cur_work = q_cur + t_cur
            oth_work = q_oth + t_oth
            useful = oth_work >= cur_work or (
                q_cur <= GAP_OUT_QUEUE and t_cur <= GAP_OUT_TRAVEL
            )
            should_switch = useful and (gap_out or plan_switch or max_out or starvation)
        else:
            should_switch = gap_out or plan_switch or max_out or starvation

    requested = other_axis if should_switch else current_axis
    _target_phase = f"{requested}_GREEN"
    return {iid: _target_phase for iid in intersections}
