# Vivado：输入清单、仿真和实现

## 选择路线

- 普通 `.v/.sv + tb + hex/mem`：用随附 `scripts/acx720_workflow.py` 的 manifest 路线。
- 已有 XPR、XCI、MIG、Block Design、厂商加密模型：先保留工程，`open_project` 后检查 part/top/`report_ip_status`/编译顺序；按项目需求 `generate_target`、导出 IP 用户文件和仿真模型。不要把 XCI 当 Verilog 喂给通用脚本，也不要跨版本直接复用旧仿真库。
- 资料包附带 Vivado 2018.3，此工作流已在 2019.1 验证；这不等于所有旧 IP 都能无条件迁移。先诊断具体 IP，再决定升级或使用对应版本，不要首先安装一套庞大软件。

## 普通 RTL 的输入清单

在工程根目录放 `flow.json`（文件名不限）：

```json
{
  "part": "xc7a100tfgg484-2",
  "top": "board_top",
  "tb_top": "tb_board_top",
  "sources": ["rtl/board_top.v", "rtl/core.sv"],
  "tb_sources": ["tb/tb_board_top.sv"],
  "include_dirs": ["rtl", "rtl/include"],
  "headers": ["rtl/include/defines.vh"],
  "defines": {"PULP_FPGA_EMUL": null, "IMEM_FILE": "\"imem.hex\""},
  "data_files": {"imem.hex": "hex/cpu_imem.hex", "dmem.hex": "hex/cpu_dmem.hex"},
  "xdc": ["constraints/pins.xdc", "constraints/timing.xdc"],
  "pre_place_tcl": "constraints/pre_place.tcl",
  "runtime": "30ms",
  "required_pass": "PASS BOARD_TOP"
}
```

仅列实际需要的项。无 CPU 就去掉 CPU 宏和镜像；无布局前钩子就去掉 `pre_place_tcl`。`project_root` 可指定相对于 manifest 的工程根目录，默认是 manifest 所在目录。所有输入都在此根目录内；需要外部依赖时选择适当共同根目录或显式整理依赖。

- `top` 是生产顶层；`tb_top` 是 testbench **模块名**。多个候选时先检查实例关系，不能选第一个文件凑数。
- `sources` 不重复列被 include 的 `.v` 头文件，否则会出现重复模块/定义。`headers` 用于宏生成或非字面量 include 等自动发现不到的依赖。
- `data_files` 键是 XSIM **运行工作目录**下的目标路径，值是工程内的原始文件。脚本也复制到综合 run 目录，防止仿真镜像正确、综合镜像却缺失。
- `required_pass` 应是 testbench 在检查完成后打印的明确前缀；脚本不把 Vivado 正常退出当作仿真功能通过。
- 运行时间覆盖真正的功能事件。显示/CPU 常需毫秒；UART 需按波特率换算帧长。可参数化缩短 POR，但不能把无限等待藏成成功。
- 本脚本将中文/带空格的工程根目录映射到独立 ASCII 输出目录；其下的相对源码路径目前也要求 ASCII。若相对目录仍含中文，先在隔离副本中连同引用关系整理，不改用户原件。

```powershell
python <skill>/scripts/acx720_workflow.py simulate --manifest flow.json --out C:/Temp/acx720/sim001 --vivado <Vivado安装目录>/bin/vivado.bat --timeout 1200
python <skill>/scripts/acx720_workflow.py build --manifest flow.json --out C:/Temp/acx720/build001 --timeout 1200
```

`--out` 必须是新目录。优先短路径；Windows 长路径可能使老版 Vivado/IP 工具失败。无法写短路径时选择当前允许写入的 ASCII 根，不为路径便利绕过文件权限。

输出包括生成的 `workflow.tcl`、输入副本、`inputs.json`（hashes）、`vivado.log`、`result.json`；实现另含 `timing.rpt / utilization.rpt / drc.rpt / design.bit`。脚本不连接下载器。需要超时时只终止自己启动的进程树。

## 仿真检查

1. 给 clock、reset 和异步输入明确初值。仿真默认 SW/按键应复现真实上拉，不能默认为全 0。
2. 检查 reset 请求电平与子模块 `if (!rst_n)`/`if (Rst_p)` 的实际实现。时钟每个域分别释放复位；等待 PLL LOCKED。
3. testbench 必须比较功能结果、检查事务或使用断言，并带 `$fatal` 超时。`$finish` 本身不代表 PASS。
4. RAM 镜像检查文件打开、字节序、位宽、深度和入口偏移。哈佛 CPU 的数据常量不能只放 IMEM。先默认初始化再读镜像，或提供完整深度镜像，避免未初始化内容掩盖问题。
5. 用生产顶层覆盖顶层连线。外设 mock、CPU 单独仿真可以缩小问题，但不能代替生产顶层。
6. 保留 simulator 日志。XSIM 遇到 `$fatal` 时可能仍向外层返回 0；脚本同时检查实际仿真日志中的 FAIL/Fatal 和 PASS 标记。

对于独立 xvlog/xelab 路线：SystemVerilog 显式启用对应模式；按源目录设置 include；宏含引号时优先 Tcl fileset 属性或文件内定义，避免 PowerShell→bat→工具多层引用丢失。使用 MMCM/BUFG 时链接 `unisims_ver` 和 `glbl`；缺省 timescale 一致。工程路线由 Vivado 生成这些库/全局模块参数。

## 实现检查

- 综合和实现都核对当前 top/part/宏/镜像哈希；生产和测试源集合不要混入其他版本的同名模块。
- XDC 仅绑定当前顶层存在的端口，逐一对应物理信号。DDR3 电平、差分 IO、RGMII 的时序不能套普通 GPIO 的约束。
- 先确认 generated clocks、时钟交互和 CDC，再谈 WNS。打开独立综合 DCP 时，工程外部 XDC 可能未包含在内；必须重新读板级/时序 XDC。无时钟、无引脚的“很高正裕量”不构成通过。
- 不修改 `NSTD-1 / UCIO-1` 严重级别来强行生成位流；不把整设计端口或时钟域全部 false path 来隐藏失败。
- 构建脚本的 setup/hold 门槛只覆盖现有约束。查看未约束内部路径与 IO 时序范围，不能把 “All user specified timing constraints are met” 解释为板外接口已经完整验证。
- bit 生成成功仍要核对实际资源、时序、DRC 和输入版本。功能失败时，策略/seed sweep 不是第一步。

附带 `assets/smoke/flow.json` 是可运行的小型工具链自检：include、ROM 文件、默认高电平开关、低有效复位和真实生产顶层。它不是用户 CPU 的验证替代品。相邻 `flow_fail.json` 的预期结果是 FAIL，用来检查错误能被传播；不要当作板卡故障。
