from __future__ import annotations

import argparse
import importlib.util
import json
import math
import threading
import time
import traceback
import webbrowser
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from traffic_arena.engine import fixed_time_controller, run_scenario
from traffic_arena.map_loader import DEFAULT_MAPS_ROOT, load_runnable_scenarios
from traffic_arena.score_profiles import score_profile
from traffic_arena.scoring import scenario_score

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / ".arena"
CONTROLLER = ROOT / "controller.py"


def load_controller():
    spec = importlib.util.spec_from_file_location("team_controller", CONTROLLER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load controller.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "control", None)):
        raise TypeError("controller.py must define control(state)")
    return module.control


def evaluate(scenario, controller) -> tuple[int, dict]:
    baseline = run_scenario(scenario, fixed_time_controller, record_replay=False)
    result = run_scenario(scenario, controller, record_replay=True)
    profile = score_profile(
        scenario.id,
        baseline_cost=baseline.metrics.cost,
        spawned=baseline.metrics.spawned,
    )
    # Prefer live baseline for scoring so local maps stay consistent with the run.
    score = scenario_score(result.metrics.cost, baseline.metrics.cost, profile.target_cost)
    return score, {
        "scenario": scenario,
        "baseline": baseline,
        "result": result,
        "score": score,
        "profile": profile,
    }


def simulate(scenario) -> None:
    try:
        controller = load_controller()
        score, payload_data = evaluate(scenario, controller)
        result = payload_data["result"]
        payload = result.replay
        assert payload is not None
        payload["score"] = score
        OUTPUT.mkdir(exist_ok=True)
        temporary = OUTPUT / "replay.tmp"
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        temporary.replace(OUTPUT / "replay.json")
        write_status(
            {
                "ok": True,
                "revision": time.time_ns(),
                "score": score,
                "scenario": scenario.name,
                "scenario_id": scenario.id,
                "metrics": asdict(result.metrics),
            }
        )
        print(f"[{time.strftime('%H:%M:%S')}] {scenario.id}: {score:,} points")
    except Exception as exc:
        OUTPUT.mkdir(exist_ok=True)
        error = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()[-4000:]}
        write_status({**error, "revision": time.time_ns()})
        print(f"[{time.strftime('%H:%M:%S')}] Error: {exc}")


def write_status(payload: dict) -> None:
    OUTPUT.mkdir(exist_ok=True)
    temporary = OUTPUT / "status.tmp"
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(OUTPUT / "status.json")


def list_scenarios(scenarios) -> None:
    print(f"Maps root: {DEFAULT_MAPS_ROOT}")
    print(f"{'id':<32} {'grid':>7} {'name'}")
    print("-" * 72)
    for scenario in scenarios:
        grid = f"{scenario.rows}x{scenario.cols}"
        print(f"{scenario.id:<32} {grid:>7} {scenario.name}")
    print(f"\n{len(scenarios)} scenarios (PUBLIC + maps/**/*.scenario.json)")


def run_all(scenarios) -> None:
    controller = load_controller()
    scores: list[int] = []
    print(f"{'id':<32} {'cost':>8} {'base':>8} {'score':>7}")
    print("-" * 60)
    for scenario in scenarios:
        score, data = evaluate(scenario, controller)
        cost = data["result"].metrics.cost
        base = data["baseline"].metrics.cost
        scores.append(score)
        print(f"{scenario.id:<32} {cost:>8} {base:>8} {score:>7,}")
    if scores:
        geo = round(math.exp(sum(math.log(score) for score in scores) / len(scores)))
        print("-" * 60)
        print(f"{'geometric_mean':<32} {'':>8} {'':>8} {geo:>7,}")


class NoCacheHandler(SimpleHTTPRequestHandler):
    def allowed_request(self) -> bool:
        host = (self.headers.get("Host") or "").split(":", 1)[0].lower()
        if host not in {"127.0.0.1", "localhost"}:
            self.send_error(403)
            return False

        requested_path = unquote(urlsplit(self.path).path)
        requested = (ROOT / requested_path.lstrip("/")).resolve()
        viewer_root = (ROOT / "viewer").resolve()
        public_runtime_files = {
            (OUTPUT / "status.json").resolve(),
            (OUTPUT / "replay.json").resolve(),
        }
        if (
            requested != viewer_root
            and viewer_root not in requested.parents
            and requested not in public_runtime_files
        ):
            self.send_error(404)
            return False
        return True

    def do_GET(self) -> None:
        if self.allowed_request():
            super().do_GET()

    def do_HEAD(self) -> None:
        if self.allowed_request():
            super().do_HEAD()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return


def create_server(port: int) -> ThreadingHTTPServer:
    handler = lambda *args, **kwargs: NoCacheHandler(*args, directory=str(ROOT), **kwargs)
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def main() -> None:
    scenarios = load_runnable_scenarios()
    if not scenarios:
        raise SystemExit("No scenarios found (PUBLIC_SCENARIOS empty and no maps/**/*.scenario.json)")

    parser = argparse.ArgumentParser(
        description="Run Traffic Lights Arena locally. Discovers maps/**/*.scenario.json from any folder."
    )
    parser.add_argument(
        "--scenario",
        choices=[scenario.id for scenario in scenarios],
        default=scenarios[0].id,
        help="Scenario id (public or any maps/**/*.scenario.json)",
    )
    parser.add_argument("--list", action="store_true", help="List all runnable scenarios and exit")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every discovered scenario once (geometric mean) and exit",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_scenarios(scenarios)
        return

    if args.all:
        run_all(scenarios)
        return

    scenario = next(item for item in scenarios if item.id == args.scenario)

    try:
        httpd = create_server(args.port)
    except OSError as exc:
        raise SystemExit(f"Could not start viewer on port {args.port}: {exc}") from exc
    server = threading.Thread(target=httpd.serve_forever, daemon=True)
    server.start()
    simulate(scenario)
    url = f"http://127.0.0.1:{args.port}/viewer/"
    print(f"Viewer: {url}")
    print("Watching controller.py. Save the file to run again. Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)

    last_modified = CONTROLLER.stat().st_mtime_ns
    try:
        while True:
            time.sleep(0.35)
            modified = CONTROLLER.stat().st_mtime_ns
            if modified != last_modified:
                last_modified = modified
                time.sleep(0.15)
                simulate(scenario)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
