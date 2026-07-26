"""Finer isolated sweep around plateau cliff for Variant Q."""
import subprocess
import sys
from pathlib import Path

CTRL = Path(__file__).resolve().parent / "controller_variant_q.py"
EVAL = Path(__file__).resolve().parent / "eval_all.py"
CTRL_DIR = Path(__file__).resolve().parent

CONFIGS = [
    # (name, floor, amp, start, ref, occ, mg, hyst, mode)
    ("b_match_s799_r05", 1.0, 0.15, 7.99, 0.05, 0.0, 50, 1.0, "plat"),
    ("s70_r15", 1.0, 0.15, 7.0, 1.5, 0.0, 50, 1.0, "plat"),
    ("s70_r20", 1.0, 0.15, 7.0, 2.0, 0.0, 50, 1.0, "plat"),
    ("s70_r25", 1.0, 0.15, 7.0, 2.5, 0.0, 50, 1.0, "plat"),
    ("s70_r30", 1.0, 0.15, 7.0, 3.0, 0.0, 50, 1.0, "plat"),
    ("s75_r10", 1.0, 0.15, 7.5, 1.0, 0.0, 50, 1.0, "plat"),
    ("s75_r15", 1.0, 0.15, 7.5, 1.5, 0.0, 50, 1.0, "plat"),
    ("s75_r20", 1.0, 0.15, 7.5, 2.0, 0.0, 50, 1.0, "plat"),
    ("s65_r20", 1.0, 0.15, 6.5, 2.0, 0.0, 50, 1.0, "plat"),
    ("s70_a14_r20", 1.0, 0.14, 7.0, 2.0, 0.0, 50, 1.0, "plat"),
    ("s70_a155_r20", 1.0, 0.155, 7.0, 2.0, 0.0, 50, 1.0, "plat"),
    ("s70_a16_r20", 1.0, 0.16, 7.0, 2.0, 0.0, 50, 1.0, "plat"),
    ("s70_r20_mg52", 1.0, 0.15, 7.0, 2.0, 0.0, 52, 1.0, "plat"),
    ("s70_r20_mg48", 1.0, 0.15, 7.0, 2.0, 0.0, 48, 1.0, "plat"),
    ("s70_r20_h08", 1.0, 0.15, 7.0, 2.0, 0.0, 50, 0.8, "plat"),
    ("s70_r20_h12", 1.0, 0.15, 7.0, 2.0, 0.0, 50, 1.2, "plat"),
    ("s70_r20_occ10", 1.0, 0.15, 7.0, 2.0, 0.10, 50, 1.0, "plat"),
    ("s70_r20_occ20", 1.0, 0.15, 7.0, 2.0, 0.20, 50, 1.0, "plat"),
    ("exp_s70_r20", 1.0, 0.15, 7.0, 2.0, 0.0, 50, 1.0, "exp"),
    ("exp_s75_r15", 1.0, 0.15, 7.5, 1.5, 0.0, 50, 1.0, "exp"),
    ("qden_s70_r20", 1.0, 0.15, 7.0, 2.0, 0.0, 50, 1.0, "qden"),
    ("qden_s75_r15", 1.0, 0.15, 7.5, 1.5, 0.0, 50, 1.0, "qden"),
    ("s72_r18", 1.0, 0.15, 7.2, 1.8, 0.0, 50, 1.0, "plat"),
    ("s68_r22", 1.0, 0.15, 6.8, 2.2, 0.0, 50, 1.0, "plat"),
]


def render(floor, amp, start, ref, occ, mg, hyst, mode):
    return f'''"""Variant Q: Density-Adaptive Queue Bonus on Strategy B sync hybrid."""

import math

MIN_GREEN = 5
YELLOW_PLUS_ALLRED = 3
LINK_TRAVEL_TICKS = 5

AXIS_DIRECTIONS = {{
    "NS": ("N", "S"),
    "EW": ("E", "W"),
}}

BONUS_FLOOR = {floor}
BONUS_AMP = {amp}
SOFTEN_START = {start}
DENSITY_REF = {ref}
OCC_WEIGHT = {occ}
HYSTERESIS = {hyst}
HYSTERESIS_RATIO = 0.0
DOWNSTREAM_WEIGHT = 0.0
GAP_OUT_QUEUE = 0
GAP_OUT_TRAVEL = 0
MAX_GREEN = {mg}
ENDGAME_TICKS = 0
ENDGAME_SWITCH_MARGIN = 1.0
OLDEST_WAIT_WEIGHT = 0.0
REQUIRE_PRESSURE_TO_SWITCH = True
TRAVEL_IN_PRESSURE = 0.0
SCALE_MODE = "{mode}"  # plat | exp | qden

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
    return f"{{chr(65 + row)}}{{col + 1}}"


def _queue_totals(intersections: dict) -> dict[str, int]:
    totals = {{"NS": 0, "EW": 0}}
    for intersection in intersections.values():
        for axis, dirs in AXIS_DIRECTIONS.items():
            totals[axis] += sum(intersection["queues"][d] for d in dirs)
    return totals


def _travel_totals(links: dict) -> dict[str, int]:
    totals = {{"NS": 0, "EW": 0}}
    for link in (links or {{}}).values():
        axis = _link_axis(link)
        if axis:
            totals[axis] += int(link.get("vehicles") or 0)
    return totals


def _mean_occupancy(links: dict) -> float:
    if not links:
        return 0.0
    total = 0.0
    n = 0
    for link in links.values():
        capacity = max(1, int(link.get("capacity") or 1))
        occ = int(link.get("vehicles") or 0)
        total += occ / capacity
        n += 1
    return total / max(1, n)


def _max_junction_queue(intersections: dict, axis: str) -> int:
    dirs = AXIS_DIRECTIONS[axis]
    best = 0
    for intersection in intersections.values():
        best = max(best, sum(intersection["queues"][d] for d in dirs))
    return best


def _plan_scale(density: float, mean_occ: float) -> float:
    amp = BONUS_AMP
    if OCC_WEIGHT > 0:
        amp = BONUS_AMP * max(0.0, 1.0 - OCC_WEIGHT * mean_occ)
    over = max(0.0, density - SOFTEN_START)
    if SCALE_MODE == "exp":
        return BONUS_FLOOR + amp * math.exp(-over / max(1e-6, DENSITY_REF))
    return BONUS_FLOOR + amp / (1.0 + over / max(1e-6, DENSITY_REF))


def _axis_pressure(state: dict, axis: str, travel_totals: dict[str, int]) -> float:
    intersections = state["intersections"]
    links = state.get("links") or {{}}
    rows = state["map"]["rows"]
    cols = state["map"]["cols"]
    pressure = TRAVEL_IN_PRESSURE * travel_totals.get(axis, 0)
    for item, intersection in intersections.items():
        for direction in AXIS_DIRECTIONS[axis]:
            q = intersection["queues"][direction]
            oldest = (intersection.get("oldest_wait") or {{}}).get(direction, 0)
            pressure += q + OLDEST_WAIT_WEIGHT * oldest
            if DOWNSTREAM_WEIGHT <= 0:
                continue
            nxt = _neighbor(item, direction, rows, cols)
            if nxt is None:
                continue
            link = links.get(f"{{item}}->{{nxt}}")
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
        return {{}}

    reference = next(iter(intersections.values()))
    current_phase = reference["phase"]

    if current_phase not in ("NS_GREEN", "EW_GREEN"):
        return {{iid: _target_phase for iid in intersections}}

    current_axis = current_phase[:2]
    other_axis = "EW" if current_axis == "NS" else "NS"
    age = reference["phase_age"]
    remaining = int(state.get("remaining_ticks", 10**9))

    queues = _queue_totals(intersections)
    links = state.get("links") or {{}}
    travel = _travel_totals(links)
    q_cur, q_oth = queues[current_axis], queues[other_axis]
    t_cur, t_oth = travel[current_axis], travel[other_axis]

    if age == 0 or _planned_axis != current_axis:
        rows = state["map"]["rows"]
        cols = state["map"]["cols"]
        corridor_length = rows if current_axis == "NS" else cols
        traversal = LINK_TRAVEL_TICKS * max(0, corridor_length - 1)
        n = max(1, len(intersections))
        if SCALE_MODE == "qden":
            density = (q_cur + q_oth) / n
        else:
            density = (q_cur + q_oth + t_cur + t_oth) / n
        scale = _plan_scale(density, _mean_occupancy(links))
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
    _target_phase = f"{{requested}}_GREEN"
    return {{iid: _target_phase for iid in intersections}}
'''


def apply(cfg):
    name, floor, amp, start, ref, occ, mg, hyst, mode = cfg
    CTRL.write_text(render(floor, amp, start, ref, occ, mg, hyst, mode))
    return name


def parse(out: str):
    pub = allg = None
    unfinished = 0
    floors = {}
    watch = {
        "balanced-grid",
        "northbound-morning",
        "city-rush",
        "combo-4x4-sparse-slow",
        "grid-2x2-saturated",
        "grid-2x2-balanced",
    }
    for line in out.splitlines():
        if line.startswith("PUBLIC geometric mean"):
            pub = int(line.split(":")[1].split()[0])
        elif line.startswith("ALL geometric mean"):
            allg = int(line.split(":")[1].split()[0])
        else:
            parts = line.split()
            if len(parts) >= 5 and parts[0] != "id":
                try:
                    unfinished += int(parts[4])
                except ValueError:
                    continue
                if parts[0] in watch:
                    floors[parts[0]] = int(parts[3])
    return pub, allg, unfinished, floors


def main():
    # smoke
    apply(CONFIGS[0])
    compile(CTRL.read_text(), str(CTRL), "exec")
    print("syntax ok", flush=True)

    results = []
    for cfg in CONFIGS:
        name = apply(cfg)
        print(f"\n=== {name} {cfg[1:]} ===", flush=True)
        proc = subprocess.run(
            [sys.executable, str(EVAL), str(CTRL)],
            capture_output=True,
            text=True,
            cwd=str(CTRL_DIR.parent),
        )
        if proc.returncode != 0:
            print("ERR", proc.stderr[-400:], flush=True)
            continue
        pub, allg, unf, floors = parse(proc.stdout)
        print(f"PUBLIC={pub} ALL={allg} unf={unf} floors={floors}", flush=True)
        results.append((allg or 0, pub or 0, -unf, name, cfg, unf, floors, proc.stdout))

    def rank_key(r):
        allg, pub, neg_unf, *_ = r
        pub_ok = 1 if pub >= 22900 else (0 if pub >= 22000 else -1)
        return (pub_ok, allg, pub, neg_unf)

    results.sort(key=rank_key, reverse=True)
    print("\n===== RANKED =====")
    for allg, pub, _, name, cfg, unf, floors, _ in results:
        tag = "OK" if pub >= 22900 else ("NEAR" if pub >= 22000 else "LOW")
        delta = (allg or 0) - 20469
        print(f"{name:18s} [{tag}] ALL={allg} ({delta:+d}) PUB={pub} unf={unf} {floors}")

    best = results[0]
    apply(best[4])
    Path("/tmp/variant_q_best.txt").write_text(best[7])
    print(f"\nKept best: {best[3]}")


if __name__ == "__main__":
    main()
