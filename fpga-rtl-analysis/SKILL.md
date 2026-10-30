---
name: fpga-rtl-analysis
description: Analyse and verify FPGA RTL with the fpga-rtl-analyzer plugin - hierarchy elaboration, gate-based architecture/mapping/CDC/QoR checks, Icarus Verilog compile-and-simulate evidence, and reproducible Markdown/JSON/HTML reports. Use when reviewing RTL quality, diagnosing a simulation failure, closing a QoR gap, or when new RTL has been added to this project.
metadata:
  short-description: Gate-based RTL analysis and verification with evidence
---

# FPGA RTL Analysis

Drive the `fpga-rtl-analyzer` plugin over the project's RTL. The plugin is
mechanical: it parses the design, elaborates the hierarchy, runs named checks,
runs Icarus Verilog when asked, and writes a report in which every statement
carries a file, a line and a command. Your job is to interpret that evidence and
fix the design — not to restate the report.

The plugin is a *tool*, not an oracle. It cannot synthesise, place, route or
measure. Anything about timing, utilisation, Fmax or board behaviour is out of
reach until a vendor implementation report or a hardware measurement exists.

## Start Here

1. `fpga_list_designs` — which RTL revisions exist and how big each one is.
2. `fpga_check_rtl` — findings as data, no files written. Start here while iterating.
3. `fpga_gate_status` — per-gate counts, to decide which gate to work on next.
4. `fpga_analyze` — the full run that writes Markdown + JSON + HTML reports.
5. `fpga_verify` — compile and simulate with Icarus Verilog, with logs preserved.

Command line equivalents (same code path):

```powershell
$env:PYTHONPATH = "<plugin>\src"
python -m fpga_rtl.cli designs  <project>
python -m fpga_rtl.cli check    <project> --design rtl-all --severity error warning
python -m fpga_rtl.cli analyze  <project> --design rtl-all --out <project>\build\rtl-analysis --verify
python -m fpga_rtl.cli verify   <project> --design rtl-all --testbench tb_soc
python -m fpga_rtl.cli gates    <project> --design rtl-all --verify
python -m fpga_rtl.cli doctor   <project>
```

`--fail-on error|warning|info|none` turns a run into a gate you can script.
Exit `0` passes the threshold, `1` meets it, `2` is a usage or environment problem.

## Map The Output Onto The Project Flow

Findings are grouped by the gate they belong to. Report which gate you are
working on, and fix causes in this order — architecture before syntax:

| Gate | What the checks actually measure |
| --- | --- |
| `feasibility` | Per-module resource estimates (FF/LUT/DSP/BRAM) and budget comparison; memory bits per array |
| `numerics` | Operand and destination widths, signed/unsigned mixing, shift-amount truncation, carry loss |
| `cycle_model` | Interface contracts between modules: unconnected inputs, undeclared connection targets, width mismatches |
| `rtl_mapping` | Latch inference, reset policy and polarity, BRAM/LUTRAM/SRL classification, multiply and divide sites, power-on state |
| `implementation` | Clock-domain crossings, fabric-generated clocks, fanout of control and bus nets, combinational logic depth, multiple drivers |
| `verification` | Icarus compile and simulate evidence: exit codes, PASS/FAIL/TIMEOUT verdicts, assertions, cycle counts |

Pick the gate from the symptom, not from the check that happened to fire:

- Reports "renders wrong data" but the testbench says PASS → `verification`
  first: confirm the testbench compiled against the *current* RTL and that its
  assertions would actually catch the defect.
- Fmax or slack problems → `implementation` (fanout, depth, CDC), then
  `rtl_mapping` (is the arithmetic on a DSP or in fabric?).
- Suspected stale or mismatched interfaces → `cycle_model`: a testbench can
  compile while a production top has interface errors, and vice versa.
- Before adding hardware → `feasibility`: read the estimate as an estimate.

## Work In This Order

1. **Reproduce.** Run `fpga_check_rtl` on the design you are changing and save
   the JSON. A finding without the revision it came from is not evidence.
2. **Triage by gate, not by count.** Ten `info` estimates are quieter than one
   `error` CDC finding. Read `error` first, then `warning`.
3. **Fix one causal level at a time**, then re-run the smallest check that can
   show the change — usually `--checks <id>` rather than the whole suite.
4. **Prove the fix.** Static checks cannot confirm behaviour: run
   `fpga_verify` with the testbench that exercises the change, and quote its
   verdict, cycles and log path.
5. **Record the before/after**: revision stamp, finding counts per gate, the
   compile/sim verdicts. `rtl_report.json` carries the per-file revision hashes
   needed to tie a result to a revision.

## Interpreting Findings Correctly

- **`error`** means a real structural defect with a citation: two drivers on one
  net, an unknown module, a latch, a testbench that will not compile.
- **`warning`** is a design decision that needs justification, not automatically
  a bug. `map.dsp_mapping` flagging an unregistered 64-bit multiply is a
  question ("is this on the critical path?"), not a verdict.
- **`info`** is measured context: resource estimates, power-on state, memory
  classification. Do not report these as defects.
- **Estimates are not measurements.** Every `map.resource_ledger` number is
  produced by the model in its `meta.estimate_model` and labelled `estimate`;
  the LUT figure in particular is pessimistic. Never write it into a QoR table
  as a resource number.
- **`sorry:` lines from Icarus are tool limitations, not failures.** When a
  construct such as `unique case` is reported as unsupported, the runtime check
  is *not* enforced — cover full case coverage and defaults with an explicit
  test instead of assuming the simulator checked it.
- **A compile is not a test.** `verification` reports compile and simulation
  separately on purpose: passing one says nothing about the other.
- **Zero findings is not a clean bill of health.** A check that could not measure
  something records why in its `meta` (`unavailable`, `unknowns`,
  `fanout_unavailable_reason`). Read those before claiming a gate is closed.

## Manifest And New RTL

The plugin reads `<project>/.fpga-rtl.toml`; without it, it auto-discovers
design directories (any directory holding `*.sv`/`*.v`, plus `RTL*`), skipping
`.git`, `.Xil`, `.workbuddy`, `build`, `Tb`/`sim` and any `_`-prefixed or
`tmp`/`dbg`/`scratch` directory. When RTL is added:

- New directory of RTL → it appears as a design on the next `fpga_list_designs`
  (or write it into the manifest with `fpga_suggest_config` output as a guide).
- New testbench → it is picked up from `Tb/*.sv` and `Tb/*.v` automatically.
- Retargeted top module → pass `--top`, or set `top = "..."` in the manifest.
- Changed device, clock or budget → update `[ledger]` so `feasibility` compares
  against the real numbers instead of the defaults.

State assumptions explicitly when a value is missing. Do not invent a frequency,
a device limit or a board constraint.

## Reporting A Result

Report, in this order: what was analysed (design, top, revision), which gate was
addressed, the finding(s) fixed with file and line, the evidence that the fix
works (command, exit code, verdict, cycles, log path), and what remains
unverified. Say plainly which gates you did not run.

Never claim a board-level result, an Fmax, a resource total or a "verified"
status from this plugin's output alone.
