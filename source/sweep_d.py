"""Ablation sweep for strategy D optimization.

Variants toggle: measured travel, gap-out, compact platoon hold,
compact completion guard, weighted deadline endgame.
"""
from __future__ import annotations

import sys
from collections import deque

from traffic_arena.engine import run_scenario, fixed_time_controller
from traffic_arena.map_loader import load_runnable_scenarios
from traffic_arena.score_profiles import PUBLIC_SCORE_PROFILES
from traffic_arena.scoring import scenario_score, geometric_mean

AXIS_DIRECTIONS = {"NS": ("N", "S"), "EW": ("E", "W")}
MIN_GREEN = 5
MAX_GREEN = 50
DEFAULT_TRAVEL = 5


def _link_axis(frm, to):
    if frm[0] == to[0]:
        return "EW"
    if frm[1:] == to[1:]:
        return "NS"
    return None


def make_controller(
    measure_travel=False,
    gap_out=False,
    platoon_hold=True,
    completion_guard=True,
    endgame_weighted=False,
    floor_guard=True,
):
    target_phase = "NS_GREEN"
    planned_axis = None
    planned_green = MIN_GREEN
    ema = {"NS": 0.0, "EW": 0.0}
    # travel measurement: link -> (entry_tick or None), samples deque
    solo_entry = {}
    samples = deque(maxlen=25)
    prev_counts = {}

    def measured_travel(state):
        tick = state["tick"]
        links = state.get("links") or {}
        seen = set()
        for lid, link in links.items():
            seen.add(lid)
            cur = link.get("vehicles") or 0
            prev = prev_counts.get(lid, 0)
            if prev == 0 and cur == 1:
                solo_entry[lid] = tick
            elif cur != 1:
                if prev == 1 and cur == 0 and lid in solo_entry:
                    samples.append(tick - solo_entry.pop(lid))
                else:
                    solo_entry.pop(lid, None)
            prev_counts[lid] = cur
        for lid in list(prev_counts):
            if lid not in seen:
                if prev_counts[lid] == 1 and lid in solo_entry:
                    samples.append(tick - solo_entry.pop(lid))
                else:
                    solo_entry.pop(lid, None)
                prev_counts[lid] = 0
        if len(samples) >= 3:
            counts = {}
            for v in samples:
                counts[v] = counts.get(v, 0) + 1
            mode = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
            return float(max(1, min(15, mode)))
        return None

    def value(state, axis, horizon):
        rows, cols = state["map"]["rows"], state["map"]["cols"]
        v = 0.0
        for node, inter in state["intersections"].items():
            r = ord(node[0]) - 65
            c = int(node[1:]) - 1
            for d in AXIS_DIRECTIONS[axis]:
                q = inter["queues"][d]
                dist = {"N": r, "S": rows - 1 - r, "W": c, "E": cols - 1 - c}[d]
                v += q / (dist + 1)
        for link in (state.get("links") or {}).values():
            ax = _link_axis(link["from"], link["to"])
            if ax == axis:
                v += 0.5 * (link.get("vehicles") or 0)
        return v

    def control(state):
        nonlocal target_phase, planned_axis, planned_green

        intersections = state["intersections"]
        if not intersections:
            return {}

        mt = measured_travel(state) if measure_travel else None

        reference = next(iter(intersections.values()))
        phase = reference["phase"]
        if phase not in ("NS_GREEN", "EW_GREEN"):
            return {i: target_phase for i in intersections}

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
            ema[a] = 0.9 * ema[a] + 0.1 * r

        if mt is not None:
            travel = mt
        else:
            travel = max(4.5, min(7.0, DEFAULT_TRAVEL * (1.0 + 0.2 * ema[cur])))
            if capacities:
                avg_cap = sum(capacities) / len(capacities)
                travel = max(3.5, min(10.0, travel * max(0.85, min(1.25, avg_cap / 8.0))))

        ns_hops = state["map"]["rows"] - 1
        ew_hops = state["map"]["cols"] - 1
        hops = ns_hops if cur == "NS" else ew_hops
        compact = max(ns_hops, ew_hops) <= 1

        if reference["phase_age"] == 0 or planned_axis != cur:
            planned_green = max(
                MIN_GREEN,
                min(MAX_GREEN, int(round(travel * max(0, hops) + mq[cur]))),
            )
            planned_axis = cur

        age = reference["phase_age"]
        can = reference["can_switch"]
        rem = state.get("remaining_ticks", 10**9)
        dem = {a: qt[a] + 0.5 * link_veh[a] for a in ("NS", "EW")}

        should = can and age >= planned_green and dem[other] > 0

        if gap_out and can and age >= MIN_GREEN and qt[cur] == 0 and link_veh[cur] == 0 and qt[other] > 0:
            should = True

        if (
            platoon_hold
            and compact
            and can
            and age >= planned_green
            and dem[other] > 0
            and dem[cur] > dem[other] * 1.1
            and link_veh[cur] > 0
        ):
            should = False
            planned_green = min(MAX_GREEN, age + 2)

        if completion_guard and rem <= 100 and compact:
            if dem[cur] >= dem[other] and qt[cur] > 0 and age < planned_green + 10:
                should = False
            elif dem[other] > dem[cur] * 1.3 and can and age >= MIN_GREEN + 3:
                should = True

        if (
            floor_guard
            and (not compact)
            and can
            and qt[other] > 0
            and ow[other] >= 55
            and age >= planned_green
        ):
            should = True

        if endgame_weighted and should and rem <= 50:
            should = rem > 3 and value(state, other, rem - 3) > value(state, cur, rem) + 4

        if should and rem < 8:
            should = False

        req = other if should else cur
        target_phase = f"{req}_GREEN"
        return {i: target_phase for i in intersections}

    return control


def main():
    scenarios = load_runnable_scenarios()
    baselines = {}
    for s in scenarios:
        if s.id not in PUBLIC_SCORE_PROFILES:
            baselines[s.id] = run_scenario(s, fixed_time_controller, record_replay=False).metrics.cost

    variants = {
        "A_d_base": dict(),
        "B_mt": dict(measure_travel=True),
        "C_mt_gap": dict(measure_travel=True, gap_out=True),
        "D_mt_gap_noph": dict(measure_travel=True, gap_out=True, platoon_hold=False),
        "E_mt_gap_nocg": dict(measure_travel=True, gap_out=True, completion_guard=False),
        "F_mt_gap_plain": dict(measure_travel=True, gap_out=True, platoon_hold=False, completion_guard=False),
        "G_C_endg": dict(measure_travel=True, gap_out=True, endgame_weighted=True),
        "H_F_endg": dict(measure_travel=True, gap_out=True, platoon_hold=False, completion_guard=False, endgame_weighted=True),
    }

    for name, kwargs in variants.items():
        scores = {}
        for s in scenarios:
            res = run_scenario(s, make_controller(**kwargs), record_replay=False)
            if s.id in PUBLIC_SCORE_PROFILES:
                p = PUBLIC_SCORE_PROFILES[s.id]
                base_cost, target = p.baseline_cost, p.target_cost
            else:
                base_cost = baselines[s.id]
                target = max(1, min(round(base_cost * 0.85), base_cost - 1))
            scores[s.id] = scenario_score(res.metrics.cost, base_cost, target)
        pub = [scores[i] for i in PUBLIC_SCORE_PROFILES]
        allsc = list(scores.values())
        worst = sorted(scores.items(), key=lambda kv: kv[1])[:5]
        print(
            f"{name:16s} pubG={geometric_mean(pub):6d} allG={geometric_mean(allsc):6d} "
            f"min={min(allsc):6d} worst={[(k, v) for k, v in worst]}"
        )
        sys.stdout.flush()


if __name__ == "__main__":
    main()
