"""Additional stress scenarios for local controller evaluation.

These scenarios are deliberately kept separate from ``PUBLIC_SCENARIOS``.  The
public maps have frozen score profiles, while this suite is intended to expose
controllers that perform poorly on one family of maps and therefore drag down
the geometric mean.
"""

from __future__ import annotations

from .scenarios import DemandWindow, Scenario


MPOW_SCENARIOS = (
    # Long corridor: a single bad phase decision can block the whole route.
    Scenario(
        "mpow-corridor",
        "MPOW corridor bottleneck",
        rows=1,
        cols=8,
        seed=60_101,
        ticks=1_200,
        travel_ticks=6,
        link_capacity=5,
        horizontal_rate=0.24,
        vertical_rate=0.025,
        rush_axis="EW",
    ),
    # Large, dense grid: stresses phase coordination and sustained queues.
    Scenario(
        "mpow-dense-grid",
        "MPOW dense grid",
        rows=5,
        cols=5,
        seed=60_102,
        ticks=1_200,
        travel_ticks=4,
        link_capacity=7,
        horizontal_rate=0.23,
        vertical_rate=0.23,
        burst_period=120,
    ),
    # Demand reverses twice, making a controller that only learns the initial
    # rush direction look good on average but fail badly on part of the map.
    Scenario(
        "mpow-reversing-rush",
        "MPOW reversing rush",
        rows=4,
        cols=3,
        seed=60_103,
        ticks=1_200,
        travel_ticks=5,
        link_capacity=6,
        demand_windows=(
            DemandWindow(0, 300, 0.30, 0.08, 0.07, 0.07),
            DemandWindow(300, 600, 0.08, 0.30, 0.07, 0.07),
            DemandWindow(600, 900, 0.07, 0.07, 0.30, 0.08),
            DemandWindow(900, 1_200, 0.07, 0.07, 0.08, 0.30),
        ),
    ),
    # Uneven lane weights create a hot row and hot column without changing
    # the overall demand, which catches strategies based only on global load.
    Scenario(
        "mpow-hot-lanes",
        "MPOW hot lanes",
        rows=4,
        cols=4,
        seed=60_104,
        ticks=1_000,
        travel_ticks=5,
        link_capacity=6,
        demand_windows=(
            DemandWindow(
                0,
                1_000,
                0.15,
                0.15,
                0.15,
                0.15,
                row_weights=(3.0, 0.6, 0.6, 0.6),
                col_weights=(0.6, 0.6, 0.6, 3.0),
            ),
        ),
    ),
    # Tiny grid with severe capacity: useful for detecting starvation and
    # excessive switching, which can otherwise be hidden by larger maps.
    Scenario(
        "mpow-tight-junction",
        "MPOW tight junction",
        rows=2,
        cols=2,
        seed=60_105,
        ticks=1_000,
        travel_ticks=7,
        link_capacity=2,
        horizontal_rate=0.19,
        vertical_rate=0.19,
        burst_period=75,
    ),
    # A wider map with alternating row/column hotspots tests whether a policy
    # adapts to local queues instead of applying one global phase.
    Scenario(
        "mpow-alternating-hotspots",
        "MPOW alternating hotspots",
        rows=3,
        cols=6,
        seed=60_106,
        ticks=1_200,
        travel_ticks=6,
        link_capacity=6,
        demand_windows=(
            DemandWindow(
                0,
                400,
                0.18,
                0.10,
                0.28,
                0.06,
                row_weights=(2.2, 0.7, 0.7),
                col_weights=(0.7, 0.7, 2.0, 0.7, 0.7, 2.0),
            ),
            DemandWindow(
                400,
                800,
                0.10,
                0.18,
                0.06,
                0.28,
                row_weights=(0.7, 0.7, 2.2),
                col_weights=(2.0, 0.7, 0.7, 2.0, 0.7, 0.7),
            ),
            DemandWindow(
                800,
                1_200,
                0.16,
                0.16,
                0.16,
                0.16,
                row_weights=(0.7, 2.2, 0.7),
                col_weights=(0.7, 2.0, 0.7, 0.7, 2.0, 0.7),
            ),
        ),
    ),
)

