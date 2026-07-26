# HN3Ttk Package

This folder contains the main Python package for HN3Ttk.

## Package Structure

- `nodes/`
  Local hydraulic node models such as reservoirs, demand nodes, junctions and
  configurable boundary conditions.

- `connections/`
  Local hydraulic connection models such as power-law pipes, Darcy-based pipes
  and interpolation or regression-based elements.

- `system/`
  Global hydraulic system assembly, topology handling, residual evaluation,
  dense Jacobian assembly and full state evaluation.

- `solvers/`
  Nonlinear solvers, including custom Newton variants and SciPy wrappers.

- `results/`
  Result summaries, table helpers and JSON/CSV export utilities.

- `benchmarks/`
  Internal validation cases, reproducible benchmark networks and solver
  comparison helpers.

- `io/`
  Reserved for import and export workflows beyond the current result utilities.

## Recommended Entry Points

For explicit imports in regular code:

- `hn3ttk.nodes`
- `hn3ttk.connections`
- `hn3ttk.system`
- `hn3ttk.solvers`
- `hn3ttk.results`
- `hn3ttk.benchmarks`

For quick experiments and interactive use:

- `hn3ttk.api`

Import it with:

```python
from hn3ttk.api import *
```

Minimal example:

```python
from hn3ttk.api import *

system = build_single_pipe_system()
result = solve_newton_raphson(system)

print_result_summary(result)
print(nodes_table(result))
print(links_table(result))
```

## Suggested Reading Order

1. Repository root `README.md`
2. `docs/quickstart.md`
3. `examples/01_single_pipe_step_by_step.py`
4. Submodule READMEs inside this package
