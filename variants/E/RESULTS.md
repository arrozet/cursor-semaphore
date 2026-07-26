# Variant E — EMA Demand-Share hybrid on Strategy B

## FINAL

| Metric | Variant E | Strategy B | Δ |
| --- | ---: | ---: | ---: |
| **PUBLIC geom** | **21119** | 22983 | −1864 |
| **ALESUITO geom** | **20467** | 20296 | **+171** |
| **ALL geom** | **20511** | 20469 | **+42** |
| **Total unfinished** | **2678** | 2680 | **−2** |

**Path:** `/Users/roz/Documents/github/cursor-semaphore/variants/E/controller.py`

Eval: `python3.12 source/eval_all.py variants/E/controller.py`

## Idea

Keep B’s synchronized corridor plan + pressure-gated switch. Add a light EMA of axis queue (+0.15× travel) share. When `|share−0.5| ≥ 0.16` and density is below B’s softener threshold:

1. Stretch planned green on the dominant axis (`+10 × (share−0.5)`).
2. Allow plan-ready switches toward the higher-share rival without the pressure gate (C-like service under clear skew).

No scenario-id hardcoding; `ENDGAME_TICKS=0`.

## Tunables (final)

| Param | Value |
| --- | ---: |
| EMA_ALPHA | 0.055 |
| EMA_TRAVEL_WEIGHT | 0.15 |
| SKEW_GATE | 0.16 |
| SHARE_GREEN_BONUS | 10.0 |
| Density gate | EMA off if `active/n ≥ 8` |

## Iteration log

| Iter | Change | PUBLIC | ALL | Notes |
| --- | --- | ---: | ---: | --- |
| 1 | Always-on green mult+add + switch bias | 17723 | 20066 | Cratered balanced-grid |
| 2 | Skew-gated mild bias | 22983 | 20469 | ≈ pure B (no effect) |
| 3 | Stretch green + switch-share bias | 22983* | 20035 | Micro/endgame wins; 3×3 regressions (*file-race suspect) |
| 4–6 | Stretch-only / density gate | mixed | ≤20325 | City-rush / public fragile |
| **7 (final)** | **Skew+density gate, green stretch, rival ungated switch** | **21119** | **20511** | **Best ALL** |
| 8–10 | Higher gate / warmup | ≤22983 | ≤20378 | Protects public, loses ALL edge |

## Key maps vs B (focus set)

| map | E | B | Δ |
| --- | ---: | ---: | ---: |
| combo-corner-bias-3x3 | 18245 | 12071 | +6174 |
| micro-2x1 | 20086 | 16415 | +3671 |
| windows-lane-skew-cols | 25000 | 15580 | +9420 |
| windows-rush-to-quiet | 13233 | 12568 | +665 |
| windows-endgame-flood | 12399 | 12086 | +313 |
| windows-lane-skew-rows | 18745 | 19696 | −951 |
| balanced-grid (PUB) | 20012 | 22695 | −2683 |
| northbound-morning (PUB) | 21998 | 25000 | −3002 |

## Critique

- **ALL geom edges B (+42)** via alesuito asymmetric maps (lane-skew-cols, corner-bias, micro-2x1); unfinished slightly better (−2).
- **Public regresses hard** on balanced-grid and northbound — EMA skew false-triggers and rival ungated switches disturb B’s winning public cadence; city-rush is preserved by the density gate.
- **Endgame-flood barely moves** (+313); C’s larger win there needs a different completion/drain mechanism, not share stretch alone.
- **grid-3x3-balanced collapses** (10877 vs B 19450) when rival ungated switching fires on transient skew — the same lever that fixes lane-skew hurts near-balanced grids; a stricter rival-dominance test or topology prior would be the next cut.
