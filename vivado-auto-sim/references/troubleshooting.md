# Vivado 仿真常见错误与修复

## 1. `cannot open include file 'defines.v'`

**原因**: testbench 或 RTL 用了 `` `include "xxx.v" ``，但 Vivado 的 include_dirs 没设对。

**修复**:
- TCL 中确保同时设置两个 fileset:
  ```tcl
  set_property include_dirs "C:/path/to/rtl/core" [get_filesets sources_1]
  set_property include_dirs "C:/path/to/rtl/core" [get_filesets sim_1]
  ```
- 如果 `set_property` 不生效（Vivado 偶发 bug），兜底方案：把 defines.v 拷贝到 testbench 同目录:
  ```bash
  copy rtl\core\defines.v vivado_proj\auto_sim.srcs\sim_1\imports\tb\
  ```

## 2. 仿真跑了但没有任何输出，clk 是 Z（高阻）

**原因**: 仿真顶层设成了 RTL 顶层（如 tinyriscv_soc_top）而不是 testbench。没有 testbench 驱动时钟。

**修复**:
```tcl
set_property top <testbench模块名> [get_filesets sim_1]
launch_simulation
```
在 GUI 中: Flow Navigator → Simulation Settings → General → Top module name 填入 testbench 模块名。

## 3. `$readmemh` 加载失败 / 指令全是 0 / 仿真超时

**原因**: testbench 用 `$readmemh("inst.data", ...)` 加载程序，但 inst.data 不在 xsim 工作目录。

**xsim 工作目录**: `<工程目录>/<工程名>.sim/sim_1/behav/xsim/`

**修复**: 在 TCL 中 launch_simulation 之前拷贝:
```tcl
set xsim_dir "<工程目录>/<工程名>.sim/sim_1/behav/xsim"
file mkdir $xsim_dir
file copy -force "C:/path/to/inst.data" "$xsim_dir/inst.data"
```

## 4. `launch_simulation` 编译失败但错误信息不完整

查看完整日志:
```
<工程目录>/<工程名>.sim/sim_1/behav/xsim/xvlog.log
```

## 5. 批处理文件中文乱码 / 命令无法识别

**原因**: .bat 文件含中文，保存为 UTF-8 无 BOM，cmd.exe 按 GBK 解析导致乱码。

**修复**: .bat 文件只用英文/ASCII 字符。用 `chcp 65001` 也不可靠（命令本身会被乱码）。

## 6. `set_property include_dirs` 设置后不生效

Vivado 2019.1 偶发问题。按顺序执行:
1. `set_property include_dirs "..." [get_filesets sim_1]`
2. `update_compile_order -fileset sim_1`
3. 关闭当前仿真（如果开着）
4. `launch_simulation`

如果仍不生效，用兜底方案（第 1 条的拷贝 defines.v）。

## 7. 仿真运行时间不够，testbench 的 $finish 没触发

在 TCL 中设置足够长的运行时间:
```tcl
set_property -name {xsim.simulate.runtime} -value {10ms} -objects [get_filesets sim_1]
```
或在 xsim 控制台输入 `run all`（跑到 $finish 自动停）。

## 8. `xvlog` 报 `dynamic range is not allowed in net declaration`

通常是 include 失败的连锁反应（宏未定义导致 `wire[\`RegBus]` 变成 `wire[0:0]` 之类）。修好 include 路径后自动消失。
