# Strategy B Optimization Results

Evaluation command:

```bash
/opt/homebrew/bin/python3.12 source/eval_all.py source/controller.py
```

Suite: 3 public scenarios plus all 41 `maps/alesuito/*.scenario.json` files.
All runs were deterministic and no submission was made.

## Final result

| Controller | Public geom | Alesuito geom | All-44 geom | Min score | Unfinished |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seeded Strategy B | 22,983 | 20,296 | 20,469 | 7,037 | 2,680 |
| **Final optimized B** | **22,983** | **21,563** | **21,657** | **8,414** | **2,587** |
| Change | 0 | **+1,267** | **+1,188** | **+1,377** | **-93** |

The final controller keeps every public score unchanged: balanced-grid 22,695,
northbound-morning 25,000, and city-rush 21,397.

## Experiment log

More than 150 parameter and structural variants were screened; promising
variants were rerun over all 44 scenarios.

| Experiment | Public | Alesuito | All | Min | Unfinished | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Seeded Strategy B | 22,983 | 20,296 | 20,469 | 7,037 | 2,680 | Reference |
| Measured travel, asymmetric sample guard | 22,983 | 20,507 | 20,667 | 8,211 | 2,668 | Keep |
| + topology density threshold (`n <= 2`) | 22,983 | 20,789 | 20,932 | 8,211 | 2,665 | Keep |
| + EMA share bonus 2 | 22,983 | 21,005 | 21,134 | 8,208 | 2,669 | Keep |
| Soft high-density bonus 1.06 | 22,983 | 21,198 | 21,315 | 8,211 | 2,614 | Keep |
| EMA + capacity + compact hysteresis | 22,983 | 21,541 | 21,636 | 8,208 | 2,603 | Keep |
| + slow-travel queue scale 0.90 | 22,983 | 21,563 | 21,657 | 8,414 | 2,587 | **Final** |
| Density threshold 10 globally | 21,498 | 20,695 | 20,748 | 8,211 | 2,652 | Reject: public loss |
| Continuous density ramp 0.5 | 22,983 | 20,798 | 20,940 | 8,211 | 2,666 | Reject: burst regression |
| EMA bonus 2.5 with softening | 20,799 | 21,442 | 21,398 | 8,208 | 2,659 | Reject: public loss |
| Large-map freeze 12 | 22,983 | 20,806 | 20,947 | 8,211 | 2,663 | Reject: flip-axis loss |
| Travel pressure 0.10 | 22,983 | 20,314 | 20,486 | 8,175 | 2,680 | Reject |
| Oldest-wait pressure 0.03 | 22,977 | 19,981 | 20,173 | 8,334 | 2,695 | Reject |
| Downstream pressure 0.25 | 22,977 | 19,990 | 20,180 | 8,334 | 2,693 | Reject |

Other measured findings:

- `MAX_GREEN=60` preserved every score and reduced final unfinished from 2,600
  at 50 to 2,587; 70 tied, while 80 regressed unfinished.
- Capacity weight 0.25 lifted `fat-links-3x3` to 25,000 without changing public
  scores. Larger weights sharply regressed that map.
- Compact hysteresis 2, gated to at most two junctions, capped both micro maps.
- A global 12-tick endgame freeze greatly helped `windows-endgame-flood`, but
  destroyed balanced and micro maps. Size-gating still lost heavily on
  `windows-flip-axis`; the final controller does not use it.
- Strategy C and occupancy-floor Strategy D benchmarks reached All-44 geoms
  20,037 and 20,179 respectively, both below seeded Strategy B.

## Largest changes versus seeded B

### Wins

| Scenario | Score change | Cost change | Unfinished change |
| --- | ---: | ---: | ---: |
| windows-endgame-flood | 12,086 → 24,337 (**+12,251**) | 76,346 → 69,010 | 142 → 117 |
| micro-2x1 | 16,415 → 25,000 (**+8,585**) | 13,398 → 12,056 | 15 → 11 |
| windows-lane-skew-cols | 15,580 → 21,411 (**+5,831**) | 14,412 → 13,788 | 20 → 18 |

### Regressions

| Scenario | Score change | Cost change | Unfinished change |
| --- | ---: | ---: | ---: |
| windows-mid-spike | 23,563 → 22,835 (**-728**) | 26,533 → 26,653 | 11 → 11 |
| combo-1x3-burst-tiny-links | 25,000 → 25,000 | 169,913 → 172,267 | 208 → 229 |
| combo-5x5-mild | 25,000 → 25,000 | 136,406 → 138,546 | 162 → 166 |

The latter two remain score-capped but are real raw-cost and unfinished
regressions.
