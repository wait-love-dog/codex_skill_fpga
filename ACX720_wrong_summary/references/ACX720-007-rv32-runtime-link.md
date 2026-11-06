# ACX720-007：定点程序新增 64 位除法后的运行库链接

## 现象和范围

2026-11-02，RV32IM 定点 FFT 固件使用 64 位中间结果做除法。freestanding 构建必须处理编译器生成的运行库调用；加入 `-lgcc` 后又报告找不到 archive。

实际搜索可找到匹配 `rv32im/ilp32/libgcc.a`，编译器的 print-libgcc-file-name 也指向它。因此不能把该错误直接解释为未安装 libgcc，更不能改用另一个 ABI 的 archive。

## 处理

- 保持 `-march=rv32im -mabi=ilp32`，将该架构目录下的 archive 复制进 ASCII 构建目录，以显式文件名链接。
- ELF 符号表确认只有所需整数运行库例程，不引入浮点依赖；检查 text、rodata、bss 和栈预留。
- 软件启动明确清零 BSS，不能依赖上次软复位留下的算法状态。
- 使用固定测试向量，对比本机同一份 C 与实际 RV32 返回的字段和完整 FFT 指纹，不能只以链接成功作为验收。

本次 8 组实际 RV32 回放通过，字段/FFT 指纹与本机 C 完全一致。库搜索/路径解析的具体内部原因未进一步拆分，不推广为所有 GCC 版本都不支持中文路径。

原工程证据：`video/tools/build_d6.py`、`video/sw/link_d6.ld`、`video/sw/start_d6.S`、`video/evidence/d6_cpu_20261102/firmware_build.json`、`video/evidence/d6_cpu_20261102/board_verification.json`。
