"""
pynput 输入控制实现

基于 pynput 库的键盘和鼠标模拟。
"""

from time import sleep

from pynput import keyboard as pynput_kb
from pynput import mouse as pynput_mouse

from module.control.control_abc import ControlProvider, KeyCode, MouseButton
from module.log import Log

_log = Log("control.pynput", "i").logger

# 全局复用，避免反复创建 Controller 对象
_kb = pynput_kb.Controller()
_mouse = pynput_mouse.Controller()


class PynputControl(ControlProvider):
    """基于 pynput 的输入控制实现"""

    def key_down(self, key: KeyCode) -> None:
        pk = self._resolve_key(key)
        _kb.press(pk)

    def key_up(self, key: KeyCode) -> None:
        pk = self._resolve_key(key)
        _kb.release(pk)

    def key_tap(self,
                key: KeyCode,
                times: int = 1,
                interval: float = 0.1) -> None:
        pk = self._resolve_key(key)
        for _ in range(times):
            _kb.press(pk)
            sleep(0.05)
            _kb.release(pk)
            sleep(interval)

    def mouse_click(self,
                    x: int | None = None,
                    y: int | None = None,
                    button: MouseButton = "left",
                    times: int = 1,
                    interval: float = 0.1) -> None:
        if x is not None and y is not None:
            _mouse.position = (x, y)
        btn = pynput_mouse.Button[button]
        for _ in range(times):
            _mouse.click(btn)
            sleep(interval)

    # ----------------------------------------------------------
    #  内部
    # ----------------------------------------------------------

    @staticmethod
    def _resolve_key(key: KeyCode):
        """统一解析键码 → pynput Key / KeyCode 对象"""
        if isinstance(key, int):
            return pynput_kb.KeyCode.from_vk(key)
        # 字符串：尝试 KEY_MAP 或单字符
        from module.util import KEY_MAP
        vk = KEY_MAP.get(key.lower())
        if vk is not None:
            return pynput_kb.KeyCode.from_vk(vk)
        if len(key) == 1:
            return pynput_kb.KeyCode.from_char(key)
        raise ValueError(f"未知的按键名: '{key}'")
