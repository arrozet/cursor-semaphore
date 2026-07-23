"""Discover runnable scenarios from maps/**/*.scenario.json sidecars."""

from __future__ import annotations

import json
from pathlib import Path

from .scenarios import PUBLIC_SCENARIOS, DemandWindow, Scenario

# source/ -> repo root -> maps/
DEFAULT_MAPS_ROOT = Path(__file__).resolve().parents[2] / "maps"


def scenario_to_dict(scenario: Scenario) -> dict:
    return {
        "id": scenario.id,
        "name": scenario.name,
        "rows": scenario.rows,
        "cols": scenario.cols,
        "seed": scenario.seed,
        "ticks": scenario.ticks,
        "travel_ticks": scenario.travel_ticks,
        "link_capacity": scenario.link_capacity,
        "horizontal_rate": scenario.horizontal_rate,
        "vertical_rate": scenario.vertical_rate,
        "rush_axis": scenario.rush_axis,
        "burst_period": scenario.burst_period,
        "demand_windows": [
            {
                "start_tick": window.start_tick,
                "end_tick": window.end_tick,
                "north_rate": window.north_rate,
                "south_rate": window.south_rate,
                "east_rate": window.east_rate,
                "west_rate": window.west_rate,
                "row_weights": list(window.row_weights),
                "col_weights": list(window.col_weights),
            }
            for window in scenario.demand_windows
        ],
    }


def scenario_from_dict(data: dict) -> Scenario:
    windows = tuple(
        DemandWindow(
            start_tick=int(window["start_tick"]),
            end_tick=int(window["end_tick"]),
            north_rate=float(window["north_rate"]),
            south_rate=float(window["south_rate"]),
            east_rate=float(window["east_rate"]),
            west_rate=float(window["west_rate"]),
            row_weights=tuple(window.get("row_weights") or ()),
            col_weights=tuple(window.get("col_weights") or ()),
        )
        for window in data.get("demand_windows") or ()
    )
    return Scenario(
        id=str(data["id"]),
        name=str(data["name"]),
        rows=int(data["rows"]),
        cols=int(data["cols"]),
        seed=int(data["seed"]),
        ticks=int(data.get("ticks", 900)),
        travel_ticks=int(data.get("travel_ticks", 5)),
        link_capacity=int(data.get("link_capacity", 8)),
        horizontal_rate=float(data.get("horizontal_rate", 0.13)),
        vertical_rate=float(data.get("vertical_rate", 0.13)),
        rush_axis=data.get("rush_axis"),
        burst_period=int(data.get("burst_period", 0)),
        demand_windows=windows,
    )


def load_scenario_file(path: Path) -> Scenario:
    return scenario_from_dict(json.loads(path.read_text(encoding="utf-8")))


def discover_scenario_files(maps_root: Path | None = None) -> list[Path]:
    root = maps_root if maps_root is not None else DEFAULT_MAPS_ROOT
    if not root.is_dir():
        return []
    return sorted(root.glob("**/*.scenario.json"))


def load_runnable_scenarios(maps_root: Path | None = None) -> tuple[Scenario, ...]:
    """Public scenarios first, then every maps/**/*.scenario.json (any folder).

    Later files with the same id override earlier ones so a teammate folder can
    shadow a stress-suite entry; official public ids always keep their coded
    definition unless a matching sidecar exists (then sidecar wins for local runs).
    """
    by_id: dict[str, Scenario] = {scenario.id: scenario for scenario in PUBLIC_SCENARIOS}

    for path in discover_scenario_files(maps_root):
        scenario = load_scenario_file(path)
        by_id[scenario.id] = scenario

    ordered: list[Scenario] = []
    seen: set[str] = set()
    for scenario in PUBLIC_SCENARIOS:
        current = by_id[scenario.id]
        ordered.append(current)
        seen.add(current.id)

    extras = sorted(
        (scenario for scenario_id, scenario in by_id.items() if scenario_id not in seen),
        key=lambda item: item.id,
    )
    ordered.extend(extras)
    return tuple(ordered)


def write_scenario_file(path: Path, scenario: Scenario) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scenario_to_dict(scenario), indent=2) + "\n", encoding="utf-8")
