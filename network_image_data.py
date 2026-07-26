"""Values transcribed from the second hydraulic-network image.

The tuples are ordered by increasing pipe identifier within each family. The
figure caption defines ``h = 0.5 mm`` as the height of the rectangular
cross-section of every non-cellular channel.
"""

from __future__ import annotations


ROWS = 10
COLUMNS = 14

INLET_NODE_ID = 1
OUTLET_NODE_ID = 302

NODE_COUNT = 2 + 2 * ROWS * (COLUMNS + 1)
PIPE_COUNT = ROWS * (3 * COLUMNS + 2)


# Pipes 1..10, ordered from the inlet upwards along the blue manifold.
SUPPLY_MANIFOLD_PIPE_IDS = tuple(range(1, 11))
SUPPLY_MANIFOLD_LENGTHS_MM = (1.0,) + (2.0,) * 9
SUPPLY_MANIFOLD_WIDTHS_MM = (1.4,) * 10

# Pipes 11..20, ordered by pipe identifier.  Pipe 11 is the short segment
# between node 301 and outlet node 302; pipes 12..20 continue downwards.
DRAIN_MANIFOLD_PIPE_IDS = tuple(range(11, 21))
DRAIN_MANIFOLD_LENGTHS_MM = (1.0,) + (2.0,) * 9
DRAIN_MANIFOLD_WIDTHS_MM = (1.4,) * 10


# Every horizontal segment is labelled with length 1.2 mm.  For both the blue
# and red families, increasing local pipe ID uses this same width sequence.
HORIZONTAL_LENGTHS_MM = (1.2,) * COLUMNS
HORIZONTAL_WIDTHS_MM = (
    1.500,
    1.341,
    1.241,
    1.141,
    1.041,
    0.941,
    0.841,
    0.741,
    0.641,
    0.541,
    0.441,
    0.341,
    0.241,
    0.141,
)

SUPPLY_HORIZONTAL_PIPE_IDS = tuple(range(21, 161))
DRAIN_HORIZONTAL_PIPE_IDS = tuple(range(161, 301))


# Pipes 301..440 are the green cellular channels.  Their labels give the
# empirical law delta_P[Pa] = K * Q[mm3/s]**n.
CELLULAR_PIPE_IDS = tuple(range(301, 441))
CELLULAR_COEFFICIENT_K = 2.483
CELLULAR_EXPONENT_N = 1.8

# Geometric height h of all blue and red rectangular channels.
NON_CELLULAR_CHANNEL_HEIGHT_MM = 0.5


def validate_image_data() -> None:
    """Fail early if a future edit breaks the transcribed dimensions."""
    if NODE_COUNT != OUTLET_NODE_ID:
        raise ValueError("The parametric node count does not end at node 302.")

    if PIPE_COUNT != 440:
        raise ValueError("The parametric pipe count must be 440.")

    if len(HORIZONTAL_LENGTHS_MM) != COLUMNS:
        raise ValueError("One horizontal length is required per column.")

    if len(HORIZONTAL_WIDTHS_MM) != COLUMNS:
        raise ValueError("One horizontal width is required per column.")

    families = (
        SUPPLY_MANIFOLD_PIPE_IDS,
        DRAIN_MANIFOLD_PIPE_IDS,
        SUPPLY_HORIZONTAL_PIPE_IDS,
        DRAIN_HORIZONTAL_PIPE_IDS,
        CELLULAR_PIPE_IDS,
    )
    all_ids = tuple(pipe_id for family in families for pipe_id in family)

    if all_ids != tuple(range(1, PIPE_COUNT + 1)):
        raise ValueError("Pipe families must cover identifiers 1..440 exactly.")


validate_image_data()
