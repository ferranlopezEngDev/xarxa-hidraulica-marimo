# Connections Module

The `connections` module contains the local hydraulic models used to represent
the behaviour of hydraulic elements such as pipes, empirical curves, tabulated
relations and custom head-loss laws.

A connection only describes the local relation between flow rate and head
variation. It does not store network topology and it does not know which nodes it
connects. The system assembler is responsible for assigning connections to nodes,
defining their orientation and building the global residual system.

---

## Sign Convention

All passive connection models follow the same sign convention:

```text
q > 0  ->  delta_h < 0
q < 0  ->  delta_h > 0
````

where:

```text
q       = signed flow rate [m³/s]
delta_h = signed head variation [m]
```

This means that a positive flow rate produces a negative head variation because
passive hydraulic elements dissipate energy in the direction of flow.

For example, a passive quadratic law is written as:

```text
ΔH = -k · sign(Q) · |Q|^n
```

---

## Base API

Every connection model inherits from `Connection` and must implement the same
public interface:

```python
head_loss(q)
flow_rate(delta_h)
head_loss_derivative(q)
flow_rate_derivative(delta_h)
```

The expected meaning is:

```python
head_loss(q)
```

Returns the signed head variation produced by a given flow rate.

```python
flow_rate(delta_h)
```

Returns the signed flow rate associated with a given head variation.

```python
head_loss_derivative(q)
```

Returns:

```text
d(ΔH)/dQ
```

```python
flow_rate_derivative(delta_h)
```

Returns:

```text
dQ/d(ΔH)
```

The base class also provides:

```python
head_loss_tendency(q)
flow_rate_tendency(delta_h)
jacobian_derivative(delta_h, method="default")
get_jacobian_derivative_mode()
set_jacobian_derivative_mode(mode)
validate()
to_dict()
from_dict(data)
model_info()
```

---

## Jacobian Derivative Strategy

Each connection can store a default jacobian derivative mode in:

```python
parameters["jacobian_derivative"]
```

Available methods are:

```text
normal
tendency
inverse_head_loss
finite_difference
```

The special selector:

```text
default
```

means that `jacobian_derivative(...)` uses the mode configured in the
connection itself. If no mode is provided, the default stored value is:

```python
parameters["jacobian_derivative"] = "normal"
```

Example:

```python
from hn3ttk.connections import PipeFixedPowerLaw

pipe = PipeFixedPowerLaw(
    parameters={
        "k": 100.0,
        "n": 2.0,
        "jacobian_derivative": "tendency",
    }
)

dq_dh = pipe.jacobian_derivative(-1.0)
```

---

## Implemented Connection Models

The current implemented models are:

```text
PipeDarcy
PipeLocalPowerLaw
PipeFixedPowerLaw
LinearInterpolationConnection
PolynomialRegressionConnection
SplineInterpolationConnection
SplineSecantExtrapolationConnection
SplineTangentExtrapolationConnection
CustomFactorPolynomialConnection
```

---

## PipeDarcy

Complete Darcy-Weisbach pipe model.

The signed head variation is computed as:

```text
ΔH = -f · 8 · L · Q · |Q| / (g · π² · D⁵)
```

where:

```text
L = pipe length [m]
D = internal diameter [m]
Q = flow rate [m³/s]
g = gravity [m/s²]
f = Darcy friction factor [-]
```

The friction factor is computed from the Reynolds number:

```text
Laminar regime:      f = 64 / Re
Turbulent regime:    Swamee-Jain approximation
Transition regime:   linear interpolation of |ΔH|(Q)
```

Example:

```python
from hn3ttk.connections import PipeDarcy

pipe = PipeDarcy(
    parameters={
        "length": 100.0,
        "diameter": 0.05,
        "roughness": 1.5e-4,
    }
)

q = 0.001
delta_h = pipe.head_loss(q)
q_inv = pipe.flow_rate(delta_h)

print(delta_h)
print(q_inv)
```

Expected behaviour:

```text
delta_h < 0
q_inv ≈ q
```

---

## PipeLocalPowerLaw

Local power-law approximation derived from Darcy-Weisbach.

The model approximates the Darcy-Weisbach curve locally as:

```text
ΔH = -k(Q) · sign(Q) · |Q|^n(Q)
```

The coefficients `k(Q)` and `n(Q)` are recalculated around the current operating
point.

In the transition regime, the model interpolates the head-loss curve directly
with a linear segment and derives equivalent local `k(Q)` and `n(Q)` from the
local line value and slope.

This model is useful for comparing a full Darcy-Weisbach formulation with a
local potential approximation.

Example:

```python
from hn3ttk.connections import PipeLocalPowerLaw

pipe = PipeLocalPowerLaw(
    parameters={
        "length": 100.0,
        "diameter": 0.05,
        "roughness": 1.5e-4,
    }
)

q = 0.001
delta_h = pipe.head_loss(q)
q_inv = pipe.flow_rate(delta_h)
k, n = pipe.local_power_law_parameters(q)

print(delta_h)
print(q_inv)
print(k, n)
```

---

## PipeFixedPowerLaw

Fixed power-law pipe model.

The signed head variation is:

```text
ΔH = -k · sign(Q) · |Q|^n
```

where `k` and `n` are fixed parameters.

Example:

```python
from hn3ttk.connections import PipeFixedPowerLaw

pipe = PipeFixedPowerLaw(
    parameters={
        "k": 120.0,
        "n": 2.0,
    }
)

q = 0.1
delta_h = pipe.head_loss(q)
q_inv = pipe.flow_rate(delta_h)

print(delta_h)
print(q_inv)
```

Expected result:

```text
-1.2
0.1
```

---

## LinearInterpolationConnection

Tabulated connection using piecewise-linear interpolation.

The model stores tabulated data in the form:

```text
Q -> ΔH
```

using:

```python
flow_rates
head_losses
```

Example:

```python
from hn3ttk.connections import LinearInterpolationConnection

connection = LinearInterpolationConnection(
    parameters={
        "flow_rates": [-0.02, 0.0, 0.02],
        "head_losses": [3.0, 0.0, -3.0],
    }
)

print(connection.head_loss(0.01))
print(connection.flow_rate(-1.5))
```

Expected result:

```text
-1.5
0.01
```

This model requires the tabulated head-loss relation to be invertible.

---

## PolynomialRegressionConnection

Connection fitted using polynomial regression from tabulated data.

The model fits:

```text
ΔH = P(Q)
```

where `P(Q)` is a polynomial of selected degree.

Example:

```python
from hn3ttk.connections import PolynomialRegressionConnection

connection = PolynomialRegressionConnection(
    parameters={
        "flow_rates": [-0.02, 0.0, 0.02],
        "head_losses": [3.0, 0.0, -3.0],
        "degree": 1,
    }
)

print(connection.head_loss(0.01))
print(connection.flow_rate(-1.5))
print(connection.get_coefficients())
```

The polynomial coefficients are computed during initialization. If the
tabulation is modified, the model is rebuilt automatically.

---

## SplineInterpolationConnection

Tabulated connection using spline interpolation.

Supported methods:

```text
pchip
cubic_spline
```

The recommended method for hydraulic curves is:

```text
pchip
```

because it preserves monotonicity better than a classical cubic spline and helps
avoid non-physical oscillations between tabulated points.

Example:

```python
from hn3ttk.connections import SplineInterpolationConnection

connection = SplineInterpolationConnection(
    parameters={
        "flow_rates": [-0.02, -0.01, 0.0, 0.01, 0.02],
        "head_losses": [3.0, 1.0, 0.0, -1.0, -3.0],
        "method": "pchip",
    }
)

print(connection.head_loss(0.01))
print(connection.flow_rate(-1.0))
print(connection.get_method())
```

---

## SplineTangentExtrapolationConnection

Tabulated connection using spline interpolation inside the tabulated domain and
tangent-line extrapolation outside it.

Supported methods:

```text
pchip
cubic_spline
```

Outside the tabulated range:

```text
forward curve  Q -> ΔH: tangent line at the nearest endpoint
inverse curve  ΔH -> Q: tangent line at the nearest endpoint
```

This is useful when plain spline extrapolation is too aggressive or
non-physical and a locally linear continuation is preferred.

Example:

```python
from hn3ttk.connections import SplineTangentExtrapolationConnection

connection = SplineTangentExtrapolationConnection(
    parameters={
        "flow_rates": [-0.02, -0.01, 0.0, 0.01, 0.02],
        "head_losses": [3.0, 1.0, 0.0, -1.0, -3.0],
        "method": "pchip",
    }
)

print(connection.head_loss(0.01))
print(connection.head_loss(0.03))
print(connection.flow_rate(-1.0))
```

---

## SplineSecantExtrapolationConnection

Tabulated connection using spline interpolation inside the tabulated domain and
the straight line defined by the first two or last two tabulated points outside
it.

Supported methods:

```text
pchip
cubic_spline
```

Outside the tabulated range:

```text
left side:   line through (x1, y1) and (x2, y2)
right side:  line through (xn-1, yn-1) and (xn, yn)
```

This corresponds to a linear fit built from the two boundary samples of each
side.

Example:

```python
from hn3ttk.connections import SplineSecantExtrapolationConnection

connection = SplineSecantExtrapolationConnection(
    parameters={
        "flow_rates": [-0.02, -0.01, 0.0, 0.01, 0.02],
        "head_losses": [3.0, 1.0, 0.0, -1.0, -3.0],
        "method": "pchip",
    }
)

print(connection.head_loss(0.01))
print(connection.head_loss(0.03))
print(connection.flow_rate(-1.0))
```

---

## CustomFactorPolynomialConnection

Custom passive polynomial factor model.

The model evaluates:

```text
ΔH = -Σ ai · sign(Q) · |Q|^ni
```

where each coefficient and exponent is user-defined.

Example:

```python
from hn3ttk.connections import CustomFactorPolynomialConnection

connection = CustomFactorPolynomialConnection(
    parameters={
        "coefficients": [10.0, 120.0],
        "exponents": [1.0, 2.0],
    }
)

q = 0.1
delta_h = connection.head_loss(q)
q_inv = connection.flow_rate(delta_h)

print(delta_h)
print(q_inv)
print(connection.get_terms())
```

This example represents:

```text
ΔH = -(10 · sign(Q) · |Q| + 120 · sign(Q) · |Q|²)
```

---

## Tabulation Modification API

The tabulated and regression-based models include methods to access and modify
their data.

Available methods include:

```python
get_tabulation()
set_tabulation(flow_rates, head_losses)
add_point(flow_rate, head_loss)
remove_point(index)
sample(n)
```

For generic plotting support, every connection also exposes:

```python
head_loss_plot_data(q_start, q_end, n)
flow_rate_plot_data(delta_h_start, delta_h_end, n)
```

These helpers return equally spaced inputs together with the function values,
derivatives and tendencies needed to plot `ΔH(Q)` or `Q(ΔH)` directly.

When tabulated data is modified, the internal interpolation or regression model
is rebuilt automatically.

Example:

```python
connection.add_point(0.03, -5.0)

flow_rates, head_losses = connection.get_tabulation()
```

The returned tabulation values are copies, so external modifications do not
silently modify the internal model.

---

## Internal Rebuild Logic

Models that require precomputed internal data use:

```python
_rebuild_model()
```

This method is called automatically during initialization and after any
modification of the tabulated data or model parameters.

Examples of internal data:

```text
linear interpolation cache
polynomial coefficients
spline interpolator objects
custom polynomial terms
```

This avoids recalculating expensive data during every evaluation.

---

## Inversion Check

A basic consistency check for every connection is:

```python
q = 0.001
delta_h = connection.head_loss(q)
q_inv = connection.flow_rate(delta_h)

assert q_inv ≈ q
```

This verifies that the forward relation and inverse relation are coherent.

---

## Current Design Principles

The `connections` module follows these design principles:

```text
1. Connections represent local hydraulic behaviour only.
2. Connections do not store node connectivity.
3. The system assembler defines orientation and topology.
4. All models expose the same public API.
5. Passive models follow the convention q > 0 -> delta_h < 0.
6. Models with internal fitted data rebuild themselves after modifications.
7. Tabulated models return copies of their stored data.
8. Numerical inversion is handled locally when no analytical inverse exists.
```

---

## Minimal Import Example

```python
from hn3ttk.connections import (
    PipeDarcy,
    PipeLocalPowerLaw,
    PipeFixedPowerLaw,
    LinearInterpolationConnection,
    PolynomialRegressionConnection,
    SplineInterpolationConnection,
    CustomFactorPolynomialConnection,
)
```

---

## Basic Test Command

```bash
python -c "from hn3ttk.connections import PipeFixedPowerLaw; p=PipeFixedPowerLaw(parameters={'k':120,'n':2}); print(p.head_loss(0.1)); print(p.flow_rate(-1.2))"
```
