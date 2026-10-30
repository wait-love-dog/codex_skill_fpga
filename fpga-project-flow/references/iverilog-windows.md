# Icarus Verilog On Windows

Use Icarus Verilog as a quick, reproducible RTL compile and simulation loop. Run the command from a deliberate working directory and keep generated `.vvp`, logs, and waveforms outside the source directories.

## Locate And Invoke The Tool

For SystemVerilog, use `-g2012`. Discover `iverilog.exe` and `vvp.exe` from `PATH` or a user-provided installation path; do not hard-code a machine-specific location into project sources. A typical PowerShell flow is:

```powershell
$projectRoot = (Get-Location).Path
$buildDir = Join-Path $projectRoot 'build\sim'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

Push-Location $projectRoot
& iverilog -g2012 -I (Join-Path $projectRoot 'RTL') -s tb_top `
  -o (Join-Path $buildDir 'tb_top.vvp') Tb\tb_top.sv RTL\*.sv
& vvp (Join-Path $buildDir 'tb_top.vvp')
$runExit = $LASTEXITCODE
Pop-Location
exit $runExit
```

Adapt source directories, include directories, and top names to the project. A source list or manifest is more reliable than a wildcard when compile order or duplicate modules are possible.

## Preserve The Runtime Context

Two path rules cause many false results:

- `include` resolution depends on the current working directory and `-I` include directories. Compile from the project root or pass all required `-I` paths explicitly.
- `$readmemh` and `$readmemb` filenames are normally resolved relative to the `vvp` process working directory, not the source file. Run `vvp` from the directory expected by the test or use a deliberate, documented path.

Record the top module, test program, macro definitions, runtime working directory, and simulation duration with each test result. In imported vendor GUI projects, also confirm that the project snapshot contains the current RTL and test data rather than an older copied source.

## Compile The Right Things

Compile the production/DUT top separately from the testbench top when interfaces or generated wrappers are changing. A testbench can compile even while a production module is uninstantiated, has a port mismatch, or has a duplicate-module issue elsewhere in the source set.

When a multi-file compile reports an early parser failure, compile suspect files independently to isolate the first real error:

```powershell
& iverilog -g2012 -I . -tnull RTL\suspect.sv
```

An undefined Verilog macro may expand to empty text and create misleading downstream syntax errors. Check macro definitions and include paths before repairing every later diagnostic.

## Interpret Diagnostics Correctly

- `syntax error`, malformed statements, unresolved modules, missing includes, and a nonzero exit code are failures.
- A `sorry:` message can indicate an Icarus implementation limitation. Do not classify it as harmless merely by wording; verify that compilation succeeded and decide whether the affected construct needs a second simulator.
- Treat warnings about ignored `unique`/`priority` intent as a reason to test full case coverage and defaults. The tool may not enforce the intended runtime check.
- A successful compile only proves elaboration of the selected top and source set. Require explicit testbench assertions or completion criteria to claim functional success.

## Cover Simulator Differences

Icarus and vendor simulators may differ in support and exceptional arithmetic behavior. Check the delivery simulator for constructs central to correctness, particularly package/interface features, memory initialization, and division or remainder corner cases. Guard divide-by-zero and signed overflow cases so illegal operands do not execute an arithmetic operator before the RTL selects the architecture-defined result.

For a failing vendor GUI simulation, first verify configuration: top module, source snapshot, macro/test-program selection, memory-file path, and total run time. Do not diagnose the RTL from a result produced with stale source or an incomplete simulation run.

## Keep Verification Meaningful

Use testbench-visible interfaces for functional checks when practical. Hierarchical references can aid debug but may hide a missing production port and are not part of synthesizable hardware. Cover reset release, invalid/unknown propagation where relevant, handshakes under random stalls, boundary arithmetic, and completion/timeout behavior. Preserve the failing seed, logs, waveforms, and exact command so the result can be reproduced.
