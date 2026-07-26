# Solvers Module

The `solvers` module contains nonlinear solvers for hydraulic systems built
with HN3Ttk.

The currently implemented solvers are:

- Simple Newton-Raphson
- Damped Newton-Raphson
- Alpha continuation using simple Newton-Raphson at each continuation step
- Alpha continuation using damped Newton-Raphson at each continuation step
- SciPy root wrappers
- SciPy least_squares wrappers

## Simple Newton-Raphson

This solver evaluates:

- the residual vector `R(H)`
- the dense Jacobian `dR/dH`

and applies the standard Newton correction:

```text
J · step = -R
H_new = H_old + step
```

This is a plain Newton-Raphson method:

- no damping
- no line search
- no step clipping

## Alpha Continuation

The continuation solver resolves a sequence of problems:

```text
R(H, alpha) = 0
```

from `alpha_start` to `alpha_end`. The solution of each alpha step is used as
the initial guess for the next one.

## Damped Newton-Raphson

The damped variant computes the Newton step first and then performs
backtracking on a damping factor until the maximum absolute residual decreases.

This provides a simple line-search style stabilization without changing the
residual definition or the dense Jacobian assembly.

## SciPy Wrappers

The module also provides wrappers around SciPy nonlinear solvers:

- `solve_scipy_root`
- `solve_alpha_continuation_scipy_root`
- `solve_scipy_least_squares`
- `solve_alpha_continuation_scipy_least_squares`

| HN3Ttk wrapper | SciPy function | Direct root | Continuation |
|---|---|---|---|
| solve_scipy_root | scipy.optimize.root | yes | no |
| solve_alpha_continuation_scipy_root | scipy.optimize.root | yes | yes |
| solve_scipy_least_squares | scipy.optimize.least_squares | residual minimization | no |
| solve_alpha_continuation_scipy_least_squares | scipy.optimize.least_squares | residual minimization | yes |

Notes:

- `root` solves `R(H) = 0`.
- `least_squares` minimizes `||R(H)||²`.
- `use_jacobian=True` uses `system.dense_jacobian(...)` when the method allows it.
- For `root`, the analytical Jacobian is used only with `"hybr"` and `"lm"`.
- For `least_squares`, the analytical Jacobian is used whenever `use_jacobian=True`.

## Future Extensions

More advanced damping strategies, alternative acceptance rules and additional
solver wrappers can still be added later on top of this first architecture.

## Example

```python
from hn3ttk.solvers import solve_newton_raphson

result = solve_newton_raphson(system)

if result.success:
    print(result.unknown_heads)
    print(result.max_abs_residual)
```

For the damped version:

```python
from hn3ttk.solvers import solve_damped_newton_raphson

result = solve_damped_newton_raphson(system)
```
