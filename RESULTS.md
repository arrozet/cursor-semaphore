# Strategy A — Completion-Aware Drain

## Results (public geometric mean)

**Geometric mean: 21434**

| Scenario | Score | Cost | Unfinished | Wait ticks |
|---|---:|---:|---:|---:|
| balanced-grid | 18710 | 15553 | 8 | 13153 |
| northbound-morning | 24541 | 28933 | 30 | 19933 |
| city-rush | 21445 | 66518 | 50 | 51518 |

Scoring matches `run.py`: measured `fixed_time` baseline cost + official `score_profile.target_cost`.

## Controller summary

Path: `/Users/roz/Documents/github/cursor-semaphore-strategy-a/source/controller.py`

- **Synchronized** network-wide phase (all intersections share one axis).
- Green length = corridor traversal (`5 * (len-1)`) + max junction queue on the active axis (clamped to `[5, 50]`).
- **Late-switch veto**: never start a transition unless `remaining >= yellow+allred+useful` (3+5).
- **Compact-grid endgame drain** (`max(rows,cols) <= 2`, last 40 ticks): if the rival axis has more queued demand, shorten planned green to 6 and flip so near-exit cars can finish.
- Larger grids keep the synchronized adaptive policy unchanged (aggressive endgame flips hurt city-rush).

## Variants tried (best kept)

1. Aggressive global exit-steal / finishable bias — geom ~12k–16k (city-rush unfinished spiked).
2. Late-switch veto only — geom **17587** (≈ synchronized baseline).
3. Compact-only endgame replan — geom **21434** (winner; balanced unfinished 11→8, score 10.3k→18.7k).
4. Universal late exit-steal add-on — geom ~12k (rejected).
