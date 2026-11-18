#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unisoc MOCOR flash partition checker.

Parse mem_cfg.h (+ build macros) and compare partition capacity / burn
addresses against compiled img binaries.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

SECTOR = 0x10000  # default; overridden by FLASH_SECTOR_SIZE if present

DEFINE_RE = re.compile(
    r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)\s*(?://.*)?$"
)
IFDEF_RE = re.compile(r"^\s*#\s*(ifdef|ifndef)\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
IF_DEFINED_RE = re.compile(
    r"^\s*#\s*(if|elif)\s+(!\s*)?defined\s*(?:\(\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\)?\s*$"
)
# Bare `#if MACRO` / `#elif MACRO` (common in spiflash_cfg.c on some trees)
IF_IDENT_RE = re.compile(r"^\s*#\s*if\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
ELIF_IDENT_RE = re.compile(r"^\s*#\s*elif\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
ELSE_RE = re.compile(r"^\s*#\s*else\b")
ENDIF_RE = re.compile(r"^\s*#\s*endif\b")
ELIF_OTHER_RE = re.compile(r"^\s*#\s*elif\b")
IF_OTHER_RE = re.compile(r"^\s*#\s*if\b")
FLASH_SIZE_MACROS = (
    "FLASH_SIZE_128MBITX64MBIT_NEW",
    "FLASH_SIZE_128MBITX128MBIT",
    "FLASH_SIZE_128MBITX64MBIT_OLD",
    "FLASH_SIZE_64MBITX128MBIT",
    "FLASH_SIZE_64MBITX64MBIT",
    "FLASH_SIZE_64MBITX32MBIT",
    "FLASH_SIZE_64MBITX8MBIT",
    "FLASH_SIZE_128MBIT",
    "FLASH_SIZE_64MBIT",
)


@dataclass
class BinInfo:
    path: Path
    size: int


@dataclass
class Partition:
    name: str
    base: Optional[int]
    size: Optional[int]
    bin_name: str = ""
    bin_size: Optional[int] = None
    note: str = ""
    download_only: bool = False  # FDL/TFBOOT etc.


@dataclass
class Report:
    root: Path
    mem_cfg: Path
    product: str
    builddir: Optional[Path]
    macros_src: str
    flash_macro: str
    macros: Dict[str, str] = field(default_factory=dict)
    values: Dict[str, int] = field(default_factory=dict)
    partitions: List[Partition] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def is_compile_root(p: Path) -> bool:
    if not p.is_dir():
        return False
    if not (p / "make.bat").is_file():
        return False
    return bool(list(p.glob("project_*.mk"))) or (p / "MS_Customize").is_dir()


def find_compile_root(start: Path) -> Path:
    """Locate MOCOR compile root for UIS8910 / L / LC / FF-S style trees.

    Prefers the nearest root: 1) start itself, 2) start/idh.code/MS_Code,
    3) walk parents the same way.
    """
    start = start.resolve()

    def consider(p: Path) -> Optional[Path]:
        if is_compile_root(p):
            return p
        ms = p / "idh.code" / "MS_Code"
        if is_compile_root(ms) or (
            ms.is_dir()
            and (
                (ms / "make.bat").is_file()
                or list(ms.glob("project_*.mk"))
            )
        ):
            return ms
        return None

    hit = consider(start)
    if hit is not None:
        return hit
    for p in start.parents:
        hit = consider(p)
        if hit is not None:
            return hit
    die(f"cannot find Unisoc compile root under {start}")


def _config_sort_key(p: Path) -> Tuple:
    name = p.parent.name.lower()
    return (
        0 if "uis8910" in name else 1,
        0 if "refphone" in name else 1,
        0 if p.name.lower() == "mem_cfg.h" else 1,
        str(p),
    )


def find_mem_cfg(root: Path) -> Optional[Path]:
    """Find partition layout source under compile root.

    Classic trees: MS_Customize/.../config/*/mem_cfg.h
    Some FF-S trees: same dir's spiflash_cfg.c (macros live there, no mem_cfg.h)
    Returns None when neither exists (e.g. pure simulator / mpphone trees).
    """
    patterns = (
        "MS_Customize/source/product/config/*/mem_cfg.h",
        "MS_Customize/source/product/config/*/spiflash_cfg.c",
    )
    preferred: List[Path] = []
    for pat in patterns:
        preferred.extend(root.glob(pat))
        if preferred and pat.endswith("mem_cfg.h"):
            break  # prefer .h when present
    if preferred:
        preferred.sort(key=_config_sort_key)
        return preferred[0]

    hits: List[Path] = []
    for pat in (
        "**/MS_Customize/source/product/config/*/mem_cfg.h",
        "**/MS_Customize/source/product/config/*/spiflash_cfg.c",
    ):
        hits = [h for h in root.glob(pat) if "build" not in h.parts]
        if hits:
            break
    if hits:
        hits.sort(key=_config_sort_key)
        return hits[0]
    return None


def list_builddirs(root: Path) -> List[Path]:
    build = root / "build"
    if not build.is_dir():
        return []
    dirs = [
        p
        for p in build.iterdir()
        if p.is_dir() and p.name.endswith("_builddir") and (p / "img").is_dir()
    ]

    def mtime(p: Path) -> float:
        img = p / "img"
        try:
            return max((f.stat().st_mtime for f in img.iterdir() if f.is_file()), default=0.0)
        except OSError:
            return 0.0

    dirs.sort(key=mtime, reverse=True)
    return dirs


def pick_builddir(root: Path, product: Optional[str]) -> Optional[Path]:
    dirs = list_builddirs(root)
    if not dirs:
        return None
    if product:
        exact = root / "build" / f"{product}_builddir"
        if exact.is_dir():
            return exact
        for d in dirs:
            if product.lower() in d.name.lower():
                return d
    return dirs[0]


def product_from_builddir(builddir: Optional[Path]) -> str:
    if not builddir:
        return ""
    name = builddir.name
    return name[: -len("_builddir")] if name.endswith("_builddir") else name


def parse_dash_d_macros(text: str) -> Set[str]:
    defined: Set[str] = set()
    for m in re.finditer(r"-D([A-Za-z_][A-Za-z0-9_]*)(?:\s|=|$)", text):
        defined.add(m.group(1))
    for m in re.finditer(
        r'--pd\s+"([A-Za-z_][A-Za-z0-9_]*)\s+SETL\s*\{\s*TRUE\s*\}"', text
    ):
        defined.add(m.group(1))
    return defined


def load_defined_macros(builddir: Optional[Path], root: Path) -> Tuple[Set[str], str]:
    defined: Set[str] = set()
    sources: List[str] = []

    search_files: List[Path] = []
    if builddir:
        tmp = builddir / "tmp"
        if tmp.is_dir():
            for name in (
                "app_main.macro",
                "sprd_macro.tmp",
                "app_main_C_MACRO_INC.txt",
                "app_main_A_MACRO_INC.txt",
            ):
                p = tmp / name
                if p.is_file():
                    search_files.append(p)
            # any other *MACRO* hints
            search_files.extend(sorted(tmp.glob("*MACRO*")))

    seen = set()
    for f in search_files:
        if f in seen:
            continue
        seen.add(f)
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        got = parse_dash_d_macros(text)
        if got:
            defined |= got
            sources.append(str(f.relative_to(root)) if f.is_relative_to(root) else str(f))

    # Config fallback: FOTA_SUPPORT = NONE → FOTA_SUPPORT_NONE
    for cfg in root.glob("*.cfg"):
        try:
            text = cfg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = re.search(
            r"^\s*FOTA_SUPPORT\s*=\s*(\w+)", text, flags=re.MULTILINE | re.IGNORECASE
        )
        if m:
            val = m.group(1).upper()
            if val == "NONE":
                defined.add("FOTA_SUPPORT_NONE")
            elif val == "ABUP":
                defined.add("FOTA_SUPPORT_ABUP")
            sources.append(f"{cfg.name}:FOTA_SUPPORT={val}")
            break

    # Flash size from product / project mk name if missing
    if not any(x in defined for x in FLASH_SIZE_MACROS):
        names = [p.name for p in root.glob("project_*.mk")]
        if builddir is not None:
            names.append(builddir.name)
        blob = " ".join(names)
        if re.search(r"_16MB_|16MB|128MBIT", blob, re.I):
            defined.add("FLASH_SIZE_128MBIT")
            sources.append("heuristic:FLASH_SIZE_128MBIT")
        elif re.search(r"_8MB_|8MB|64MBIT", blob, re.I):
            defined.add("FLASH_SIZE_64MBIT")
            sources.append("heuristic:FLASH_SIZE_64MBIT")

    return defined, ", ".join(sources[:4]) if sources else "(none)"


def active_flash_macro(defined: Set[str]) -> str:
    for name in FLASH_SIZE_MACROS:
        if name in defined:
            return name
    return "FLASH_SIZE_128MBIT"  # common default for these phones


def preprocess_defines(text: str, defined: Set[str]) -> Dict[str, str]:
    """Walk mem_cfg.h keeping #defines under active #if/#ifdef branches."""
    lines = text.splitlines()
    # stack of (parent_active, branch_taken_in_this_if, current_active)
    stack: List[Tuple[bool, bool, bool]] = [(True, True, True)]
    out: Dict[str, str] = {}

    def cur_active() -> bool:
        return stack[-1][2]

    i = 0
    while i < len(lines):
        line = lines[i]
        # strip block comments roughly for directive detection
        stripped = line.strip()

        m = IFDEF_RE.match(line)
        if m:
            kind, name = m.group(1), m.group(2)
            parent = cur_active()
            cond = (name in defined) if kind == "ifdef" else (name not in defined)
            active = parent and cond
            stack.append((parent, cond, active))
            i += 1
            continue

        m = IF_DEFINED_RE.match(line)
        if m:
            kind = m.group(1)
            neg = bool(m.group(2))
            name = m.group(3)
            cond = (name not in defined) if neg else (name in defined)
            if kind == "if":
                parent = cur_active()
                stack.append((parent, cond, parent and cond))
            else:  # elif
                parent, taken, _ = stack.pop()
                use = parent and (not taken) and cond
                stack.append((parent, taken or use, use))
            i += 1
            continue

        m = IF_IDENT_RE.match(line)
        if m:
            name = m.group(1)
            parent = cur_active()
            cond = name in defined
            stack.append((parent, cond, parent and cond))
            i += 1
            continue

        m = ELIF_IDENT_RE.match(line)
        if m:
            name = m.group(1)
            parent, taken, _ = stack.pop()
            cond = name in defined
            use = parent and (not taken) and cond
            stack.append((parent, taken or use, use))
            i += 1
            continue

        if ELSE_RE.match(line):
            parent, taken, _ = stack.pop()
            use = parent and (not taken)
            stack.append((parent, True, use))
            i += 1
            continue

        if ENDIF_RE.match(line):
            if len(stack) > 1:
                stack.pop()
            i += 1
            continue

        # Unsupported #if / #elif → treat as false branch starter / skip
        if IF_OTHER_RE.match(line):
            parent = cur_active()
            stack.append((parent, False, False))
            i += 1
            continue
        if ELIF_OTHER_RE.match(line):
            parent, taken, _ = stack.pop()
            stack.append((parent, taken, False))
            i += 1
            continue

        if cur_active():
            dm = DEFINE_RE.match(line)
            if dm:
                name, body = dm.group(1), dm.group(2).strip()
                # object-like empty define
                if body == "":
                    out[name] = "1"
                    defined.add(name)
                else:
                    # drop trailing backslash continuations (rare in mem_cfg)
                    out[name] = body
                    defined.add(name)
        i += 1

    return out


def tokenize_expr(expr: str) -> List[str]:
    expr = expr.strip()
    if expr.startswith("(") and expr.endswith(")"):
        # keep parens as tokens via regex
        pass
    tokens = re.findall(
        r"0[xX][0-9A-Fa-f]+|\d+|[A-Za-z_][A-Za-z0-9_]*|[+\-*/()]|.",
        expr,
    )
    return [t for t in tokens if not t.isspace()]


class ExprError(Exception):
    pass


def eval_expr(expr: str, env: Dict[str, int], defining: Optional[str] = None) -> int:
    tokens = tokenize_expr(expr)
    pos = 0

    def peek() -> Optional[str]:
        return tokens[pos] if pos < len(tokens) else None

    def get() -> str:
        nonlocal pos
        if pos >= len(tokens):
            raise ExprError(f"unexpected end in {expr!r}")
        t = tokens[pos]
        pos += 1
        return t

    def parse_value() -> int:
        nonlocal pos
        t = get()
        if t == "+":
            return parse_value()
        if t == "-":
            return -parse_value()
        if t == "(":
            v = parse_expr()
            if get() != ")":
                raise ExprError(f"missing ) in {expr!r}")
            return v
        if re.fullmatch(r"0[xX][0-9A-Fa-f]+", t):
            return int(t, 16)
        if re.fullmatch(r"\d+", t):
            return int(t, 10)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t):
            if defining and t == defining:
                raise ExprError(f"recursive macro {t}")
            if t not in env:
                raise ExprError(f"unknown identifier {t}")
            return env[t]
        raise ExprError(f"bad token {t!r} in {expr!r}")

    def parse_term() -> int:
        v = parse_value()
        while peek() in ("*", "/"):
            op = get()
            rhs = parse_value()
            v = v * rhs if op == "*" else int(v / rhs)
        return v

    def parse_expr() -> int:
        v = parse_term()
        while peek() in ("+", "-"):
            op = get()
            rhs = parse_term()
            v = v + rhs if op == "+" else v - rhs
        return v

    val = parse_expr()
    if pos != len(tokens):
        # tolerate trailing garbage like casts rarely present
        rest = tokens[pos:]
        if rest and rest != [""]:
            raise ExprError(f"trailing tokens {rest} in {expr!r}")
    return val


def resolve_all(macros: Dict[str, str]) -> Dict[str, int]:
    env: Dict[str, int] = {}
    pending = dict(macros)
    # Seed INVALID_FLASH_ADDR
    if "INVALID_FLASH_ADDR" not in pending:
        pending["INVALID_FLASH_ADDR"] = "(-1)"

    progress = True
    while pending and progress:
        progress = False
        for name in list(pending.keys()):
            body = pending[name]
            try:
                # If body is just another macro name or expression of knowns
                env[name] = eval_expr(body, env, defining=name)
                del pending[name]
                progress = True
            except ExprError:
                continue

    # Second pass: allow unresolved to stay missing
    return env


def fmt_addr(v: Optional[int]) -> str:
    if v is None:
        return "-"
    if v < 0:
        return "INVALID"
    return f"0x{v:08X}"


def fmt_size(v: Optional[int]) -> str:
    if v is None:
        return "-"
    if v < 0:
        return "INVALID"
    kb = v / 1024
    if abs(kb - round(kb)) < 1e-6:
        return f"{v} ( {int(round(kb))} KB )"
    return f"{v} ( {kb:.2f} KB )"


def fmt_kb(v: Optional[int]) -> str:
    if v is None:
        return "-"
    if v < 0:
        return "INVALID"
    return f"{v/1024:.2f} KB"


def find_bins(img: Path) -> Dict[str, BinInfo]:
    out: Dict[str, BinInfo] = {}
    if not img.is_dir():
        return out
    files = [f for f in img.iterdir() if f.is_file()]

    def add(key: str, path: Path) -> None:
        out[key] = BinInfo(path=path, size=path.stat().st_size)

    for f in files:
        n = f.name.lower()
        if n == "nor_bootloader.bin":
            add("BOOTLOADER", f)
        elif n == "nor_fdl1.bin":
            add("NOR_FDL1", f)
        elif n == "nor_fdl.bin":
            add("NOR_FDL", f)
        elif n == "tfboot.bin":
            add("TFBOOT", f)
        elif n == "nvitem.bin":
            add("NV", f)
        elif n.endswith("_stone.bin") or n == "stone.bin":
            add("PS", f)
        elif n.endswith("_cp.bin") or n == "cp.bin":
            add("CP", f)
        elif n.startswith("mmi_res") and n.endswith(".bin"):
            # Prefer non-QA unless only QA exists
            if "MMIRes" not in out or ("qa" in out["MMIRes"].path.name.lower() and "qa" not in n):
                add("MMIRes", f)
        elif n.endswith(".pac"):
            add("PAC", f)
    return out


def build_partitions(values: Dict[str, int], bins: Dict[str, BinInfo]) -> List[Partition]:
    def g(*names: str) -> Optional[int]:
        for n in names:
            if n in values:
                return values[n]
        return None

    ps_base = g("PS_BASE_ADDR", "AP_BASE_ADDR")
    fota_addr = g("FOTA_BOOTLOADER_ADDR")
    mmi_base = g("MMI_RES_BASE_ADDR")
    # PS capacity: space until FOTA (or MMI if FOTA size 0 / invalid)
    fota_size = g("FOTA_BOOTLOADER_SIZE") or 0
    if ps_base is not None:
        if fota_size > 0 and fota_addr is not None and fota_addr > 0:
            ps_end = fota_addr
        elif mmi_base is not None and mmi_base > 0:
            ps_end = mmi_base
        else:
            ps_end = None
        ps_size = (ps_end - ps_base) if ps_end is not None else g("AP_SIZE")
    else:
        ps_size = g("AP_SIZE")

    parts: List[Partition] = [
        Partition("BOOTLOADER", g("BOOTLOADER_BASE_ADDR"), g("BOOTLOADER_SIZE"), "nor_bootloader.bin"),
        Partition("PS", ps_base, ps_size, "*_stone.bin"),
    ]
    if fota_size and fota_size > 0:
        parts.append(
            Partition(
                "FOTA_BOOTLOADER",
                g("FOTA_BOOTLOADER_ADDR", "FOTA_BOOTLOADER_ADDR_EX"),
                fota_size,
                note="FOTA on",
            )
        )
    parts.extend(
        [
            Partition("MMIRes", mmi_base, g("MMI_RESOURCE_SIZE"), "mmi_res_*.bin"),
            Partition("CP", g("CP_BASE_ADDR"), g("CP_SIZE"), "*_cp.bin"),
            Partition(
                "IMS_TOGGLE",
                g("IMS_TOGGEL_CFG_ADDR"),
                g("IMS_TOGGEL_CFG_SIZE"),
                note="runtime/NV-ish",
            ),
            Partition(
                "CRYSTAL_AGING",
                g("CRYSTAL_AGING_ADDR"),
                g("CRYSTAL_AGING_SIZE"),
                note="runtime",
            ),
            Partition(
                "SIM_LOCK",
                g("SIM_LOCK_BASE_ADDR"),
                g("SIM_LOCK_SIZE"),
                note="runtime",
            ),
            Partition(
                "CONFIG_NV",
                g("CONFIG_NV_BASE_ADDR"),
                g("CONFIG_NV_SIZE"),
                note="runtime/NV",
            ),
            Partition(
                "OperatorData",
                g("OPERATOR_DATA_BASE_ADDR"),
                g("OPERATOR_DATA_SIZE"),
                note="runtime",
            ),
            Partition("NV", g("FIXED_NV_BASE_ADDR"), g("FIXED_NV_SIZE"), "nvitem.bin"),
            Partition(
                "PROD_INFO",
                g("PRODUCT_NV_BASE_ADDR"),
                None,
                note="inside fixnv region",
            ),
            Partition(
                "RUNNIN_NV",
                g("RUNNIN_NV_BASE_ADDR"),
                g("RUNNIN_NV_SIZE"),
                note="runtime EFS",
            ),
            Partition("UDISK", g("UDISK_BASE_ADDR"), g("UDISK_SIZE"), note="UMEM"),
        ]
    )

    # Download helpers (not NOR layout slots in the same sense)
    parts.extend(
        [
            Partition("NOR_FDL1", None, None, "nor_fdl1.bin", download_only=True, note="download helper"),
            Partition("NOR_FDL", None, None, "nor_fdl.bin", download_only=True, note="download helper"),
            Partition("TFBOOT", None, None, "tfboot.bin", download_only=True, note="download helper"),
        ]
    )

    key_map = {
        "BOOTLOADER": "BOOTLOADER",
        "PS": "PS",
        "MMIRes": "MMIRes",
        "CP": "CP",
        "NV": "NV",
        "NOR_FDL1": "NOR_FDL1",
        "NOR_FDL": "NOR_FDL",
        "TFBOOT": "TFBOOT",
    }
    for p in parts:
        bkey = key_map.get(p.name)
        if bkey and bkey in bins:
            p.bin_size = bins[bkey].size
            p.bin_name = bins[bkey].path.name
    return parts


def status_of(p: Partition) -> str:
    if p.download_only:
        if p.bin_size is None:
            return "no-bin"
        return "helper"
    if p.base is not None and p.base < 0:
        return "off"
    if p.size is None or p.size == 0:
        if p.bin_size:
            return "no-part?"
        return "empty"
    if p.bin_size is None:
        return "ok" if not p.bin_name or p.bin_name.startswith("*") or "runtime" in p.note else "no-bin"
    if p.bin_size > p.size:
        return "OVER"
    used = 100.0 * p.bin_size / p.size if p.size else 0
    if used >= 95:
        return "TIGHT"
    return "ok"


def print_report(rep: Report, as_json: bool = False) -> int:
    if as_json:
        import json

        data = {
            "root": str(rep.root),
            "mem_cfg": str(rep.mem_cfg),
            "product": rep.product,
            "builddir": str(rep.builddir) if rep.builddir else None,
            "flash_macro": rep.flash_macro,
            "macros_src": rep.macros_src,
            "values": {k: v for k, v in sorted(rep.values.items()) if k.endswith(("_ADDR", "_SIZE", "_NUM")) or k in ("PHY_FLASH_SIZE", "FLASH_SECTOR_SIZE", "AP_SIZE")},
            "partitions": [
                {
                    "name": p.name,
                    "base": p.base,
                    "size": p.size,
                    "bin": p.bin_name,
                    "bin_size": p.bin_size,
                    "status": status_of(p),
                    "note": p.note,
                }
                for p in rep.partitions
            ],
            "warnings": rep.warnings,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 1 if any(status_of(p) == "OVER" for p in rep.partitions) else 0

    print("======== Unisoc Flash Partition Check ========")
    print(f"Root       : {rep.root}")
    print(f"Layout src : {rep.mem_cfg}")
    print(f"Product    : {rep.product or '(none)'}")
    print(f"Builddir   : {rep.builddir or '(no build/*/img)'}")
    print(f"Flash macro: {rep.flash_macro}")
    print(f"Macros from: {rep.macros_src}")
    phy = rep.values.get("PHY_FLASH_SIZE")
    sec = rep.values.get("FLASH_SECTOR_SIZE", SECTOR)
    if phy is not None:
        print(f"Flash size : {fmt_addr(phy)} ({phy/1024/1024:.0f} MB), sector {fmt_addr(sec)}")
    print()

    # Layout order by base address
    layout = [
        p
        for p in rep.partitions
        if not p.download_only and p.base is not None and p.base >= 0 and (p.size or 0) >= 0
    ]
    layout.sort(key=lambda p: p.base or 0)

    print("--- NOR layout (from layout source) ---")
    print(
        f"{'Partition':<16} {'BurnAddr':<12} {'PartSize':<22} {'BinSize':<18} {'Stat':<6} Bin/Note"
    )
    print("-" * 100)
    over = False
    for p in layout:
        st = status_of(p)
        if st == "OVER":
            over = True
        bin_s = fmt_kb(p.bin_size) if p.bin_size is not None else "-"
        note = p.bin_name if p.bin_name else p.note
        print(
            f"{p.name:<16} {fmt_addr(p.base):<12} {fmt_size(p.size):<22} {bin_s:<18} {st:<6} {note}"
        )

    helpers = [p for p in rep.partitions if p.download_only]
    if helpers:
        print()
        print("--- Download helpers (PAC, not Flash layout slots) ---")
        for p in helpers:
            bin_s = fmt_kb(p.bin_size) if p.bin_size is not None else "-"
            print(f"{p.name:<16} burn=n/a       bin={bin_s:<18} {p.bin_name or '-'}")

    # Key macros summary
    print()
    print("--- Key macros ---")
    keys = [
        "BOOTLOADER_BASE_ADDR",
        "BOOTLOADER_SIZE",
        "PS_BASE_ADDR",
        "AP_BASE_ADDR",
        "AP_SIZE",
        "FOTA_BOOTLOADER_ADDR",
        "FOTA_BOOTLOADER_SIZE",
        "MMI_RES_BASE_ADDR",
        "MMI_RESOURCE_SIZE",
        "MMI_RES_SECTOR_NUM",
        "CP_BASE_ADDR",
        "CP_SIZE",
        "CP_SECTOR_SECTOR_NUM",
        "IMS_TOGGEL_CFG_ADDR",
        "CRYSTAL_AGING_ADDR",
        "SIM_LOCK_BASE_ADDR",
        "CONFIG_NV_BASE_ADDR",
        "OPERATOR_DATA_BASE_ADDR",
        "FIXED_NV_BASE_ADDR",
        "FIXED_NV_SIZE",
        "RUNNIN_NV_BASE_ADDR",
        "RUNNIN_NV_SIZE",
        "UDISK_BASE_ADDR",
        "UDISK_SIZE",
        "PHY_FLASH_START_ADDR",
        "PHY_FLASH_SIZE",
    ]
    for k in keys:
        if k in rep.values:
            v = rep.values[k]
            if k.endswith("_ADDR") or k in ("PHY_FLASH_START_ADDR",):
                print(f"  {k}={fmt_addr(v)}")
            elif k.endswith("_NUM"):
                print(f"  {k}={v}")
            else:
                print(f"  {k}={fmt_size(v)}")

    if rep.warnings:
        print()
        print("--- Warnings ---")
        for w in rep.warnings:
            print(f"  ! {w}")

    print()
    if over:
        print("RESULT: FAIL — at least one image exceeds its partition (DL1138 risk)")
        return 1
    print("RESULT: OK — compiled images fit within partition capacities (where bins exist)")
    return 0


def analyze(root: Path, product: Optional[str] = None) -> Optional[Report]:
    root = find_compile_root(root)
    mem_cfg = find_mem_cfg(root)
    if mem_cfg is None:
        print(
            "N/A: no mem_cfg.h / spiflash_cfg.c under "
            "MS_Customize/source/product/config/*/ — "
            "likely simulator/mpphone tree; partition check does not apply."
        )
        print(f"Compile root: {root}")
        return None

    builddir = pick_builddir(root, product)
    prod = product or product_from_builddir(builddir)

    defined, macros_src = load_defined_macros(builddir, root)
    flash = active_flash_macro(defined)
    # Ensure chosen flash macro is defined for preprocessor
    defined.add(flash)
    # spiflash_cfg.c often gates bootloader/UMEM behind these; enable when unknown
    # so layout macros still resolve for planning (bins still show occupancy).
    for optional in ("NOR_BOOTLOADER_SUPPORT", "UMEM_SUPPORT"):
        if optional not in defined:
            defined.add(optional)

    text = mem_cfg.read_text(encoding="utf-8", errors="ignore")
    macros = preprocess_defines(text, set(defined))
    # spiflash_cfg.c often references MAX_HW_FLASH_SIZE from spiflash_spec.h
    if mem_cfg.name.lower() == "spiflash_cfg.c":
        spec = root / "MS_Customize" / "export" / "inc" / "spiflash_spec.h"
        if spec.is_file():
            try:
                spec_macros = preprocess_defines(
                    spec.read_text(encoding="utf-8", errors="ignore"), set(defined)
                )
                merged = dict(spec_macros)
                merged.update(macros)
                macros = merged
                macros_src = (
                    f"{macros_src}, {spec.relative_to(root)}"
                    if macros_src != "(none)"
                    else str(spec.relative_to(root))
                )
            except OSError:
                pass
        # Last-resort seed if still missing (16MB / 8MB phones)
        if "MAX_HW_FLASH_SIZE" not in macros:
            if flash == "FLASH_SIZE_64MBIT":
                macros["MAX_HW_FLASH_SIZE"] = "0x00800000"
            else:
                macros["MAX_HW_FLASH_SIZE"] = "0x01000000"

    values = resolve_all(macros)
    # Some trees only define PHY_FLASH_START_ADDR for bootloader base
    if "BOOTLOADER_BASE_ADDR" not in values and "PHY_FLASH_START_ADDR" in values:
        values["BOOTLOADER_BASE_ADDR"] = values["PHY_FLASH_START_ADDR"]

    warnings: List[str] = []
    if mem_cfg.name.lower() != "mem_cfg.h":
        warnings.append(
            f"layout source is {mem_cfg.name} (no mem_cfg.h in this tree)"
        )
    needed_any = [
        ("BOOTLOADER_BASE_ADDR", "PHY_FLASH_START_ADDR"),
        ("PS_BASE_ADDR", "AP_BASE_ADDR"),
        ("MMI_RES_BASE_ADDR",),
        ("MMI_RESOURCE_SIZE",),
        ("CP_BASE_ADDR",),
        ("CP_SIZE",),
    ]
    for group in needed_any:
        if not any(n in values for n in group):
            warnings.append(
                f"failed to resolve {'/'.join(group)} (check #ifdef / macros)"
            )

    bins: Dict[str, BinInfo] = {}
    if builddir:
        bins = find_bins(builddir / "img")
        if not bins:
            warnings.append(f"no bins under {builddir / 'img'}")
    else:
        warnings.append("no build/*_builddir/img found — showing partition plan only")

    # Verify against nor_fdl embedded MMI_RES if present
    if "NOR_FDL" in bins and "MMI_RES_BASE_ADDR" in values:
        data = bins["NOR_FDL"].path.read_bytes()
        addr = int(values["MMI_RES_BASE_ADDR"]) & 0xFFFFFFFF
        ab = addr.to_bytes(4, "little")
        size_ok = False
        if "MMI_RESOURCE_SIZE" in values:
            sb = (int(values["MMI_RESOURCE_SIZE"]) & 0xFFFFFFFF).to_bytes(4, "little")
            size_ok = sb in data
        if ab not in data and not size_ok:
            warnings.append(
                f"MMI_RES_BASE_ADDR {fmt_addr(values['MMI_RES_BASE_ADDR'])} not found in nor_fdl.bin — "
                "rebuild custom_drv/nor_fdl after partition layout change"
            )

    parts = build_partitions(values, bins)
    return Report(
        root=root,
        mem_cfg=mem_cfg,
        product=prod,
        builddir=builddir,
        macros_src=macros_src,
        flash_macro=flash,
        macros=macros,
        values=values,
        partitions=parts,
        warnings=warnings,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check Unisoc mem_cfg.h partition sizes vs compiled img bins"
    )
    ap.add_argument(
        "project",
        nargs="?",
        default=".",
        help="project root or MS_Code path (default: cwd)",
    )
    ap.add_argument(
        "-p",
        "--product",
        help="product / project name (matches build/<name>_builddir)",
    )
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument(
        "--list-builddirs",
        action="store_true",
        help="list build/*_builddir and exit",
    )
    args = ap.parse_args(argv)

    root = Path(args.project).resolve()
    if not root.exists():
        die(f"path not found: {root}")

    if args.list_builddirs:
        cr = find_compile_root(root)
        dirs = list_builddirs(cr)
        print(f"Compile root: {cr}")
        if not dirs:
            print("(no build/*_builddir/img)")
            return 0
        for d in dirs:
            img = d / "img"
            pacs = list(img.glob("*.pac"))
            print(f"  {d.name}  pac={pacs[0].name if pacs else '-'}")
        return 0

    rep = analyze(root, args.product)
    if rep is None:
        return 0
    return print_report(rep, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
