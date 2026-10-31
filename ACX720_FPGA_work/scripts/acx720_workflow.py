#!/usr/bin/env python3
"""ACX720 helpers: verified pin lookup, isolated XSIM and Vivado builds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_PART = 'xc7a100tfgg484-2'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def tcl(value):
    value = value.as_posix() if isinstance(value, Path) else str(value)
    if '\n' in value or '\r' in value:
        raise ValueError('Newlines are not allowed in Tcl argument values')
    for char in ['\\', '$', '[', ']', '"']:
        value = value.replace(char, '\\' + char)
    return '"' + value + '"'

def tcl_list(values):
    return '[list ' + ' '.join(tcl(v) for v in values) + ']'

def vivado_path(explicit=None):
    options = [explicit, os.environ.get('ACX720_VIVADO'), shutil.which('vivado')]
    for option in options:
        if option and Path(option).is_file():
            return Path(option).resolve()
    raise ValueError('Vivado not found; pass --vivado or set ACX720_VIVADO')

def pin_command(args):
    board = json.loads((SKILL/'assets/board.json').read_text(encoding='utf-8'))
    pins = board['pins']
    if args.signal:
        if args.signal not in pins:
            raise ValueError('Unknown board signal: '+args.signal)
        print(json.dumps(pins[args.signal], ensure_ascii=False, indent=2))
        return
    if not args.mapping:
        print('\n'.join(pins))
        return
    mapping = json.loads(Path(args.mapping).read_text(encoding='utf-8'))
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Pin map must be a nonempty JSON object: RTL port -> board signal')
    lines = ['# ACX720-V3: explicitly selected, cross-checked pins only.']
    used = {}
    for port, signal in mapping.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?', port):
            raise ValueError('Unsupported RTL port spelling: '+port)
        pin = pins.get(signal)
        if not pin or not pin.get('verified_for_xdc'):
            raise ValueError('Signal needs schematic/vendor-XDC review: '+str(signal))
        ball = pin['pin']
        if ball in used:
            raise ValueError(f'Duplicate package pin {ball}: {used[ball]} and {port}')
        used[ball] = port
        lines.append(f'set_property -dict {{PACKAGE_PIN {ball} IOSTANDARD {pin["iostandard"]}}} [get_ports {{{port}}}]')
        if signal == 'FPGA_GCLK1':
            lines.append(f'create_clock -name clk50 -period 20.000 [get_ports {{{port}}}]')
    content = '\n'.join(lines)+'\n'
    if args.output:
        output = Path(args.output)
        if output.exists():
            raise ValueError('Output already exists; select a new XDC path')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding='utf-8')
    else:
        for target, path in data_files.items():
            lines += ['set synthdir [get_property DIRECTORY [get_runs synth_1]]',
                      f'file mkdir [file dirname [file join $synthdir {tcl(target)}]]',
                      f'file copy -force {tcl(stage(path))} [file join $synthdir {tcl(target)}]']
        print(content)

def prepare(args):
    manifest = Path(args.manifest).resolve()
    cfg = json.loads(manifest.read_text(encoding='utf-8'))
    root = (manifest.parent / cfg.get('project_root', '.')).resolve()
    out = Path(args.out).resolve()
    if not str(out).isascii():
        raise ValueError('--out must be an ASCII path; the source root may contain Chinese/spaces')
    if out.exists():
        raise ValueError('Build directory already exists; use a fresh --out to preserve evidence')
    top = cfg.get('top', '')
    tb = cfg.get('tb_top', '')
    part = cfg.get('part', DEFAULT_PART)
    for value in [top] + ([tb] if args.command == 'simulate' else []):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', value):
            raise ValueError('Set an explicit top and (for simulation) tb_top module name')
    if not re.fullmatch(r'xc7a(?:35|100|200)t[a-z0-9]+-[123]', part):
        raise ValueError('Confirm the full ACX720 Artix-7 part, package and speed grade')
    runtime = cfg.get('runtime', '10us')
    if not re.fullmatch(r'\d+(?:\.\d+)?(?:fs|ps|ns|us|ms|s)', runtime):
        raise ValueError('runtime must include a time unit, for example 10us')
    if not cfg.get('sources'):
        raise ValueError('sources must explicitly list the current production RTL')
    if args.command == 'simulate' and not cfg.get('tb_sources'):
        raise ValueError('tb_sources must explicitly list the selected testbench')
    if args.command == 'build' and not cfg.get('xdc'):
        raise ValueError('A hardware build requires explicit board/timing XDC files')

    files = set()
    def source(value):
        path = (root / value).resolve()
        try:
            rel = path.relative_to(root)
        except ValueError:
            raise ValueError('Input outside project_root; choose the common project root: '+str(path))
        if not path.is_file():
            raise ValueError('Missing input: '+str(path))
        if not str(rel).isascii():
            raise ValueError('Use ASCII paths below project_root when staging vendor tools: '+str(rel))
        files.add(path)
        return path

    sources = [source(p) for p in cfg['sources']]
    benches = [source(p) for p in cfg.get('tb_sources', [])]
    xdcs = [source(p) for p in cfg.get('xdc', [])]
    hooks = [source(cfg['pre_place_tcl'])] if cfg.get('pre_place_tcl') else []
    for path in sources + benches:
        if path.suffix.lower() not in ['.v', '.sv']:
            raise ValueError('Helper supports plain Verilog/SystemVerilog; preserve XPR/XCI IP flows separately')
    include_dirs = [(root/p).resolve() for p in cfg.get('include_dirs', [])]
    for directory in include_dirs:
        if not directory.is_dir() or not directory.is_relative_to(root):
            raise ValueError('Invalid project include directory: '+str(directory))
    for header in cfg.get('headers', []):
        source(header)
    pending = list(sources+benches+list(files))
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen or path.suffix.lower() not in ['.v', '.sv', '.vh', '.svh']:
            continue
        seen.add(path)
        text = path.read_text(encoding='utf-8', errors='replace')
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
        for name in re.findall(r'`include\s+"([^"\r\n]+)"', text):
            matches = [d/name for d in [path.parent]+include_dirs+[root] if (d/name).is_file()]
            if not matches:
                raise ValueError(f'Unresolved include {name} from {path}; set include_dirs/headers')
            pending.append(source(matches[0]))
    data_files = {}
    for target, original in cfg.get('data_files', {}).items():
        target_path = Path(target)
        if target_path.is_absolute() or '..' in target_path.parts or not target.isascii():
            raise ValueError('data_files destinations must be safe ASCII paths relative to XSIM cwd')
        data_files[target] = source(original)

    out.mkdir(parents=True)
    staged = out/'inputs'
    for path in files:
        target = staged/path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    def stage(path):
        return staged/path.relative_to(root)
    includes = [staged] + [stage(d) for d in include_dirs] + sorted({stage(p).parent for p in files})
    definitions = []
    for key, value in cfg.get('defines', {}).items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ValueError('Invalid Verilog macro name: '+key)
        definitions.append(key if value is None else f'{key}={value}')
    lines = [f'create_project acx720_work {tcl(out/"project")} -part {tcl(part)}',
             'set_property target_language Verilog [current_project]',
             'puts "ACX720_TOOL_VERSION=[version -short]"',
             f'add_files -norecurse -fileset sources_1 {tcl_list(stage(p) for p in sources)}',
             f'set_property top {tcl(top)} [get_filesets sources_1]']
    for fileset in ['sources_1', 'sim_1']:
        lines += [f'set_property include_dirs {tcl_list(includes)} [get_filesets {fileset}]',
                  f'set_property verilog_define {tcl_list(definitions)} [get_filesets {fileset}]']
    for xdc in xdcs:
        lines.append(f'add_files -norecurse -fileset constrs_1 {tcl(stage(xdc))}')
    lines.append('update_compile_order -fileset sources_1')
    if args.command == 'simulate':
        lines += [f'add_files -norecurse -fileset sim_1 {tcl_list(stage(p) for p in benches)}',
                  f'set_property top {tcl(tb)} [get_filesets sim_1]',
                  f'set_property xsim.simulate.runtime {tcl(runtime)} [get_filesets sim_1]',
                  'set_property -dict [list xsim.elaborate.xelab.more_options {-timescale 1ns/1ps}] [get_filesets sim_1]',
                  'update_compile_order -fileset sim_1',
                  'launch_simulation -simset sim_1 -mode behavioral -scripts_only',
                  f'set simdir {tcl(out/"project/acx720_work.sim/sim_1/behav/xsim")}',
                  'file mkdir $simdir']
        for target, path in data_files.items():
            lines += [f'file mkdir [file dirname [file join $simdir {tcl(target)}]]',
                      f'file copy -force {tcl(stage(path))} [file join $simdir {tcl(target)}]']
        lines += ['launch_simulation -simset sim_1 -mode behavioral',
                  'close_sim', 'puts "ACX720_SIM_TOOL_DONE"']
    else:
        if hooks:
            lines.append(f'set_property STEPS.PLACE_DESIGN.TCL.PRE {tcl(stage(hooks[0]))} [get_runs impl_1]')
        lines += ['launch_runs synth_1 -jobs 4', 'wait_on_run synth_1',
                  'if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} { error "Synthesis failed" }',
                  'launch_runs impl_1 -to_step write_bitstream -jobs 4', 'wait_on_run impl_1',
                  'if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} { error "Implementation failed" }',
                  'open_run impl_1',
                  f'report_timing_summary -report_unconstrained -file {tcl(out/"timing.rpt")}',
                  f'report_utilization -file {tcl(out/"utilization.rpt")}',
                  f'report_drc -file {tcl(out/"drc.rpt")}',
                  'set setup_paths [get_timing_paths -delay_type max -max_paths 1]',
                  'set hold_paths [get_timing_paths -delay_type min -max_paths 1]',
                  'if {![llength $setup_paths] || ![llength $hold_paths]} { error "No constrained timing paths; review clock constraints" }',
                  'set wns [get_property SLACK $setup_paths]', 'set whs [get_property SLACK $hold_paths]',
                  'puts "ACX720_TIMING WNS=$wns WHS=$whs"',
                  'if {$wns < 0 || $whs < 0} { error "Timing failed; do not deliver/program this image" }',
                  f'file copy [file join [get_property DIRECTORY [get_runs impl_1]] {tcl(top+".bit")}] {tcl(out/"design.bit")}',
                  'puts "ACX720_BUILD_DONE"']
    script = out/'workflow.tcl'
    script.write_text('if {[catch {\n'+'\n'.join(lines)+'\n} message options]} {\nputs stderr $message\nputs stderr [dict get $options -errorinfo]\nexit 1\n}\nexit 0\n', encoding='utf-8')
    receipt = {'mode':args.command, 'part':part, 'top':top, 'tb_top':tb,
               'manifest':str(manifest), 'manifest_sha256':digest(manifest),
               'input_sha256':{str(p.relative_to(root)):digest(p) for p in sorted(files)},
               'required_pass':cfg.get('required_pass'), 'runtime':runtime,
               'root':str(root), 'output':str(out)}
    write_json(out/'inputs.json', receipt)
    return out, script, receipt

def execute(args):
    executable = vivado_path(args.vivado)
    out, script, receipt = prepare(args)
    command = [str(executable), '-mode', 'batch', '-nojournal', '-nolog', '-source', str(script)]
    receipt['command'] = command
    started = time.monotonic()
    print('STAGED', out, flush=True)
    with (out/'vivado.log').open('w', encoding='utf-8') as log:
        proc = subprocess.Popen(command, cwd=out, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
            else:
                proc.kill()
            receipt.update(verdict='TIMEOUT', seconds=time.monotonic()-started)
            write_json(out/'result.json', receipt)
            return 1
    main_log = (out/'vivado.log').read_text(encoding='utf-8', errors='replace')
    simulation_logs = [p for p in out.rglob('*.log') if p.name.lower() in ['simulate.log','xsim.log']]
    sim_text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in simulation_logs) or main_log
    fatal = bool(re.search(r'^\s*(?:Fatal:|FATAL:|FAIL(?:\s|:)|ERROR:)', sim_text, re.M))
    if args.command == 'simulate':
        token = receipt['required_pass']
        passed = bool(token and any(line.strip().startswith(token) for line in sim_text.splitlines()))
        okay = code == 0 and not fatal and passed and 'ACX720_SIM_TOOL_DONE' in main_log.splitlines()
        receipt['simulation_logs'] = [str(p.relative_to(out)) for p in simulation_logs]
        receipt['pass_marker_found'] = passed
    else:
        okay = code == 0 and 'ACX720_BUILD_DONE' in main_log.splitlines() and (out/'design.bit').is_file()
    receipt.update(verdict='PASS' if okay else 'FAIL', tool_exit_code=code,
                   seconds=round(time.monotonic()-started,3))
    write_json(out/'result.json', receipt)
    print(json.dumps({k:receipt[k] for k in ['mode','verdict','tool_exit_code','seconds','output']},indent=2))
    if not okay:
        print('\n'.join(main_log.splitlines()[-18:]))
    return 0 if okay else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor')
    doctor.add_argument('--vivado')
    pins = commands.add_parser('pins')
    pins.add_argument('--signal')
    pins.add_argument('--map', dest='mapping')
    pins.add_argument('--output')
    for mode in ['simulate','build']:
        sub = commands.add_parser(mode)
        sub.add_argument('--manifest', required=True)
        sub.add_argument('--out', required=True)
        sub.add_argument('--vivado')
        sub.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            exe = vivado_path(args.vivado)
            print(json.dumps({'vivado':str(exe),'default_part':DEFAULT_PART,
                              'tools':{n:(exe.parent/(n+'.bat')).exists() for n in ['xvlog','xelab','xsim']},
                              'license_checked':False},indent=2))
            return 0
        if args.command == 'pins':
            pin_command(args)
            return 0
        return execute(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print('ERROR:', error, file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
