"""Probe: on one map, force constant green length L (synchronized alternation
whenever both axes have work) and report cost. Reveals the optimal green
structure independent of B's planning heuristics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "source"))

from traffic_arena.engine import run_scenario, fixed_time_controller
from traffic_arena.map_loader import load_runnable_scenarios

MAP_ID = sys.argv[1] if len(sys.argv) > 1 else "combo-4x4-sparse-slow"


def make_const_controller(length: int):
    state_box = {"target": "NS_GREEN"}

    def control(state):
        inter = state["intersections"]
        ref = next(iter(inter.values()))
        if ref["phase"] not in ("NS_GREEN", "EW_GREEN"):
            return {i: state_box["target"] for i in inter}
        cur = ref["phase"][:2]
        oth = "EW" if cur == "NS" else "NS"
        q = {"NS": 0, "EW": 0}
        for i in inter.values():
            for ax, dirs in (("NS", ("N", "S")), ("EW", ("E", "W"))):
                q[ax] += sum(i["queues"][d] for d in dirs)
        switch = ref["can_switch"] and ref["phase_age"] >= length and q[oth] > 0
        state_box["target"] = f"{oth if switch else cur}_GREEN"
        return {i: state_box["target"] for i in inter}

    return control


scenario = {s.id: s for s in load_runnable_scenarios()}[MAP_ID]
base = run_scenario(scenario, fixed_time_controller, record_replay=False).metrics
print(f"{MAP_ID}: fixed-time cost={base.cost} waits={base.wait_ticks} unf={base.unfinished}")
for L in (5, 6, 8, 10, 12, 15, 20, 25, 30, 35):
    m = run_scenario(scenario, make_const_controller(L), record_replay=False).metrics
    print(f"  L={L:3d}  cost={m.cost:7d}  waits={m.wait_ticks:7d}  unf={m.unfinished:4d}")
