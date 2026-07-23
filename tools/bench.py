"""Benchmark the controller against the fixed-time baseline.

Runs the 3 public scenarios plus a synthetic battery of unseen-style maps
(different grids, biases, demand windows, bursts, capacities) and reports
cost ratios vs baseline. Selection metric mimics the event: 20% public /
80% synthetic (as a stand-in for private maps), geometric means.

Usage: python tools/bench.py [--quick]
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
sys.path.insert(0, str(SOURCE))

from traffic_arena.engine import fixed_time_controller, run_scenario  # noqa: E402
from traffic_arena.scenarios import PUBLIC_SCENARIOS, DemandWindow, Scenario  # noqa: E402
from traffic_arena.score_profiles import PUBLIC_SCORE_PROFILES  # noqa: E402
from traffic_arena.scoring import scenario_score  # noqa: E402


def make_synthetic():
    """Deterministic battery of plausible private-style scenarios."""
    scenarios = []

    def windows(ticks, *specs):
        """specs: (span, n, s, e, w, row_w, col_w) covering [0, ticks)."""
        result = []
        start = 0
        for span, n, s, e, w, row_w, col_w in specs:
            result.append(
                DemandWindow(start, start + span, n, s, e, w, row_w or (), col_w or ())
            )
            start += span
        assert start == ticks
        return tuple(result)

    scenarios.append(Scenario("syn-1x1", "Single crossing", 1, 1, 11, horizontal_rate=0.15, vertical_rate=0.11))
    scenarios.append(Scenario("syn-corridor-ew", "EW corridor", 1, 4, 23, horizontal_rate=0.30, vertical_rate=0.07))
    scenarios.append(Scenario("syn-corridor-ns", "NS corridor", 4, 1, 37, horizontal_rate=0.07, vertical_rate=0.30))
    scenarios.append(Scenario("syn-ns-rush", "NS rush 2x2", 2, 2, 41, vertical_rate=0.24, horizontal_rate=0.08, rush_axis="NS"))
    scenarios.append(Scenario("syn-dense-3x3", "Dense 3x3", 3, 3, 53, horizontal_rate=0.20, vertical_rate=0.20))
    scenarios.append(Scenario("syn-burst-3x3", "Burst 3x3", 3, 3, 59, horizontal_rate=0.15, vertical_rate=0.15, burst_period=60))
    scenarios.append(Scenario("syn-light-2x2", "Light 2x2", 2, 2, 61, horizontal_rate=0.06, vertical_rate=0.06))
    scenarios.append(Scenario("syn-4x4", "Moderate 4x4", 4, 4, 71, horizontal_rate=0.14, vertical_rate=0.14))
    scenarios.append(Scenario("syn-tight-links", "Tight links 2x3", 2, 3, 83, horizontal_rate=0.16, vertical_rate=0.16, link_capacity=5, travel_ticks=8))
    scenarios.append(
        Scenario(
            "syn-flip", "Direction flip 2x3", 2, 3, 89,
            demand_windows=windows(
                900,
                (450, 0.28, 0.05, 0.08, 0.08, None, None),
                (450, 0.05, 0.06, 0.26, 0.10, None, None),
            ),
        )
    )
    scenarios.append(
        Scenario(
            "syn-lane-skew", "Lane skew 3x3", 3, 3, 97,
            demand_windows=windows(
                900,
                (900, 0.14, 0.14, 0.14, 0.14, (2.0, 0.6, 0.6), (0.5, 1.0, 2.0)),
            ),
        )
    )
    scenarios.append(
        Scenario(
            "syn-pulse", "Pulsed windows 2x2", 2, 2, 101,
            demand_windows=windows(
                900,
                (300, 0.30, 0.30, 0.05, 0.05, None, None),
                (300, 0.05, 0.05, 0.30, 0.30, None, None),
                (300, 0.18, 0.18, 0.18, 0.18, None, None),
            ),
        )
    )
    return scenarios


def load_controller():
    """Fresh module per map, mimicking the clean-process evaluation."""
    spec = importlib.util.spec_from_file_location("team_controller", SOURCE / "controller.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.control


def geo_mean(values):
    return math.exp(sum(math.log(max(v, 1e-9)) for v in values) / len(values))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="public maps only")
    args = parser.parse_args()

    print(f"{'scenario':<22}{'base':>8}{'ours':>8}{'ratio':>7}{'unfin':>6}  score")
    public_scores, public_ratios, syn_ratios = [], [], []

    for scenario in PUBLIC_SCENARIOS:
        baseline = run_scenario(scenario, fixed_time_controller, record_replay=False)
        ours = run_scenario(scenario, load_controller(), record_replay=False)
        profile = PUBLIC_SCORE_PROFILES[scenario.id]
        score = scenario_score(ours.metrics.cost, profile.baseline_cost, profile.target_cost)
        ratio = ours.metrics.cost / baseline.metrics.cost
        public_scores.append(score)
        public_ratios.append(ratio)
        print(f"{scenario.id:<22}{baseline.metrics.cost:>8}{ours.metrics.cost:>8}{ratio:>7.3f}{ours.metrics.unfinished:>6}  {score:,}")

    if not args.quick:
        for scenario in make_synthetic():
            baseline = run_scenario(scenario, fixed_time_controller, record_replay=False)
            ours = run_scenario(scenario, load_controller(), record_replay=False)
            ratio = ours.metrics.cost / baseline.metrics.cost
            syn_ratios.append(ratio)
            print(f"{scenario.id:<22}{baseline.metrics.cost:>8}{ours.metrics.cost:>8}{ratio:>7.3f}{ours.metrics.unfinished:>6}")

    print()
    print(f"public geo score : {geo_mean(public_scores):,.0f}")
    print(f"public geo ratio : {geo_mean(public_ratios):.3f}  (lower is better)")
    if syn_ratios:
        print(f"synth  geo ratio : {geo_mean(syn_ratios):.3f}")
        print(f"synth  worst     : {max(syn_ratios):.3f}")
        combined = 0.2 * geo_mean(public_ratios) + 0.8 * geo_mean(syn_ratios)
        print(f"combined 20/80   : {combined:.3f}")


if __name__ == "__main__":
    main()
