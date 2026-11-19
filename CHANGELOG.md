# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。  
Skill 版本见 `SKILL.md` 头部 `version`；作者见 `author`。

## [Unreleased]

## [1.1.0] - 2026-11-19

### 新增

- 补丁仓 **zxe / sprdbuildE** 编译入口：`Prj_mk\<工程>\*.zxe` + `sprdbuildE.pl`（先拷资源/驱动/NV 再 `make`）
- 与裸 `make.bat` 的等价性说明、菜单目标对照、候选工程枚举 `Prj_mk\*\*.zxe`

### 变更

- `REPO` / `COMPILE` / `SKILL`：编译入口与仓型正交；有 zxe 时优先 sprdbuildE
- 全文强化脱敏：占位 `<工程>` / `*.zxe`，勿写死客户/SKU/BOM/绝对路径
- 去掉对其它 skill 的指名引用；边界改为自述「不负责 git 提交」

## [1.0.0] - 2026-11-18

### 新增

- 展锐 UIS8910 / UIS8910L / UIS8910LC MOCOR：固件编译排障、Flash 分区核对、ATC、平台版本查询
- 仓型口径：**客户 bat 仓** / **Prj_mk 补丁仓** / **平台仓**
- 文档：`REPO` / `COMPILE` / `SIMULATOR` / `PARTITION` / `AT` / `VERSION` / `TROUBLESHOOT`
- 脚本：`scripts/partition_check.py`（容量 / 烧写地址 vs img bin，防 DL1138）
- 编译：优先增量；编完强制 §5 自检（exit / 日志 / 产物）
- 模拟器：成功以 `msdevkernel.dll` + `simulator_main.log` 为准；含是否已编过核对与启动冒烟
- 范围边界：负责编译 / 分区 / ATC / 平台版本；不负责烧写、设备抓 log、git 提交/暂存清单
