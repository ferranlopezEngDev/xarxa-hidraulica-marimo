# Benchmarks Module

The `benchmarks` module contains small reproducible hydraulic systems that can
be used for validation, regression testing, solver comparison and teaching.

The currently included cases are:

- single pipe
- parallel pipes
- three reservoirs
- looped network inspired by classical Hardy-Cross examples
- medium generic network
- Larock Example 2.6 parallel branch flow
- Larock Example 2.7 three reservoirs
- Larock Problem 2.13 single-pipe Darcy validation
- Larock Problem 4.1a six-node Darcy network
- Larock Problem 4.1b pumped Darcy network
- Larock Problem 4.8 parallel pipes with a valve-loss branch

## What Each Case Tests

- `single_pipe`: analytical validation, sign conventions and first solver tests
- `parallel_pipes`: flow splitting and one junction with multiple incident links
- `three_reservoirs`: one unknown node connected to several fixed-head nodes
- `hardy_cross_loop`: a small looped network with alternative paths
- `medium_generic_network`: a more realistic internal benchmark for robust
  solvers, exports and tutorials
- `larock_example_2_6_parallel_branch`: textbook branch splitting with
  published discharges
- `larock_example_2_7_three_reservoirs`: textbook three-reservoir benchmark
  with published junction head and flows
- `larock_problem_2_13_single_pipe`: Darcy-Weisbach single-pipe benchmark
  validated against a selected end-of-book answer
- `larock_problem_4_1a_system`: six-node textbook Darcy network validated
  against the selected discharges from Problem 4.23(a)
- `larock_problem_4_1b_system`: pumped textbook Darcy network validated
  against the selected discharges from Problem 4.23(b)
- `larock_problem_4_8_parallel_pipes`: branch splitting with a local valve
  loss validated against a selected end-of-book answer

## Recommended Solvers

- `single_pipe`: simple Newton-Raphson, damped Newton or SciPy wrappers
- `parallel_pipes`: damped Newton or `scipy_root(method="hybr")`
- `three_reservoirs`: damped Newton or `scipy_root(method="hybr")`
- `hardy_cross_loop`: alpha continuation with damped Newton or
  `scipy_least_squares(method="trf")`
- `medium_generic_network`: alpha continuation with damped Newton or
  `scipy_least_squares(method="trf")`
- `larock_example_2_6_parallel_branch`: damped Newton or
  `scipy_root(method="hybr")`
- `larock_example_2_7_three_reservoirs`: damped Newton or
  `scipy_root(method="hybr")`
- `larock_problem_2_13_single_pipe`: damped Newton or
  `scipy_root(method="hybr")`
- `larock_problem_4_1a_system`: alpha continuation with damped Newton
- `larock_problem_4_1b_system`: alpha continuation with damped Newton
- `larock_problem_4_8_parallel_pipes`: damped Newton or
  `scipy_root(method="hybr")`

These cases are internal and reproducible. They are useful for development and
teaching, but they do not replace validation against EPANET or another external
reference simulator.
