#!/usr/bin/env python3
"""Generate diverse stress-suite replays into maps/alesuito/ (same schema as maps/basic/).

Does not modify any source controller or engine code — only imports the arena
to emit version-2 replay JSON for extreme / asymmetric / sparse / bursty maps.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
sys.path.insert(0, str(SOURCE))

from traffic_arena.engine import fixed_time_controller, run_scenario  # noqa: E402
from traffic_arena.map_loader import write_scenario_file  # noqa: E402
from traffic_arena.scenarios import DemandWindow, Scenario  # noqa: E402

OUT = Path(__file__).resolve().parent


def _w(*weights: float) -> tuple[float, ...]:
    return tuple(weights)


# ---------------------------------------------------------------------------
# Stress suite: each entry targets a different failure mode / extreme.
# Seeds and ids are unique; no duplicate topology+demand pairs.
# ---------------------------------------------------------------------------
SUITE: list[Scenario] = [
    # --- tiny / degenerate grids ---
    Scenario("single-cell", "Single intersection", 1, 1, 101, horizontal_rate=0.18, vertical_rate=0.18),
    Scenario("corridor-1x4", "Thin EW corridor", 1, 4, 102, horizontal_rate=0.28, vertical_rate=0.04),
    Scenario("corridor-5x1", "Thin NS corridor", 5, 1, 103, horizontal_rate=0.04, vertical_rate=0.28),
    Scenario("micro-2x1", "Micro 2x1", 2, 1, 104, horizontal_rate=0.10, vertical_rate=0.22),
    Scenario("micro-1x2", "Micro 1x2", 1, 2, 105, horizontal_rate=0.22, vertical_rate=0.10),
    # --- balanced vs biased on same size ---
    Scenario("grid-2x2-balanced", "2x2 balanced medium", 2, 2, 201, horizontal_rate=0.14, vertical_rate=0.14),
    Scenario("grid-2x2-ns-storm", "2x2 NS storm", 2, 2, 202, horizontal_rate=0.05, vertical_rate=0.32, rush_axis="NS"),
    Scenario("grid-2x2-ew-storm", "2x2 EW storm", 2, 2, 203, horizontal_rate=0.32, vertical_rate=0.05, rush_axis="EW"),
    Scenario("grid-2x2-sparse", "2x2 sparse trickle", 2, 2, 204, horizontal_rate=0.03, vertical_rate=0.03),
    Scenario("grid-2x2-saturated", "2x2 near saturation", 2, 2, 205, horizontal_rate=0.35, vertical_rate=0.35),
    # --- rectangular / larger ---
    Scenario("grid-3x2-ns-rush", "3x2 NS rush", 3, 2, 301, horizontal_rate=0.08, vertical_rate=0.24, rush_axis="NS"),
    Scenario("grid-2x3-ew-rush", "2x3 EW rush", 2, 3, 302, horizontal_rate=0.24, vertical_rate=0.08, rush_axis="EW"),
    Scenario("grid-3x3-balanced", "3x3 balanced", 3, 3, 303, horizontal_rate=0.15, vertical_rate=0.15),
    Scenario("grid-3x3-burst90", "3x3 burst period 90", 3, 3, 304, horizontal_rate=0.18, vertical_rate=0.18, burst_period=90),
    Scenario("grid-3x3-burst45", "3x3 fast burst 45", 3, 3, 305, horizontal_rate=0.16, vertical_rate=0.16, burst_period=45),
    Scenario("grid-4x4-heavy", "4x4 heavy city", 4, 4, 306, horizontal_rate=0.16, vertical_rate=0.16, burst_period=120),
    Scenario("grid-5x3-wide", "5x3 wide rectangle", 5, 3, 307, horizontal_rate=0.12, vertical_rate=0.18),
    Scenario("grid-3x5-tall", "3x5 tall rectangle", 3, 5, 308, horizontal_rate=0.18, vertical_rate=0.12),
    Scenario("grid-4x2-strip", "4x2 strip", 4, 2, 309, horizontal_rate=0.10, vertical_rate=0.20, rush_axis="NS"),
    # --- capacity / travel extremes ---
    Scenario(
        "tiny-links-2x2",
        "2x2 tiny link capacity",
        2,
        2,
        401,
        link_capacity=3,
        horizontal_rate=0.20,
        vertical_rate=0.20,
    ),
    Scenario(
        "fat-links-3x3",
        "3x3 fat links",
        3,
        3,
        402,
        link_capacity=14,
        horizontal_rate=0.22,
        vertical_rate=0.22,
    ),
    Scenario(
        "slow-travel-3x3",
        "3x3 slow travel",
        3,
        3,
        403,
        travel_ticks=12,
        horizontal_rate=0.14,
        vertical_rate=0.14,
    ),
    Scenario(
        "fast-travel-2x3",
        "2x3 fast travel",
        2,
        3,
        404,
        travel_ticks=2,
        horizontal_rate=0.20,
        vertical_rate=0.12,
    ),
    # --- one-sided / almost empty axis ---
    Scenario("ns-only-3x3", "3x3 almost NS only", 3, 3, 501, horizontal_rate=0.01, vertical_rate=0.26),
    Scenario("ew-only-3x3", "3x3 almost EW only", 3, 3, 502, horizontal_rate=0.26, vertical_rate=0.01),
    Scenario("dead-quiet-2x2", "2x2 near empty", 2, 2, 503, horizontal_rate=0.01, vertical_rate=0.01),
    # --- demand_windows: regime shifts & weird exceptions ---
    Scenario(
        "windows-quiet-to-rush",
        "Quiet then NS rush",
        3,
        3,
        601,
        demand_windows=(
            DemandWindow(0, 300, 0.06, 0.06, 0.06, 0.06),
            DemandWindow(300, 700, 0.30, 0.28, 0.06, 0.06),
            DemandWindow(700, 900, 0.08, 0.08, 0.08, 0.08),
        ),
    ),
    Scenario(
        "windows-rush-to-quiet",
        "Opening rush then die",
        3,
        2,
        602,
        demand_windows=(
            DemandWindow(0, 250, 0.28, 0.26, 0.22, 0.20),
            DemandWindow(250, 900, 0.04, 0.04, 0.04, 0.04),
        ),
    ),
    Scenario(
        "windows-flip-axis",
        "NS then flip to EW",
        3,
        3,
        603,
        demand_windows=(
            DemandWindow(0, 450, 0.26, 0.24, 0.05, 0.05),
            DemandWindow(450, 900, 0.05, 0.05, 0.26, 0.24),
        ),
    ),
    Scenario(
        "windows-oscillate",
        "Oscillating 150-tick windows",
        2,
        2,
        604,
        demand_windows=(
            DemandWindow(0, 150, 0.28, 0.28, 0.06, 0.06),
            DemandWindow(150, 300, 0.06, 0.06, 0.28, 0.28),
            DemandWindow(300, 450, 0.28, 0.28, 0.06, 0.06),
            DemandWindow(450, 600, 0.06, 0.06, 0.28, 0.28),
            DemandWindow(600, 750, 0.28, 0.28, 0.06, 0.06),
            DemandWindow(750, 900, 0.06, 0.06, 0.28, 0.28),
        ),
    ),
    Scenario(
        "windows-lane-skew-rows",
        "Demand piled on one row",
        3,
        3,
        605,
        demand_windows=(
            DemandWindow(
                0,
                900,
                0.12,
                0.12,
                0.20,
                0.20,
                row_weights=_w(0.05, 0.15, 0.80),
                col_weights=_w(0.33, 0.34, 0.33),
            ),
        ),
    ),
    Scenario(
        "windows-lane-skew-cols",
        "Demand piled on one column",
        3,
        3,
        606,
        demand_windows=(
            DemandWindow(
                0,
                900,
                0.22,
                0.22,
                0.10,
                0.10,
                row_weights=_w(0.33, 0.34, 0.33),
                col_weights=_w(0.05, 0.10, 0.85),
            ),
        ),
    ),
    Scenario(
        "windows-north-only-pulse",
        "North-only pulses",
        4,
        2,
        607,
        demand_windows=(
            DemandWindow(0, 200, 0.35, 0.02, 0.04, 0.04),
            DemandWindow(200, 400, 0.04, 0.04, 0.04, 0.04),
            DemandWindow(400, 650, 0.35, 0.02, 0.04, 0.04),
            DemandWindow(650, 900, 0.05, 0.05, 0.08, 0.08),
        ),
    ),
    Scenario(
        "windows-asymmetric-cardinals",
        "N+E heavy S+W empty",
        3,
        3,
        608,
        demand_windows=(DemandWindow(0, 900, 0.30, 0.02, 0.28, 0.02),),
    ),
    Scenario(
        "windows-mid-spike",
        "Mid-episode spike all axes",
        2,
        3,
        609,
        demand_windows=(
            DemandWindow(0, 350, 0.08, 0.08, 0.08, 0.08),
            DemandWindow(350, 500, 0.40, 0.40, 0.40, 0.40),
            DemandWindow(500, 900, 0.07, 0.07, 0.07, 0.07),
        ),
    ),
    Scenario(
        "windows-endgame-flood",
        "Flood in last 200 ticks",
        3,
        3,
        610,
        demand_windows=(
            DemandWindow(0, 700, 0.10, 0.10, 0.10, 0.10),
            DemandWindow(700, 900, 0.32, 0.32, 0.32, 0.32),
        ),
    ),
    # --- weird combos ---
    Scenario(
        "combo-1x3-burst-tiny-links",
        "1x3 burst + tiny links",
        1,
        3,
        701,
        link_capacity=2,
        burst_period=60,
        horizontal_rate=0.30,
        vertical_rate=0.08,
    ),
    Scenario(
        "combo-4x4-sparse-slow",
        "4x4 sparse slow travel",
        4,
        4,
        702,
        travel_ticks=10,
        horizontal_rate=0.05,
        vertical_rate=0.05,
    ),
    Scenario(
        "combo-2x2-flip-tiny-cap",
        "2x2 axis flip + cap 4",
        2,
        2,
        703,
        link_capacity=4,
        demand_windows=(
            DemandWindow(0, 400, 0.30, 0.30, 0.04, 0.04),
            DemandWindow(400, 900, 0.04, 0.04, 0.30, 0.30),
        ),
    ),
    Scenario(
        "combo-5x5-mild",
        "5x5 mild large grid",
        5,
        5,
        704,
        horizontal_rate=0.09,
        vertical_rate=0.09,
    ),
    Scenario(
        "combo-corner-bias-3x3",
        "3x3 corner-weighted lanes",
        3,
        3,
        705,
        demand_windows=(
            DemandWindow(
                0,
                900,
                0.18,
                0.18,
                0.18,
                0.18,
                row_weights=_w(0.70, 0.15, 0.15),
                col_weights=_w(0.70, 0.15, 0.15),
            ),
        ),
    ),
]


def _scenario_summary(s: Scenario) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "rows": s.rows,
        "cols": s.cols,
        "seed": s.seed,
        "ticks": s.ticks,
        "travel_ticks": s.travel_ticks,
        "link_capacity": s.link_capacity,
        "horizontal_rate": s.horizontal_rate,
        "vertical_rate": s.vertical_rate,
        "rush_axis": s.rush_axis,
        "burst_period": s.burst_period,
        "demand_windows": len(s.demand_windows),
    }


def main() -> None:
    ids = [s.id for s in SUITE]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"duplicate scenario ids: {ids}")

    manifest: list[dict] = []
    t0 = time.time()
    for i, scenario in enumerate(SUITE, 1):
        print(f"[{i}/{len(SUITE)}] {scenario.id} ({scenario.rows}x{scenario.cols}) ...", flush=True)
        result = run_scenario(scenario, fixed_time_controller, record_replay=True)
        assert result.replay is not None
        out_path = OUT / f"{scenario.id}.json"
        out_path.write_text(json.dumps(result.replay, separators=(",", ":")), encoding="utf-8")
        entry = {
            **_scenario_summary(scenario),
            "metrics": {
                "spawned": result.metrics.spawned,
                "completed": result.metrics.completed,
                "unfinished": result.metrics.unfinished,
                "waitTicks": result.metrics.wait_ticks,
                "cost": result.metrics.cost,
            },
            "file": out_path.name,
            "bytes": out_path.stat().st_size,
        }
        manifest.append(entry)
        m = result.metrics
        print(
            f"    cost={m.cost} wait={m.wait_ticks} unfinished={m.unfinished} "
            f"spawned={m.spawned} -> {out_path.name}",
            flush=True,
        )

    catalog = {
        "version": 1,
        "owner": "alesuito",
        "purpose": (
            "Stress suite of extreme / asymmetric maps to probe geometric-mean "
            "robustness against hidden private maps. Same replay schema as maps/basic/."
        ),
        "controller_used": "fixed_time_controller (engine baseline)",
        "count": len(manifest),
        "maps": manifest,
    }
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"\nDone: {len(manifest)} maps in {time.time() - t0:.1f}s -> {OUT}")


if __name__ == "__main__":
    main()
