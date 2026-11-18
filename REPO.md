# 仓库类型与编译入口

按工作区识别**仓型**、定位**编译根**；目录速查与配置分层见下文。  
**用词以本节为准**；本 skill 各章 + commit-skill **仓型同口径**。本 skill **不管** git 提交（交什么/暂存清单 → commit-skill）。

## 0. 用词口径（强制）

### 0.1 仓型（三选一，先判这个）

与 commit-skill §0 一致。吃不准：搜含 `xcopy` 且引用 `Prj_mk` 的 `*.bat`。

| 仓型（全称） | 可简称 | 特征 | 编译入口 | 改哪里（防 bat 盖掉） |
|--------------|--------|------|----------|----------------------|
| **客户 bat 仓** | 客户仓 | 有 `<Product>.bat`（`xcopy`/`copy` + 调 make）且有 `Prj_mk\`；常有 `idh.code\MS_Code` | 产品 bat | 改 `Prj_mk` 等真相源，勿只改会被 xcopy 的树内副本 |
| **Prj_mk 补丁仓** | 补丁仓 | 有 `Prj_mk\`（常有 `hx_macro_option.mk`），**无**上述产品 xcopy bat | `make.bat` | **无** bat 文件覆盖链；`Prj_mk` 与树内源按引用改 |
| **平台仓** | — | 有 `make.bat`，**无**产品 xcopy bat，**无** `Prj_mk\` | `make.bat` | 树内多为真相源 |

禁止把「补丁仓」写成「平台仓」再套客户 bat 覆盖表；禁止把「客户 bat 仓」只写成含糊的「客户交付仓」而不判 bat。

### 0.2 与仓型正交（不要当成第四种仓型）

| 用语 | 含义 |
|------|------|
| **系列** | 芯片/SDK 线：`8910 主系` / `LC`；另有同工具链 FF 系补丁树（命名模式，非某仓专名）→ 见 [VERSION.md](VERSION.md) |
| **模拟器对照树** | 工程多为 `UIS8910FF_mpphone_*` + `winsimulator_tp`；仓型仍上表三选一（多为平台仓），分区常 N/A |
| **编译根** | 含 `make.bat`（及 `project_*.mk`）的那一层；客户 bat 仓常在 `idh.code\MS_Code` |
| **产品 bat** / `<Product>.bat` | 客户 bat 仓编译入口；会 xcopy `Prj_mk` |
| **USER / DEBUG** | **编译变体**（bat 第 2 参数或工程名后缀），不是 MOCOR 平台号 |
| **MOCOR 平台号** | `_MOCOR_SW_VERSION_`；≠ 产品/应用版本 |
| **可烧包** | 已更新 `img\*.pac`（`image`/`new`）；本 skill 不指导烧写 |

### 0.3 文中写法

- 首次或表格：**客户 bat 仓** / **Prj_mk 补丁仓** / **平台仓**。
- 后文可简称 **客户仓** / **补丁仓**（仅当上文已点名全称）。
- 占位：`<Product>`、`Prj_mk\<工程>`、`p=<工程>`；勿绑具体 SKU/绝对路径。

## 1. 识别编译根（在仓型之后）

| 信号 | 常见仓型 | 编译根 |
|------|----------|--------|
| `idh.code\MS_Code` 或大量 `FM*`/`FF*.bat` + `Prj_mk\` | 客户 bat 仓 | `idh.code\MS_Code`（若在下层）或 bat+mk 层 |
| 有 `Prj_mk\`，无产品 xcopy bat | Prj_mk 补丁仓 | 含 `make.bat` 的仓库根 |
| `project_UIS8910_ROM_*` / `UIS8910LC_ROM_*` 等，无 `Prj_mk\`、无产品 bat | 平台仓 | 同上 |
| `project_UIS8910FF_mpphone_*.mk` + `winsimulator_tp` | 多为平台仓 + **模拟器对照树** | 同上；分区检查常 N/A |
| 有 `make.bat` 但工程在子目录 | 继续向下找 | 同时有 `Makefile`/`make\` + `project_*.mk` 的层 |

系列（8910 / LC）看工程名集合，**不能**单靠 `CHIP_VER` 判 LC → [VERSION.md](VERSION.md)。

可选：读 `.cursor/context/project-context.md` 作候选，**仍须向用户确认工程名**。

## 2. 目录速查（相对编译根）

| 路径 | 职责 | 查找时优先看 |
|------|------|----------------|
| `make.bat` / `Makefile*` / `make\` | 编译入口与模块 makefile | 怎么编、模块名 |
| `project_*.mk` / `uis8910_*_base_config.cfg` | 工程宏、Flash/分辨率/modem | 工程差异 |
| `UIX8910.modules` / `Makefile.modules` | 模块/库组成 | 链了哪些库 |
| `MS_MMI_Main\` | MMI 应用 / GUI / 资源 / 模拟器 | UI、字符串、图标 |
| `MS_Customize\` | 产品配置、驱动、`config\*\mem_cfg.h` 或 `spiflash_cfg.c` | LCD/Sensor/分区 |
| `MS_Ref\` | 参考层 / glue | 显示、中间件衔接 |
| `chip_drv\` / `fdl_bootloader\` | 芯片驱动、FDL | 底层、nor_fdl |
| `BASE\atc\` | ATC / AT（FP 默认 `feature_phone`） | 自定义 AT；见 [AT.md](AT.md) |
| `Prj_mk\` | 补丁与宏桥（客户 bat 仓 / 补丁仓） | 差分配置；客户 bat 仓的 xcopy **源** |
| `build\<工程>_builddir\` | 编译产物与 log | PAC、img、排障 |
| `lib\` | 预置基库（modem 等） | USER/DEBUG 库路径 |
| `Third-party\` / `tools\` | 三方与工具 | 一般非主业务 |
| `version\` | 版本信息 | MOCOR / 产品版本；见 [VERSION.md](VERSION.md) |

**外层包装（客户 bat 仓常见）**：工作区根可能要进 `idh.code\MS_Code` 才到编译根；根上 `doc\` 多为笔记，**不是**平台目录说明书。

## 3. 列出候选工程

```bat
cd /d <编译根>
dir /b *.bat | findstr /i "FM FF"
dir /b project_*.mk
```

- **客户 bat 仓**：工程名 ≈ 产品 bat 主名；有 `project_<同名>.mk`、`Prj_mk\<同名>\`。
- **补丁仓 / 平台仓**：工程名 = `project_XXX.mk` → `XXX`；USER/DEBUG 成对则成对列出。

## 4. 配置分层

```
uis8910_phone_*_base_config.cfg
    ↓
project_<工程>.mk
    ↓
Prj_mk/USER_DEBUG.mk          ← 仅客户 bat 仓：bat 按第 2 参数生成
    ↓
Prj_mk/<工程>/                ← 补丁（LCD/Sensor/资源/NV/hx_cust_config.h）
```

补丁仓 / 平台仓一般无 bat 写 `USER_DEBUG.mk`；编译变体看工程名 `_USER` / `_DEBUG`。

## 5. 其它章节

| 主题 | 读 |
|------|-----|
| MOCOR 平台号、系列、SS·DS | [VERSION.md](VERSION.md) |
| 编译命令与按改动选模块 | [COMPILE.md](COMPILE.md) |
| 模拟器 | [SIMULATOR.md](SIMULATOR.md) |

要点：客户 bat 仓改 `Prj_mk` → **跑产品 bat**；补丁仓 / 平台仓 → 直接 `make.bat`。CMD 执行；PowerShell 用 `cmd /c "..."`。
