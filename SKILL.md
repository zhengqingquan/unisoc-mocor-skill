---
name: unisoc-mocor-skill
version: "1.1.0"
author: zqingquan
description: |
  展锐 UIS8910/UIS8910L/UIS8910LC MOCOR：固件编译排障 + Flash 分区核对
  （mem_cfg 容量/烧写地址 vs img bin，防 DL1138）+ ATC/自定义 AT
  + 查 MOCOR 平台号/系列（8910·LC）。仓型：客户 bat 仓 / Prj_mk 补丁仓 / 平台仓。
  补丁仓另可走 sprdbuildE.pl + Prj_mk\<工程>\*.zxe（先拷资源/驱动再 make）。
  触发：编译、make、new、bat、zxe、sprdbuildE、USER/DEBUG、resource_main、PAC、
  模拟器、MSDev、链接失败、mmi_res、改了没编到；分区、mem_cfg、MMI_RES_SECTOR、
  CP_SECTOR、DL1138、镜像超分区、烧写地址、Flash 布局、扩资源挪扇区；
  AT、ATC、AT+、atc_custom_cmd、atc.atd、自定义 AT、AT 不生效；
  平台版本、MOCOR、version.txt、Wxx.yy.z、什么平台、LC还是8910、
  客户 bat 仓、补丁仓、仓型。
---

# 展锐 MOCOR（unisoc-mocor-skill）

**版本**：1.1.0 · **作者**：zqingquan  

原 `unisoc-build` + `unisoc-flash-partition`。在 **CMD** 下编译。

**适用**：UIS8910 / UIS8910L / UIS8910LC，以及同工具链的 FF 系补丁树（工程常为 `UIS8910_ROM_*` / 补丁目录命名模式，非特指某一工作区）。仓型三选一：**客户 bat 仓** / **Prj_mk 补丁仓** / **平台仓**（口径见 [REPO.md](REPO.md) §0）。  
**脱敏**：文中用 `<工程>` / `Prj_mk\<工程>\*.zxe` 等占位，勿写入具体客户/SKU/BOM/绝对路径。

**本 skill 范围**：编译、分区核对、ATC、平台版本。  
**不负责**：① PAC/ResearchDownload **烧写**；② Logel/串口 **抓设备日志**；③ git **commit / 暂存 / 该交什么**。勿在本 skill 内展开烧写、抓 log、提交清单，或代为 `git commit`。

## A. 编译（强制流程）

1. **定仓型 + 编译根 + 编译入口**：见 [REPO.md](REPO.md)。客户 bat 仓编译根常在 `idh.code\MS_Code`。若编译根有 `sprdbuildE.pl` 且 `Prj_mk\<工程>\*.zxe` → **zxe 入口**（见 [COMPILE.md](COMPILE.md) §1.1），优先于裸 `make.bat`。
2. **问工程（必问）**：未指定则列出候选（有 zxe 时列 `Prj_mk\*\*.zxe` 主名）再编。
3. **问编译变体（必问）**：USER / DEBUG；切变体倾向 `new`。
4. **先看改动再编（优先增量）**：列出改动文件 → 按 [COMPILE.md](COMPILE.md) §4 定模块（`mmi_app\app\<模块>` 有独立 make 时勿当 `app_main`）→ 单模块/`app_main`/资源等增量；仅必要时全编。要可烧包再 `image`/`new`。
5. **编译后自检（强制）**：命令结束 ≠ 成功。按 [COMPILE.md](COMPILE.md) §5 查 exit/控制台、`log\<模块>.log`、产物；通过才可报成功，否则 → [TROUBLESHOOT.md](TROUBLESHOOT.md)。

| 仓型 / 入口 | USER / DEBUG |
|-------------|--------------|
| 客户 bat 仓 | 产品 bat 第 2 参数：`1`=USER，省略=DEBUG |
| 补丁仓 / 平台仓（裸 make） | `p=..._USER` / `p=..._DEBUG` |
| **zxe / sprdbuildE** | 菜单全编时选 1→再选 user/debug（写 `Prj_mk\USER_DEBUG.mk`）；工程名常无 `_USER`/`_DEBUG` 后缀 |

命令与方式一览 → [COMPILE.md](COMPILE.md)。模拟器细节 → [SIMULATOR.md](SIMULATOR.md)。

## B. Flash 分区（查看 / 修改）

改 `mem_cfg.h` / 资源变大 / 遇 **DL1138**（镜像超分区）时：**实际执行**脚本，勿手算。改扇区流程见 [PARTITION.md](PARTITION.md)。

```powershell
$PY = Join-Path "{skill根}" "scripts\partition_check.py"
python $PY "{项目根}"
python $PY "{项目根}" -p <工程名>
python $PY "{项目根}" --list-builddirs
python $PY "{项目根}" --json
```

- 汇报：BurnAddr / PartSize / BinSize / Stat（`OVER`/`TIGHT` 必提）。
- 改分区后：重编 `custom_drv`/`nor_fdl`（客户 bat 仓：产品 bat `4`，再 `6`/`image` 或 `new`；zxe 入口：sprdbuildE 菜单 `4` 再 `6`/`1`；无 zxe 补丁仓/平台仓：`m=custom_drv` 再 `image`/`new`）→ 再跑脚本确认；交付用**新 PAC**（含新 `nor_fdl`）。
- 布局源可能是 `mem_cfg.h` 或 `spiflash_cfg.c`（脚本自动选）；**模拟器对照树**常无布局源 → 脚本报 N/A。

| Stat | 含义 |
|------|------|
| ok / TIGHT / OVER | 正常 / ≥95% / 超分区（DL1138） |
| helper / no-bin | FDL 等辅助镜像 / 无对应 bin |

## C. AT / ATC

加/改自定义 AT、AT 无回或不生效 → [AT.md](AT.md)。

要点：三仓型共性 `BASE\atc\feature_phone\` + `m=atc`；命令表真相在 `atc.atd`（`atc_gen` 盖生成物）。**产品 bat 不盖 `BASE\atc`**；`hx_cust_config.h` 仅客户 bat 仓被 xcopy——只改 `Prj_mk\<工程>\`；补丁仓 / 平台仓勿套该规则。

## D. 版本 / 平台

问 MOCOR 多少、什么平台、LC 还是 8910、`version.txt` 准不准 → [VERSION.md](VERSION.md)。

要点：权威读 `version\version_software_mocor.h` 的 `_MOCOR_SW_VERSION_`；`version.txt` 可能过期；**勿用 `CHIP_VER` 单独判 LC**。

## Agent 约定

- 开编前写清：**仓型**、**编译入口**（产品 bat / 裸 make / zxe）、编译根、工程、USER|DEBUG、目标、依据改动路径；未确认只问不编。
- **客户 bat 仓**改 `Prj_mk\<工程>\` → 优先产品 bat；**zxe 入口** → `sprdbuildE.pl` + `*.zxe`（勿只 `make`，会漏拷）；**无 zxe 的补丁仓 / 平台仓** → 直接 `make.bat`。
- **编完必须自检**（exit / 日志 / 产物）；未自检不得报成功。模拟器另见 [SIMULATOR.md](SIMULATOR.md)：`MSDev.exe` ≠ 编成功，以 `msdevkernel.dll` + 日志为准。
- 排障读 `build\<工程>_builddir\log\`（编译 log，不是设备抓 log）。
- 动 AT：先分清 atd/生成物 vs 处理函数 vs Prj 宏；见 [AT.md](AT.md) §5。
- 用户要烧写 / 抓设备 log / **commit·该交什么** → **不在本 skill 处理**（勿展开步骤、勿代提交）。
- 用词口径 → [REPO.md](REPO.md) §0。本 skill **不管** git 提交。**勿在回复或 skill 正文写死客户/SKU/BOM 名；勿引用其它 skill 名。**

## 参考（场景 → 文件）

| 场景 | 读 |
|------|-----|
| 仓型口径 / 编译根 / zxe 入口 / 目录速查 | [REPO.md](REPO.md) |
| MOCOR 平台号 / 系列·LC·SS·DS / version.txt | [VERSION.md](VERSION.md) |
| 编译（含 sprdbuildE；优先增量；按改动定模块） | [COMPILE.md](COMPILE.md) |
| 编译失败、资源/链接/USER·DEBUG 混用 | [TROUBLESHOOT.md](TROUBLESHOOT.md) |
| Windows 模拟器编/启 | [SIMULATOR.md](SIMULATOR.md) |
| 分区查看、改扇区、DL1138 | [PARTITION.md](PARTITION.md) + `scripts/partition_check.py` |
| AT/ATC、自定义命令、atd/gen、覆盖边界 | [AT.md](AT.md) |
