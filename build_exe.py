"""
GBFR AutoReBattle  PyInstaller 单文件 EXE 打包脚本

使用方法:
    python build_exe.py

输出:
    dist/GBFR_AutoReBattle.exe
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_FILE    = PROJECT_ROOT / "granblue_fantasy_relink.ico"
APP_NAME     = "GBFR_AutoReBattle"
DIST_DIR     = PROJECT_ROOT / "dist"


# ── 辅助 ─────────────────────────────────────────────────
def find_upx() -> str | None:
    """查找 UPX 可执行文件，找不到返回 None"""
    # 1) 尝试在 PATH 中找到
    which = shutil.which("upx")
    if which:
        return which
    # 2) 尝试常见 pip 安装路径
    candidates = [
        PROJECT_ROOT / ".venv" / "Scripts" / "upx.exe",
        Path(sys.executable).parent / "Scripts" / "upx.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def cleanup() -> None:
    """清理上次构建的临时文件"""
    for name in ["build", "dist", "__pycache__"]:
        p = PROJECT_ROOT / name
        if p.exists():
            shutil.rmtree(p)
    spec = PROJECT_ROOT / f"{APP_NAME}.spec"
    if spec.exists():
        spec.unlink()


# ── 构建命令 ─────────────────────────────────────────────
def build_command() -> list[str]:
    cmd = [
        sys.executable, "-m", "PyInstaller",

        # ── 输出控制 ──
        "--onefile",                          # 单文件 EXE
        "--console",                          # 控制台程序（带日志窗口）
        f"--name={APP_NAME}",
        f"--icon={ICON_FILE}",
        "--clean",                            # 清除 PyInstaller 缓存
        "--noconfirm",                        # 覆盖输出不询问
        "--log-level=WARN",                   # 减少无害的 missing module 输出

        # ── 数据文件（ONNX 模型 + YAML 配置） ──
        f"--add-data=module{os.sep}rapidocr_onnxruntime{os.sep}config.yaml{os.pathsep}module{os.sep}rapidocr_onnxruntime",
        f"--add-data=module{os.sep}rapidocr_onnxruntime{os.sep}models{os.pathsep}module{os.sep}rapidocr_onnxruntime{os.sep}models",

        # ── 隐藏导入（部分库 PyInstaller 自动检测不到） ──
        "--hidden-import=shapely",
        "--hidden-import=shapely.geometry",
        "--hidden-import=shapely.affinity",
        "--hidden-import=pyclipper",
        "--hidden-import=skimage",
        "--hidden-import=lazy_loader",
        "--hidden-import=yaml",

        # ── 排除无用标准库（不破坏依赖的前提下压缩体积） ──
        # 注意：pickle / email / shelve 是 numpy / logging / importlib 的依赖，不可排除！
        "--exclude-module=tkinter",
        "--exclude-module=unittest",
        "--exclude-module=test",
        "--exclude-module=pydoc",
        "--exclude-module=distutils",
        "--exclude-module=setuptools",
        "--exclude-module=pkg_resources",
        "--exclude-module=html",
        "--exclude-module=http",
        "--exclude-module=xmlrpc",
        "--exclude-module=lib2to3",
        "--exclude-module=ensurepip",

        # ── 入口 ──
        str(ENTRY_SCRIPT),
    ]

    # ── UPX 压缩（如果可用） ──
    upx_path = find_upx()
    if upx_path:
        cmd.insert(5, f"--upx-dir={os.path.dirname(upx_path)}")

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

    # 3) UPX 状态
    upx = find_upx()
    if upx:
        print(f"[UPX] 可用 → {upx}")
    else:
        print("[UPX] 未检测到（Exe 体积会较大）")
        print("       安装 UPX: pip install upx  或  下载 https://upx.github.io")

    # 4) 打包
    cmd = build_command()
    print(f"\n{'=' * 55}")
    print(f"  PyInstaller 打包: {APP_NAME}.exe")
    print(f"{'=' * 55}\n")
    print(" ".join(cmd), "\n")

    subprocess.run(cmd, check=True)

    # 5) 结果
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
