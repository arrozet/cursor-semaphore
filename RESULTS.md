# Strategy D — Occupancy Travel-Time + Floor Guard

Isolated worktree: `/Users/roz/Documents/github/cursor-semaphore-wt-d`  
Controller: `/Users/roz/Documents/github/cursor-semaphore-wt-d/source/controller.py`

## Final public metrics

| Scenario | Score | Cost | Wait ticks | Unfinished | Spawned | Completed |
|----------|------:|-----:|-----------:|-----------:|--------:|----------:|
| balanced-grid | 19,540 | 15,502 | 13,102 | 8 | 963 | 955 |
| northbound-morning | 24,541 | 28,933 | 19,933 | 30 | 1,250 | 1,220 |
| city-rush | 21,445 | 66,518 | 51,518 | 50 | 2,297 | 2,247 |

- **Public geometric mean:** 21,746
- **Min scenario score (floor):** 19,540
- **Total unfinished:** 88

Eval: `/opt/homebrew/bin/python3.12`, `fixed_time` baseline + `scenario_score` + `geometric_mean`, controller module re-executed per scenario.

### Baseline costs (fixed_time) / gold targets

| Scenario | Baseline cost | Gold target |
|----------|--------------:|------------:|
| balanced-grid | 16,648 | 15,211 |
| northbound-morning | 36,398 | 28,816 |
| city-rush | 83,137 | 64,111 |

## Sync adaptive reference (~17,585 geom)

| Scenario | Score | Cost | Unfinished |
|----------|------:|-----:|-----------:|
| balanced-grid | 10,336 | 16,433 | 11 |
| northbound-morning | 24,533 | 28,935 | 30 |
| city-rush | 21,445 | 66,518 | 50 |

## Variants tried

| Variant | Geom | Min | Unf | Notes |
|---------|-----:|----:|----:|-------|
| D1 aggressive floor/gap-out | 8,481 | 7,315 | high | Over-switched; shredded platoons |
| D2 mild occupancy + soft floor | 12,745 | 9,971 | 108 | Still too reactive |
| D3 completion green-extend | 11,135 | 9,577 | 132 | Late extension hurt throughput |
| D4 spillback / demand-ratio | ≤17k | — | — | Below sync baseline |
| **D-final compact platoon hold** | **21,746** | **19,540** | **88** | Winner |

## Design (winner)

1. **Synchronized** network-wide NS/EW phase (sticky through yellow/all-red).
2. **Occupancy travel:** EMA of per-axis `vehicles/capacity` scales travel around 5; `capacity/8` mild scale for private maps.
3. **Green:** `round(travel * hops + max_junction_queue)`, clamped `[5, 50]`.
4. **Compact platoon hold:** if `max(rows, cols) <= 2`, delay switch while current axis has link vehicles and higher demand.
5. **Completion guard (compact):** last 100 ticks — hold busy axis or force clearly heavier demand.
6. **Floor guard (non-compact):** after planned green, switch if red `oldest_wait >= 55`.
7. Block switches when `remaining_ticks < 8`.

## Delta vs sync adaptive

- Geom **21,746** vs 17,585 (+4,161)
- Floor (min score) **19,540** vs 10,336
- balanced-grid unfinished 8 (was 11); cost under gold band
- city-rush unchanged vs sync adaptive on this winner; northbound slightly better
