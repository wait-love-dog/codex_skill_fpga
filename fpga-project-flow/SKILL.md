---
name: fpga-project-flow
description: Plan, implement, verify, and close FPGA projects that need high throughput, efficient resource use, and reproducible RTL simulation. Use for FPGA architecture, RTL/QoR optimization, or Windows Icarus Verilog verification; not for board-specific pin assignment alone.
metadata:
  short-description: FPGA architecture, QoR, and RTL verification
---

# FPGA Project Flow

Build FPGA work around measurable throughput, latency, accuracy, bandwidth, and resource targets. Make the architecture feasible before optimizing RTL or implementation directives. Preserve the user's selected device, vendor tools, interfaces, and validation boundary.

## Establish The Engineering Contract

Before changing architecture or RTL, collect the values that determine feasibility:

- Device family, speed grade, clock target, tool version, and the implementation boundary (module, out-of-context, or full design).
- Interface protocol, clock/reset ownership, ordering and backpressure behavior, and every clock-domain crossing.
- Sustained throughput, latency limit, numerical error or bit-accurate behavior, power limit, and off-chip bandwidth.
- LUT, FF, DSP, BRAM, and URAM budgets with headroom. Keep a per-module ledger rather than relying on a whole-design total.
- A repeatable functional test and the report or measurement that will establish QoR success.

State assumptions explicitly when values are unavailable. Do not invent a frequency, device limit, or board constraint.

## Work In Gates

Use the following gates as decision points. A gate may be lightweight for a small module, but do not skip its evidence.

1. **Feasibility:** Calculate compute demand, memory bandwidth, arithmetic intensity, and a resource budget. Determine whether the bottleneck is compute, memory, or data movement. Read [performance architecture](references/performance-architecture.md) for formulas and planning choices.
2. **Numerics:** Choose fixed-point formats, rounding, saturation, and error limits before finalizing datapath widths. Compare against a bit-accurate reference when numerical behavior matters.
3. **Cycle Model:** Set initiation interval, parallelism, pipeline latency, FIFO depths, and backpressure behavior. Confirm that producers, consumers, and external memory can sustain the target rate.
4. **RTL And Mapping:** Express the selected microarchitecture in synthesizable RTL, then verify that arithmetic and storage map to the intended DSP, BRAM, URAM, SRL, LUTRAM, or fabric resources.
5. **Implementation And Hardware:** Check timing constraints, CDC, utilization, congestion, and post-route timing. Use on-board counters or logic analysis when hardware measurement is in scope.

Keep a small before/after record for each material iteration: source revision, target clock, resource totals, worst slack, latency, and sustained throughput. A strategy sweep is evidence, not a substitute for fixing an architectural bottleneck.

## Design For Useful Work Per Cycle

Start with the throughput equation and identify the limiting term. Prefer changes with a structural payoff:

- Adjust algorithm, precision, reuse, tiling, or folding before micro-optimizing Boolean logic.
- Use streaming stages, valid/ready or credit-based flow control, and correctly sized FIFOs to hide variable memory or consumer latency.
- Match memory banks and ports to accesses per cycle. Capacity alone does not prove a buffer can feed the compute array.
- Use ping-pong buffers or other overlap only when transfer and compute schedules demonstrate the overlap is real.
- Pipeline from a logic-level and routing budget. A pipeline register that creates long enable or reset fanout can reduce Fmax.
- For fixed coefficients or structured workloads, evaluate symmetry, polyphase decomposition, constant-multiply alternatives, and reduced bit width before duplicating multipliers.

Use vendor primitives and inferred memories in the form the selected tool can map reliably. Retain portable RTL unless a primitive is needed to meet a verified goal.

## RTL, Clocks, And Reset

Treat interface timing as a contract. A change to latency, hold behavior, reset, or ready/valid semantics must be reflected in the testbench and in every adjacent stage.

- Keep control and datapath reset policies intentional. Reset control state where required; avoid resetting large datapaths merely by habit when it prevents efficient DSP, SRL, or memory inference.
- Do not generate clocks with fabric logic. Use clock enables or dedicated clock-management resources.
- Do not synchronize a multi-bit payload by independently adding two flip-flops to every bit. Use an asynchronous FIFO, handshake, or an encoding appropriate to the transfer.
- Register and constrain crossings between clock regions or SLRs. Treat wide, high-frequency crossings as pipeline design problems.
- Avoid a direct global ready/enable signal across a deep pipeline. Break its timing path with local buffering or an architecture that keeps the datapath moving.

## Verify In Layers

Verify function, protocol, performance, and QoR independently. Passing a testbench does not establish the synthesized hardware or the target simulator behavior.

- Compare bit-accurate output with a golden model for numeric kernels.
- Exercise reset, protocol boundaries, random backpressure, empty/full FIFO cases, exceptional arithmetic inputs, and sustained traffic.
- Compile both the DUT top and the testbench top. A testbench can compile while an uninstantiated production top has interface errors.
- Measure busy, idle, and stall cycles in simulation. On hardware, retain lightweight counters when real throughput must be demonstrated.
- Run CDC and timing methodology checks in the vendor flow when their reports are available.

For Windows Icarus Verilog flows, read [Icarus Verilog on Windows](references/iverilog-windows.md) before compiling or diagnosing a failure. Treat Icarus as a fast functional check and rerun in the delivery simulator when its elaboration or arithmetic behavior can differ.

## Close QoR With Evidence

Inspect synthesis and implementation reports at the same scope as the budget. Check inferred arithmetic and memory resources, high-fanout controls, logic depth, routing delay, unconstrained paths, congestion, and clock interaction. Compare each result with the ledger and target throughput rather than celebrating a single positive slack value.

When QoR misses, investigate in this order:

1. Architecture: parallelism, initiation interval, reuse, memory schedule, and arithmetic intensity.
2. Mapping: DSP/BRAM/URAM/SRL use and their internal pipeline registers.
3. RTL: logic depth, fanout, control sets, reset policy, and accidental width growth.
4. Constraints and physical partitioning: clocks, CDC, floorplanning, and long interconnect.
5. Tool directives and seed exploration.

Report achieved function, clock, slack, resources, latency, throughput, and any unverified boundary. Do not claim a board-level result from RTL simulation or an estimated Fmax.
