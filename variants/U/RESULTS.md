# Variant U — Unfinished / Endgame Guard (on Strategy B)

## Goal

Beat Strategy B **ALL geom 20469** by cutting unfinished (+300 each) and protecting floors, without cratering **balanced-grid ~22695**. Conservative: prior aggressive compact endgame cratered public 22983→17205.

## Winner: U9 spike-gated drain

**Path:** `/Users/roz/Documents/github/cursor-semaphore/variants/U/u9_spike_drain.py`  
(also `variants/U/controller_final.py`)

### Scores vs Strategy B

| | PUBLIC geom | ALESUITO geom | ALL geom | Total unfinished |
|---|---:|---:|---:|---:|
| **B (baseline)** | 22983 | 20296 | 20469 | 2680 |
| **U9 (winner)** | **22983** | **20857** | **20996** | 2867 |
| Δ | 0 | +561 | **+527** | +187 |

Public floors held: balanced-grid **22695**, northbound **25000**, city-rush **21397** (unf 50 unchanged).

### Key map wins

| Map | B score / unf | U9 score / unf |
|---|---:|---:|
| windows-endgame-flood | 12086 / 142 | **25000 / 114** |
| windows-rush-to-quiet | 12568 / 7 | **14181 / 6** |
| micro-1x2 | 19293 / 8 | **25000 / 6** |
| windows-flip-axis | 24928 / 74 | **25000 / 48** |

## Mechanism

Strategy B sync max-pressure hybrid, plus:

1. **Late freeze** (last `YELLOW+ALLRED+MIN_GREEN` = 8 ticks): switch only if current axis queues **and** in-flight are empty.
2. **Soft hold** (last 80 ticks always): switch only if current cleared or other work dominates; **no max-out** in that window (esp. large grids).
3. **Spike-gated drain** (last 200 ticks, ≥9 cells): if density spikes vs early-episode mean (`≥ max(5.5, 1.45×early_mean)` and active≥40), extend soft-hold, suppress max-out, mild planned-green boost (`×1.15`, max green 68).

Spike gate is the critical filter: steady city-rush does **not** trigger drain-extend; late floods (endgame-flood) do.

## Variant sweep (selected)

| Variant | Idea | PUB | ALL | Notes |
|---|---|---:|---:|---|
| U0 | B copy | 22983 | 20469 | baseline |
| U1 | soft hold 24 | 22983 | 20469 | no-op on targets |
| U2 | soft hold 80 + no max-out | 22983 | 20652 | safe ALL +183 |
| U3 | soft 60 + starve 55 | 22983 | 20651 | ≈U2 |
| U4 | dense drain extend (ungated size) | **15561** | 19101 | flood↑ but public crater |
| U5 | dense soft 160 (no extend) | 22983 | 20652 | ≈U2 |
| U6 | soft hold 120 | 22983 | 20210 | rush-to-quiet regress |
| U7 | large-grid dense drain | 20396 | 20570 | flood→25000, city-rush↓ |
| U8 | stronger large drain | 21091 | 20275 | city-rush / 3x3 hurt |
| **U9** | **spike-gated drain** | **22983** | **20996** | **winner** |
| U10 | spike soft-only | 22983 | 20652 | flood unchanged |
| U11 | milder spike drain | 22983 | 20996 | ≈U9 |

## Critique

- **Spike gating is the unlock** — absolute density/size gates either miss floods or overhold steady rush (city-rush); comparing late density to early-episode mean separates the two.
- **Green extend is powerful but brittle** — U4’s drain-extend fixed endgame-flood (12086→24061+) but density≥4 on 2×2 balanced-grid cratered public; always size-gate (≥9 cells) and avoid mid-episode overhold.
- **Soft hold alone (U2) is a free +183 ALL** with zero public risk — keep it even if spike drain is rejected; late freeze was already in B and was not enough.
- **Total unfinished can rise while ALL rises** — several score-capped maps (e.g. grid-5x3-wide) accrued more leftover cars; tertiary unfinished optimization still open, but geom priority is met without touching public floors.

## Eval command

```bash
/opt/homebrew/bin/python3.12 \
  /Users/roz/Documents/github/cursor-semaphore/source/eval_all.py \
  /Users/roz/Documents/github/cursor-semaphore/variants/U/u9_spike_drain.py
```
