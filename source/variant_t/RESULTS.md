# Variant T — Travel-Inference (on Strategy B)

## Winner

| Metric | Value | vs B |
|---|---:|---:|
| PUBLIC geom | **22983** | +0 |
| ALESUITO geom | **20477** | +181 |
| ALL geom (44) | **20639** | **+170** |
| total unfinished | **2669** | −11 |

**Controller path:** `/Users/roz/Documents/github/cursor-semaphore/source/variant_t/controller_T_best.py`

Also mirrored to `source/controller.py` and `source/variant_t/t1_solo_mode.py`.

B baseline: PUBLIC 22983 · ALESUITO 20296 · ALL 20469 · unfinished 2680.

## Method

Keep Strategy B (sync max-pressure, corridor planned green, pressure-gated switch).
Replace hardcoded `LINK_TRAVEL_TICKS = 5` with **solo-occupancy dwell**:

- When a link goes `0 → 1` vehicles, record entry tick.
- When it returns `1 → 0`, sample `duration` (= exact `travel_ticks`).
- Use **mode** of recent samples once `MIN_SAMPLES ≥ 3`; else fallback **5**.
- Reset inference + plan state at `tick == 0` (safe if the module is reused across maps).

Net-occupancy FIFO (counting all arrivals/departures) was tried and **rejected**: concurrent enter/exit in one tick biases the estimate (e.g. city-rush mode drifted to 10).

## Variant ladder (clean per-map reload)

| Variant | PUBLIC | ALESUITO | ALL | unfinished | Notes |
|---|---:|---:|---:|---:|---|
| **T1 solo mode** | 22983 | 20477 | **20639** | **2669** | **winner** |
| T4 solo + occ/cap prior | 22983 | 20477 | 20639 | 2678 | tie ALL; worse unfinished |
| T3 solo MIN_SAMPLES=1 | 22983 | 20440 | 20604 | 2656 | early adopt hurts a bit |
| T2 solo + mid-phase replan | 22983 | 20434 | 20599 | 2656 | replan slightly worse |
| (discarded) FIFO net-change | ~16–19k | — | ~17k | — | destroys public geom |

## Worst 8 (winner T1)

| map | score | unfinished |
|---|---:|---:|
| combo-4x4-sparse-slow | 8211 | 53 |
| grid-2x2-saturated | 9703 | 80 |
| grid-2x2-balanced | 10323 | 17 |
| fast-travel-2x3 | 10892 | 21 |
| combo-corner-bias-3x3 | 12071 | 21 |
| windows-endgame-flood | 12086 | 142 |
| windows-rush-to-quiet | 12568 | 7 |
| windows-lane-skew-cols | 15580 | 20 |

Key target moves vs B: `fast-travel-2x3` 8842→10892; `combo-4x4-sparse-slow` 7037→8211. Public maps unchanged (travel=5).

## Eval

```bash
cd /Users/roz/Documents/github/cursor-semaphore/source
python3.12 eval_all.py /Users/roz/Documents/github/cursor-semaphore/source/variant_t/controller_T_best.py
```

Official `eval_all.py` confirmed: PUBLIC 22983, ALL 20639.
