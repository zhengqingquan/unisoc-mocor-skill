# 版本与平台

查「这是什么平台 / MOCOR 多少 / 和交付包一不一致」时读本文件。先定**仓型 + 编译根**（[REPO.md](REPO.md) §0）；路径均相对编译根（除非注明）。**系列 ≠ 仓型**。

## 1. 先分清三件事

| 名称 | 是什么 | 不是 |
|------|--------|------|
| **MOCOR 平台号** | SDK/基线版本（`_MOCOR_SW_VERSION_`） | 某客户产品对外版本 |
| **USER / DEBUG** | 本次编译变体（工程名后缀或 bat 第 2 参数） | 平台 SDK 号 |
| **产品/应用版本** | 客户工程发布串（`version_sw_release.h` 等） | 平台号 |

汇报时默认给：**系列（8910 / LC / …）+ MOCOR 平台号**；需要再补 USER|DEBUG、产品版本。

## 2. MOCOR 平台号（权威）

打开：

```
version\version_software_mocor.h
```

读宏 **`_MOCOR_SW_VERSION_`**。

| 形态 | 含义 |
|------|------|
| `UIS8910_Wxx.yy.z` | 常见；`Wxx.yy.z` 为周次/修订 |
| `Wxx.yy.z`（无 `UIS8910_` 前缀） | 部分较老/对照树仍可见；仍以该宏为准 |

**多仓对比、回答「平台版本是多少」→ 以本宏为准**，不要只信目录名或 `version.txt`。

## 3. Platform Version 串（机上/日志常见）

在 `version\UIX8910_*_version.c`（或同目录同类 `*_version.c`）中，常见拼接：

```text
Platform Version: MOCOR_20B.<_MOCOR_SW_VERSION_>_Release
Platform Version: MOCOR_20B.<_MOCOR_SW_VERSION_>_Debug
```

例：宏为 `UIS8910_Wxx.yy.z` → 串为 `MOCOR_20B.UIS8910_Wxx.yy.z_Debug`（DEBUG 编）。  
`MOCOR_20B` 为前缀习惯写法；**变的是中间的 `_MOCOR_SW_VERSION_`**。

## 4. `version.txt`（交付标注，可能过期）

| 位置 | 说明 |
|------|------|
| 工作区根或编译根上的 `version.txt`（有则看） | 形态如 `MOCOR_20B_Wxx.yy.z__日期时间` |

- **可能与 `version_software_mocor.h` 不一致**（包未改、源已升）。
- 冲突时：**头文件宏为准**；可在汇报里写一句「version.txt 仍为 …，源码为 …」。

## 5. 产品 / 应用版本

| 常见位置 | 说明 |
|----------|------|
| `version\version_sw_release.h` 等 | 客户/产品软件版本 |
| 客户 bat 内版本变量 → 生成的 `version\version_sw_release.h` | 客户 bat 仓可能被 bat 重写；改变量/源勿只改生成头。提交边界不在本 skill |

不要把产品版本答成「平台是 Wxx」。

## 6. 判系列 / 平台形态（与版本一起报）

**LC 与 SS 不是同一维**：LC = 芯片/SDK 系列；SS/DS = 单卡/双卡。

### 6.1 芯片 / SDK 系列

| 线索 | 怎么判 |
|------|--------|
| `project_*.mk` 文件名 | `project_UIS8910LC_ROM_*` → **LC**；`project_UIS8910_ROM_*` → **8910 主系**；客户 bat 仓常见 `project_FM*` / `project_FF*`（系列看树/基线，不单看 FM 名） |
| 仓内工程集合 | 几乎全是 `UIS8910LC_*` → LC；全是 `UIS8910_ROM_*` → 8910 主系；`UIS8910FF_mpphone_*` → **模拟器对照树**（形态，不是第四仓型） |
| 当前 `project_<工程>.mk` | `PLATFORM = UIX8910`；`CHIP_VER` 常见 `UIS8910FF` |

注意：`CHIP_VER` 在 **LC** 上也常写成 `UIS8910FF`，**不能单靠 CHIP_VER 区分 LC**；优先看工程名是否带 `UIS8910LC`。

同工具链 **FF 系补丁树** / **Prj_mk 补丁仓**：工程名可能是 `UIS8910_ROM_*` 或分辨率变体、补丁目录常见 `FF*` 前缀；系列仍按工程集合 + MOCOR 平台号回答，勿发明未在 mk 出现的芯片名、勿绑某一工作区路径。

### 6.2 单卡 / 双卡（SS / DS）

| 线索 | 怎么判 |
|------|--------|
| 工程名 | `_SS_` → 单卡；`_DS_` → 双卡 |
| `project_<工程>.mk` | `MMI_MULTI_SIM_SYS = SINGLE` / `DUAL` |

### 6.3 其它工程名片段

| 片段 | 含义 |
|------|------|
| `_USER` / `_DEBUG` | 编译变体 |
| `_16MB_` / `_8MB_` 等 | Flash 容量倾向（对照分区 `FLASH_SIZE_*`） |
| `_BT_` | 带蓝牙相关配置的变体（以 mk 内容为准） |

查某工程：打开 `project_<工程>.mk`，读 `MMI_MULTI_SIM_SYS`、`CHIP_VER`、`PLATFORM`、`PRODUCT_CONFIG`；再对照 §2 宏。

## 7. Agent 怎么查、怎么报

1. 定**仓型** + 编译根（[REPO.md](REPO.md) §0）。  
2. 读 `version\version_software_mocor.h` → `_MOCOR_SW_VERSION_`。  
3. 扫 `project_*.mk` 命名 → **系列**（8910 / LC）与是否模拟器对照树。  
4. 若有 `version.txt`，与宏比对；不一致则两处都写明。  
5. 用户要「当前工程」时再读指定 `project_*.mk` 的 PLATFORM/CHIP_VER/SS·DS；未指定则报仓级结论。

**汇报模板（一句即可）**：

```text
仓型：<客户 bat 仓 | Prj_mk 补丁仓 | 平台仓>
系列：<8910 主系 | LC | …>（可选形态：模拟器对照树）
MOCOR：<_MOCOR_SW_VERSION_>
（可选）version.txt：<…或无>；与宏<一致|不一致>
（可选）样例工程：PLATFORM=… CHIP_VER=… SIM=SS|DS
```

勿把具体本机绝对路径、客户 SKU 写进通用结论；举例用命名模式（`UIS8910_Wxx.yy.z`、`project_UIS8910LC_ROM_*_DS_*_DEBUG.mk`）。
