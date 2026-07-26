# A/B/C/D vs public + alesuito

Scored with `eval_all.py` rules: official profiles for public; fixed_time baseline + target=0.85*base for stress maps.

| Strat | Public geom | Alesuito geom | All geom | Total unfinished |
|---|---:|---:|---:|---:|
| A | 21434 | 19443 | 19572 | 2843 |
| B | 22983 | 20296 | 20469 | 2680 |
| C | 21514 | 19933 | 20037 | 2743 |
| D | 21746 | 19517 | 19662 | 2809 |

| map | A | B | C | D | best |
|---|---:|---:|---:|---:|---|
| balanced-grid PUB| 18710 | 22695 | 18177 | 19540 | **B** |
| northbound-morning PUB| 24541 | 25000 | 25000 | 24541 | **B** |
| city-rush PUB| 21445 | 21397 | 21914 | 21445 | **C** |
| combo-1x3-burst-tiny-links | 25000 | 25000 | 25000 | 25000 | **A** |
| combo-2x2-flip-tiny-cap | 25000 | 25000 | 25000 | 25000 | **A** |
| combo-4x4-sparse-slow | 6985 | 7037 | 7169 | 6985 | **C** |
| combo-5x5-mild | 25000 | 25000 | 25000 | 25000 | **A** |
| combo-corner-bias-3x3 | 12183 | 12071 | 18034 | 12183 | **C** |
| corridor-1x4 | 25000 | 25000 | 25000 | 25000 | **A** |
| corridor-5x1 | 25000 | 25000 | 25000 | 25000 | **A** |
| dead-quiet-2x2 | 24689 | 25000 | 25000 | 24844 | **B** |
| ew-only-3x3 | 25000 | 25000 | 25000 | 25000 | **A** |
| fast-travel-2x3 | 9745 | 8842 | 8797 | 9745 | **A** |
| fat-links-3x3 | 25000 | 22289 | 22133 | 12525 | **A** |
| grid-2x2-balanced | 9971 | 10323 | 9166 | 9443 | **B** |
| grid-2x2-ew-storm | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-2x2-ns-storm | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-2x2-saturated | 9642 | 9703 | 10327 | 10102 | **C** |
| grid-2x2-sparse | 17071 | 25000 | 25000 | 25000 | **B** |
| grid-2x3-ew-rush | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-3x2-ns-rush | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-3x3-balanced | 20884 | 19450 | 14611 | 20884 | **A** |
| grid-3x3-burst45 | 19232 | 22314 | 16704 | 19232 | **B** |
| grid-3x3-burst90 | 19498 | 25000 | 22978 | 19498 | **B** |
| grid-3x5-tall | 14127 | 23885 | 20240 | 14127 | **B** |
| grid-4x2-strip | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-4x4-heavy | 25000 | 25000 | 25000 | 25000 | **A** |
| grid-5x3-wide | 25000 | 25000 | 25000 | 25000 | **A** |
| micro-1x2 | 14026 | 19293 | 12278 | 9863 | **B** |
| micro-2x1 | 25000 | 16415 | 24973 | 25000 | **A** |
| ns-only-3x3 | 25000 | 25000 | 25000 | 25000 | **A** |
| single-cell | 18546 | 25000 | 24256 | 22600 | **B** |
| slow-travel-3x3 | 25000 | 25000 | 25000 | 25000 | **A** |
| tiny-links-2x2 | 25000 | 25000 | 25000 | 25000 | **A** |
| windows-asymmetric-cardinals | 15236 | 18764 | 20447 | 15236 | **C** |
| windows-endgame-flood | 13037 | 12086 | 15549 | 13037 | **C** |
| windows-flip-axis | 25000 | 24928 | 23055 | 25000 | **A** |
| windows-lane-skew-cols | 25000 | 15580 | 15195 | 25000 | **A** |
| windows-lane-skew-rows | 19917 | 19696 | 16758 | 19917 | **A** |
| windows-mid-spike | 23385 | 23563 | 25000 | 23385 | **C** |
| windows-north-only-pulse | 25000 | 25000 | 25000 | 25000 | **A** |
| windows-oscillate | 13406 | 25000 | 21805 | 25000 | **B** |
| windows-quiet-to-rush | 25000 | 25000 | 25000 | 25000 | **A** |
| windows-rush-to-quiet | 10123 | 12568 | 10299 | 10123 | **B** |

## Map wins (including ties counted for each)
- A: 25
- B: 30
- C: 28
- D: 26

## Worst 8 per strategy
### A
- combo-4x4-sparse-slow: score=6985 cost=48419 unf=58
- grid-2x2-saturated: score=9642 cost=76663 unf=80
- fast-travel-2x3: score=9745 cost=24240 unf=21
- grid-2x2-balanced: score=9971 cost=20226 unf=18
- windows-rush-to-quiet: score=10123 cost=18486 unf=10
- combo-corner-bias-3x3: score=12183 cost=17745 unf=21
- windows-endgame-flood: score=13037 cost=75411 unf=139
- windows-oscillate: score=13406 cost=25009 unf=31
### B
- combo-4x4-sparse-slow: score=7037 cost=48061 unf=58
- fast-travel-2x3: score=8842 cost=26716 unf=28
- grid-2x2-saturated: score=9703 cost=76179 unf=80
- grid-2x2-balanced: score=10323 cost=19723 unf=17
- combo-corner-bias-3x3: score=12071 cost=17773 unf=21
- windows-endgame-flood: score=12086 cost=76346 unf=142
- windows-rush-to-quiet: score=12568 cost=17578 unf=7
- windows-lane-skew-cols: score=15580 cost=14412 unf=20
### C
- combo-4x4-sparse-slow: score=7169 cost=47180 unf=56
- fast-travel-2x3: score=8797 cost=26852 unf=28
- grid-2x2-balanced: score=9166 cost=22001 unf=24
- windows-rush-to-quiet: score=10299 cost=18344 unf=9
- grid-2x2-saturated: score=10327 cost=72278 unf=69
- micro-1x2: score=12278 cost=12175 unf=10
- grid-3x3-balanced: score=14611 cost=48594 unf=57
- windows-lane-skew-cols: score=15195 cost=14463 unf=19
### D
- combo-4x4-sparse-slow: score=6985 cost=48419 unf=58
- grid-2x2-balanced: score=9443 cost=21357 unf=22
- fast-travel-2x3: score=9745 cost=24240 unf=21
- micro-1x2: score=9863 cost=13110 unf=13
- grid-2x2-saturated: score=10102 cost=73000 unf=68
- windows-rush-to-quiet: score=10123 cost=18486 unf=10
- combo-corner-bias-3x3: score=12183 cost=17745 unf=21
- fat-links-3x3: score=12525 cost=74658 unf=89
