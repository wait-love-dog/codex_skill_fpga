---
name: vivado-auto-sim
description: 自动将 Verilog RTL + testbench 工程转化为 Vivado 行为级仿真。当用户需要在 Vivado 中跑仿真、建立 Vivado 仿真工程、将 iverilog/Modelsim 项目迁移到 Vivado XSIM、或遇到 Vivado 仿真编译错误（include 找不到、顶层设错、$readmemh 加载失败）时使用。核心能力：自动扫描 .v 文件、检测 include 路径和数据文件、生成一键 TCL + 批处理启动器。
---

# Vivado 自动化仿真

将任意 Verilog 工程（RTL + testbench）一键转化为 Vivado 行为级仿真工程，自动处理 include 路径、$readmemh 数据文件、仿真顶层设置等常见坑。

## 快速开始

```bash
python <skill_dir>/scripts/gen_vivado_project.py <工程根目录>
```

脚本自动完成：
1. 递归扫描所有 `.v`/`.sv` 文件，区分 RTL 和 testbench
2. 检测 `` `include `` 头文件，自动设置 `include_dirs`（sources_1 + sim_1）
3. 检测 `$readmemh`/`$readmemb` 数据文件，自动拷贝到 xsim 工作目录
4. 从 testbench 提取顶层模块名，设置为仿真顶层
5. 生成 `vivado_sim.tcl` + `launch_vivado_sim.bat`（纯 ASCII，无编码问题）

然后双击 `launch_vivado_sim.bat`，或在 Vivado 中 `Tools → Run Tcl Script` 选择 `vivado_sim.tcl`，最后点 **Run Simulation → Run Behavioral Simulation**。

## 常用参数

```bash
python gen_vivado_project.py <工程目录> \
  --tb tb/my_tb.v          # 指定 testbench（默认自动选 tb/ 目录下第一个）
  --part xc7a100tcsg324-1  # FPGA 型号
  --runtime 10ms           # 仿真运行时间
  --vivado "D:\Xilinx\Vivado\2019.1\bin\vivado.bat"  # vivado.bat 路径
```

## 关键约束（踩坑总结）

1. **testbench 必须在 `tb/` 目录下或文件名含 `_tb`**，否则会被当成 RTL。
2. **批处理文件只用英文**——含中文的 .bat 在 cmd 中会乱码导致命令失效。
3. **include_dirs 必须同时设 sources_1 和 sim_1**，只设一个会导致另一个 fileset 编译失败。
4. **$readmemh 的数据文件必须在 xsim 工作目录**：`<工程>/<项目名>.sim/sim_1/behav/xsim/`，脚本自动处理。
5. **仿真顶层必须是 testbench 模块名**，不能是 RTL 顶层（否则 clk 是高阻 Z，无任何输出）。

## 排错

遇到编译错误或仿真异常时，读取 `references/troubleshooting.md`，覆盖 8 类常见问题：
- include 文件找不到
- 仿真顶层设错（clk=Z）
- $readmemh 加载失败
- 批处理中文乱码
- set_property 不生效的兜底方案
- 仿真时间不够
- xvlog 连锁错误

## 文件结构

```
vivado-auto-sim/
├── SKILL.md                          # 本文件
├── scripts/
│   └── gen_vivado_project.py         # 核心：扫描工程 + 生成 TCL + 批处理
└── references/
    └── troubleshooting.md            # 常见错误与修复
```
