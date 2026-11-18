# Windows 模拟器编译与启动

模拟器是 Win32 MMI（`winsimulator_tp`），**不是**真机 PAC。需要 **VC6（msdev）** 或 **VS2010（devenv）**。

编译前仍须：定**仓型**（[REPO.md](REPO.md) §0）+ **确认工程名** + 是否要模拟器（而非只编真机模块）。

## 何时编模拟器

- 用户明确要模拟器 / winsim / MSDev
- 当前为 **模拟器对照树**（`UIS8910FF_mpphone_*` + `winsimulator_tp`；仓型多为平台仓）
- 改了 MMI 且要用 PC 看效果（真机 `app_main` ≠ 模拟器已更新）
- 普通 `UIS8910_ROM_*` / 产品工程也可 `m=simulator_main`（不限于 mpphone）

## 是否已编过（问「哪个仓编了模拟器 / 编成功了没」时）

只认产物与日志，**不要**把空 `win\`、仅有 `simulator.dsw`、或模板拷贝的 `MSDev.exe` 当成编成功。

| 状态 | 判据 |
|------|------|
| 未编 / 空壳 | 无 `build\*_builddir\win\`，或 `win\` 为空目录 |
| make 半截失败 | 有 `simulator.dsw` / 已拷 `MSDev.exe`，但无可用的 `bin\msdevkernel.dll`，或 `log\simulator_main.log` 末尾有 `Error` / `不是内部或外部命令` |
| 编通（可启动） | `win\bin\msdevkernel.dll` 存在且体积通常 >数 MB；时间戳不早于本轮 `simulator_main`；日志末尾无 `make ... Error` |
| 曾跑通 | 另有 `MS_Log.txt`（非空增长）或近期 `yyyy-mm-dd HHMMSS.log`；进程能 `MSDev.exe -start` 常驻 |

多工作区对比时：各仓查上表；**以有 `msdevkernel.dll` 的仓为准**，再对照该仓 `simulator_main.log` 是否本轮成功。

## A. 客户 bat 仓

```bat
<Product>.bat 5     :: VC6 → simulator.dsw
<Product>.bat 55    :: VS2010 → MSDev2010.sln（常拷 lib\simu_VS2010）
```

等价：

```bat
make.bat p=<工程> m=simulator clean
make.bat p=<工程> m=simulator_main -j8 job=8
```

产物目录：`build\<工程>_builddir\win\`（`simulator.dsw` / `MSDev2010.sln`，`bin\MSDev.exe`，**关键** `bin\msdevkernel.dll`）。

Win10/11 上部分 bat 会设 `VS2010=1`；VC6 失败可试 `55`。

## B. Prj_mk 补丁仓 / 平台仓

用已确认的工程名（含 `_DEBUG` / `_USER`）：

```bat
make.bat p=<工程> m=simulator_main -j8 job=8
```

编前确认 PATH 含 VC6 `msdev`（或改用 VS2010/`55`），否则 make 生成 dsw 后会在调用 `msdev` 时失败，却仍可能留下模板 `MSDev.exe`。

## C. 模拟器对照树（mpphone）

仓型仍按 [REPO.md](REPO.md) §0；本节只补工程挑选与增量。

1. 在该树编译根列出 `project_UIS8910FF_mpphone_*.mk`，**请用户选工程**（勿默认某一具体工程名）。
2. 首次：`make.bat p=<工程> m=simulator_main -j8 job=8`。
3. 已有 `win\simulator.dsw` 后，仅改 MMI 可对 dsw 增量，例如：

```bat
set PATH=<VC6>\Common\MSDev98\Bin;<VC6>\VC98\Bin;%PATH%
cd /d <编译根>\build\<工程>_builddir\win
msdev simulator.dsw /MAKE "app_main - Win32 Debug" /BUILD
msdev simulator.dsw /MAKE "ctrl - Win32 Debug" /BUILD
msdev simulator.dsw /MAKE "msdevkernel - Win32 Debug" /BUILD
```

若仓内有 `.cursor\context\rebuild_sim_*.bat` / `run_sim_*.bat`，优先用。

## 启动与冒烟

```bat
cd /d <编译根>\build\<工程>_builddir\win\bin
MSDev.exe -start
```

通过：`MSDev` 进程常驻、窗口标题含 `MSDev`；`MS_Log.txt` 开始增长。失败则先核 `msdevkernel.dll` / `img\mmi_res_*.bin` / `MSSimCfg.ini` 里 skin 与 bin 路径。

常见附属：`winsimulator_tp\skin\*.png|*.ini`；资源 `img\mmi_res_*.bin`（文件名以工程为准）。

## 排障

| 问题 | 处理 |
|------|------|
| 无 `msdev`/`devenv` / 日志含「不是内部或外部命令」 | 把 VC6 `MSDev98\Bin`+`VC98\Bin` 加入 PATH，或 bat `55`；已有 dsw 时可手工 `msdev simulator.dsw /MAKE ...` |
| 无 `MSDev.exe` | 先跑通 `simulator_main`（会从 `winsimulator_tp` 拷贝） |
| 有 `MSDev.exe` 但启动失败 / 无界面逻辑 | 查是否缺少或过旧的 `msdevkernel.dll`；勿仅凭 exe 报编成功 |
| 白屏/无图 | 查 `img\mmi_res_*.bin` 与 `MSSimCfg.ini`；必要时先 `resource_main` |
| 对照树基线偏旧 | 只读对照 UI；产品逻辑在主产品仓改 |
| 编译失败 | `log\simulator_main.log` 末尾；或缩小到单个 msdev 工程（`app_main` / `ctrl` / `msdevkernel`） |

## 边界

- 模拟器产物不是真机 PAC；真机**可烧包**来自同工程 `new`/`image` 的 `img\*.pac`。本 skill 不指导烧写。
- 模拟器对照树与客户 bat 仓 / 补丁仓产品树勿混编、勿整树互拷进 git。
