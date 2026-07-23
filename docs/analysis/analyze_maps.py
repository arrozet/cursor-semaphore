#!/usr/bin/env python3
"""Regenera estadísticas descriptivas de los tres replays públicos.

No importa código del motor ni presupone que el replay sea su API. Solo usa
la biblioteca estándar y trata los JSON como evidencia observacional.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPS = (
    ROOT / "maps/basic/balanced-grid.json",
    ROOT / "maps/basic/northbound-morning.json",
    ROOT / "maps/basic/city-rush.json",
)
GREEN_PHASES = {"NS_GREEN", "EW_GREEN"}


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def describe(values: Iterable[float]) -> dict[str, float | int | None]:
    materialized = list(values)
    if not materialized:
        return {"count": 0, "min": None, "median": None, "mode": None, "max": None}
    counts = Counter(materialized)
    highest = max(counts.values())
    modes = sorted(value for value, count in counts.items() if count == highest)
    return {
        "count": len(materialized),
        "min": min(materialized),
        "median": statistics.median(materialized),
        "mode": modes[0],
        "max": max(materialized),
    }


def get_tick(frame: dict[str, Any], fallback: int) -> int:
    for key in ("tick", "t", "time"):
        if key in frame:
            return int(frame[key])
    return fallback


def signal_runs(frames: list[dict[str, Any]], ids: list[str]) -> dict[str, Any]:
    ticks_by_phase: Counter[str] = Counter()
    runs_by_phase: defaultdict[str, list[int]] = defaultdict(list)
    per_intersection: dict[str, Any] = {}

    for intersection_id in ids:
        phases = [frame.get("signals", {}).get(intersection_id) for frame in frames]
        phases = [phase for phase in phases if phase is not None]
        local_counts = Counter(phases)
        local_runs: defaultdict[str, list[int]] = defaultdict(list)
        if phases:
            current = phases[0]
            length = 1
            for phase in phases[1:]:
                if phase == current:
                    length += 1
                else:
                    local_runs[current].append(length)
                    runs_by_phase[current].append(length)
                    current, length = phase, 1
            local_runs[current].append(length)
            runs_by_phase[current].append(length)
        ticks_by_phase.update(local_counts)
        green_total = sum(local_counts[phase] for phase in GREEN_PHASES)
        per_intersection[intersection_id] = {
            "phase_ticks": dict(sorted(local_counts.items())),
            "ns_green_share_of_green": (
                round(local_counts["NS_GREEN"] / green_total, 4) if green_total else None
            ),
            "runs": {
                phase: describe(lengths)
                for phase, lengths in sorted(local_runs.items())
            },
        }

    total_green = sum(ticks_by_phase[phase] for phase in GREEN_PHASES)
    return {
        "aggregate_phase_ticks": dict(sorted(ticks_by_phase.items())),
        "ns_green_share_of_green": (
            round(ticks_by_phase["NS_GREEN"] / total_green, 4)
            if total_green
            else None
        ),
        "run_lengths": {
            phase: describe(lengths) for phase, lengths in sorted(runs_by_phase.items())
        },
        "per_intersection": per_intersection,
    }


def vehicle_fields(vehicle: Any) -> tuple[Any, float, float, Any] | None:
    if isinstance(vehicle, list) and len(vehicle) >= 4:
        return vehicle[0], float(vehicle[1]), float(vehicle[2]), vehicle[3]
    if isinstance(vehicle, dict):
        vehicle_id = vehicle.get("id")
        x, y = vehicle.get("x"), vehicle.get("y")
        heading = vehicle.get("heading")
        if x is not None and y is not None:
            return vehicle_id, float(x), float(y), heading
    return None


def spatial_stats(
    frames: list[dict[str, Any]], intersections: list[dict[str, Any]]
) -> dict[str, Any]:
    proximity_sums = Counter({item["id"]: 0 for item in intersections})
    proximity_peaks = Counter({item["id"]: 0 for item in intersections})
    heading_counts: Counter[str] = Counter()
    cardinal_observations: Counter[str] = Counter()
    first_heading_by_vehicle: dict[Any, str] = {}
    x_bands = Counter()
    y_bands = Counter()
    observations = 0
    x_sum = 0.0
    y_sum = 0.0

    def cardinal(heading: Any) -> str:
        # En estos replays: 0°=este, 90°=sur, 180°=oeste, 270°=norte.
        labels = ("E", "S", "W", "N")
        return labels[int(((float(heading) + 45) % 360) // 90)]

    for frame in frames:
        local = Counter()
        for raw_vehicle in frame.get("vehicles", []):
            parsed = vehicle_fields(raw_vehicle)
            if parsed is None:
                continue
            vehicle_id, x, y, heading = parsed
            observations += 1
            x_sum += x
            y_sum += y
            heading_counts[str(heading)] += 1
            direction = cardinal(heading)
            cardinal_observations[direction] += 1
            first_heading_by_vehicle.setdefault(vehicle_id, direction)
            x_bands[min(3, max(0, int(x * 4)))] += 1
            y_bands[min(3, max(0, int(y * 4)))] += 1
            nearest = min(
                intersections,
                key=lambda item: (x - item["x"]) ** 2 + (y - item["y"]) ** 2,
            )
            distance = math.hypot(x - nearest["x"], y - nearest["y"])
            if distance <= 0.12:
                local[nearest["id"]] += 1
        for intersection_id in proximity_sums:
            proximity_sums[intersection_id] += local[intersection_id]
            proximity_peaks[intersection_id] = max(
                proximity_peaks[intersection_id], local[intersection_id]
            )

    frame_count = max(1, len(frames))
    proximity = {
        intersection_id: {
            "mean_vehicles_within_0.12": round(count / frame_count, 2),
            "peak_vehicles_within_0.12": proximity_peaks[intersection_id],
        }
        for intersection_id, count in proximity_sums.items()
    }
    return {
        "vehicle_observations": observations,
        "unique_vehicle_ids": len(first_heading_by_vehicle),
        "first_observed_direction": dict(
            Counter(first_heading_by_vehicle.values()).most_common()
        ),
        "cardinal_direction_observations": dict(cardinal_observations.most_common()),
        "heading_observations": dict(heading_counts.most_common()),
        "mean_normalized_position": {
            "x": round(x_sum / observations, 4) if observations else None,
            "y": round(y_sum / observations, 4) if observations else None,
        },
        "position_quartile_counts": {
            "x": dict(sorted(x_bands.items())),
            "y": dict(sorted(y_bands.items())),
        },
        "intersection_proximity": proximity,
    }


def summarize(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    scenario = data.get("scenario", {})
    map_data = data.get("map", {})
    intersections = map_data.get("intersections", [])
    roads = map_data.get("roads", [])
    frames = data.get("frames", [])
    metrics = data.get("metrics", data.get("summary", {}))
    ids = [item["id"] for item in intersections]

    live_curve = []
    for index, frame in enumerate(frames):
        live_curve.append(
            (
                get_tick(frame, index),
                len(frame.get("vehicles", [])),
                frame.get("waiting"),
                frame.get("completed"),
            )
        )
    peak_live = max(live_curve, key=lambda item: item[1], default=None)
    peak_waiting = max(
        (item for item in live_curve if isinstance(item[2], (int, float))),
        key=lambda item: item[2],
        default=None,
    )
    requested_ticks = {0, 150, 300, 450, 600, 750, 899}
    samples = [
        {"tick": tick, "live": live, "waiting": waiting, "completed": completed}
        for tick, live, waiting, completed in live_curve
        if tick in requested_ticks
    ]

    road_axes = Counter()
    road_endpoints = []
    for road in roads:
        dx = abs(float(road["x2"]) - float(road["x1"]))
        dy = abs(float(road["y2"]) - float(road["y1"]))
        axis = "EW" if dx >= dy else "NS"
        road_axes[axis] += 1
        road_endpoints.append(
            {
                "from": road.get("from"),
                "to": road.get("to"),
                "axis": axis,
            }
        )

    spawned = metrics.get("spawned")
    completed = metrics.get("completed")
    unfinished = metrics.get("unfinished")
    wait_ticks = metrics.get("waitTicks")
    cost = metrics.get("cost")
    return {
        "file": str(path.relative_to(ROOT)),
        "top_level_keys": sorted(data),
        "frame_keys": sorted(frames[0]) if frames else [],
        "scenario": scenario,
        "topology": {
            "rows": map_data.get("rows"),
            "cols": map_data.get("cols"),
            "intersection_count": len(intersections),
            "intersections": intersections,
            "road_count": len(roads),
            "road_axes": dict(sorted(road_axes.items())),
            "roads": road_endpoints,
        },
        "metrics": metrics,
        "cost_formula_check": {
            "observed_cost": cost,
            "waitTicks_plus_300_unfinished": (
                wait_ticks + 300 * unfinished
                if isinstance(wait_ticks, (int, float))
                and isinstance(unfinished, (int, float))
                else None
            ),
            "matches": (
                cost == wait_ticks + 300 * unfinished
                if isinstance(cost, (int, float))
                and isinstance(wait_ticks, (int, float))
                and isinstance(unfinished, (int, float))
                else None
            ),
            "spawn_balance_matches": (
                spawned == completed + unfinished
                if isinstance(spawned, (int, float))
                and isinstance(completed, (int, float))
                and isinstance(unfinished, (int, float))
                else None
            ),
        },
        "curves": {
            "samples": samples,
            "peak_live": (
                {"tick": peak_live[0], "value": peak_live[1]} if peak_live else None
            ),
            "peak_waiting": (
                {"tick": peak_waiting[0], "value": peak_waiting[2]}
                if peak_waiting
                else None
            ),
            "final_frame": (
                {
                    "tick": live_curve[-1][0],
                    "live": live_curve[-1][1],
                    "waiting": live_curve[-1][2],
                    "completed": live_curve[-1][3],
                }
                if live_curve
                else None
            ),
        },
        "signals": signal_runs(frames, ids),
        "spatial": spatial_stats(frames, intersections),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("maps", nargs="*", type=Path, default=DEFAULT_MAPS)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    output = [summarize(path.resolve()) for path in args.maps]
    print(json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2))


if __name__ == "__main__":
    main()
