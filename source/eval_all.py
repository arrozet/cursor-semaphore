import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from traffic_arena.engine import run_scenario, fixed_time_controller
from traffic_arena.map_loader import load_runnable_scenarios
from traffic_arena.score_profiles import PUBLIC_SCORE_PROFILES
from traffic_arena.scoring import scenario_score, geometric_mean


def load(path):
    spec = importlib.util.spec_from_file_location("cand_" + Path(path).stem, Path(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.control


def evaluate(controller_path, scenarios, baselines):
    rows = []
    for s in scenarios:
        result = run_scenario(s, load(controller_path), record_replay=False)
        if s.id in PUBLIC_SCORE_PROFILES:
            p = PUBLIC_SCORE_PROFILES[s.id]
            base_cost, target = p.baseline_cost, p.target_cost
        else:
            base_cost = baselines[s.id]
            target = max(1, min(round(base_cost * 0.85), base_cost - 1))
        sc = scenario_score(result.metrics.cost, base_cost, target)
        rows.append((s.id, result.metrics.cost, base_cost, sc, result.metrics.unfinished))
    return rows


if __name__ == "__main__":
    controller_path = sys.argv[1] if len(sys.argv) > 1 else "controller.py"
    scenarios = load_runnable_scenarios()
    baselines = {}
    for s in scenarios:
        if s.id not in PUBLIC_SCORE_PROFILES:
            baselines[s.id] = run_scenario(s, fixed_time_controller, record_replay=False).metrics.cost
    rows = evaluate(controller_path, scenarios, baselines)
    pub = [r[3] for r in rows if r[0] in PUBLIC_SCORE_PROFILES]
    allsc = [r[3] for r in rows]
    print(f"{'id':32s} {'cost':>8s} {'base':>8s} {'score':>7s} unf")
    for rid, cost, base, sc, unf in rows:
        tag = "PUB" if rid in PUBLIC_SCORE_PROFILES else ""
        print(f"{rid:32s} {cost:8d} {base:8d} {sc:7d} {unf:3d} {tag}")
    print()
    print("PUBLIC geometric mean :", geometric_mean(pub), pub)
    print("ALL geometric mean    :", geometric_mean(allsc), f"({len(allsc)} maps)")
    worst = sorted(rows, key=lambda r: r[3])[:8]
    print("worst 8:", [(r[0], r[3]) for r in worst])
