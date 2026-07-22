"""
GBFR AutoReBattle  Nuitka 单文件 EXE 打包脚本

- 使用 Nuitka 原生编译 Python -> C -> 可执行文件
- 禁用缓存、anti-bloat 插件排除无用 stdlib
- Windows GUI 无控制台窗口，使用项目 .ico
- 排除控制台/stdlib 无用的子模块以最小化体积

使用方法:
    pip install nuitka ordered-set zstandard
    python build_exe.py

输出:
    dist/GBFR_AutoReBattle.exe
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# 强制 UTF-8 输出
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── 路径配置 ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_FILE = PROJECT_ROOT / "granblue_fantasy_relink.ico"
APP_NAME = "GBFR_AutoReBattle"
DIST_DIR = PROJECT_ROOT / "dist"


# ── 清理 ─────────────────────────────────────────────────
def cleanup() -> None:
    """清理上次构建的临时文件"""
    for name in ["build", "dist"]:
        p = PROJECT_ROOT / name
        if p.exists():
            shutil.rmtree(p)
    # 清理 Nuitka 缓存目录
    for pattern in ["*.build", "*.dist", "*.onefile-build"]:
        for p in PROJECT_ROOT.glob(pattern):
            if p.is_dir():
                shutil.rmtree(p)


# ── Nuitka 命令 ──────────────────────────────────────────
def find_nuitka():
    """查找 nuitka 可执行文件路径"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [sys.executable, "-m", "nuitka"]
    except Exception:
        pass

    which = shutil.which("nuitka")
    if which:
        return [which]
    raise RuntimeError(
        "未找到 Nuitka，请执行: pip install nuitka ordered-set zstandard"
    )


def build_command() -> list[str]:
    nuitka = find_nuitka()
    models_dir = PROJECT_ROOT / "module" / "rapidocr_onnxruntime" / "models"
    config_file = PROJECT_ROOT / "module" / "rapidocr_onnxruntime" / "config.yaml"

    cmd = nuitka + [
        # ── 输出控制 ──
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        "--enable-plugin=tk-inter",
        f"--windows-icon-from-ico={ICON_FILE}",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={APP_NAME}.exe",
        # ── 优化 ──
        "--remove-output",
        "--disable-cache=all",
        "--assume-yes-for-downloads",
        # ── 压缩由 Nuitka 4.x 自动处理，检测到 zstandard 时自动启用 ──
        # ── anti-bloat 插件：自动排除文档/示例/语言/测试等元数据 ──
        "--enable-plugin=anti-bloat",
        # ── 数据文件 ──
        f"--include-data-files={config_file}=module/rapidocr_onnxruntime/config.yaml",
        f"--include-data-dir={models_dir}=module/rapidocr_onnxruntime/models",
        # ── 隐藏导入 ──
        "--include-package=shapely",
        "--include-package=pyclipper",
        "--include-module=skimage.measure",
        "--include-package=lazy_loader",
        "--include-package=yaml",
        "--include-package=PIL",
        # ── 禁止导入控制台模块 ──
        "--nofollow-import-to=console",
        # ── 禁止导入无用 stdlib ──
        "--nofollow-import-to=asyncio",
        "--nofollow-import-to=concurrent",
        "--nofollow-import-to=csv",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=email",
        "--nofollow-import-to=ensurepip",
        "--nofollow-import-to=html",
        "--nofollow-import-to=http",
        "--nofollow-import-to=idlelib",
        "--nofollow-import-to=json",
        "--nofollow-import-to=lib2to3",
        "--nofollow-import-to=multiprocessing",
        "--nofollow-import-to=pkg_resources",
        "--nofollow-import-to=pydoc",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=socketserver",
        "--nofollow-import-to=sqlite3",
        "--nofollow-import-to=subprocess",
        "--nofollow-import-to=test",
        "--nofollow-import-to=turtledemo",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=venv",
        "--nofollow-import-to=webbrowser",
        "--nofollow-import-to=wsgiref",
        "--nofollow-import-to=xmlrpc",
        # ── 禁止导入 tkinter 无用子模块 ──
        "--noinclude-module=tkinter.ttk",
        "--noinclude-module=tkinter.scrolledtext",
        "--noinclude-module=tkinter.filedialog",
        "--noinclude-module=tkinter.messagebox",
        "--noinclude-module=tkinter.colorchooser",
        "--noinclude-module=tkinter.simpledialog",
        "--noinclude-module=tkinter.dnd",
        "--noinclude-module=tkinter.commondialog",
        # ── 禁止冗余模块 ──
        "--noinclude-module=shapely.conftest",
        # ── 禁止冗余 DLL ──
        "--noinclude-dlls=api-ms-win-*.dll",
        "--noinclude-dlls=ext-ms-win-*.dll",
        "--include-windows-runtime-dlls=no",
        # ── 入口 ──
        str(ENTRY_SCRIPT),
    ]
    return cmd


# ── 主流程 ───────────────────────────────────────────────
def main() -> None:
    # 1) 环境检查
    if not ICON_FILE.exists():
        print(f"[错误] 图标文件不存在: {ICON_FILE}")
        sys.exit(1)
    if not ENTRY_SCRIPT.exists():
        print(f"[错误] 入口脚本不存在: {ENTRY_SCRIPT}")
        sys.exit(1)

    # 2) 清理
    cleanup()

    # 3) 打包
    cmd = build_command()

    # 使用 64 位 MSVC 编译器工具集（避免 32 位编译器 C1002 堆空间不足）
    os.environ["VSCMD_ARG_TGT_ARCH"] = "x64"

    print(f"\n{'=' * 55}")
    print(f"  Nuitka 打包: {APP_NAME}.exe")
    print(f"  C 编译器: MSVC x64")
    print(f"  模式: standalone + onefile + windows (无控制台) + GUI")
    print(f"  压缩: zstd + anti-bloat + 全面瘦身")
    print(f"{'=' * 55}\n")

    subprocess.run(cmd, check=True)

    # 4) 结果
    exe = DIST_DIR / f"{APP_NAME}.exe"
    if exe.exists():
        size = exe.stat().st_size / (1024 * 1024)
        print(f"\n{'=' * 55}")
        print(f"  ✔  打包完成")
        print(f"  📁 {exe}")
        print(f"  📦 {size:.1f} MB")
        print(f"{'=' * 55}")
    else:
        print(f"\n[错误] 打包失败，{exe} 未生成")
        sys.exit(1)


if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    main()
