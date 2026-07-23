"""Single-parameter sweep driver: patches a constant in controller.py,
runs the jittered evaluator, and prints a compact comparison table.

Usage: python3.12 exp/sweep.py PARAM v1 v2 v3 ... [--seeds 3]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent
ROOT = EXP.parent
CTRL = ROOT / "source" / "controller.py"
PY = "/opt/homebrew/bin/python3.12"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("param")
    ap.add_argument("values", nargs="+")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()

    base_src = CTRL.read_text()
    pattern = re.compile(rf"^{args.param} = .*$", re.M)
    if not pattern.search(base_src):
        sys.exit(f"param {args.param} not found in controller")

    rows = []
    for v in args.values:
        src = pattern.sub(f"{args.param} = {v}", base_src)
        tmp = EXP / f"_sweep_{args.param}_{v.replace('.', 'p').replace('-', 'm')}.py"
        tmp.write_text(src)
        name = f"sw_{args.param}_{v.replace('.', 'p').replace('-', 'm')}"
        subprocess.run(
            [PY, str(EXP / "fasteval.py"), str(tmp), "--name", name,
             "--jobs", "10", "--seeds", str(args.seeds)],
            check=True, capture_output=True,
        )
        s = json.loads((EXP / "results" / f"{name}.json").read_text())["summary"]
        rows.append((v, s))
        print(
            f"{args.param}={v:>8s}  all={s['all_geom']:6d}  pub0={s['public_geom_seed0']:6d}  "
            f"ales={s['alesuito_geom']:6d}  min={s['min_score']:6d}  unf={s['total_unfinished']:5d}",
            flush=True,
        )
        tmp.unlink()


if __name__ == "__main__":
    main()
