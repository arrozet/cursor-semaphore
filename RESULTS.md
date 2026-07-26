# Strategy C — Demand-Ratio Adaptive Split

**Worktree:** `/Users/roz/Documents/github/cursor-semaphore-strategy-c`  
**Controller:** `/Users/roz/Documents/github/cursor-semaphore-strategy-c/source/controller.py`  
**Eval:** `/opt/homebrew/bin/python3.12` · `fixed_time` baseline · `scenario_score` · `geometric_mean`  
**Module globals reset:** re-import `controller.py` each scenario.

## Final result

| Metric | Value |
|--------|------:|
| **Public geometric mean** | **21,514** |
| Baseline sync-adaptive geom | 17,585 |
| Delta vs baseline | +3,929 |

### Per scenario (final controller)

| Scenario | Score | Cost | Wait | Unfinished | Baseline cost | Target (gold) |
|----------|------:|-----:|-----:|-----------:|--------------:|--------------:|
| balanced-grid | 18,177 | 15,587 | 13,187 | 8 | 16,648 | 15,211 |
| northbound-morning | 25,000 | 28,793 | 19,793 | 30 | 36,398 | 28,816 |
| city-rush | 21,914 | 66,181 | 51,181 | 50 | 83,137 | 64,111 |

Northbound hits **gold** (cost ≤ target). Balanced still carries unfinished=8 (×300 = 2,400 cost).

## Strategy

1. **Synchronized** network-wide NS/EW phase (required for large grids).
2. **EMA demand** per axis (`α=0.055`) from live queue totals.
3. **Green allocation:**
   ```
   green = LINK_TRAVEL * max(corridor-1, 0)
         + peak_w * max_junction_queue
         + avg_w  * (axis_total / n_junctions)
         + SHARE_BONUS * (ema_share - 0.5)
   ```
   clamped to `[5, 50]`.
4. **Topology split (not scenario ids):** ≤4 junctions → `(peak_w, avg_w)=(0.7, 0.3)`; else `(0.86, 0.14)`.
5. **Switch** when planned green elapsed, rival queue > 0, and `remaining ≥ transition(3)+useful(5)` (late veto).
6. Asymmetry for NS-heavy maps comes only from **EMA share bonus**, not hard-coded scenario names.

## Variant log (selected)

| Variant | Geom | Notes |
|---------|-----:|-------|
| V0 original sync adaptive | 17,585 | `trav + peak` only |
| V1 pure cycle-split ratio | ~10k | Too many unfinished; unstable greens |
| V2 ratio stretch of peak | 9–13k | Stretch hurt city-rush bursts |
| V3 aggressive endgame lock | 7–11k | Monopolizing one axis stranded the other |
| V4 `avg_blend` uniform 0.7/0.3 + share=8 | **19,672** | Big balanced lift; NS/city regress |
| V5 topology-aware large=0.85/0.15 | **21,443** | Restored NS gold + city |
| V6 **final** large=0.86/0.14, share=7, α=0.055 | **21,514** | Best geom |

Aggressive unfinished endgames (prefer-heavy / green extension / gap-out) consistently **increased** unfinished on public maps; kept only the light late-switch affordability veto.

## Critique seeds (for peer debate)

1. Topology threshold `n≤4` is a soft overfit to public 2×2 vs larger grids; private odd sizes may land on the wrong blend.
2. Unfinished remains 8/30/50 — endgame drain attempts failed; peers may have a better completion-aware switch.
3. Share bonus is linear and tiny; multiplicative Webster-style splits underperformed here but may generalize better privately.
4. No downstream occupancy / max-pressure term — may lose on congested private corridors.
5. Balanced is still far from gold (15,211); geom is carried by NS gold + solid city, so a private family that looks like “hard balanced” could punish this controller.
