# AT / ATC

8910 系 Feature Phone 的 AT 由 **ATC 模块**解析与分发。改命令、加自定义 AT、AT 不生效时读本文件。

**跨仓共性**：三仓型（客户 bat 仓 / Prj_mk 补丁仓 / 平台仓；口径见 [REPO.md](REPO.md) §0）均有 `BASE\atc\feature_phone` + `atc.atd`/`atc_gen` + `m=atc`；**产品 bat 都不 xcopy `BASE\atc`**。差异只在：有无产品 bat、以及 `hx_cust_config.h` 是否被 bat 回写（见 §5）。

## 1. 目录与模块

| 路径（相对编译根） | 职责 |
|--------------------|------|
| `BASE\atc\feature_phone\` | **8910 FP 默认源**（`ATC_SRC_PATH`） |
| `BASE\atc\feature_phone\source\c\` | 实现：`atc_*.c`、`atc_custom_cmd.c`、生成物 `atc_info.c`/`atc_lex.c` |
| `BASE\atc\feature_phone\source\h\` | 头：`atc.h`、`atc_def.h`、`atc_custom_cmd.h` 等 |
| `BASE\atc\feature_phone\tools\` | `atc_gen.bat` + `template\atc.atd`（表/词法生成源） |
| `BASE\make\atc\atc.mk` | 模块 makefile；工程链入见 `UIX8910.modules` 的 `atc` |
| `BASE\atc\modem\` / `samsung_phone\` | 非 FP 默认路径；仅对应产品形态才用 |

判定：打开 `BASE\make\atc\atc.mk`，非 modem/SS 时 `ATC_SRC_PATH = BASE/atc/feature_phone/`。

编译目标：**`m=atc`**（客户 bat 透传模块名 `atc`）。

## 2. 处理链（简图）

```
串口/USB AT 口 → SIO/ATC 读行 → atc_lex 认命令名
  → 查 g_atc_info_table（atc_info.c）→ ATC_ProcessXXX 处理函数
  → 回 OK/ERROR/+CMD:…；需 UI/业务时再投递 MMI 消息 / 调 MMI API
```

常用宏/API（在 `atc.h`）：`AT_CMD_FUNC`、`ATC_GET_CMD_TYPE`、`PARA1`/`PARAM1_FLAG`、`ATC_BuildInfoRsp`、`S_ATC_SUCCESS` / `S_ATC_FAIL`。

## 3. 新增 / 改自定义 AT（推荐流程）

**真相源优先改 `atc.atd`，再生成，再写处理函数。** 只手改生成物、不改 atd，下次 `atc_gen` 会被盖掉。

### 3.1 登记命令（表 + 词法）

1. 编辑 `BASE\atc\feature_phone\tools\template\atc.atd`，按现有条目追加，例如：

```text
+FOO
{
    15,
    "(0-16),(0-255)"
};
```

- 第一字段：能力位（与邻近同类命令对齐即可，常见 `14`/`15`）。
- 第二字段：参数范围；多参逗号分隔。

2. 在 `tools\` 下跑 `atc_gen.bat`（需本机 flex/bison 等 gen 工具可用）。会重写：

| 生成物（会被 gen **覆盖**） |
|------------------------------|
| `source\h\atc_def.h`（`AT_CMD_xxx` 序号） |
| `source\c\atc_info.c`（命令名/参数/`g_atc_info_table`/函数表） |
| `source\c\atc_lex.c`（词法） |
| `tools\lex_yacc\atc.lex` |

3. 工具链不可用时：可**对齐现有末条**手改上述四类文件 + `atc.atd`（atd 仍要同步，避免后人 gen 丢命令）。序号须与 `g_atc_info_table` / 处理函数表**同序同下标**。

### 3.2 实现处理函数

| 方式 | 放哪里 | 何时用 |
|------|--------|--------|
| **推荐** | `atc_custom_cmd.c` / `.h` | 客户扩展、少动平台大文件 |
| 亦可 | `atc_basic_cmd.c` | 与现有大批标准/产测命令放一起 |

骨架：

```c
AT_CMD_FUNC(ATC_ProcessFOO)
{
    ATC_STATUS status = S_ATC_FAIL;
    switch (ATC_GET_CMD_TYPE) {
    case ATC_CMD_TYPE_SET:
        /* PARA1.num / PARAM1_FLAG … */
        status = S_ATC_SUCCESS;
        break;
    case ATC_CMD_TYPE_READ:
        /* ATC_BuildInfoRsp(atc_config_ptr, g_rsp_str); */
        status = S_ATC_SUCCESS;
        break;
    default:
        break;
    }
    return status;
}
```

- 在 `atc_custom_cmd.h` 声明；`atc_info.c` 函数表对应项指向 `ATC_ProcessFOO`（gen 后若表项名已对上，只需保证符号可链）。
- 需 MMI：在 ATC 里调 `MMIAPI*` / 投递 MMI 消息；业务实现放 `MS_MMI_Main\...`，**不要**把大块 UI 逻辑塞进 ATC。

### 3.3 宏开关（可选）

产品用 `hx_cust_config.h` 宏包住扩展 AT 时：

- **客户 bat 仓**：只改 `Prj_mk\<工程>\hx_cust_config.h`（见 §5），不要只改 `RTOS\export\inc\hx_cust_config.h`。
- **Prj_mk 补丁仓 / 平台仓**：按仓内实际引用改（`Prj_mk` 或树内头）；勿套客户 bat 仓「只交 Prj、弃 RTOS 副本」规则。
- 宏变更影响面大 → 客户 bat 仓倾向产品 bat + 全编/`new`；补丁仓 / 平台仓亦勿只编 `atc`。

## 4. 按改动编什么

| 改动 | 编译 | 说明 |
|------|------|------|
| 仅 `BASE\atc\...`（含 custom_cmd / basic_cmd / info/lex/def） | `atc` / `m=atc` | 要可烧包再 `6`/`image` |
| ATC + MMI API/窗口消息 | `atc` **且**对应 MMI 模块（独立 `make\<模块>` 或 `app_main`） | 只编一边会表现为 AT 有回、业务不动 |
| 改 `hx_cust_config.h` 中与 AT 相关的宏 | 客户 bat 仓：产品 bat + 建议 `1`/`new`；补丁仓 / 平台仓：按引用改源后再偏全编 | 客户 bat 仓先 xcopy 再吃宏 |
| 只改 `atc.atd` 未 gen、未改 source | **不会进固件** | 必须 gen 或同步手改生成物后再编 `atc` |

改 atd/ATC 源：三仓型均可 **`m=atc`**（产品 bat 不拷 ATC）。客户 bat 仓若同次还改了 `Prj_mk`，仍优先跑产品 bat 再编模块。

## 5. 会不会被覆盖？（强制核对）

### 5.1 产品 bat / 编译 xcopy

先定仓型（[REPO.md](REPO.md) §0）：

| 仓型 | `BASE\atc` | `hx_cust_config.h` |
|------|------------|---------------------|
| **客户 bat 仓** | **不覆盖** | bat 盖 `RTOS\export\inc\` ← 只改 `Prj_mk\<工程>\` |
| **Prj_mk 补丁仓** | **不覆盖** | 无 bat 回写；按 include 链改真相源 |
| **平台仓** | **不覆盖** | 通常无这套回写 |

| 路径 | 客户 bat 仓是否覆盖 | 结论 |
|------|---------------------|------|
| `BASE\atc\**` | **否** | 树内源即真相；可直接改（提交边界不在本 skill） |
| `MS_MMI_Main\...` 业务 AT 回调 | **否**（除非恰落在 bat 列出的资源/菜单等目标） | 一般可直接改 |
| `RTOS\export\inc\hx_cust_config.h` | **是** ← `Prj_mk\<工程>\hx_cust_config.h` | 补丁仓 / 平台仓无 bat 回写，按引用改真相源 |
| LCD/Sensor/资源/NV 等 | 源→目标全表不在本 skill；改前用 `<Product>.bat` 核对 | 与 ATC 无关，勿混 |

吃不准：打开当前 `<Product>.bat`（若有）搜文件名 / `xcopy`。  
**git 该交什么 / 暂存清单**：本 skill 不管 → `unisoc-mocor-commit-skill`。

### 5.2 `atc_gen.bat`（另一类覆盖）

跑 gen 会**覆盖** `atc_def.h`、`atc_info.c`、`atc_lex.c`、`atc.lex`。

- 持久改命令表 → 先改 **`tools\template\atc.atd`**，再 gen。
- 只在生成物里加命令、atd 未改 → 同事/下次 gen 会丢。
- 处理函数实现放 `atc_custom_cmd.c`（或 basic_cmd 里手写函数体）**不会**被 gen 抹掉；被抹的是表项/词法/序号。

## 6. 联调与排障

| 现象 | 先查 |
|------|------|
| 命令无回 / ERROR | 是否进 `atc_lex`（atd/lex 是否登记）；USB 是否 AT 口（非纯 U 盘/仅 DIAG） |
| 有 OK 但业务无动作 | MMI 是否编进；消息/API 是否接到；宏是否打开 |
| 改了 ATC 机上仍旧 | 是否编了 `m=atc` + `image`；是否错工程 USER/DEBUG |
| 宏开了仍无符号 | 是否只改了 RTOS 副本、bat 又盖回旧 Prj；或未全编导致他模块仍按旧宏 |
| gen 后编译炸 | 函数表与 `AT_CMD_*` 下标不一致；缺 `ATC_ProcessXXX` 实现 |

真机发 AT：USB AT 口或标定/调试串口（视产品 UCOM 模式）。设备抓 log / 烧写不在本 skill 范围。

## 7. Agent 约定

1. 加 AT：先定命令名与参数 → 改 **`atc.atd`**（并 gen 或同步生成物）→ 实现 `ATC_Process*` → 再定 MMI 是否要改。
2. 开编前写清：是否动 atd/生成物、是否动 `hx_cust_config`、编 `atc` 还是还要 MMI/`new`。
3. **覆盖**：动宏查 bat；动表查 atd vs gen；勿把 `BASE\atc` 误判成 bat 覆盖目标。
4. 细节命令语义以仓内注释/协议为准；本文件只定落点、生成链与编译/覆盖边界。
