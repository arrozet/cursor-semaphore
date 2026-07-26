# Strategy B — Synchronized Max-Pressure Hybrid

## Strategy

Network-wide **synchronized** green phases (all junctions share one axis), with:

1. **Locked corridor green** at phase entry: `travel_ticks * hops + scale * max_junction_queue`, capped to `[MIN_GREEN, MAX_GREEN]`.
2. **Density-aware scale**: use `QUEUE_BONUS_IN_PLAN=1.15` normally; if `active_vehicles / intersections >= 8`, soften to `SOFT_BONUS=1.0` (avoids over-holding under city-rush density).
3. **Max-pressure score** per axis from approach queues (downstream occupancy weight available but best public set uses `0`).
4. **Hysteresis / pressure gate**: after planned green, switch only if `other_pressure > current + 1` (`REQUIRE_PRESSURE_TO_SWITCH=True`).
5. **Safe gap-out**: after `MIN_GREEN`, switch if current queues **and** in-flight link traffic on that axis are empty while the other axis has queued demand.
6. **Max-out** at `MAX_GREEN=50` if the other axis still has demand.
7. Transition commitment: while yellow/all-red, keep requesting the committed target phase.

## Winning parameters

| Param | Value |
| --- | ---: |
| QUEUE_BONUS_IN_PLAN | 1.15 |
| DENSITY_SOFTEN | 8.0 |
| SOFT_BONUS | 1.0 |
| HYSTERESIS | 1.0 |
| REQUIRE_PRESSURE_TO_SWITCH | True |
| DOWNSTREAM_WEIGHT | 0.0 |
| GAP_OUT_QUEUE / TRAVEL | 0 / 0 |
| MAX_GREEN | 50 |
| ENDGAME_TICKS | 0 |

## Public results (official scoring)

**Geometric mean: 22983** (vs sync-adaptive baseline ~17585)

| Scenario | Cost | Unfinished | Wait | Score |
| --- | ---: | ---: | ---: | ---: |
| balanced-grid | 15326 | 8 | 12926 | 22695 |
| northbound-morning | 28794 | 29 | 20094 | 25000 |
| city-rush | 66553 | 50 | 51553 | 21397 |

## Parameter-set summary (selected)

| Set | Geom | Notes |
| --- | ---: | --- |
| Pure sync plan (bonus 1.0) | 17587 | Matches prior sync adaptive |
| Bonus 1.15, no density soften | 21545 | Big balanced-grid win; city-rush regresses |
| Bonus 1.15 + density soften 8 | 22552 | Recovers most city-rush |
| **+ pressure gate / hyst=1** | **22983** | Best public geom (kept) |

## Critique (peer debate)

- **Sync is non-negotiable here**, but max-pressure alone without a locked corridor hold oscillates into yellow tax and collapses city-rush.
- **`QUEUE_BONUS=1.15` is brittle** (1.10 / 1.12 / 1.18 all much worse on public maps) — likely public overfitting; private maps may need the density softener more than the bonus.
- **Downstream occupancy weight did not help** the public geom; true max-pressure may still matter on private topologies with tighter link capacity.
- **Northbound is score-capped at 25000**; further public geom gains must come from balanced-grid (near target) and city-rush unfinished/wait.
- **Endgame logic was muted** (`ENDGAME_TICKS=0`) in the winner; unfinished remains 8/29/50 — a completion-aware drain peer may beat us on terminal penalty without hurting throughput.

## Artifact

Controller: `/Users/roz/Documents/github/cursor-semaphore-strategy-b/source/controller.py`
