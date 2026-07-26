"""Strategy A: Completion-Aware Drain (synchronized network-wide phase).

Network-wide synchronized adaptive greens (corridor traversal + queues), plus:
- late-switch veto when remaining time cannot cover transition + useful service
- on compact grids (max(rows, cols) <= 2), endgame drain: if the rival axis
  has more queued demand, shorten green and flip so near-exit cars can finish
"""

MIN_GREEN = 5
MAX_GREEN = 50
LINK_TRAVEL_TICKS = 5
TRANSITION_TICKS = 3  # yellow(2) + all-red(1)
USEFUL_SERVICE = 5
# Compact-grid endgame drain window / rival margin / shortened green.
COMPACT_ENDGAME = 40
COMPACT_MARGIN = 1
COMPACT_SHORT_GREEN = MIN_GREEN + 1

AXIS_DIRECTIONS = {
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}

_target_phase = "NS_GREEN"
_planned_axis = None
_planned_green = MIN_GREEN


def _is_compact(rows: int, cols: int) -> bool:
    """Small grids finish in one hop; endgame flips matter more than long corridors."""
    return max(rows, cols) <= 2


def control(state):
    """Coordinate every junction with one adaptive network-wide phase."""
    global _planned_axis, _planned_green, _target_phase

    intersections = state["intersections"]
    if not intersections:
        return {}

    remaining = int(state.get("remaining_ticks", 10**9))
    rows = state["map"]["rows"]
    cols = state["map"]["cols"]
    compact = _is_compact(rows, cols)

    reference = next(iter(intersections.values()))
    current_phase = reference["phase"]

    # A transition cannot be cancelled. Keep requesting its committed target
    # until all signals enter the next green phase.
    if current_phase not in ("NS_GREEN", "EW_GREEN"):
        return {intersection_id: _target_phase for intersection_id in intersections}

    current_axis = current_phase[:2]
    other_axis = "EW" if current_axis == "NS" else "NS"
    queue_totals = {"NS": 0, "EW": 0}
    max_junction_queue = {"NS": 0, "EW": 0}

    for intersection in intersections.values():
        for axis, directions in AXIS_DIRECTIONS.items():
            axis_queue = sum(intersection["queues"][direction] for direction in directions)
            queue_totals[axis] += axis_queue
            max_junction_queue[axis] = max(max_junction_queue[axis], axis_queue)

    if reference["phase_age"] == 0 or _planned_axis != current_axis:
        corridor_length = rows if current_axis == "NS" else cols
        traversal_time = LINK_TRAVEL_TICKS * max(0, corridor_length - 1)
        _planned_green = max(
            MIN_GREEN,
            min(MAX_GREEN, traversal_time + max_junction_queue[current_axis]),
        )
        _planned_axis = current_axis

    # Completion-aware endgame on compact maps: leave a short drain slice for
    # the heavier rival queue instead of riding a long green into the deadline.
    if (
        compact
        and remaining <= COMPACT_ENDGAME
        and queue_totals[other_axis] >= queue_totals[current_axis] + COMPACT_MARGIN
    ):
        _planned_green = min(_planned_green, COMPACT_SHORT_GREEN)

    can_afford_switch = remaining >= TRANSITION_TICKS + USEFUL_SERVICE
    should_switch = (
        reference["can_switch"]
        and can_afford_switch
        and reference["phase_age"] >= _planned_green
        and queue_totals[other_axis] > 0
    )

    requested_axis = other_axis if should_switch else current_axis
    _target_phase = f"{requested_axis}_GREEN"
    return {intersection_id: _target_phase for intersection_id in intersections}
