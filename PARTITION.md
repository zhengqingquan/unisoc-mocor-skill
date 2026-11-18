# 展锐 Flash 分区参考

## 常见 16MB 单 Flash（`FLASH_SIZE_128MBIT`）布局

自低地址向上（扇区常为 64KB = `0x10000`）：

| 分区 | 典型基址宏 | 容量来源 | PAC/下载名 | 典型 bin |
|------|------------|----------|------------|----------|
| BOOTLOADER | `BOOTLOADER_BASE_ADDR` | `BOOTLOADER_SIZE` | BOOTLOADER | `nor_bootloader.bin` |
| PS / stone | `PS_BASE_ADDR`（LC 多为 `AP_BASE_ADDR`） | 至 FOTA 或 MMIRes | PS | `*_stone.bin` |
| FOTA_BOOTLOADER | `FOTA_BOOTLOADER_ADDR` | `FOTA_BOOTLOADER_SIZE`（常为 0） | — | — |
| MMIRes | `MMI_RES_BASE_ADDR` | `MMI_RES_SECTOR_NUM * sector` | MMIRes | `mmi_res_*.bin` |
| CP | `CP_BASE_ADDR` | `CP_SECTOR_SECTOR_NUM * sector` | CP | `*_cp.bin` |
| IMS_TOGGLE / Aging / SimLock / ConfigNV / Operator | 各 `*_ADDR` | 各扇区宏 | 部分在 PAC | 多为运行时 |
| NV | `FIXED_NV_BASE_ADDR` | `FIXED_NV_SIZE`（约 127KB） | NV | `nvitem.bin` |
| RUNNIN_NV / UDISK | 自 Flash 尾向下 | 扇区宏 | — | 运行时 |

下载辅助（**不占**上述 NOR 槽位同语义）：`nor_fdl1.bin` / `nor_fdl.bin` / `tfboot.bin`。

## 适用树

先定**仓型**（[REPO.md](REPO.md) §0），再定编译根与布局源。系列（8910 / LC）与仓型正交。

| 仓型 / 形态 | 识别信号 | 布局源 |
|-------------|----------|--------|
| 客户 bat 仓 | `idh.code\MS_Code` 或产品 bat + `Prj_mk\` | 通常 `mem_cfg.h` |
| Prj_mk 补丁仓 | 有 `Prj_mk\`、无产品 xcopy bat | 通常 `mem_cfg.h`；部分树可能仅有 `spiflash_cfg.c` |
| 平台仓 | `make.bat`，无产品 bat、无 `Prj_mk\` | 通常 `mem_cfg.h` |
| 系列 = LC | 工程名 `UIS8910LC_ROM_*`（仓型仍上表） | `mem_cfg.h`；PS 常为 `AP_BASE_ADDR`；常见 8MB |
| 模拟器对照树 | `UIS8910FF_mpphone_*` 等（仓型多为平台仓） | 常无布局源 → 脚本报 N/A |

## 宏从哪里来

优先 `build/<工程>_builddir/tmp/`：

- `app_main.macro` / `*_MACRO_INC.txt`（含 `FOTA_SUPPORT_NONE` 等）
- `sprd_macro.tmp`

配置兜底：`*.cfg` 中 `FOTA_SUPPORT = NONE` → 视为 `FOTA_SUPPORT_NONE`。

无 build 时：由 `project_*.mk` / builddir 名推断 `FLASH_SIZE_128MBIT`（16MB）或 `FLASH_SIZE_64MBIT`（8MB）。

布局源路径模式（相对编译根，脚本按序找）：

```
MS_Customize\source\product\config\<config名>\mem_cfg.h
MS_Customize\source\product\config\<config名>\spiflash_cfg.c   ← 无 .h 时
```

多份时优先含 `uis8910` / `refphone` 的配置目录；有 `.h` 时不用 `.c`。

## 查看分区（强制用脚本）

改前/改后、出现 DL1138、资源变大怀疑超分区时，**实际执行**（勿手算）：

```powershell
$PY = Join-Path "{skill根}" "scripts\partition_check.py"
python $PY "{项目根}"                 # 自动找编译根 + 最近 builddir
python $PY "{项目根}" -p <工程名>     # 指定 build/<工程>_builddir
python $PY "{项目根}" --list-builddirs
python $PY "{项目根}" --json
```

汇报必带：BurnAddr / PartSize / BinSize / Stat。`OVER`/`TIGHT` 必提；`helper` 为 FDL 等下载辅助，不占 NOR 槽位语义。

无 `mem_cfg.h`（纯**模拟器对照树**）→ 本脚本不适用，直接说明。

## 改分区流程

1. **先跑脚本**拿到当前布局与各 bin 占用（尤其 MMIRes / CP）。
2. 打开脚本报出的 **Layout src** 中对应 Flash 分支扇区宏（16MB 常见 `FLASH_SIZE_128MBIT`；写法可能是 `#elif defined(...)` 或 `#elif FLASH_SIZE_...`）：
   - 扩资源：`MMI_RES_SECTOR_NUM`（→ `MMI_RESOURCE_SIZE`）
   - 常从相邻 **CP** 借：同步改 `CP_SECTOR_SECTOR_NUM`（→ `CP_SIZE`）
3. 同步同文件内 **注释地址表**（`|mmiresource|` / `|cp|` 等）；块注释内勿再套 `/* */`。
4. **重编并链入新基址**：客户 bat 仓优先产品 bat `4`（`custom_drv`，含 `nor_fdl`）再 `6`/`image`；影响面大或 USER↔DEBUG 切过 → `1`/`new`。补丁仓 / 平台仓：`m=custom_drv`（及依赖布局头/cfg 的模块）再 `image`/`new`。
5. **再跑脚本**：确认无 `OVER`；若告警 `MMI_RES_BASE_ADDR ... not found in nor_fdl.bin` → `nor_fdl` 仍是旧表，须重编 `custom_drv`/`nor_fdl` 后再组包。
6. 交付必须用**新 PAC**（内含新 `nor_fdl`）；旧包仍带旧分区表。本 skill **不**指导烧写步骤。
