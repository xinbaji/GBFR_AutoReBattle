import atexit
import ctypes
import logging
import os
import shutil
import sys
import re
from datetime import datetime


# ============================================================
#  应用根目录（兼容 PyInstaller 单文件打包）
# ============================================================
def get_app_root() -> str:
    """返回 EXE / py 文件所在的真实目录

    Nuitka onefile 模式会用引导程序解包到临时目录运行，此时
    sys.executable 指向临时目录里的 exe 副本（非原始 exe），
    因此必须用 sys.argv[0] 才能拿到用户实际运行的原始 exe 路径。
    """
    # sys.argv[0]：onefile/standalone/PyInstaller 下是原始 exe 路径；
    #              普通 Python 下是启动脚本（main.py）路径
    argv0 = os.path.abspath(sys.argv[0])
    base = os.path.basename(argv0).lower()

    # 极少数情况下 argv[0] 指向 python 解释器，回退到 __file__ 推导
    if base in ("python.exe", "pythonw.exe", "python3.exe"):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.dirname(argv0)



# ============================================================
#  Windows ANSI 颜色支持
# ============================================================
def _enable_ansi() -> None:
    """启用 Windows 10+ 控制台 ANSI 转义序列"""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

PATTERN = re.compile(
        r"[\u3400-\u4dbf"  # 汉字 扩展A
        r"\u4e00-\u9fff"  # 汉字 基本区
        r"\uf900-\ufaff"  # 汉字 兼容区
        r"\u3000-\u303f"  # 中文标点 / CJK 符号
        r"\uff00-\uffef"  # 全角数字/字母/符号
        r"\u3040-\u309f"  # 平假名
        r"\u30a0-\u30ff"  # 片假名
        r"\uff66-\uff9d"  # 半角片假名
        r"\uac00-\ud7a3"  # 韩文音节
        r"\u3130-\u318f"  # 韩文兼容字母
        r"\u1100-\u11ff]"  # 韩文 Jamo
    )
def count_cjk(text: str) -> int:
    """统计：汉字 + 中文标点 + 全角数字/字母 + 日文假名 + 韩文 的个数"""
    
    return len(PATTERN.findall(text))


_enable_ansi()


# ============================================================
#  ANSI 颜色码
# ============================================================
class C:
    """ANSI 颜色 / 样式"""

    RST = "\033[0m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GRN = "\033[32m"
    YLW = "\033[33m"
    BLU = "\033[34m"
    CYN = "\033[36m"
    B_RED = "\033[91m"
    B_YLW = "\033[93m"


# 级别 → 控制台颜色
LEVEL_COLOR: dict[str, str] = {
    "DEBUG": C.CYN,
    "INFO": C.GRN,
    "WARNING": C.B_YLW,
    "ERROR": C.RED,
    "CRITICAL": C.B_RED,
}


# ============================================================
#  格式化器
# ============================================================
class ConsoleFormatter(logging.Formatter):
    """控制台格式: [LEVEL] message │ HH:MM:SS filename:lineno"""

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLOR.get(record.levelname, C.RST)
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        lv = f"{record.levelname:<5}"
        loc = f"{record.filename}:{record.lineno}"

        # [LEVEL] message │ HH:MM:SS  file:line
        left = f"{color}[{lv}]{C.RST} {record.getMessage()}"
        right = f"{C.DIM}{ts}  {loc}{C.RST}"

        # 补齐到 60 字符宽，保证右侧对齐
        # 计算左侧可视宽度（去掉 ANSI 码）
        left_vis = len(f"[{record.levelname:<5}] {record.getMessage()}") + count_cjk(
            record.getMessage()
        )
        pad = max(2, 59 - left_vis)
        msg = f"{left}{' ' * pad}│ {right}"

        if record.exc_info and record.exc_info[0]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


# 文件格式：完整时间 + 代码位置
_FILE_FMT = logging.Formatter(
    "%(asctime)s | %(levelname)-5s | %(filename)s:%(lineno)d | %(message)s"
)


# ============================================================
#  Log 封装
# ============================================================
class Log:
    """简洁日志：控制台彩色输出

    用法:
        log = Log("app")                 # INFO 级别
        log = Log("app", mode="d")       # DEBUG 级别
        log.logger.info("任务完成")
        log.logger.error("出错")

    文件日志由 setup_project_log() 统一管理，所有 Log 实例通过
    propagate 自动汇集到 root logger 的单一 FileHandler。
    """

    def __init__(self, log_name: str, mode: str = "d") -> None:
        # --- 级别 ---
        log_level = logging.DEBUG if mode == "d" else logging.INFO

        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(log_level)
        self.logger.propagate = True  # 向上传播到 root（统一文件输出）

        # 防止重复添加 handler（多次实例化同一 logger 名时）
        if self.logger.handlers:
            self.logger.handlers.clear()

        # --- 仅控制台 Handler（彩色），不创建独立文件 ---
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        ch.setFormatter(ConsoleFormatter())
        self.logger.addHandler(ch)


# ============================================================
#  项目级统一日志文件
# ============================================================
_PROJECT_FH: logging.FileHandler | None = None


def _flush_project_log() -> None:
    """atexit 回调：确保日志文件落盘"""
    global _PROJECT_FH
    if _PROJECT_FH is not None:
        _PROJECT_FH.flush()


def setup_project_log(log_dir: str | None = None, log_name: str = "gbfr") -> str:
    """初始化项目全局日志文件（每次运行覆盖旧日志）

    调用前：
    - 删除 logs/ 目录（清除历史日志）
    - 在 root logger 上挂载单一 FileHandler（mode='w' 覆盖写）
    - 所有 Log 实例的日志通过 propagate 汇集到此文件

    :param log_dir:  日志目录路径，默认在 EXE 同级创建 logs/
    :param log_name: 日志文件名（不含扩展名）
    :return:         日志文件完整路径
    """
    global _PROJECT_FH

    root = logging.getLogger()

    # --- 清除旧 FileHandler ---
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            h.close()
            root.removeHandler(h)

    # --- 默认日志目录：EXE 同级下的 logs/ ---
    if log_dir is None:
        log_dir = os.path.join(get_app_root(), "logs")

    # --- 删除旧日志目录 ---
    if os.path.isdir(log_dir):
        shutil.rmtree(log_dir)

    # --- 创建新日志目录和文件 ---
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{log_name}.log")

    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FILE_FMT)
    root.addHandler(fh)

    _PROJECT_FH = fh
    atexit.register(_flush_project_log)

    # 用 root logger 写第一行日志标记启动
    root.setLevel(logging.DEBUG)
    root.debug("日志文件: %s", log_path)

    return log_path
