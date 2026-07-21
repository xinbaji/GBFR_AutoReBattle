"""
pywin32 输入控制实现

基于 win32 API (SendInput / keybd_event / mouse_event) 的键盘和鼠标模拟。
无需任何第三方库，直接调用系统 API。
"""

import ctypes
from time import sleep

import win32api
import win32con

from module.control.control_abc import ControlProvider, KeyCode, MouseButton
from module.log import Log

_log = Log("control.win32", "i").logger

_MOUSE_FLAGS: dict[MouseButton, tuple[int, int]] = {
    "left":   (win32con.MOUSEEVENTF_LEFTDOWN,   win32con.MOUSEEVENTF_LEFTUP),
    "right":  (win32con.MOUSEEVENTF_RIGHTDOWN,  win32con.MOUSEEVENTF_RIGHTUP),
    "middle": (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
}


class Win32Control(ControlProvider):
    """基于 win32 API 的输入控制实现

    最低层级，不依赖任何外部库，兼容性最好。
    """

    def key_down(self, key: KeyCode) -> None:
        vk = self._resolve_vk(key)
        if vk is None:
            return
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)

    def key_up(self, key: KeyCode) -> None:
        vk = self._resolve_vk(key)
        if vk is None:
            return
        ctypes.windll.user32.keybd_event(
            vk, 0, win32con.KEYEVENTF_KEYUP, 0,
        )

    def key_tap(self,
                key: KeyCode,
                times: int = 1,
                interval: float = 0.1) -> None:
        vk = self._resolve_vk(key)
        if vk is None:
            return
        for _ in range(times):
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            sleep(0.05)
            ctypes.windll.user32.keybd_event(
                vk, 0, win32con.KEYEVENTF_KEYUP, 0,
            )
            sleep(interval)

    def mouse_click(self,
                    x: int | None = None,
                    y: int | None = None,
                    button: MouseButton = "left",
                    times: int = 1,
                    interval: float = 0.1) -> None:
        down, up = _MOUSE_FLAGS[button]
        for _ in range(times):
            if x is not None and y is not None:
                ctypes.windll.user32.SetCursorPos(x, y)
            win32api.mouse_event(down, 0, 0, 0, 0)
            sleep(0.05)
            win32api.mouse_event(up, 0, 0, 0, 0)
            sleep(interval)

    # ----------------------------------------------------------
    #  内部
    # ----------------------------------------------------------

    @staticmethod
    def _resolve_vk(key: KeyCode) -> int | None:
        """解析键码 → 虚拟键码"""
        if isinstance(key, int):
            return key
        from module.util import KEY_MAP
        vk = KEY_MAP.get(key.lower())
        if vk is None:
            _log.debug("未识别的按键: '%s'", key)
        return vk
