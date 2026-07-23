# Strategy B Optimization Conclusions

## Recommended controller

Use `source/controller.py` in this worktree. It improves the All-44 geometric
mean from 20,469 to 21,657 while preserving the seeded 22,983 public result.

The useful changes are:

1. Infer travel time from the shortest valid isolated one-vehicle link run.
   Fast travel adapts after one sample; slower-than-default travel waits for
   three samples to reject hidden back-to-back replacements.
2. Use a 0.90 queue scale after slow travel is observed. This raises the worst
   map (`combo-4x4-sparse-slow`) from 7,037 to 8,414.
3. Give maps with at most two junctions a density threshold of 10 and
   hysteresis of 2. This caps both micro scenarios without touching public
   balanced-grid.
4. At high density, soften the queue multiplier to 1.06. The narrow value is
   phase-length sensitive, but it was stable from 1.058 through 1.062.
5. Add a small EMA demand-share adjustment (maximum roughly one tick) and a
   capacity multiplier. These repair lane skew, corner bias, and fat links.
6. Allow green to max out at 60 ticks. Scores are unchanged versus 50, but
   total unfinished falls.

## Remaining risks

- The minimum is still the sparse 4x4 slow-travel map; synchronized control
  cannot fully recover its long-platoon transition cost.
- `SOFT_BONUS=1.06` is intentionally conservative but discretized by integer
  green lengths. Values at 1.07 and above caused large public regressions.
- EMA materially improves column skew but slightly regresses
  `windows-mid-spike` and `grid-2x2-balanced`.
- Capacity adaptation is learned only after an occupied link exposes its
  capacity. The first phase always uses the neutral capacity of eight.
- Two score-capped high-volume maps finish more vehicles poorly even though
  their official score remains 25,000.

## Six-point peer debate brief

- **Measured travel beats occupancy density as a clock:** shortest isolated
  link runs robustly distinguish travel 2, 5, and 10; mode-based estimation can
  mistake replacement chains for multiples.
- **Keep synchronization, adapt only its hold:** all tested pressure additions
  (downstream, in-flight, oldest-wait) lost All-44 geometric mean, so spillback
  logic needs strong gating before merging.
- **EMA should be tiny and integer-valued:** a two-tick share range fixes lane
  skew; 2.5 destroys public performance, showing a sharp phase-boundary cliff.
- **Endgame freezes are map-window fragile:** a 12-tick freeze rescues the flood
  but damages flip-axis, balanced, and micro cases; density/spike evidence is
  safer than remaining-time alone.
- **Topology gates generalize better than scenario gates:** the two-junction
  density/hysteresis rule captures both micro orientations while preserving all
  public scores.
- **Compare raw cost under capped scores:** max-green and capacity variants can
  tie at 25,000 yet move unfinished by dozens; score-only selection hides real
  private-map risk.
