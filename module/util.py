"""
工具模块

从 Controller 抽离的杂项函数：
- DPI 感知设置
- 虚拟键码映射表 KEY_MAP
- 窗口查找 / 区域获取 / 聚焦
- 热键管理
"""

import ctypes
import threading
from time import sleep

import win32con
import win32gui

from module.log import Log

_log = Log("util", "i").logger

# ============================================================
#  DPI 感知（模块导入时自动设置）
# ============================================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass

# ============================================================
#  虚拟键码映射表
# ============================================================
KEY_MAP: dict[str, int] = {
    # --- 字母键 ---
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    # --- 主键盘数字 ---
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    # --- 控制键 ---
    'enter': 0x0D, 'return': 0x0D,
    'esc': 0x1B, 'escape': 0x1B,
    'space': 0x20, 'spacebar': 0x20,
    'backspace': 0x08, 'bs': 0x08,
    'tab': 0x09,
    'shift': 0x10, 'lshift': 0xA0, 'rshift': 0xA1,
    'ctrl': 0x11, 'lctrl': 0xA2, 'rctrl': 0xA3,
    'alt': 0x12, 'lalt': 0xA4, 'ralt': 0xA5,
    'delete': 0x2E, 'del': 0x2E,
    'insert': 0x2D, 'ins': 0x2D,
    'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pagedown': 0x22,
    'capslock': 0x14, 'numlock': 0x90, 'scrolllock': 0x91,
    'printscreen': 0x2C, 'pause': 0x13,
    # --- 方向键 ---
    'left': 0x25, 'right': 0x27, 'up': 0x26, 'down': 0x28,
    # --- F功能键 ---
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    # --- 小键盘 ---
    'num0': 0x60, 'num1': 0x61, 'num2': 0x62, 'num3': 0x63, 'num4': 0x64,
    'num5': 0x65, 'num6': 0x66, 'num7': 0x67, 'num8': 0x68, 'num9': 0x69,
    'num*': 0x6A, 'num+': 0x6B, 'num-': 0x6D, 'num.': 0x6E, 'num/': 0x6F,
    # --- 符号键 ---
    ';': 0xBA, '=': 0xBB, ',': 0xBC, '-': 0xBD, '.': 0xBE, '/': 0xBF,
    '`': 0xC0, '[': 0xDB, '\\': 0xDC, ']': 0xDD, "'": 0xDE,
}


# ============================================================
#  窗口管理
# ============================================================

def find_window(title: str) -> int | None:
    """按标题模糊匹配查找可见窗口句柄

    :param title: 窗口标题关键词（不区分大小写）
    :return:      hwnd 或 None
    """
    result: list[int] = []

    def _callback(hwnd: int, _: object) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            text: str = win32gui.GetWindowText(hwnd)
            if title.lower() in text.lower():
                result.append(hwnd)
        return True

    win32gui.EnumWindows(_callback, None)
    return result[0] if result else None


def get_window_client_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口客户区在屏幕上的 (left, top, width, height)

    使用 GetClientRect + ClientToScreen 得到不含标题栏/边框的游戏渲染区域。
    """
    c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (c_left, c_top))
    right, bottom = win32gui.ClientToScreen(hwnd, (c_right, c_bottom))
    return (left, top, right - left, bottom - top)


def focus_window(hwnd: int) -> bool:
    """将窗口提升到前台并聚焦

    :param hwnd: 窗口句柄
    :return:     是否成功
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.AllowSetForegroundWindow(-1)  # ASFW_ANY = -1

    foreground = user32.GetForegroundWindow()
    if foreground and foreground != hwnd:
        fg_thread = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(foreground, ctypes.byref(fg_thread))
        my_thread = kernel32.GetCurrentThreadId()
        if fg_thread.value:
            user32.AttachThreadInput(my_thread, fg_thread.value, True)
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
            finally:
                user32.AttachThreadInput(my_thread, fg_thread.value, False)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        user32.SetForegroundWindow(hwnd)

    return True


# ============================================================
#  通用热键管理（可脱离 Controller 独立使用）
# ============================================================

class HotkeyManager:
    """全局热键管理器

    在后台线程轮询 GetAsyncKeyState 检测热键按下。
    """

    def __init__(self) -> None:
        self._hotkeys: dict[int, callable] = {}
        self._thread: threading.Thread | None = None
        self._running: bool = False

    @property
    def active(self) -> bool:
        return self._running

    @active.setter
    def active(self, value: bool) -> None:
        self._running = value

    def register(self, key: str | int, callback: callable) -> None:
        """注册热键

        :param key:      键名（str，如 'f1'）或虚拟键码（int）
        :param callback: 触发时调用的无参回调函数
        """
        if isinstance(key, str):
            vk = KEY_MAP.get(key.lower())
            if vk is None:
                raise ValueError(f"未知的按键名: '{key}'")
        else:
            vk = key
        self._hotkeys[vk] = callback
        _log.debug("注册热键: '%s' (0x%02X)", key, vk)

    def start(self) -> None:
        """启动后台热键监听线程"""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        _log.debug("热键监听已启动")

    def _loop(self) -> None:
        """后台轮询线程"""
        prev: dict[int, bool] = {}
        while True:
            for vk, cb in self._hotkeys.items():
                pressed = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                if pressed and not prev.get(vk, False):
                    _log.debug("热键触发: 0x%02X", vk)
                    cb()
                prev[vk] = pressed
            sleep(0.05)
