"""
输入控制抽象接口

定义键盘输入与鼠标点击的统一协议。
三种操作原语: key_down(按下) / key_up(弹起) / key_tap(按下与弹起) / mouse_click(点击)
"""

from abc import ABC, abstractmethod
from typing import Literal

# 统一键码类型：虚拟键码 (int) 或 键名字符串 (str)
KeyCode = int | str
MouseButton = Literal["left", "right", "middle"]


class ControlProvider(ABC):
    """输入控制抽象基类

    子类必须实现:
        key_down()     – 按下按键
        key_up()       – 弹起按键
        key_tap()      – 按下与弹起（完整一次按键）
        mouse_click()  – 鼠标点击
    """

    @abstractmethod
    def key_down(self, key: KeyCode) -> None:
        """按下按键

        :param key: 虚拟键码（int）或键名字符串（str）
        """
        ...

    @abstractmethod
    def key_up(self, key: KeyCode) -> None:
        """弹起按键

        :param key: 虚拟键码（int）或键名字符串（str）
        """
        ...

    @abstractmethod
    def key_tap(self,
                key: KeyCode,
                times: int = 1,
                interval: float = 0.1) -> None:
        """按下与弹起（完整一次按键）

        :param key:      虚拟键码（int）或键名字符串（str）
        :param times:    按键次数
        :param interval: 每次按键之间的间隔（秒）
        """
        ...

    @abstractmethod
    def mouse_click(self,
                    x: int | None = None,
                    y: int | None = None,
                    button: MouseButton = "left",
                    times: int = 1,
                    interval: float = 0.1) -> None:
        """鼠标点击（绝对屏幕坐标）

        :param x:        屏幕 X 坐标
        :param y:        屏幕 Y 坐标
        :param button:   "left" / "right" / "middle"
        :param times:    点击次数
        :param interval: 每次点击之间的间隔（秒）
        """
        ...
