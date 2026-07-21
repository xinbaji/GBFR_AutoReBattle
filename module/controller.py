"""
Controller - 战斗循环控制器

组合 ScreenshotProvider + OCRProvider + ControlProvider 三大模块，
提供高层次的游戏自动化操作接口（等待文字、按键序列、热键等）。
"""

from time import sleep, time

from PIL import Image

from module.control.control_abc import ControlProvider, MouseButton
from module.control.pynput import PynputControl
from module.log import Log
from module.ocr.ocr_abc import OCRProvider
from module.ocr.rapidocr import RapidOCRProvider
from module.screenshot.screenshot_abc import ScreenshotProvider
from module.screenshot.imagegrab import ImageGrabScreenshot
from module.util import (
    HotkeyManager,
    find_window,
    focus_window,
    get_window_client_rect,
)

_log = Log("controller", "i").logger


# ----------------------------------------------------------
#  操作协议（_do_press 接受的格式）
#  ----------------------------------------------------------
#  "key"                        → 按键，无间隔(sleep 0)
#  "click"                      → 点击(200,200)，无间隔
#  ("key", delay)               → 按键，后休眠 delay 秒
#  ("click", x, y)              → 点击(x,y)，无间隔
#  ("click", x, y, delay)       → 点击(x,y)，后休眠 delay 秒
#  ("click", delay)             → 点击(200,200)，后休眠 delay 秒
# ----------------------------------------------------------


class Controller(HotkeyManager):
    """战斗循环控制器

    组合三方模块:
        ScreenshotProvider  – 截图
        OCRProvider         – 文字识别
        ControlProvider     – 键鼠输入
    """

    def __init__(self,
                 target: str,
                 region_dict: dict | None = None,
                 *,
                 screenshot: ScreenshotProvider | None = None,
                 ocr: OCRProvider | None = None,
                 control: ControlProvider | None = None,
                 ) -> None:
        super().__init__()

        # --- 注入 / 默认实现 ---
        self.screenshot = screenshot or ImageGrabScreenshot()
        self.ocr_engine = ocr or RapidOCRProvider()
        self.control = control or PynputControl()

        # --- 窗口绑定 ---
        self.target_window = target
        self.hwnd: int | None = None
        self.window_rect: tuple[int, int, int, int] | None = None

        # --- 区域配置 ---
        self.text2region = region_dict or {}
        self.target_element: dict | None = None

        _log.info("控制器初始化 | 窗口: '%s' | 截图: %s | OCR: %s | 输入: %s",
                  target,
                  type(self.screenshot).__name__,
                  type(self.ocr_engine).__name__,
                  type(self.control).__name__)

    # ============================================================
    #  窗口管理
    # ============================================================

    def get_window_rect(self) -> tuple[int, int, int, int] | None:
        """获取目标窗口客户区 (left, top, width, height)，并缓存"""
        hwnd = find_window(self.target_window)
        if hwnd is None:
            _log.warning("未找到窗口: '%s'", self.target_window)
            self.hwnd = None
            self.window_rect = None
            return None
        self.hwnd = hwnd
        self.window_rect = get_window_client_rect(hwnd)
        return self.window_rect

    def focus_window(self) -> bool:
        """聚焦目标窗口"""
        self.get_window_rect()
        if self.hwnd is None:
            _log.warning("聚焦失败，未找到窗口: '%s'", self.target_window)
            return False
        return focus_window(self.hwnd)

    # ============================================================
    #  截图（委托给 ScreenshotProvider）
    # ============================================================

    def screenshot_text(self, text: str, save: bool = False) -> Image.Image:
        """按文字关联区域截图

        :param text: 区域标识（在 region_dict 中查找）
        :param save: 是否保存 PNG
        """
        wr = self.window_rect or self.get_window_rect()
        if wr is None:
            return Image.new("RGB", (1, 1))
        left, top, width, height = wr

        if self.text2region and text in self.text2region:
            r = self.text2region[text]
            x1 = int(left + width * r[0])
            y1 = int(top + height * r[1])
            w1 = int(width * (r[2] - r[0]))
            h1 = int(height * (r[3] - r[1]))
            img = self.screenshot.screenshot_region(x1, y1, w1, h1)
        else:
            img = self.screenshot.screenshot_region(left, top, width, height)

        if save:
            ScreenshotProvider.save_png(img, prefix=text)
        return img

    def screenshot_window(self, save: bool = False) -> Image.Image | None:
        """对目标窗口截图"""
        if self.get_window_rect() is None:
            return None
        img = self.screenshot.screenshot_window(self.window_rect)
        if save and img is not None:
            ScreenshotProvider.save_png(img)
        return img

    def screenshot_full(self) -> Image.Image:
        """全屏截图"""
        return self.screenshot.screenshot_full()

    def screenshot_region(self,
                          left: int, top: int,
                          width: int, height: int) -> Image.Image:
        """区域截图"""
        return self.screenshot.screenshot_region(left, top, width, height)

    # ============================================================
    #  OCR（委托给 OCRProvider）
    # ============================================================

    def ocr(self, pic: Image.Image, confidence: float = 0.6) -> list[dict] | None:
        """对图片进行 OCR"""
        return self.ocr_engine.ocr(pic, confidence)

    # ============================================================
    #  向后兼容别名
    # ============================================================

    @property
    def running(self) -> bool:
        """战斗循环是否运行中（兼容旧 API，等价于 active）"""
        return self.active

    @running.setter
    def running(self, value: bool) -> None:
        self.active = value

    def register_hotkey(self, key: str, callback: callable) -> None:
        """注册热键（兼容旧 API）"""
        self.register(key, callback)

    def start_hotkey(self) -> None:
        """启动热键监听（兼容旧 API）"""
        self.start()

    # ============================================================
    #  输入控制（委托给 ControlProvider）
    # ============================================================

    def press(self,
              key: str | int,
              times: int = 1,
              interval: float = 0.1,
              movement: str = "press_and_release") -> None:
        """按键操作

        :param key:      键名（如 'w'）或虚拟键码
        :param times:    次数
        :param interval: 每次间隔
        :param movement: "press" / "release" / "press_and_release"
        """
        self.focus_window()
        _log.debug("按键: '%s' x%d [%s]", key, times, movement)

        for _ in range(times):
            if movement != "release":
                self.control.key_down(key)
            sleep(0.05)
            if movement != "press":
                self.control.key_up(key)
            sleep(interval)

    def click(self,
              x: int = 200, y: int = 200,
              button: MouseButton | None = None,
              key: MouseButton = "left",
              times: int = 1,
              interval: float = 0.1) -> None:
        """窗口内相对坐标点击

        自动加上窗口左上角偏移转为屏幕绝对坐标。
        :param key: 兼容旧 API，与 button 同义
        """
        btn = button or key
        _log.debug("点击: (%d, %d) x%d [%s]", x, y, times, btn)

        wr = self.window_rect
        if wr is None:
            _log.warning("窗口 rect 未知，无法点击")
            return
        self.control.mouse_click(
            x=x + wr[0], y=y + wr[1],
            button=btn, times=times, interval=interval,
        )

    # ============================================================
    #  高层游戏逻辑
    # ============================================================

    def wait(self,
             text: str,
             timeout: float = 60,
             fail_press=None,
             success_press=None,
             poll: float = 0.5) -> bool:
        """等待指定文字出现在画面中

        :param text:         目标文字
        :param timeout:      超时秒数
        :param fail_press:   每轮未匹配时执行的操作序列
        :param success_press:匹配成功后执行的操作序列
        :param poll:         轮询间隔（秒）
        :return:             是否匹配成功
        """
        _log.debug("等待文字: '%s' (超时: %ds)", text, timeout)

        self.get_window_rect()
        start_time = time()
        first_try = True

        while time() - start_time < timeout or first_try:
            first_try = False
            if not self.active:
                _log.debug("等待中断 (热键停止): '%s'", text)
                return False

            pic = self.screenshot_text(text)
            result = self.ocr(pic)

            if isinstance(result, list) and len(result) != 0:
                ocr_string = "".join(t["text"] for t in result)
                if text in ocr_string:
                    self.target_element = result[-1]
                    elapsed = time() - start_time
                    _log.debug("已找到: '%s' (%.1fs)", text, elapsed)
                    self._do_press(success_press)
                    return True

            self._do_press(fail_press)
            sleep(poll)

        _log.debug("超时未找到: '%s' (%.0fs)", text, timeout)
        return False

    def gettextposition(self, text: str) -> dict:
        """获取文字在窗口中的比例坐标"""
        result: dict = {"text": text, "region": []}

        if self.wait(text, timeout=3):
            r = self.target_element["location"]
            s = self.window_rect
            result["region"] = [
                round(r[0] / s[2], 4),
                round(r[1] / s[3], 4),
                round(r[2] / s[2], 4),
                round(r[3] / s[3], 4),
            ]
            _log.debug("文字位置: '%s' → %s", text, result["region"])

        return result

    # ============================================================
    #  操作序列执行
    # ============================================================

    def _do_press(self, press, default_interval: float = 0.3):
        """执行操作序列"""
        if press is None or len(press) == 0:
            return

        _log.debug("执行操作: %s", press)
        for item in press:
            delay = default_interval

            if isinstance(item, str):
                if item == "click":
                    self.click()
                else:
                    self.press(item)

            elif isinstance(item, tuple):
                act, *args = item
                if act == "click":
                    if not args:
                        self.click()
                    elif len(args) == 1:
                        self.click()
                        delay = args[0]
                    elif len(args) == 2:
                        self.click(args[0], args[1])
                    else:
                        self.click(args[0], args[1])
                        delay = args[2]
                else:
                    self.press(act)
                    if args:
                        delay = args[0]

            sleep(delay)


# ============================================================
#  测试入口
# ============================================================

if __name__ == "__main__":
    print("Controller 模块已就绪")
    print(f"  默认截图:  {ImageGrabScreenshot.__name__}")
    print(f"  默认 OCR:   {RapidOCRProvider.__name__}")
    print(f"  默认输入:  {PynputControl.__name__}")
