"""Fast parallel evaluator for controller experiments.

Usage:
  python3.12 exp/fasteval.py <controller.py> [--name EXPNAME] [--maps substr1,substr2] [--jobs N]

Caches fixed-time baselines in exp/baselines.json (deterministic seeds).
Writes per-map results to exp/results/<EXPNAME>.json and prints summary.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
SRC_DIR = EXP_DIR.parent / "source"
sys.path.insert(0, str(SRC_DIR))

from traffic_arena.engine import run_scenario, fixed_time_controller  # noqa: E402
from traffic_arena.map_loader import load_runnable_scenarios  # noqa: E402
from traffic_arena.score_profiles import PUBLIC_SCORE_PROFILES  # noqa: E402
from traffic_arena.scoring import scenario_score, geometric_mean  # noqa: E402

BASELINE_CACHE = EXP_DIR / "baselines.json"
RESULTS_DIR = EXP_DIR / "results"


def _load_controller(path: str):
    spec = importlib.util.spec_from_file_location("cand_ctrl", Path(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.control


def _run_one(args: tuple[str, str]) -> tuple[str, int, int]:
    scenario_id, controller_path = args
    scenarios = {s.id: s for s in load_runnable_scenarios()}
    s = scenarios[scenario_id]
    result = run_scenario(s, _load_controller(controller_path), record_replay=False)
    return scenario_id, result.metrics.cost, result.metrics.unfinished


def _run_baseline(scenario_id: str) -> tuple[str, int]:
    scenarios = {s.id: s for s in load_runnable_scenarios()}
    s = scenarios[scenario_id]
    result = run_scenario(s, fixed_time_controller, record_replay=False)
    return scenario_id, result.metrics.cost


def get_baselines(scenario_ids: list[str], jobs: int) -> dict[str, int]:
    cache: dict[str, int] = {}
    if BASELINE_CACHE.exists():
        cache = json.loads(BASELINE_CACHE.read_text())
    missing = [sid for sid in scenario_ids if sid not in cache]
    if missing:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for sid, cost in ex.map(_run_baseline, missing):
                cache[sid] = cost
        BASELINE_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return cache


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("controller")
    ap.add_argument("--name", default=None)
    ap.add_argument("--maps", default=None, help="comma-separated id substrings filter")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--ref", default=None, help="reference results json to diff against")
    args = ap.parse_args()

    controller_path = str(Path(args.controller).resolve())
    scenarios = load_runnable_scenarios()
    if args.maps:
        needles = [n.strip() for n in args.maps.split(",") if n.strip()]
        scenarios = tuple(s for s in scenarios if any(n in s.id for n in needles))
    ids = [s.id for s in scenarios]

    hidden_ids = [sid for sid in ids if sid not in PUBLIC_SCORE_PROFILES]
    baselines = get_baselines(hidden_ids, args.jobs)

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(_run_one, [(sid, controller_path) for sid in ids]))

    rows = []
    for sid, cost, unf in results:
        if sid in PUBLIC_SCORE_PROFILES:
            p = PUBLIC_SCORE_PROFILES[sid]
            base, target = p.baseline_cost, p.target_cost
        else:
            base = baselines[sid]
            target = max(1, min(round(base * 0.85), base - 1))
        sc = scenario_score(cost, base, target)
        rows.append({"id": sid, "cost": cost, "base": base, "score": sc, "unfinished": unf})

    ref = None
    if args.ref:
        ref_rows = json.loads(Path(args.ref).read_text())["rows"]
        ref = {r["id"]: r for r in ref_rows}

    pub = [r["score"] for r in rows if r["id"] in PUBLIC_SCORE_PROFILES]
    hid = [r["score"] for r in rows if r["id"] not in PUBLIC_SCORE_PROFILES]
    allsc = [r["score"] for r in rows]

    print(f"{'id':34s} {'cost':>8s} {'score':>7s} {'unf':>4s}  {'d_score':>8s}")
    for r in sorted(rows, key=lambda r: r["score"]):
        d = ""
        if ref and r["id"] in ref:
            delta = r["score"] - ref[r["id"]]["score"]
            d = f"{delta:+8d}" if delta else ""
        tag = " PUB" if r["id"] in PUBLIC_SCORE_PROFILES else ""
        print(f"{r['id']:34s} {r['cost']:8d} {r['score']:7d} {r['unfinished']:4d}  {d:>8s}{tag}")

    summary = {
        "public_geom": geometric_mean(pub) if pub else 0,
        "alesuito_geom": geometric_mean(hid) if hid else 0,
        "all_geom": geometric_mean(allsc),
        "min_score": min(allsc),
        "total_unfinished": sum(r["unfinished"] for r in rows),
        "n_maps": len(rows),
    }
    print()
    for k, v in summary.items():
        print(f"{k:18s}: {v}")
    if ref:
        wins = sum(1 for r in rows if r["id"] in ref and r["score"] > ref[r["id"]]["score"])
        losses = sum(1 for r in rows if r["id"] in ref and r["score"] < ref[r["id"]]["score"])
        print(f"{'vs ref':18s}: +{wins} maps / -{losses} maps")

    if args.name:
        RESULTS_DIR.mkdir(exist_ok=True)
        out = {"name": args.name, "controller": controller_path, "summary": summary, "rows": rows}
        (RESULTS_DIR / f"{args.name}.json").write_text(json.dumps(out, indent=1))
        print(f"saved -> exp/results/{args.name}.json")


if __name__ == "__main__":
    main()
