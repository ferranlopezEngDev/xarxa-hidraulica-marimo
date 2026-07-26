# Results Module

The `results` module converts a `SolverResult` or an evaluated system `state`
into simple tables, summaries and exportable files.

It does not depend on pandas. The goal is to keep the inspection and export
workflow lightweight, explicit and easy to reuse in scripts, notebooks and
academic reports.

This module can export:

- JSON files
- CSV tables
- complete result folders with several files at once

It is useful for:

- result inspection
- debugging
- solver comparison
- benchmark validation
- writing the final degree project report

## Example

```python
from hn3ttk.solvers import solve_newton_raphson
from hn3ttk.results import (
    nodes_table,
    links_table,
    result_summary,
    export_result_folder,
)

result = solve_newton_raphson(system)

print(result_summary(result))
print(nodes_table(result))
print(links_table(result))

export_result_folder(result, "data/results/single_pipe")
```
