# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。  
Skill 版本见 `SKILL.md` 头部 `version`；作者见 `author`。

## [1.0.0] - 2026-11-18

### 新增

- 展锐 UIS8910 / UIS8910L / UIS8910LC MOCOR：固件编译排障、Flash 分区核对、ATC、平台版本查询
- 仓型口径：**客户 bat 仓** / **Prj_mk 补丁仓** / **平台仓**（与 commit-skill 对齐）
- 文档：`REPO` / `COMPILE` / `SIMULATOR` / `PARTITION` / `AT` / `VERSION` / `TROUBLESHOOT`
- 脚本：`scripts/partition_check.py`（容量 / 烧写地址 vs img bin，防 DL1138）
- 编译：优先增量；编完强制 §5 自检（exit / 日志 / 产物）
- 模拟器：成功以 `msdevkernel.dll` + `simulator_main.log` 为准；含是否已编过核对与启动冒烟
- 范围边界：负责编译 / 分区 / ATC / 平台版本；不负责烧写、设备抓 log、git commit/暂存清单
