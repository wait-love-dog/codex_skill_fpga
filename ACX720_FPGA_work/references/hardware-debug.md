# 实板定位与 JTAG/ILA

## 先区分三种“通过”

| 证据 | 能证明什么 | 不能直接推出什么 |
|---|---|---|
| 仿真 PASS | 该源集合/模型/激励下的行为 | 实装开关、电源、布线、实际位流和外设正确 |
| PROGRAM_OK、DONE=1 | 配置下载完成 | CPU 正在执行、像素正在更新 |
| ILA、UART、计数器、用户观察 | 对应测点与条件下的实板行为 | 未测到的路径、其他工作状态全部正确 |

先记录 raw switch、时钟 LOCKED、每个时钟域的 reset/run、PC/状态机、事务计数。然后逐层追请求→译码/握手→存储写使能/地址/数据→读口与最终外设时序。

例：一个 CPU/TFT 示例出现渐变却没有动画。只仿真 CPU 并将视频读值接常量，无法覆盖板级复位接线。修正端口复位极性后，ILA 又发现默认 raw SW=`111` 被高有效 SW0 复位逻辑一直保持复位。反转项目开关含义后，实板 PC、LED、白色像素写入均恢复，最终确认动画恢复。结论来自分层证据，不是因为“LED 不亮所以一定 CPU 坏了”。

## 编程范围与核对

当前请求包含“直接烧入”“上板调试”时可继续 JTAG；已有授权无需重复请求。单纯创建 skill、读资料或仿真不授权编程。SRAM JTAG 下载掉电丢失；写 QSPI cfgmem 是另一个动作，需用户有固化/掉电保存意图。

用 Vivado 本机 hardware server，核对唯一匹配的目标及器件，再设置明确的 bit 文件；核对哈希，禁止“目录下最新 bit”猜选。多个板子/器件或不匹配时不要写入。

2019.1 可先 `load_features labtools`，再判断当前版本提供 `open_hw_manager` 还是 `open_hw`，关闭接口同理。编程之后 refresh，读取实际属性列表中 DONE/INIT/CRC 状态。2019.1 观测到的 DONE 名称是：

- `REGISTER.CONFIG_STATUS.BIT13_DONE_INTERNAL_SIGNAL_STATUS`
- `REGISTER.CONFIG_STATUS.BIT14_DONE_PIN`

不要假定缩写 `BIT13_DONE` 一定存在。记录目标、bit SHA256、工具退出码和原始日志。不要在最终答案暴露无关本机信息。

## 加 ILA 时的易错点

优先复用可证明版本的综合网表，或在 RTL 中加入少量有目的的计数器。新增调试逻辑应有明确测点目的，不能为了调试重写原架构。

- 从综合网表查询真实 net 名；常量位/别名可能被优化掉。记录每个 probe 的 LSB→MSB 对应关系。比如 `pc_id[31:1]` 的 CSV 数值需要补回最低位，不能直接当完整 PC。
- 时钟用持续运行的 BUFG 输出；debug hub 与 ILA 各用合适时钟。复位期间 CPU 核虽不执行，CPU 时钟未必停止，适合观测复位状态；若连时钟本身都不确定，可用板载 50 MHz 域先观测。
- 打开 DCP 后显式核对/重读 XDC，不要生成没有 IOSTANDARD/LOC 或没有 generated clocks 的调试镜像。
- 插入 ILA 会改变布局和负载，重新检查布线后时序/资源/DRC；保存对应 `.bit + .ltx`，不要混用旧 probes 文件。
- 先 immediate trigger 抓稳定状态；再以真正的 `write_enable && data==目标值` 触发，区分“最后的数据寄存器是白色”与“此刻发生了白色写入”。
- `wait_on_hw_ila -timeout` 的单位是分钟，允许小数；使用有限等待，例如 `0.1` 为约 6 秒，不能在模型不明时无限等触发。
- 2019.1 的某些固定 ILA 配置会让 `CONTROL.CAPTURE_MODE` 等属性只读。先读属性和硬件能力，不能反复写失败属性；关闭 storage qualification 的简单 ILA 可直接 immediate trigger。
- CSV 应保留原始文件，并汇总复位、时钟、PC、实际事务和地址范围。不能用截断/重排后的列丢掉位映射含义。

相关官方参考：

- [UG908 2019.1：综合网表插入调试核](https://docs.amd.com/api/khub/documents/w9gyY5_BkWsOxGXiWOrqFQ/content)
- [UG835：run_hw_ila](https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/run_hw_ila)
- [UG835：wait_on_hw_ila 参数](https://docs.amd.com/r/jNAIYEKDr3MtkPafPidAqQ/AHFcYOmzT~4_HwpDAqk1rQ)

## 其他接口的定位起点

- UART：确认是 CH340 口、实际 CPU 时钟/分频、波特率和帧格式；程序启动文本不能代替重复心跳。
- TFT：先已知彩条验证时序，再帧缓冲写入，再读口/DE/RGB；考虑同步 BRAM 读延迟与坐标/DE 对齐。不要把静止屏幕直接解释成 RAM 写口坏了。
- 摄像头：先 SCCB ACK、XCLK、PCLK/HREF/VS，再字节/像素拼接、位序、缓存和显示。JTAG 重配会影响 XCLK；断电恢复并不能独自证明具体相位根因。
- DDR3：先 MIG 校准与仿真模型/约束，再 BIST 和总线协议；不要把未校准的读取当算法错误。
- Ethernet/USB：先 PHY/FX2 状态和方向/电压、时钟/复位，再协议与吞吐；复用引脚必须明确仲裁。
