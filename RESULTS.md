# Variant S — Saturated/Spillback Pressure on Strategy B

## Strategy

Base: Strategy B synchronized max-pressure hybrid (locked corridor green +
pressure-gated switch + density soften).

Change: re-enable classic downstream occupancy penalty in axis pressure:

```text
pressure -= DOWNSTREAM_WEIGHT * (occ / capacity) * max(q, 1)
```

with `DOWNSTREAM_WEIGHT = 0.10`, gated to **square grids only**
(`rows == cols` and both ≥ 2). Strip maps (e.g. mid-spike 2×3, rush-to-quiet
3×2) and 1-wide micros keep pure B behavior. Sync phases unchanged.

## Winning parameters (S3)

| Param | Value |
| --- | ---: |
| DOWNSTREAM_WEIGHT | 0.10 |
| REQUIRE_SQUARE_GRID | True |
| TRAVEL_IN_PRESSURE | 0.0 |
| (all other B tunables) | unchanged |

## Official eval (`eval_all.py`)

| Slice | Variant S | Strategy B | Δ |
| --- | ---: | ---: | ---: |
| PUBLIC geom | 22977 | 22983 | −6 |
| ALESUITO geom | 20441 | 20296 | +145 |
| ALL geom | **20605** | 20469 | **+136** |
| Total unfinished | 2652 | 2680 | −28 |

Public: balanced-grid 22676 (−19), northbound 25000, city-rush 21397 (held).

Notable alesuito moves vs B:

| Map | S | B | Δ |
| --- | ---: | ---: | ---: |
| windows-lane-skew-cols | 20234 | 15580 | +4654 |
| grid-2x2-balanced | 10563 | 10323 | +240 |
| windows-flip-axis | 25000 | 24928 | +72 |
| grid-2x2-saturated | 9762 | 9703 | +59 |
| combo-4x4-sparse-slow | 7028 | 7037 | −9 |
| fat-links-3x3 | 22289 | 22289 | 0 |
| windows-mid-spike | 23563 | 23563 | 0 (gated) |
| windows-rush-to-quiet | 12568 | 12568 | 0 (gated) |

## Variants tried (2–4)

| ID | Idea | ALL geom | Notes |
| --- | --- | ---: | --- |
| S1 | Classic DW≥0.03, all ≥2×2 grids | 20250 | mid-spike −11147, rush-to-quiet −1477; net loss |
| S2 | Near-capacity thresh / density-gate / green-shorten-only | 20469 | Never flips decisions (= B) |
| **S3** | **Square-gated classic DW=0.10** | **20605** | **Best; beats B** |
| S4 | Square ≥3×3 only, DW=0.10 | 20592 | Preserves public 22983; misses 2×2 gains |

Ungated spill-gap / TRAVEL_IN_PRESSURE≥0.04 either no-oped or erased the
square-gated win. Fat-links (cap=14) barely feels `occ/capacity`.

## Critique

- Square gating is the whole win: same DW that helps lane-skew/saturated
  destroys mid-spike when allowed on 2×3 strips.
- Saturated/sparse-slow/fat-links barely move (+59 / −9 / 0); the ALL gain
  is mostly `windows-lane-skew-cols`, not the stated failure modes.
- Public balanced-grid pays −19 for enabling 2×2 spillback; S4 avoids that
  but loses ALL points on 2×2 stress maps.
- Soft near-full thresholds and plan-time green shortening never fired —
  spillback only mattered as a continuous pressure bias on square grids.

## Artifact

Controller: `/Users/roz/Documents/github/cursor-semaphore/source/controller.py`
