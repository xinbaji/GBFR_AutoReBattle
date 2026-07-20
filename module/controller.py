import ctypes
import os
import threading
from datetime import datetime
from time import sleep, time

import win32api
import win32con
import win32gui
from PIL import Image, ImageGrab
from pynput import keyboard as pynput_keyboard
from module.log import Log, get_app_root
from module.rapidocr_onnxruntime import RapidOCR

# ---- 设置进程 DPI 感知 ----
# 默认情况下非 DPI 感知进程的窗口坐标会被 Windows 按缩放比例"虚拟化"，
# 例如 2560×1440 在 150% 缩放时 GetWindowRect 只返回 1707×960。
# 设置为 Per-Monitor DPI Aware 后，所有坐标 API 均返回物理像素值。
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass  # 兼容旧版 Windows（低于 8.1）


_log = Log("controller","i").logger
_kb_controller = pynput_keyboard.Controller()    # 新增：全局复用


# ============================================================
#  虚拟键码 (Virtual-Key Codes) 速查表
# ============================================================
#  字母/数字键:
#    0x30~0x39  = '0'~'9' (主键盘)
#    0x41~0x5A  = 'A'~'Z'
#
#  功能键:
#    0x70~0x7B  = F1~F12
#
#  控制键:
#    0x0D  = ENTER (回车)
#    0x1B  = ESC
#    0x20  = SPACE (空格)
#    0x08  = BACKSPACE
#    0x09  = TAB
#    0x10  = SHIFT
#    0x11  = CTRL
#    0x12  = ALT
#    0x2E  = DELETE
#
#  方向键:
#    0x25  = LEFT
#    0x26  = UP
#    0x27  = RIGHT
#    0x28  = DOWN
#
#  小键盘 (Numpad):
#    0x60~0x69 = Numpad 0~9
#    0x6A  = Numpad *
#    0x6B  = Numpad +
#    0x6D  = Numpad -
#    0x6E  = Numpad .
#    0x6F  = Numpad /
#
#  符号键:
#    0xBA  = ; (分号)      0xBB  = = (等号)
#    0xBC  = , (逗号)      0xBD  = - (减号)
#    0xBE  = . (句号)      0xBF  = / (斜杠)
#    0xC0  = ` (反引号)    0xDB  = [ (左方括号)
#    0xDC  = \ (反斜杠)    0xDD  = ] (右方括号)
#    0xDE  = ' (单引号)
# ============================================================


class Controller:
    def __init__(self, target, region_dict) -> None:
        self.ocrmodel = RapidOCR()
        self.target_window = target
        self.window_rect = None
        self.text2region = region_dict
        self.target_element = None

        # ---- 热键 ----
        self._running: bool = False
        self._hotkeys: dict[int, callable] = {}
        self._hotkey_thread: threading.Thread | None = None

        _log.info("初始化完成 | 目标窗口: '%s'", target)
        _log.debug("区域配置: %s 个", len(region_dict) if region_dict else 0)

    def screenshot_text(self, text, save: bool = False):
        if self.window_rect is None:
            left, top, width, height = self.get_window_rect()
        else:
            left, top, width, height = self.window_rect
        if self.text2region is None or text not in self.text2region.keys():
            img = Controller.screenshot(region=(left, top, width, height))
        else:
            x1 = int(left + width * self.text2region[text][0])
            y1 = int(top + height * self.text2region[text][1])
            width1 = int(width * (self.text2region[text][2] - self.text2region[text][0]))
            height1 = int(height * (self.text2region[text][3] - self.text2region[text][1]))
            region = (x1, y1, width1, height1)
            img = Controller.screenshot(region=region)
        if save:
            self._save_png(img, prefix=text)
        return img

    @staticmethod
    def screenshot(region: tuple[int, int, int, int] | None = None,
                   save: bool = False) -> Image.Image:
        """区域截图 (left, top, width, height)

        优先按 bbox 直接截取指定区域，避免先截全虚拟桌面再裁切的性能浪费。
        - 窗口在主屏或右/下侧副屏(坐标非负)：直接 bbox 截取，高性能。
        - 窗口在左/上侧副屏(坐标为负)：Pillow 对负 bbox 有偏移 bug，
          回退为截全虚拟桌面再裁切。

        :param save: 是否同时保存 PNG 到 screenshot/ 文件夹
        """
        if region is None:
            img = ImageGrab.grab(all_screens=True)
        else:
            left, top, width, height = region
            if left >= 0 and top >= 0:
                img = ImageGrab.grab(
                    bbox=(left, top, left + width, top + height),
                    all_screens=True,
                )
            else:
                full = ImageGrab.grab(all_screens=True)
                img = full.crop((left, top, left + width, top + height))
        if save:
            Controller._save_png(img)
        return img

    def screenshot_window(self, save: bool = False) -> Image.Image | None:
        """对指定标题的窗口截图。返回 PIL Image，未找到窗口返回 None。

        :param save: 是否同时保存 PNG 到 screenshot/ 文件夹
        """
        self.get_window_rect()
        if self.window_rect is None:
            return None
        img = Controller.screenshot(region=self.window_rect)
        if save and img is not None:
            self._save_png(img)
        return img

    @staticmethod
    def _save_png(img: Image.Image, prefix: str = "screenshot") -> str:
        """将 PIL Image 保存为 PNG 到 screenshot/ 文件夹

        :param prefix: 文件名前缀
        :return:     保存的完整路径
        """
        out_dir = os.path.join(get_app_root(), "screenshot")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]  # 截断微秒到毫秒
        path = os.path.join(out_dir, f"{prefix}_{ts}.png")
        img.save(path, "PNG")
        _log.debug("截图已保存: %s", path)
        return path
    def get_window_rect(self):
        hwnd = self._find_window(self.target_window)
        if hwnd is None:
            _log.warning("未找到窗口: '%s'", self.target_window)
            return None

        # 使用客户区矩形 (GetClientRect) 获取实际游戏渲染区域（不含标题栏/边框）
        # 再通过 ClientToScreen 转换为屏幕物理坐标
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        left, top = win32gui.ClientToScreen(hwnd, (c_left, c_top))
        right, bottom = win32gui.ClientToScreen(hwnd, (c_right, c_bottom))
        width = right - left
        height = bottom - top
        self.window_rect = (left, top, width, height)
        return (left, top, width, height)
    
    def focus_window(self,interval=0) -> bool:
        
        
    
        hwnd = self._find_window(self.target_window)
        if hwnd is None:
            _log.warning("聚焦失败，未找到窗口: '%s'", self.target_window)
            return False

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # 允许任意进程设置前台窗口
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


    def _find_window(self, title: str) -> int | None:
        """按标题（不区分大小写模糊匹配）查找可见窗口句柄"""
        result: list[int] = []

        def callback(hwnd: int, _: object) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                text: str = win32gui.GetWindowText(hwnd)
                if title.lower() in text.lower():
                    result.append(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        return result[0] if result else None

    # ============================================================
    #  热键 (F1 启动 / F2 停止)
    # ============================================================
    @property
    def running(self) -> bool:
        """战斗循环是否运行中，由 F1/F2 切换"""
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
        self._running = value

    def register_hotkey(self, key: str, callback: callable) -> None:
        """注册热键回调

        :param key:     按键名 (如 'f1', 'f2')，需在 KEY_MAP 中存在
        :param callback:触发时调用的无参回调函数
        """
        vk = self.KEY_MAP.get(key.lower()) if isinstance(key, str) else key
        if vk is None:
            raise ValueError(f"未知的按键名: '{key}'")
        self._hotkeys[vk] = callback
        _log.debug("注册热键: '%s' (0x%02X)", key, vk)

    def start_hotkey(self) -> None:
        """启动后台热键监听线程"""
        if self._hotkey_thread is not None:
            return
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop, daemon=True
        )
        self._hotkey_thread.start()
        _log.debug("热键监听已启动")

    def _hotkey_loop(self) -> None:
        """后台线程：轮询 GetAsyncKeyState 检测热键按下"""
        prev: dict[int, bool] = {}
        while True:
            for vk, cb in self._hotkeys.items():
                pressed = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                if pressed and not prev.get(vk, False):
                    _log.debug("热键触发: 0x%02X", vk)
                    cb()
                prev[vk] = pressed
            sleep(0.05)

    def ocr(self, pic, confidence=0.6):
        result = self.ocrmodel(pic, use_cls=False)

        if result is None or result[0] is None or len(result[0]) == 0:
            _log.debug("OCR: 未识别到文本")
            return None

        ocr_result_list = []
        for item in result[0]:
            if item[2] > confidence:
                d = {
                    "text": item[1],
                    "location": (
                        int(item[0][0][0]) - 1,
                        int(item[0][0][1]) - 1,
                        int(item[0][2][0]) + 1,
                        int(item[0][2][1]) + 1,
                    ),
                }
                ocr_result_list.append(d)

        texts = [t["text"] for t in ocr_result_list]
        _log.debug("OCR: %d 个文本 → %s", len(ocr_result_list), texts)
        return ocr_result_list
        
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
    def wait(self, text, timeout=60, fail_press=None, success_press=None,
             poll: float = 0.5):
        """等待文字出现在画面中
        :param poll: 轮询间隔(秒)，控制截图+OCR频率，避免CPU占满导致游戏卡顿
        """
        _log.debug("等待文字: '%s' (超时: %ds)", text, timeout)
        
        self.get_window_rect()
        first_try=True
        start_time = time()
        while time() - start_time < timeout or first_try==True:
            first_try=False
            if not self._running:
                _log.debug("等待中断 (热键停止): '%s'", text)
                return False
            pic = self.screenshot_text(text)
            result = self.ocr(pic)

            if isinstance(result,list) and len(result) != 0:
                ocrstring=""
                for t in result:
                    ocrstring+=t["text"]
                if text in ocrstring:
                    self.target_element = t
                    elapsed = time() - start_time
                    _log.debug("已找到: '%s' (%.1fs)", text, elapsed)
                        
                    self._do_press(success_press)
                    return True
            
            self._do_press(fail_press)
                
            sleep(poll)
        _log.debug("超时未找到: '%s' (%.0fs)", text, timeout)
        return False

    def _do_press(self, press, default_interval=0.3):
        """执行操作序列"""
        if press is None:
            return
        if len(press) == 0:
            return
        _log.debug("执行操作: %s", press)
        for item in press:
            delay = default_interval
            if isinstance(item, str):
                
                self.click() if item in "click" else self.press(item)
            elif isinstance(item, tuple):
                act, *a = item
                if act == "click":
                    if not a:       self.click()
                    elif len(a) == 1: self.click();   delay = a[0]        # (click, d)
                    elif len(a) == 2: self.click(a[0], a[1])              # (click, x, y)
                    else:            self.click(a[0], a[1]); delay = a[2] # (click, x, y, d)
                else:
                    self.press(act)
                    if a: delay = a[0]                                    # (key, d)
            sleep(delay)
        return True
                
    def gettextposition(self, text):
        result = {"text": text, "region": []}

        if self.wait(result["text"], timeout=3):
            r = self.target_element["location"]
            s = self.window_rect
            x1 = int(r[0] / s[2] * 10000) / 10000
            y1 = int(r[1] / s[3] * 10000) / 10000
            x2 = int(r[2] / s[2] * 10000) / 10000
            y2 = int(r[3] / s[3] * 10000) / 10000

            result["region"] = [x1, y1, x2, y2]
            _log.debug("文字位置: '%s' → %s", text, result["region"])
                
    MOUSE_MAP={
            "left":[win32con.MOUSEEVENTF_LEFTDOWN,win32con.MOUSEEVENTF_LEFTUP],
            "right":[win32con.MOUSEEVENTF_RIGHTDOWN,win32con.MOUSEEVENTF_RIGHTUP],
            "middle":[win32con.MOUSEEVENTF_MIDDLEDOWN,win32con.MOUSEEVENTF_MIDDLEUP],
            "left":[win32con.MOUSEEVENTF_XDOWN,win32con.MOUSEEVENTF_XUP],
        }
    def click(self, x=200, y=200, key="left",times=1, interval=0.1):
        _log.debug("点击: (%d, %d) x%d", x, y, times)
        
        for _ in range(times):
            
            xx, yy = x + self.window_rect[0], y + self.window_rect[1]
            ctypes.windll.user32.SetCursorPos(xx, yy)
            win32api.mouse_event(self.MOUSE_MAP[key][0], xx, yy, 0, 0)
            sleep(0.1)
            win32api.mouse_event(self.MOUSE_MAP[key][1], xx, yy, 0, 0)
            sleep(interval)
    
    # 按键名字符串 → 虚拟键码映射表
    KEY_MAP: dict[str, int] = {
        # --- 字母键 ---
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
        'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
        'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
        'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
        'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
        # --- 主键盘数字 (也用作别名 '0'-'9') ---
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

    @staticmethod
    def _to_pynput_key(key: str | int):
        """把字符串键名 / 虚拟键码 转成 pynput 的 Key 对象"""
        if isinstance(key, int):
            return pynput_keyboard.KeyCode.from_vk(key)
        vk = Controller.KEY_MAP.get(key.lower())
        if vk is not None:
            return pynput_keyboard.KeyCode.from_vk(vk)
        if len(key) == 1:
            return pynput_keyboard.KeyCode.from_char(key)
        raise ValueError(f"未知的按键名: '{key}'，请检查 KEY_MAP")

    def press(self, key: str | int, times: int = 1, interval: float = 0.1,movement="press_and_release") -> None:
        """使用 pynput.keyboard 模拟键盘按键（按下+松开）"""
        self.focus_window()
        pk = self._to_pynput_key(key)
        _log.debug("按键: '%s' x%d", key, times)
        for _ in range(times):
            if movement =="release":
                pass
            else:
                _kb_controller.press(pk)
            
            sleep(0.05)
            if movement =="press":
                pass
            else:
                _kb_controller.release(pk)
            sleep(interval)
        
    

if __name__ == "__main__":
    pass