from __future__ import annotations

import csv
import json
from functools import partial
from math import inf
from pathlib import Path
from typing import Any, Callable

from hn3ttk.solvers import (
    solve_alpha_continuation_damped_newton,
    solve_alpha_continuation_newton,
    solve_alpha_continuation_scipy_least_squares,
    solve_alpha_continuation_scipy_root,
    solve_damped_newton_raphson,
    solve_newton_raphson,
    solve_scipy_least_squares,
    solve_scipy_root,
)
from hn3ttk.system import HydraulicSystem


def _to_builtin(value: Any) -> Any:
    """Convert common container and scalar types to JSON-safe builtins."""
    if value is None:
        return None

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _to_builtin(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_to_builtin(item) for item in value]

    item_method = getattr(value, "item", None)

    if callable(item_method):
        try:
            return _to_builtin(item_method())
        except Exception:
            pass

    return value


def available_default_solvers() -> dict[str, Callable]:
    """Return a small default solver set for reproducible comparisons."""
    return {
        "newton": solve_newton_raphson,
        "alpha_newton": solve_alpha_continuation_newton,
        "damped_newton": solve_damped_newton_raphson,
        "alpha_damped_newton": solve_alpha_continuation_damped_newton,
        "scipy_root_hybr": partial(solve_scipy_root, method="hybr"),
        "alpha_scipy_root_hybr": partial(
            solve_alpha_continuation_scipy_root,
            method="hybr",
        ),
        "scipy_least_squares_trf": partial(
            solve_scipy_least_squares,
            method="trf",
        ),
        "alpha_scipy_least_squares_trf": partial(
            solve_alpha_continuation_scipy_least_squares,
            method="trf",
        ),
    }


def compare_solvers(
    system: HydraulicSystem,
    solvers: dict[str, Callable] | None = None,
    residual_tolerance: float = 1.0e-8,
) -> list[dict[str, Any]]:
    """Run several solvers on one system and return compact comparison rows."""
    solver_map = available_default_solvers() if solvers is None else dict(solvers)
    rows: list[dict[str, Any]] = []

    for name, solver in solver_map.items():
        try:
            result = solver(system)
            success = bool(result.success) and (
                float(result.max_abs_residual) <= float(residual_tolerance)
            )
            rows.append(
                {
                    "solver": name,
                    "success": success,
                    "message": result.message,
                    "iterations": result.iterations,
                    "max_abs_residual": result.max_abs_residual,
                    "unknown_heads": result.unknown_heads,
                }
            )
        except Exception as error:
            rows.append(
                {
                    "solver": name,
                    "success": False,
                    "message": f"Exception: {error}",
                    "iterations": 0,
                    "max_abs_residual": inf,
                    "unknown_heads": [],
                }
            )

    return rows


def export_solver_comparison_csv(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    """Export solver comparison rows to CSV."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file_obj:
        if not rows:
            return output_path

        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            serialized_row: dict[str, Any] = {}

            for key in fieldnames:
                value = _to_builtin(row.get(key))

                if isinstance(value, (dict, list)):
                    serialized_row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_row[key] = value

            writer.writerow(serialized_row)

    return output_path
