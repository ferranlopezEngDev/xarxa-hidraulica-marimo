# Nodes Module

The `nodes` module contains the local hydraulic node models used by HN3Ttk.

A node represents local nodal information only. It does not store which
connections are attached to it. The system assembler is responsible for network
topology, incidence relations and residual assembly.

---

## Design Principle

Nodes define local boundary information:

```text
- geometric elevation
- fixed or unknown hydraulic head
- initial head guess
- external nodal flow
- continuation scaling
- metadata
````

Nodes do not know:

```text
- connected pipes
- connected pumps
- neighbouring nodes
- incidence orientation
- global residual equations
```

That responsibility belongs to the `system` module.

---

## Hydraulic Quantities

The main nodal quantities are:

```text
z = elevation [m]
H = hydraulic head [m]
p/γ = pressure head [m]
```

The relation is:

```text
H = z + p/γ
```

Therefore:

```text
pressure_head = H - z
```

---

## External Flow Sign Convention

External nodal flow follows this convention:

```text
external_flow > 0  -> injection into the network
external_flow < 0  -> demand/extraction from the network
```

Examples:

```text
Injection of 0.002 m³/s  -> external_flow =  0.002
Demand of 0.002 m³/s     -> external_flow = -0.002
```

---

## Base API

Every node model inherits from `Node` and exposes the following public interface:

```python
is_fixed_head()
is_unknown_head()
fixed_head(alpha=1.0)
initial_head()
external_flow(alpha=1.0)
elevation()
pressure_head(head=None, alpha=1.0)
to_dict()
from_dict(data)
model_info()
```

---

## Continuation Factor

Some node boundary conditions can be scaled using a continuation factor:

```text
0 <= alpha <= 1
```

This is useful for staged nonlinear solving or continuation methods.

For example, a demand node may apply:

```text
external_flow(alpha) = -alpha · demand
```

A fixed-head node may optionally apply:

```text
fixed_head(alpha) = elevation + alpha · (head - elevation)
```

This avoids starting continuation from an unrealistic hydraulic head of zero.
At `alpha = 0`, the fixed head becomes equal to the node elevation.

---

## Implemented Node Models

The current implemented models are:

```text
ConfigurableNode
JunctionNode
FixedHeadNode
ReservoirNode
DemandNode
InjectionNode
```

---

## ConfigurableNode

Fully configurable hydraulic node.

It can represent either a fixed-head node or an unknown-head node depending on
the `fixed_head` parameter.

Example fixed-head configuration:

```python
from hn3ttk.nodes import ConfigurableNode

node = ConfigurableNode(
    parameters={
        "elevation": 10.0,
        "fixed_head": True,
        "head": 30.0,
        "scale_head_with_alpha": True,
    }
)

print(node.fixed_head(alpha=0.0))
print(node.fixed_head(alpha=1.0))
```

Expected output:

```text
10.0
30.0
```

Example unknown-head configuration:

```python
from hn3ttk.nodes import ConfigurableNode

node = ConfigurableNode(
    parameters={
        "elevation": 5.0,
        "fixed_head": False,
        "initial_head": 20.0,
        "external_flow": -0.002,
        "scale_external_flow_with_alpha": True,
    }
)

print(node.initial_head())
print(node.external_flow(alpha=1.0))
print(node.pressure_head())
```

Expected output:

```text
20.0
-0.002
15.0
```

---

## JunctionNode

Unknown-head junction node.

A junction normally represents a network node where mass conservation is imposed.
It may optionally include an external flow term.

Example:

```python
from hn3ttk.nodes import JunctionNode

node = JunctionNode(
    parameters={
        "elevation": 5.0,
        "initial_head": 15.0,
    }
)

print(node.is_unknown_head())
print(node.external_flow())
```

Expected output:

```text
True
0.0
```

---

## FixedHeadNode

Fixed hydraulic-head boundary node.

This node prescribes hydraulic head. It does not impose an external nodal flow.
The flow exchanged with the network is determined by the hydraulic solution.

Example:

```python
from hn3ttk.nodes import FixedHeadNode

node = FixedHeadNode(
    parameters={
        "elevation": 10.0,
        "head": 30.0,
    }
)

print(node.is_fixed_head())
print(node.fixed_head())
print(node.pressure_head())
```

Expected output:

```text
True
30.0
20.0
```

---

## ReservoirNode

Semantic fixed-head node representing a reservoir.

The prescribed hydraulic head normally represents the reservoir water surface
head.

Example:

```python
from hn3ttk.nodes import ReservoirNode

reservoir = ReservoirNode(
    id="reservoir_1",
    parameters={
        "elevation": 10.0,
        "head": 30.0,
    },
    metadata={
        "name": "Reservoir A",
    },
)

print(reservoir.fixed_head())
print(reservoir.metadata["name"])
```

Expected output:

```text
30.0
Reservoir A
```

---

## DemandNode

Unknown-head node with prescribed demand.

Demand is stored as a positive magnitude and returned as negative external flow.

Example:

```python
from hn3ttk.nodes import DemandNode

node = DemandNode(
    parameters={
        "elevation": 5.0,
        "initial_head": 20.0,
        "demand": 0.002,
    }
)

print(node.external_flow(alpha=0.0))
print(node.external_flow(alpha=1.0))
```

Expected output:

```text
0.0
-0.002
```

---

## InjectionNode

Unknown-head node with prescribed injection.

Injection is stored as a positive magnitude and returned as positive external
flow.

Example:

```python
from hn3ttk.nodes import InjectionNode

node = InjectionNode(
    parameters={
        "elevation": 5.0,
        "initial_head": 20.0,
        "injection": 0.002,
    }
)

print(node.external_flow(alpha=0.0))
print(node.external_flow(alpha=1.0))
```

Expected output:

```text
0.0
0.002
```

---

## Factory API

The module includes a node factory to create nodes from dictionaries.

Example:

```python
from hn3ttk.nodes import node_from_dict

data = {
    "id": "reservoir_1",
    "type": "reservoir_node",
    "parameters": {
        "elevation": 10.0,
        "head": 30.0,
    },
    "metadata": {
        "name": "Reservoir A",
    },
}

node = node_from_dict(data)

print(type(node).__name__)
print(node.fixed_head())
```

Expected output:

```text
ReservoirNode
30.0
```

Available factory functions:

```python
node_from_dict(data)
node_to_dict(node)
available_node_types()
register_node_type(node_class)
```

---

## Metadata

Every node includes a `metadata` dictionary.

Metadata does not affect hydraulic calculations. It is used for descriptive,
organizational or visualization information.

Example:

```python
metadata = {
    "name": "Main reservoir",
    "zone": "validation_case",
    "notes": "Boundary condition for three-reservoir example",
}
```

---

## Current Design Principles

The `nodes` module follows these design principles:

```text
1. Nodes represent local nodal data only.
2. Nodes do not store network topology.
3. The system assembler defines connectivity and residual equations.
4. All node models expose the same public API.
5. Elevation and hydraulic head are stored separately.
6. External flow is positive for injection and negative for demand.
7. Continuation scaling is available for staged nonlinear solving.
8. Metadata is flexible and does not affect hydraulic calculations.
```

---

## Minimal Import Example

```python
from hn3ttk.nodes import (
    ConfigurableNode,
    JunctionNode,
    FixedHeadNode,
    ReservoirNode,
    DemandNode,
    InjectionNode,
    node_from_dict,
    available_node_types,
)
```

---

## Basic Test Command

```bash
python tests/test_nodes_basic.py
```

Expected output:

```text
All basic node tests passed.
```