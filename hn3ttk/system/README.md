# System Module

The `system` module contains the hydraulic network assembly layer of HN3Ttk.

It combines:

```text
nodes
connections
links
````

The `system` module is responsible for topology, orientation, head evaluation,
flow evaluation and nodal mass-balance residual assembly.

---

## Core Design Principle

The project separates local physical models from network topology.

```text
Connection -> local hydraulic behaviour
Node       -> local nodal boundary information
Link       -> topological placement of a connection
System     -> network assembly and residual evaluation
```

A connection does not know which nodes it connects.

A node does not know which connections are attached to it.

The hydraulic system owns the complete network structure.

---

## Main Classes

The module currently implements:

```text
Link
HydraulicSystem
```

---

## Link

A `Link` defines how a connection is placed inside the network.

It stores:

```text
id
connection_id
from_node_id
to_node_id
metadata
```

Example:

```python
from hn3ttk.system import Link

link = Link(
    id="link_1",
    connection_id="pipe_1",
    from_node_id="reservoir",
    to_node_id="junction_1",
)
```

This means that connection `pipe_1` is placed between `reservoir` and
`junction_1`.

---

## Link Orientation Convention

The positive flow direction is defined by the link orientation:

```text
q > 0 -> flow from from_node_id to to_node_id
q < 0 -> flow from to_node_id to from_node_id
```

The signed head variation across the link is defined as:

```text
delta_h = H_to - H_from
```

This convention is consistent with passive hydraulic connections:

```text
q > 0 -> delta_h < 0
```

Example:

```text
from_node = reservoir
to_node   = demand

H_from = 10 m
H_to   = 5 m

delta_h = H_to - H_from = -5 m
```

Since `delta_h < 0`, a passive connection returns `q > 0`, meaning flow from
the reservoir to the demand node.

---

## Link Validation

A link validates:

```text
id is a non-empty string
connection_id is a non-empty string
from_node_id is a non-empty string
to_node_id is a non-empty string
from_node_id != to_node_id
metadata is a dictionary
```

A link does not validate whether the referenced nodes or connection exist. That
is the responsibility of `HydraulicSystem`.

---

## HydraulicSystem

`HydraulicSystem` is the main network container.

It owns:

```python
nodes: dict[str, Node]
connections: dict[str, Connection]
links: dict[str, Link]
```

Example:

```python
from hn3ttk.system import HydraulicSystem
from hn3ttk.nodes import ReservoirNode, DemandNode
from hn3ttk.connections import PipeFixedPowerLaw

system = HydraulicSystem(id="single_pipe_system")

system.add_node(
    ReservoirNode(
        id="reservoir",
        parameters={
            "elevation": 0.0,
            "head": 10.0,
        },
    )
)

system.add_node(
    DemandNode(
        id="demand",
        parameters={
            "elevation": 0.0,
            "initial_head": 5.0,
            "demand": 0.1,
        },
    )
)

system.add_connection(
    PipeFixedPowerLaw(
        id="pipe",
        parameters={
            "k": 100.0,
            "n": 2.0,
        },
    )
)

system.connect(
    connection_id="pipe",
    from_node_id="reservoir",
    to_node_id="demand",
    link_id="link_1",
)
```

---

## Adding Objects

The system provides:

```python
add_node(node)
add_connection(connection)
add_link(link)
connect(connection_id, from_node_id, to_node_id, link_id=None, metadata=None)
```

`connect(...)` is a convenience method that creates and adds a `Link`.

Example:

```python
system.connect(
    connection_id="pipe",
    from_node_id="reservoir",
    to_node_id="demand",
    link_id="link_1",
)
```

---

## ID Conflict Behaviour

The system checks duplicated IDs when adding objects.

If a node ID already exists:

```text
ValueError: Node id '...' already exists.
```

If a connection ID already exists:

```text
ValueError: Connection id '...' already exists.
```

If a link ID already exists:

```text
ValueError: Link id '...' already exists.
```

The system also validates that link references point to existing nodes and
connections.

---

## Fixed and Unknown Head Nodes

The system separates nodes into:

```python
fixed_head_node_ids()
unknown_head_node_ids()
```

Fixed-head nodes are boundary conditions.

---

## Jacobian Assembly

`HydraulicSystem` also provides dense Jacobian assembly with respect to the
unknown nodal heads:

```python
dense_jacobian(unknown_heads, alpha=1.0, derivative_mode="default")
jacobian(unknown_heads, alpha=1.0, derivative_mode="default")
finite_difference_jacobian(
    unknown_heads,
    alpha=1.0,
    relative_step=1.0e-6,
    absolute_step=1.0e-8,
)
```

Notes:

```text
dense_jacobian()              -> returns np.ndarray
jacobian()                    -> alias of dense_jacobian()
finite_difference_jacobian()  -> returns np.ndarray
nodal_flow_residuals()        -> still returns list[float]
```

The `derivative_mode` used by `dense_jacobian()` can be:

```text
default
normal
tendency
inverse_head_loss
finite_difference
```

Difference between the two finite-difference approaches:

```text
derivative_mode="finite_difference":
    local finite difference inside each connection for dQ/d(delta_h)

finite_difference_jacobian():
    global finite difference over the full residual vector R(H)
```

Unknown-head nodes are solver unknowns.

Example:

```python
fixed_nodes = system.fixed_head_node_ids()
unknown_nodes = system.unknown_head_node_ids()
```

For nonlinear solvers, the system can also provide the initial unknown-head
vector:

```python
x0 = system.initial_unknown_heads()
```

---

## Building Complete Head Dictionaries

A solver normally works only with unknown heads.

However, flow evaluation requires the hydraulic head of every node.

The system provides:

```python
heads_from_unknowns(unknown_heads, alpha=1.0)
```

Example:

```python
heads = system.heads_from_unknowns([5.0])
```

Output:

```python
{
    "reservoir": 10.0,
    "demand": 5.0,
}
```

Fixed-head nodes are filled automatically using:

```python
node.fixed_head(alpha)
```

Unknown-head nodes are filled from the supplied vector.

---

## Link Head Difference

The system computes the signed head variation across a link using:

```python
link_delta_h(link_id, heads)
```

Convention:

```text
delta_h = H_to - H_from
```

Example:

```python
heads = {
    "reservoir": 10.0,
    "demand": 5.0,
}

delta_h = system.link_delta_h("link_1", heads)
```

Result:

```text
delta_h = -5.0
```

---

## Link Flow Rate

The system computes flow through a link using:

```python
link_flow_rate(link_id, heads)
```

Internally:

```python
delta_h = system.link_delta_h(link_id, heads)
q = connection.flow_rate(delta_h)
```

The sign of `q` follows the link orientation:

```text
q > 0 -> from_node_id to to_node_id
q < 0 -> to_node_id to from_node_id
```

Example:

```python
q = system.link_flow_rate("link_1", heads)
```

For a fixed power law with:

```text
k = 100
n = 2
delta_h = -5
```

the result is:

```text
q = sqrt(5 / 100) = 0.223606...
```

---

## All Link Flow Rates

The system can evaluate all link flow rates:

```python
flows = system.all_link_flow_rates(heads)
```

Example output:

```python
{
    "link_1": 0.22360679774997896,
}
```

---

## Nodal Flow Residuals

The main system assembly method is:

```python
nodal_flow_residuals(unknown_heads, alpha=1.0)
```

It returns the mass-balance residuals for unknown-head nodes.

Residual convention:

```text
residual = external_flow + inflow_from_links - outflow_to_links
```

For each link:

```text
q > 0 from from_node to to_node

contribution to from_node = -q
contribution to to_node   = +q
```

At the solution:

```text
residual = 0
```

The residual units are:

```text
m³/s
```

---

## Single Pipe Example

Consider:

```text
Reservoir head = 10 m
Demand node initial head = 5 m
Demand = 0.1 m³/s
Pipe law: ΔH = -100 · sign(Q) · |Q|²
Link orientation: reservoir -> demand
```

At the initial guess:

```text
H_reservoir = 10 m
H_demand = 5 m
```

The link head variation is:

```text
delta_h = H_demand - H_reservoir
delta_h = 5 - 10
delta_h = -5 m
```

The pipe flow is:

```text
Q = sqrt(5 / 100)
Q = 0.223606... m³/s
```

The demand node residual is:

```text
residual = external_flow + inflow
residual = -0.1 + 0.223606...
residual = 0.123606... m³/s
```

Since the residual is not zero, the initial head is not the solution.

At the solution:

```text
Demand = 0.1 m³/s
Q = 0.1 m³/s
ΔH = -100 · 0.1² = -1 m
H_demand - H_reservoir = -1
H_demand = 9 m
```

Therefore:

```python
residuals = system.nodal_flow_residuals([9.0])
```

returns approximately:

```text
[0.0]
```

---

## Serialization

The system can be exported to a dictionary:

```python
data = system.to_dict()
```

The exported structure contains:

```text
id
nodes
connections
links
metadata
```

Example structure:

```python
{
    "id": "single_pipe_system",
    "nodes": [...],
    "connections": [...],
    "links": [...],
    "metadata": {},
}
```

A full `from_dict` system factory is not implemented yet.

---

## Current Limitations

The current `system` module does not yet include:

```text
nonlinear solver
Jacobian assembly
system factory from dictionary
ID renaming utilities
residual convergence checker
global residual tolerances
graph analysis utilities
network validation beyond basic references
```

These features belong to later milestones.

---

## Current Design Principles

The `system` module follows these design principles:

```text
1. Nodes and connections remain topology-independent.
2. Links define orientation and topology.
3. The system owns all network relationships.
4. Positive link flow goes from from_node_id to to_node_id.
5. Link head variation is delta_h = H_to - H_from.
6. Unknown-head nodes define the nonlinear system unknowns.
7. Fixed-head nodes are boundary conditions.
8. Residuals represent nodal mass balance in m³/s.
9. The system assembles residuals but does not solve them yet.
```

---

## Minimal Import Example

```python
from hn3ttk.system import HydraulicSystem, Link
```

---

## Basic Test Command

```bash
python tests/test_system_basic.py
```

Expected output:

```text
All basic system tests passed.
```

---

## Complete Quick Test

```python
from hn3ttk.system import HydraulicSystem
from hn3ttk.nodes import ReservoirNode, DemandNode
from hn3ttk.connections import PipeFixedPowerLaw

system = HydraulicSystem()

system.add_node(
    ReservoirNode(
        id="res",
        parameters={
            "elevation": 0.0,
            "head": 10.0,
        },
    )
)

system.add_node(
    DemandNode(
        id="demand",
        parameters={
            "elevation": 0.0,
            "initial_head": 5.0,
            "demand": 0.1,
        },
    )
)

system.add_connection(
    PipeFixedPowerLaw(
        id="pipe",
        parameters={
            "k": 100.0,
            "n": 2.0,
        },
    )
)

system.connect(
    connection_id="pipe",
    from_node_id="res",
    to_node_id="demand",
    link_id="link_1",
)

x0 = system.initial_unknown_heads()
heads = system.heads_from_unknowns(x0)
flows = system.all_link_flow_rates(heads)
residuals = system.nodal_flow_residuals(x0)

print("x0 =", x0)
print("heads =", heads)
print("flows =", flows)
print("residuals =", residuals)
```
