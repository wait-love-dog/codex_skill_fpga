# Performance And Resource Architecture

Use this reference after the project contract is known and before deciding the RTL structure. The values below are planning models; validate them against the selected device and implementation reports.

## Quantify Feasibility

For a streaming compute engine, begin with effective performance:

```text
effective throughput = parallel lanes * useful operations per lane per cycle
                     * clock frequency * utilization
```

`utilization` includes bubbles from dependency, backpressure, memory stalls, and control transitions. A peak calculation with utilization assumed to be one is a capacity bound, not a performance claim.

For an input rate `R` with `W` bits per item, the raw interface requirement is approximately `R * W` bits/s before protocol overhead. For compute work `P` and available memory bandwidth `B`, the minimum arithmetic intensity to remain compute-bound is `P / B` operations per byte. Compare the workload's achievable reuse with that threshold before increasing parallel compute.

Build a ledger per module for LUT, FF, DSP, BRAM, URAM, I/O bandwidth, and clock margin. Reserve routing and integration headroom; a design near device saturation may fail due to congestion even when the arithmetic total fits.

## Choose Architecture Before RTL

Select the smallest combination of parallelism, clock rate, and reuse that reaches the sustained target.

- **Unroll or replicate** when data and memory can feed every lane each cycle.
- **Fold or time-multiplex** when a higher internal clock and schedule can reuse hardware without violating input/output deadlines.
- **Pipeline** when dependency depth limits Fmax or initiation interval. Measure latency separately from throughput.
- **Tile and reuse** when external bandwidth is the limiter. Size tiles from bandwidth and on-chip-port demand, not capacity alone.
- **Stream with FIFO decoupling** when stages have different latency or intermittent stalls. Derive FIFO depth from the maximum expected rate mismatch and burst, then verify it under randomized backpressure.
- **Double-buffer** when DMA and compute must overlap. Account for both buffers and ensure the DMA can fill one before the other is consumed.

For a loop or repeated operation, track the initiation interval (II). Sustainable rate is often one result per `II` cycles per lane. An unrolled datapath with II greater than one may deliver less than a smaller, well-fed II=1 structure.

## Constrain Numerics Deliberately

Use the smallest width that satisfies dynamic range and error requirements. Define signedness, intermediate growth, rounding, clipping/saturation, and overflow behavior at each boundary. Test extrema and sign combinations instead of relying only on typical random values.

Align choices with hardware where it is useful: DSP input/output widths, RAM word widths, and memory packing. Do not widen a datapath by default to host-language `int` or `float` widths when the hardware contract is narrower.

## Map Compute And Storage

Make intended mapping visible in synthesis reports.

| Need | Preferred evaluation |
| --- | --- |
| Multiply-accumulate chain | DSP blocks with internal registers and cascade paths |
| Small delay line or shallow queue | SRL or LUTRAM |
| Medium block with few ports | BRAM or LUTRAM based on depth and port demand |
| Large dense buffer | BRAM/URAM with banking sized for accesses per cycle |
| Fixed coefficient multiply | DSP, shift/add, CSD, or distributed arithmetic after resource comparison |
| Wide/high-rate transfer | Packing, banking, bursts, and local reuse before adding compute lanes |

Using a BRAM because it has enough bits can fail when ports cannot supply enough words per cycle. Likewise, a DSP used without its internal registers can turn a hard block into part of the timing bottleneck.

## Protect Timing And Routability

Separate logic-delay failures from routing-delay failures. Logic-delay failures usually call for pipeline, balancing, or an arithmetic transformation. Routing-delay failures often point to high fanout, wide crossings, excessive local utilization, long physical distance, or control nets reaching too many registers.

- Let data flow determine coarse placement. Avoid long data-path detours between hard blocks and memories.
- Register wide transfers across major physical regions; use the target vendor's guidance for SLR or die crossings.
- Apply Pblocks or floorplanning only after reports identify a physical problem. Over-constraining early can create congestion.
- Keep control-set diversity low, and use synchronous clock enables rather than fabric-generated clocks.
- Review post-route timing as the signoff value. Synthesis estimates guide early work but do not prove Fmax.

## Diagnose Misses

| Symptom | First investigation |
| --- | --- |
| Rate below target while Fmax is near limit | Parallelism, II, data reuse, and memory feed rate |
| Low Fmax with large logic delay | Pipeline boundaries, arithmetic depth, priority chains |
| Low Fmax with large routing delay | Fanout, reset/enable network, local utilization, physical distance |
| DSP pressure | Symmetry, folding, precision, coefficient implementation, SIMD/packing where supported |
| LUT/FF pressure | Width reduction, DSP absorption, SRL/LUTRAM, removal of unnecessary resets |
| BRAM pressure | Banking efficiency, depth/width packing, LUTRAM for shallow storage, URAM for dense storage |
| External bandwidth limit | Tiling, reuse, wider bursts, packing, compression or lower precision |
| Peak rate far above measured rate | Stalls, rate mismatch, missing overlap, FIFO depth, protocol behavior |
| Congestion | Local utilization, wide cross-connections, partitioning before strategy changes |

When a result falls short, change one causal level at a time and rerun the smallest meaningful check. Strategy and seed sweeps are useful for judging implementation variability, but persistent dependence on them indicates an unresolved design issue.
