# ACX720-014：Vivado 2019.1 脚本路径损坏导致仿真/报告失败

- 日期/状态：2026-11-07，构建与报告生成已修复；属于工具环境问题，不是 RTL 逻辑修复。
- 环境：Windows，Vivado 2019.1，XSIM scripts-only 和布局布线后 Tcl 报告。
- 现象：隐藏目录下的仿真生成脚本丢失路径中的 `.codex` 片段，生成的命令无法找到输入；将带中文的工程绝对路径写入批处理 Tcl 报告文件名后，Vivado 按错误编码解释，输出路径乱码而失败。两类路径现象分别保存失败日志，不能推断所有 Vivado 版本都不支持中文。
- 测量：保持 RTL 和约束相同，将输入与输出改成短的非隐藏 ASCII 临时目录。XSIM 行协议测试和生产顶层测试均运行通过；CDC 与 flag→SLWR 报告生成成功。
- 修复：PowerShell/Python 先将生产输入复制到短 ASCII 目录；Tcl 的 build/report 路径都使用 ASCII，完成后由主机文件 API 把报告复制回工程。Python 文本读写显式 UTF-8，不能依赖 Windows 默认 GBK。
- 失败尝试：只把构建输入移出中文路径、却仍把报告输出写回中文绝对路径，报告阶段仍失败。不能仅修正输入目录。
- 验证：独立行协议 XSIM PASS，生产顶层 XSIM PASS，Vivado 布局布线与 bitgen 完成；报告能读出 F13 的资源、WNS/WHS 和 +4.723 ns 的 FX2 外部路径余量。后续 JTAG 版本读回与实板 USB 图像已通过。
- 证据：`fall_detection/tools/verify_usb_rtl.py`、`tools/build_fpga.py`、`tools/fx2_postroute_ascii.tcl`、`evidence/fx2/cdc.rpt`、`flag_to_write.rpt`；原失败的仿真与 Tcl 日志保留在各自运行目录。
- 限制/复用：遇到“找不到文件”、编码或路径乱码时先查看实际生成的 xsim/vivado 命令与 Tcl 字符串。路径修复不等于功能、CDC 或时序通过；这些必须保留独立证据。
