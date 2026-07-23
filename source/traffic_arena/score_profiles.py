from __future__ import annotations

from .scoring import ScoreProfile


# Generated from the organizer's redacted public scenario registry.
PUBLIC_SCORE_PROFILES = {
    "balanced-grid": ScoreProfile(16_648, 15_211, 963),
    "northbound-morning": ScoreProfile(36_398, 28_816, 1_250),
    "city-rush": ScoreProfile(83_137, 64_111, 2_297),
}

# For local maps without an official gold target, aim ~15% under live baseline.
_LOCAL_GOLD_RATIO = 0.85


def score_profile(scenario_id: str, *, baseline_cost: int | None = None, spawned: int | None = None) -> ScoreProfile:
    if scenario_id in PUBLIC_SCORE_PROFILES:
        return PUBLIC_SCORE_PROFILES[scenario_id]
    if baseline_cost is None or baseline_cost <= 1:
        raise KeyError(f"No score profile for {scenario_id!r}; pass baseline_cost for local maps")
    target = max(1, round(baseline_cost * _LOCAL_GOLD_RATIO))
    if target >= baseline_cost:
        target = max(1, baseline_cost - 1)
    return ScoreProfile(baseline_cost, target, max(1, spawned or 1))
