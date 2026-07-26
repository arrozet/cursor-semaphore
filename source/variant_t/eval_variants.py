"""Eval Variant T controllers; cache fixed_time baselines."""
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from traffic_arena.engine import run_scenario, fixed_time_controller
from traffic_arena.map_loader import load_runnable_scenarios
from traffic_arena.score_profiles import PUBLIC_SCORE_PROFILES
from traffic_arena.scoring import scenario_score, geometric_mean

CACHE = Path(__file__).resolve().parent / "_baselines.json"


def load_control(path):
    spec = importlib.util.spec_from_file_location("cand_" + Path(path).stem + str(time.time()), path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.control


def get_baselines(scenarios):
    if CACHE.exists():
        data = json.loads(CACHE.read_text())
        if all(s.id in data or s.id in PUBLIC_SCORE_PROFILES for s in scenarios):
            return {k: int(v) for k, v in data.items()}
    baselines = {}
    for s in scenarios:
        if s.id in PUBLIC_SCORE_PROFILES:
            continue
        baselines[s.id] = run_scenario(s, fixed_time_controller, record_replay=False).metrics.cost
        print(f"  baseline {s.id}: {baselines[s.id]}", flush=True)
    CACHE.write_text(json.dumps(baselines, indent=2))
    return baselines


def evaluate(controller_path, scenarios, baselines):
    rows = []
    for s in scenarios:
        # Reload per scenario (matches eval_all.py; avoids cross-map memory leak).
        control = load_control(controller_path)
        result = run_scenario(s, control, record_replay=False)
        if s.id in PUBLIC_SCORE_PROFILES:
            p = PUBLIC_SCORE_PROFILES[s.id]
            base_cost, target = p.baseline_cost, p.target_cost
        else:
            base_cost = baselines[s.id]
            target = max(1, min(round(base_cost * 0.85), base_cost - 1))
        sc = scenario_score(result.metrics.cost, base_cost, target)
        rows.append((s.id, result.metrics.cost, base_cost, sc, result.metrics.unfinished))
    return rows


def summarize(name, path, rows):
    pub = [r for r in rows if r[0] in PUBLIC_SCORE_PROFILES]
    ale = [r for r in rows if r[0] not in PUBLIC_SCORE_PROFILES]
    pub_g = geometric_mean([r[3] for r in pub])
    ale_g = geometric_mean([r[3] for r in ale])
    all_g = geometric_mean([r[3] for r in rows])
    unf = sum(r[4] for r in rows)
    worst = sorted(rows, key=lambda r: r[3])[:8]
    print(f"\n=== {name} ===")
    print(f"path: {path}")
    print(f"PUBLIC geom : {pub_g}")
    print(f"ALESUITO geom: {ale_g}")
    print(f"ALL geom    : {all_g}")
    print(f"total unfinished: {unf}")
    print("worst 8:", [(r[0], r[3], r[4]) for r in worst])
    return {
        "name": name,
        "path": str(path),
        "public": pub_g,
        "alesuito": ale_g,
        "all": all_g,
        "unfinished": unf,
        "worst": [(r[0], r[3], r[4]) for r in worst],
        "rows": rows,
    }


if __name__ == "__main__":
    variants = sys.argv[1:] or [
        "t1_fifo_mode.py",
        "t2_fifo_median.py",
        "t3_fifo_mode_cap.py",
        "t4_fifo_replan.py",
    ]
    base_dir = Path(__file__).resolve().parent
    scenarios = load_runnable_scenarios()
    print(f"maps: {len(scenarios)}", flush=True)
    print("computing/caching baselines...", flush=True)
    baselines = get_baselines(scenarios)
    results = []
    for name in variants:
        path = base_dir / name if not Path(name).is_absolute() else Path(name)
        t0 = time.time()
        rows = evaluate(path, scenarios, baselines)
        summary = summarize(path.stem, path, rows)
        summary["seconds"] = round(time.time() - t0, 1)
        results.append(summary)
        print(f"elapsed {summary['seconds']}s", flush=True)

    results.sort(key=lambda r: (-r["all"], -r["public"], r["unfinished"]))
    print("\n=== RANKING (best ALL geom) ===")
    for i, r in enumerate(results, 1):
        print(
            f"{i}. {r['name']}: ALL={r['all']} PUB={r['public']} ALE={r['alesuito']} unf={r['unfinished']}"
        )
    out = base_dir / "_eval_results.json"
    # drop raw rows for compactness in ranking file; keep worst
    slim = [{k: v for k, v in r.items() if k != "rows"} for r in results]
    out.write_text(json.dumps(slim, indent=2))
    print(f"wrote {out}")
