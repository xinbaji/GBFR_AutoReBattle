"""
vgamepad (虚拟手柄) 输入控制实现

将键盘按键映射为 Xbox 360 手柄按钮，通过虚拟手柄驱动发送。
依赖: pip install vgamepad

注意：需要安装 ViGEmBus 驱动才能使用。
      https://github.com/nefarius/ViGEmBus/releases
"""

from time import sleep

from module.control.control_abc import ControlProvider, KeyCode, MouseButton
from module.log import Log

_log = Log("control.vgame", "i").logger

# 键盘 → 手柄按钮映射表（可扩展）
_KEY_TO_GAMEPAD: dict[str, str] = {
    "w":      "DPAD_UP",
    "a":      "DPAD_LEFT",
    "s":      "DPAD_DOWN",
    "d":      "DPAD_RIGHT",
    "space":  "A",
    "enter":  "A",
    "j":      "X",
    "k":      "Y",
    "u":      "B",
    "i":      "A",
    "esc":    "BACK",
    "tab":    "START",
    "shift":  "LEFT_SHOULDER",
    "ctrl":   "RIGHT_SHOULDER",
}


class VGameControl(ControlProvider):
    """基于 vgamepad 的虚拟手柄输入控制

    将键盘输入转换为 Xbox 360 手柄信号，适合格斗 / 动作类游戏。
    """

    def __init__(self):
        try:
            import vgamepad as vg
        except ImportError:
            raise ImportError(
                "vgamepad 未安装，请执行: pip install vgamepad"
            )
        self._vg = vg
        self._pad = vg.VX360Gamepad()
        _log.info("虚拟手柄 (Xbox 360) 初始化完成")

    def key_down(self, key: KeyCode) -> None:
        btn = self._key_to_button(key)
        if btn is None:
            return
        self._pad.press_button(btn)
        self._pad.update()

    def key_up(self, key: KeyCode) -> None:
        btn = self._key_to_button(key)
        if btn is None:
            return
        self._pad.release_button(btn)
        self._pad.update()

    def key_tap(self,
                key: KeyCode,
                times: int = 1,
                interval: float = 0.1) -> None:
        btn = self._key_to_button(key)
        if btn is None:
            return
        for _ in range(times):
            self._pad.press_button(btn)
            self._pad.update()
            sleep(0.05)
            self._pad.release_button(btn)
            self._pad.update()
            sleep(interval)

    def mouse_click(self,
                    x: int | None = None,
                    y: int | None = None,
                    button: MouseButton = "left",
                    times: int = 1,
                    interval: float = 0.1) -> None:
        # 手柄不支持鼠标操作，映射为 A 按钮
        btn = self._vg.VX360Gamepad.XUSB_GAMEPAD_A
        for _ in range(times):
            self._pad.press_button(btn)
            self._pad.update()
            sleep(0.05)
            self._pad.release_button(btn)
            self._pad.update()
            sleep(interval)

    # ----------------------------------------------------------
    #  内部
    # ----------------------------------------------------------

    def _key_to_button(self, key: KeyCode):
        """键盘键 → 手柄按钮"""
        if isinstance(key, int):
            return None  # 虚拟键码暂不支持直接映射，需扩展
        name = _KEY_TO_GAMEPAD.get(key.lower())
        if name is None:
            _log.debug("未映射的按键: '%s'", key)
            return None
        return getattr(
            self._vg.VX360Gamepad, f"XUSB_GAMEPAD_{name}", None
        )
