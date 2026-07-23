# Agent Guide

Working strategy for solving the challenge. Read [`challenge.md`](challenge.md) first for rules, API, and scoring.

## Principles

1. **Controller only** — all logic changes go in the single controller file; do not touch the simulation engine.
2. **Generalize** — 80% of the score comes from private maps; do not overfit to the public ones.
3. **Test freely** — run `python run.py` as often as needed; local validation is unlimited.
4. **Submissions are scarce** — max 20 attempts; a broken controller still consumes an attempt. Never run `python submit.py` without **explicit user confirmation** first (ask and wait). Always validate with `python run.py` before proposing a submit.
5. **Aim for gold** — between baseline and gold, progress is squared; a near-gold improvement is worth far more than a small early gain.

## Version control

- Commit **incrementally** with [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, …).
- After every meaningful change: **commit + push** immediately. Do not stockpile unpushed work.
- One commit = one clear idea (a strategy tweak, a fix, a docs update).

## Work loop

1. Understand the current controller and local results.
2. Propose a small, measurable change (heuristic, weights, thresholds, within-map memory).
3. Implement only that change.
4. Validate with `python run.py`.
5. Commit + push with Conventional Commits.
6. If results improve stably, propose a submission to the user; only run `python submit.py` after they explicitly confirm.
7. Repeat: iterate fast, measure, keep what generalizes.

## What to optimize

- Move more cars and reduce waiting at junctions.
- Adapt to different densities and topologies (unseen maps).
- Use memory **within** a map (queues, phases, trends); assume a clean process between maps.
- Prefer robust rules over magic constants tuned to a single map.

## Replay viewer (`viz/`)

Plain HTML/CSS/JS viewer for the public demo replays in `maps/basic/`. Do **not** open `viz/index.html` via `file://` — `fetch` of the JSON maps will fail.

**Cross-platform** (1× macOS + Windows): only needs Python 3. From the repo root:

```bash
python3 viz/serve.py
```

```bat
python viz\serve.py
```

Opens [http://localhost:8765/viz/](http://localhost:8765/viz/) with hot reload on `viz/` (HTML/CSS/JS). Port: `python3 viz/serve.py --port 9000`.

Optional wrappers: `./viz/serve.sh` · `viz\serve.cmd`. Analysis: `docs/analysis/`.
