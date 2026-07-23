"""Fast parallel evaluator for controller experiments.

Usage:
  python3.12 exp/fasteval.py <controller.py> [--name EXPNAME] [--maps substr1,substr2] [--jobs N]

Caches fixed-time baselines in exp/baselines.json (deterministic seeds).
Writes per-map results to exp/results/<EXPNAME>.json and prints summary.
"""

from __future__ import annotations

import argparse
import dataclasses
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


def _variant(scenario_id: str, k: int):
    scenarios = {s.id: s for s in load_runnable_scenarios()}
    s = scenarios[scenario_id]
    if k == 0:
        return s
    return dataclasses.replace(s, seed=s.seed + 7919 * k)


def _load_controller(path: str):
    spec = importlib.util.spec_from_file_location("cand_ctrl", Path(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.control


def _run_one(args: tuple[str, int, str]) -> tuple[str, int, int, int]:
    scenario_id, k, controller_path = args
    s = _variant(scenario_id, k)
    result = run_scenario(s, _load_controller(controller_path), record_replay=False)
    return scenario_id, k, result.metrics.cost, result.metrics.unfinished


def _run_baseline(key: str) -> tuple[str, int]:
    scenario_id, _, ks = key.partition("@")
    s = _variant(scenario_id, int(ks or 0))
    result = run_scenario(s, fixed_time_controller, record_replay=False)
    return key, result.metrics.cost


def get_baselines(keys: list[str], jobs: int) -> dict[str, int]:
    cache: dict[str, int] = {}
    if BASELINE_CACHE.exists():
        cache = json.loads(BASELINE_CACHE.read_text())
    missing = [k for k in keys if k not in cache]
    if missing:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for key, cost in ex.map(_run_baseline, missing):
                cache[key] = cost
        BASELINE_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return cache


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("controller")
    ap.add_argument("--name", default=None)
    ap.add_argument("--maps", default=None, help="comma-separated id substrings filter")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=1, help="seed variants per map")
    ap.add_argument("--ref", default=None, help="reference results json to diff against")
    args = ap.parse_args()

    controller_path = str(Path(args.controller).resolve())
    scenarios = load_runnable_scenarios()
    if args.maps:
        needles = [n.strip() for n in args.maps.split(",") if n.strip()]
        scenarios = tuple(s for s in scenarios if any(n in s.id for n in needles))
    ids = [s.id for s in scenarios]

    tasks = [(sid, k) for sid in ids for k in range(args.seeds)]
    base_keys = [
        f"{sid}@{k}" for sid, k in tasks if not (k == 0 and sid in PUBLIC_SCORE_PROFILES)
    ]
    baselines = get_baselines(base_keys, args.jobs)

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        results = list(
            ex.map(_run_one, [(sid, k, controller_path) for sid, k in tasks])
        )

    variant_scores: dict[str, list[int]] = {sid: [0] * args.seeds for sid in ids}
    variant_unf: dict[str, list[int]] = {sid: [0] * args.seeds for sid in ids}
    variant_costs: dict[str, list[int]] = {sid: [0] * args.seeds for sid in ids}
    for sid, k, cost, unf in results:
        if k == 0 and sid in PUBLIC_SCORE_PROFILES:
            p = PUBLIC_SCORE_PROFILES[sid]
            base, target = p.baseline_cost, p.target_cost
        else:
            base = baselines[f"{sid}@{k}"]
            target = max(1, min(round(base * 0.85), base - 1))
        variant_scores[sid][k] = scenario_score(cost, base, target)
        variant_unf[sid][k] = unf
        variant_costs[sid][k] = cost

    rows = []
    for sid in ids:
        scores = variant_scores[sid]
        rows.append(
            {
                "id": sid,
                "cost": variant_costs[sid][0],
                "score": geometric_mean(scores),
                "score0": scores[0],
                "scores": scores,
                "unfinished": sum(variant_unf[sid]) // len(variant_unf[sid]),
            }
        )

    ref = None
    if args.ref:
        ref_rows = json.loads(Path(args.ref).read_text())["rows"]
        ref = {r["id"]: r for r in ref_rows}

    pub = [r["score"] for r in rows if r["id"] in PUBLIC_SCORE_PROFILES]
    pub0 = [r["score0"] for r in rows if r["id"] in PUBLIC_SCORE_PROFILES]
    hid = [r["score"] for r in rows if r["id"] not in PUBLIC_SCORE_PROFILES]
    allsc = [r["score"] for r in rows]

    print(f"{'id':34s} {'score':>7s} {'unf':>4s}  {'d_score':>8s}  variants")
    for r in sorted(rows, key=lambda r: r["score"]):
        d = ""
        if ref and r["id"] in ref:
            delta = r["score"] - ref[r["id"]]["score"]
            d = f"{delta:+8d}" if delta else ""
        tag = " PUB" if r["id"] in PUBLIC_SCORE_PROFILES else ""
        var = ",".join(str(s) for s in r["scores"]) if len(r["scores"]) > 1 else ""
        print(f"{r['id']:34s} {r['score']:7d} {r['unfinished']:4d}  {d:>8s}  {var}{tag}")

    summary = {
        "public_geom": geometric_mean(pub) if pub else 0,
        "public_geom_seed0": geometric_mean(pub0) if pub0 else 0,
        "alesuito_geom": geometric_mean(hid) if hid else 0,
        "all_geom": geometric_mean(allsc),
        "min_score": min(allsc),
        "total_unfinished": sum(r["unfinished"] for r in rows),
        "n_maps": len(rows),
        "seeds": args.seeds,
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
