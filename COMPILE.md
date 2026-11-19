# 编译

在 **CMD** 下执行（PowerShell 用 `cmd /c "..."`）。开编前须已确认：**仓型、编译根、工程名、USER|DEBUG**（仓型口径见 [REPO.md](REPO.md) §0；流程见 [SKILL.md](SKILL.md) A）。

**默认优先增量**：先根据改动文件判定模块再编；能单模块就不要全编。全编仅用于首编、切 USER↔DEBUG、改工程宏/大面积底层、或影响面确实说不清。

## 1. 按仓型 / 入口选命令

| 仓型 | 入口 | 编译变体怎么选 |
|------|------|----------------|
| **客户 bat 仓** | `<Product>.bat <%1> [<%2>]`（会 xcopy `Prj_mk`） | `%2`：`1`=USER，省略=DEBUG |
| **Prj_mk 补丁仓**（无 zxe） | `make.bat p=<工程> <目标> -j8 job=8` | 工程名带 `_USER` / `_DEBUG` |
| **Prj_mk 补丁仓**（有 zxe） | **`sprdbuildE.pl` + `Prj_mk\<工程>\<工程>.zxe`**（§1.1） | 菜单全编选 user/debug；写 `USER_DEBUG.mk` |
| **平台仓** | `make.bat` | 工程名带 `_USER` / `_DEBUG` |

- 客户 bat 仓改了 `Prj_mk\<工程>\` → **优先跑产品 bat**，不要只 `make`（会漏拷贝）。
- **有 `sprdbuildE.pl` + `*.zxe`** → **优先 zxe 入口**；裸 `make.bat p=<工程>` 与之**不等价**（缺拷贝）。
- 无 zxe 的补丁仓 / 平台仓 → 直接 `make.bat`。

### 1.1 zxe / sprdbuildE 入口（补丁仓常见）

**识别**：编译根有 `sprdbuildE.pl`，且存在 `Prj_mk\<工程>\<工程>.zxe`。  
**`.zxe` 不是可执行文件**，是工程配置（版本/BOM 键、资源目录键、驱动目录键、射频 NV 键、联合 PID 等；键名以仓内 zxe 为准，正文勿写死客户值）。

**推荐启动**（在 `Prj_mk\<工程>\` 下，CMD）：

```bat
cd /d <编译根>\Prj_mk\<工程>
..\..\make\make_cmd\perl.exe ..\..\sprdbuildE.pl <工程>.zxe
```

- 无额外参数 → 交互菜单（选模块 / `new` / `image` / 模拟器等）。
- 也可把 `<工程>.zxe` 拖到上述 perl 命令上；或在命令后追加目标（如 `m=app_main`），具体以仓内 `sprdbuildE.pl` 为准。

**脚本在 `make` 前会做的事（摘要）**：按 zxe 键把驱动（如 lcd/sensor）、MMI 资源（壁纸/开关机/主菜单/铃音/xls 等）、射频 NV、工程头等 **xcopy/copy 进树内**，再执行：

```bat
make.bat p=<工程> <目标>
```

| 对比 | sprdbuildE + zxe | 裸 `make.bat p=<工程>` |
|------|------------------|------------------------|
| 按 zxe 拷资源/驱动/NV/头 | 会 | 不会 |
| 真正编译 | 调同一 `make.bat` | 直接 make |
| 改了 zxe 指向的 `Prj_mk` 资源/驱动后 | **必须**走 sprdbuildE | 易漏拷，产物不对 |
| 树已是上次拷好的状态，且只改不会被覆盖的源 | 仍推荐 sprdbuildE | 结果可能接近，非正式产品路径 |

菜单数字与目标大致对齐客户 bat（以脚本 `show_menu` 为准）：`1`≈new（先问 USER/DEBUG）、`2`≈app_main、`3`≈resource_main、`4`≈custom_drv、`5`/`13`≈模拟器、`6`≈image、`10`≈chip_drv 等。

并行度：脚本读环境变量 `JOB`（常见默认 8），再传给 make。

## 2. 编译方式一览

| 方式 | 何时用 | 客户 bat `%1` | sprdbuildE 菜单 | make 目标 |
|------|--------|---------------|-----------------|-----------|
| **单模块增量（首选）** | 改动落在某一 `make\<模块>\` | 模块名（bat 透传 `<模块>`） | 直接输 `m=<模块>` | `m=<模块>` |
| **应用增量** | 改动在 `app_main` 覆盖的 MMI（无独立 make 模块） | `2` | `2` | `m=app_main` |
| **资源增量** | 字符串/图片/铃音/xls 等 | `3` | `3` | `m=resource_main` |
| **客户驱动增量** | LCD/Sensor/keymap、分区 `mem_cfg`/`spiflash_cfg`、须拷补丁 | `4` | `4` | `m=custom_drv` |
| **芯片驱动** | `chip_drv\` | `10` | `10` | `m=chip_drv` |
| **组 PAC/镜像** | 模块已编过，只需重打 PAC | `6` | `6` | `image` |
| **模拟器** | PC 上看 UI（≠ 真机 PAC） | `5`（VC6）/ `55`（VS2010） | `5` / `13` 等 | `m=simulator_main`（常先 clean） |
| **全编** | 首编、切 USER↔DEBUG、改工程宏/大面积底层、影响面说不清 | `1` | `1`（再选 user/debug） | `new` |

说明：

- `new` 一般已含链镜像/PAC；只编了单模块 / `app_main` **不等于**已更新 PAC，要可烧包再加 `6`/`image`。
- 多模块改动：按依赖顺序分别增量（如先 `3` 再单模块），不要轻易升全编。
- 模拟器细节：[SIMULATOR.md](SIMULATOR.md)。

## 3. 命令模板

```bat
:: —— 客户 bat ——
<Product>.bat <模块>            :: 单模块透传（DEBUG）
<Product>.bat <模块> 1          :: 同上 USER
<Product>.bat 2                 :: app_main
<Product>.bat 3 / 4 / 6 / 10 / 5 / 55
<Product>.bat 1                 :: 全编 DEBUG（非首选）
<Product>.bat 1 1               :: 全编 USER

:: —— zxe / sprdbuildE（补丁仓有 *.zxe 时优先）——
cd /d <编译根>\Prj_mk\<工程>
..\..\make\make_cmd\perl.exe ..\..\sprdbuildE.pl <工程>.zxe
:: 交互选 2/3/4/6/1 …；或按脚本支持追加目标

:: —— 裸 make（无 zxe / 平台仓；或确认无需再拷时）——
make.bat p=<工程> m=<模块> -j8 job=8
make.bat p=<工程> m=app_main -j8 job=8
make.bat p=<工程> image -j8 job=8
make.bat p=<工程> new -j8 job=8
make.bat p=<工程> m=simulator clean
make.bat p=<工程> m=simulator_main -j8 job=8
```

`-j8 job=8` 可按机器调整。可选 `set CC_VER=RVCT41` 或 `V504`。zxe 路径下也可用 `set JOB=8`。

## 4. 按改动选目标（开编前必做）

原则：

1. **先列出改动文件**（git diff / 用户说明 / 当前打开文件）。
2. **先查是否有独立 make 模块**：路径落在 `make\<模块>\` 的 `MSRCPATH`/`SOURCES` 里 → 编该模块。  
   捷径：`MS_MMI_Main\source\mmi_app\app\<子目录>\` 若存在 `make\<子目录>\` → **`m=<子目录>`**，不要当成 `app_main`。
3. 无独立模块再按下表归到 `app_main` / 资源 / 驱动等。
4. **能增量不全编**；多处改动取模块并集分别编。

### 独立模块优先（易误判）

| 改动路径（相对编译根） | 正确目标 | 勿当成 |
|------------------------|----------|--------|
| `...\mmi_app\app\<模块>\`（该目录下 `.c/.h`） | 若有 `make\<模块>\` → `m=<模块>` | `app_main` / bat `2` |
| `...\mmi_app\app\<模块>\` 且 **无** `make\<模块>\` | 再归 `app_main` | — |

判定法：看编译根是否有 `make\<目录名>\<目录名>.mk`，或在 `make\*\*.mk` 里搜该源文件名是否出现在 `SOURCES`。  
举例（模式，非某仓专用）：`app\foo\` + `make\foo\foo.mk` → 编 `m=foo`，不要 bat `2`。

### 路径速查（无独立模块时）

| 改动路径（相对编译根） | 编什么 | 客户 bat `%1` | make 目标 |
|------------------------|--------|---------------|-----------|
| `MS_MMI_Main\source\mmi_app\`（**无**对应 `make\<子目录>\`） | MMI 主应用 | `2` | `m=app_main` |
| `MS_MMI_Main\source\mmi_service\` | MMI 服务 | （无专用） | `m=mmi_service` |
| `MS_MMI_Main\source\mmi_gui\` / `mmi_ctrl\` | GUI/控件 | | `m=gui_main`（或相关 gui/ctrl 模块） |
| `MS_MMI_Main\source\mmi_kernel\` | 窗口/消息框架 | | `m=mmk_main` / `m=mmk`（以仓内 make 名为准） |
| `MS_MMI_Main\source\resource\`、`*\str_table.xls`、图标/铃音/壁纸、`CustomImages\` | 资源 bin | `3` | `m=resource_main` |
| `Prj_mk\<工程>\` 下资源类（xls、图片、铃音） | 先靠 bat/**sprdbuildE** 拷贝再编资源 | `3`（必用 bat/zxe） | 同上 |
| zxe 指向的共享 `Prj_mk\<资源目录>\` / 驱动修订目录 | 须 **sprdbuildE** 拷进树内再编 | — | 菜单 `3`/`4` 或对应 `m=` |
| `MS_Customize\...\driver\lcd`、`dc`、sensor、`config\`（keymap/pinmap） | 客户驱动 | `4` | `m=custom_drv` |
| `Prj_mk\<工程>\` 下 `tft*` / `sensor*` / keymap 补丁 | 须 bat/**sprdbuildE** 拷进 Customize 再编驱动 | `4` | `m=custom_drv` |
| `Prj_mk\<工程>\hx_cust_config.h`、NV、`Fota_*` 等头/配置补丁 | 影响面大 | 建议 `1` 全编 | `new` |
| `chip_drv\` | 芯片驱动 | `10` | `m=chip_drv` |
| `MS_Ref\` | 参考/glue | | `m=refbase`（或具体子模块） |
| `BASE\atc\`（`feature_phone`、`atc_custom_cmd`、`atc_*.c`、atd/gen 生成物） | ATC / AT 命令 | `atc` | `m=atc`；细节 → [AT.md](AT.md) |
| `RTOS\`、`BASE\`（非 atc）、连接/协议大面积 | 平台底层 | | 相关模块或 **`new`** |
| `hx_cust_config.h` 仅开/关 AT 相关宏 | 宏进多模块 | 客户 bat 仓建议 `1`（先 bat） | 偏 **`new`**；勿只编 `atc`。补丁仓 / 平台仓：改真相源后再偏全编 |
| `MS_Customize\...\config\*\mem_cfg.h` 或同目录 `spiflash_cfg.c` | 分区表进 `custom_drv`/`nor_fdl` | `4` 后再 `6`；大改建议 `1` | `m=custom_drv` 再 `image`/`new`；改后跑 `partition_check.py` |
| `project_<工程>.mk`、`uis8910_phone_*_base_config.cfg`、`Prj_mk\USER_DEBUG.mk` | 工程宏/版本 | | **`new`**（USER↔DEBUG 必全编） |
| `version\`、版本头生成逻辑 | 版本信息 | | `m=version` 或随 `new`/`image` |
| 仅需重打 PAC、源码已编过 | 组包 | `6` | `image` |
| 模拟器 / `winsimulator_tp` | Win32 模拟器 | `5` / `55` | `m=simulator_main` |

模块目录以编译根下 `make\<模块名>\` 为准；上表与仓内不一致时，以 `make\` 实际目录名为准。

### Agent 决策步骤

1. 列出本次改动相对路径。
2. **每个路径**：若 `make\<同名子目录>\` 存在或 mk 的 SOURCES 含该文件 → 记入该模块；否则按下表。
3. **客户 bat 仓**改 `Prj_mk` → **必须走产品 bat**；**zxe 入口**改 zxe 指向的资源/驱动/NV/工程头 → **必须走 sprdbuildE**；无 zxe 的补丁仓改 `Prj_mk` → 直接 `make`。
4. 目标集合以增量执行；「资源 + 独立模块」→ 先 `3` 再 `m=<模块>`；不要无故升 `new`。
5. 要可烧包：增量后再 `6`/`image`。
6. 确认一句：「根据改动 `…`，建议增量编 `<模块列表>`；入口 `<bat|zxe|make>`；工程 `<名>`，`<USER|DEBUG>`。」
7. **命令跑完必须做 §5 成功检查**；未通过不得报「编译成功」。

### 反例

| 错误做法 | 后果 |
|----------|------|
| 有 `*.zxe` + `sprdbuildE.pl` 却只跑裸 `make.bat` | 漏拷资源/驱动/NV，产物与 zxe 配置不一致 |
| 把 `.zxe` 当可执行文件双击/直接运行 | 不会进入编译流程 |
| 改了 `mmi_app\app\<模块>\`（且有独立 make）却跑 `m=app_main` / bat `2` | 独立模块未重编，改动不进镜像 |
| 改了 `Prj_mk\...\sensor*` 只跑 `m=app_main` | 驱动未拷贝、未进 `custom_drv` |
| 改了 `str_table.xls` / 图片只跑 `app_main` | 机上字符串/图仍是旧资源 |
| 改了 `hx_cust_config.h` 只跑单一模块 | 其它已编译单元仍用旧宏 |
| DEBUG 工程产物却用 USER 库路径增量 | 链接/行为错乱 |
| 只编单模块就当 PAC 已新 | 可能未 `image`，PAC 未更新 |
| 小改动直接 `new` | 耗时长，非必要 |
| 进程结束就当成功，不看 exit / 日志 / 产物 | 失败被当成成功 |

真机模块编完 ≠ 模拟器已更新；PC 看 UI 另走 `5`/`55` 或 `simulator_main`（见 [SIMULATOR.md](SIMULATOR.md)）。

## 5. 编译后成功检查（强制）

**命令跑完 ≠ 编译成功。** Agent 必须自己核对后再下结论；任一项不过 → 按失败处理，见 [TROUBLESHOOT.md](TROUBLESHOOT.md)。

1. **退出码 / 控制台**：非 0，或末尾有 `Error` / `make ... Error 1` / `Not_find_PAC_file` → 失败。
2. **本次目标日志**：`build\<工程>_builddir\log\<模块>.log`（如 `app_main.log`、或本次 `m=<模块>` 对应名）看**末尾**；对照 `log\time_consuming.log` 确认本轮确实跑过该模块（防读旧日志）。
3. **产物**（按本次目标选查）：

| 本次编了什么 | 至少确认 |
|--------------|----------|
| 单模块 / `app_main` 等 | 对应 `log\<模块>.log` 无 Error；要可烧包时再确认有新 `img\*.pac` |
| `resource_main` / bat `3` | `img\mmi_res_*.bin` 存在且非 0 字节 |
| `image` / `new` / bat `6`/`1` | `img\*.pac` 存在，时间戳为本次之后 |
| `simulator_main` | `log\simulator_main.log` 末尾无 `Error`；**关键** `win\bin\msdevkernel.dll` 存在、体积通常 >数 MB、时间戳为本轮之后。`MSDev.exe` 多为模板拷贝，**单独存在不算编成功**（详见 [SIMULATOR.md](SIMULATOR.md)） |

4. **向用户汇报**：成功则写明工程、目标、关键产物路径；失败则贴日志末尾关键 1～3 行 + 建议下一命令，**不要**写「已编译完成」充成功。

产物路径（相对编译根）：

| 产物 | 路径 |
|------|------|
| PAC / axf / map | `build\<工程>_builddir\img\` |
| 日志 | `build\<工程>_builddir\log\` |
| 模拟器 | `build\<工程>_builddir\win\bin\msdevkernel.dll`（关键）；同目录 `MSDev.exe` 为启动器 |
| 资源 bin | `build\<工程>_builddir\img\mmi_res_*.bin` |
