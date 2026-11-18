# 编译失败排查

路径均相对：`build\<工程>_builddir\`。

## 先定位失败步骤

1. 看控制台最后 **Error** / `make ... Error 1` 出现在哪个目标（`resource_main`、`app_main`、`link`…）。
2. 打开同名日志：`log\<模块>.log` **末尾 80～150 行**。
3. 对照 `log\time_consuming.log` 确认本次是否跑过该模块（避免看旧日志）。
4. 缺文件类再查 `tmp\error.log`（可能残留历史记录，需结合时间戳）。

## 日志地图

| 现象 | 先看 |
|------|------|
| 资源 / `mmi_res_*.bin` 缺失或 0 字节 / PAC 缺资源 | `log\resource_main.log` |
| C/汇编编译错误 | `log\<模块>.log`（如 `app_main.log`、`custom_drv.log`） |
| 链接失败、缺符号、section 警告 | `log\link.log`；辅以根下 `*_feedback.txt` |
| 哪步卡住/很慢 | `log\time_consuming.log` |
| 警告汇总 | `tmp\warning.log` |
| fromelf / 版本 | `log\fromelf.log`、`log\version.log` |

若仓库有 `.cursor/context/critical-logs.md`，以其工程名示例为准，规则相同。

## 资源失败（最高频）

`resource_main.log` 关键字：

| 关键字 | 含义 |
|--------|------|
| `Generate resource bin successful!` | 资源 bin 已生成 |
| `Generate resource file failed` | resgen 失败 |
| `ResCmd.exe` / `run...` | 进入 ResView 打包 |
| 随后「系统找不到指定的文件」 | 多为 bin 未生成，makefile `copy` 失败 |

处理顺序：

1. 确认 `img\mmi_res_*.bin` 是否存在且非 0 字节。  
2. **不要**拿 `lib\modem\...\mmi_res_*.bin` 当产物（常是占位）。  
3. 编资源前关掉残留 `EXCEL.EXE`（`str_table.xls`）。  
4. **客户 bat 仓**确认产品 bat 已拷 `Prj_mk\...\str_table.xls`、`CustomImages`、铃音目录。  
5. 重跑：`bat 3` 或 `make.bat p=<工程> m=resource_main`。

## 编译 / 链接常见类

| 症状 | 方向 |
|------|------|
| 头文件找不到 / 宏未定义 | 是否跑错工程；客户 bat 仓是否跳过产品 bat 导致未拷 `hx_cust_config.h`；USER_DEBUG.mk 是否与预期一致 |
| 库路径 / unresolved external（modem、BT 基库） | USER 与 DEBUG 工程/库混用；对照 `Prj_mk\USER_DEBUG.mk` 或 `MODEM_BIN_FILE`、`lib\` 下目录名 |
| `L6312W` / `L6314W` / 镜像过大 / DL1138（超分区） | `link.log` + 跑 `scripts/partition_check.py`；资源过大查 `MMI_RES_SECTOR_NUM`，流程见 [PARTITION.md](PARTITION.md) |
| `sprd_macro` 检查失败 | `make/perl_script/sprd_macro_check.pl` ↔ `lib\...\sprd_macro.txt` |
| PAC 未生成但前面模块 OK | 查 `image` / 打包步骤与 `img\`；bat 可能打印 `Not_find_PAC_file!` |

## USER / DEBUG 混用排查

1. 读当前 `Prj_mk\USER_DEBUG.mk`（客户 bat 仓）或确认 `p=` 工程名后缀（补丁仓 / 平台仓）。  
2. `MODEM_BIN_FILE` / `PRODUCT_BASELIB_DIR` 是否指向存在的 `lib\` 子目录。  
3. 从 DEBUG 切 USER（或反向）后做一次 `new`，不要只编 `app_main`。

## 环境类

| 症状 | 方向 |
|------|------|
| `armcc` / 许可证错误 | RVCT 安装与 `LM_LICENSE_FILE` |
| Perl / ResCmd 起不来 | 工具链 PATH；杀毒拦截；Excel 占用 xls |
| 并行偶发失败 | 降 `-j` / `job=` 重试同一步 |
| PowerShell 下 make 怪错 | 改用 `cmd /c "make.bat ..."` |

## Agent 汇报模板

失败时按此结构回复（简短）：

1. 工程 / USER|DEBUG / 失败目标  
2. 日志文件路径 + 末尾关键 1～3 行原文  
3. 根因判断（一句话）  
4. 建议下一命令（一条即可）
