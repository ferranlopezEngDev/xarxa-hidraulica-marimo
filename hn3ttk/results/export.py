from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from hn3ttk.results.tables import (
    _get_state,
    links_table,
    nodes_table,
    residuals_table,
    unknown_heads_table,
)


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


def _write_csv_rows(rows: list[dict[str, Any]], path: Path) -> Path:
    """Write a list of dictionaries to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file_obj:
        if not rows:
            return path

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

    return path


def export_state_json(result_or_state: Any, path: str | Path) -> Path:
    """Export a system state to JSON."""
    state = _get_state(result_or_state)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(_to_builtin(state), file_obj, indent=2, ensure_ascii=False)

    return output_path


def export_result_json(result: Any, path: str | Path) -> Path:
    """Export a SolverResult-like object to JSON."""
    to_dict = getattr(result, "to_dict", None)

    if not callable(to_dict):
        raise TypeError(
            "Expected a SolverResult-like object with a callable to_dict() "
            "method."
        )

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(_to_builtin(to_dict()), file_obj, indent=2, ensure_ascii=False)

    return output_path


def export_nodes_csv(result_or_state: Any, path: str | Path) -> Path:
    """Export node results to CSV."""
    return _write_csv_rows(nodes_table(result_or_state), Path(path))


def export_links_csv(result_or_state: Any, path: str | Path) -> Path:
    """Export link results to CSV."""
    return _write_csv_rows(links_table(result_or_state), Path(path))


def export_residuals_csv(result_or_state: Any, path: str | Path) -> Path:
    """Export residuals to CSV."""
    return _write_csv_rows(residuals_table(result_or_state), Path(path))


def export_unknown_heads_csv(result_or_state: Any, path: str | Path) -> Path:
    """Export the unknown-head vector to CSV."""
    return _write_csv_rows(unknown_heads_table(result_or_state), Path(path))


def export_result_folder(
    result: Any,
    folder: str | Path,
    prefix: str = "result",
) -> dict[str, Path]:
    """Export a result and, when available, its evaluated state to a folder."""
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    result_json_path = export_result_json(
        result,
        folder_path / f"{prefix}_result.json",
    )

    if getattr(result, "state", None) is None:
        return {
            "result_json": result_json_path,
        }

    state_json_path = export_state_json(
        result,
        folder_path / f"{prefix}_state.json",
    )
    nodes_csv_path = export_nodes_csv(
        result,
        folder_path / f"{prefix}_nodes.csv",
    )
    links_csv_path = export_links_csv(
        result,
        folder_path / f"{prefix}_links.csv",
    )
    residuals_csv_path = export_residuals_csv(
        result,
        folder_path / f"{prefix}_residuals.csv",
    )
    unknown_heads_csv_path = export_unknown_heads_csv(
        result,
        folder_path / f"{prefix}_unknown_heads.csv",
    )

    return {
        "result_json": result_json_path,
        "state_json": state_json_path,
        "nodes_csv": nodes_csv_path,
        "links_csv": links_csv_path,
        "residuals_csv": residuals_csv_path,
        "unknown_heads_csv": unknown_heads_csv_path,
    }
