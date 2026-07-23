import ctypes
import threading
from ctypes import wintypes
from time import sleep, time
import tkinter as tk
import sys
import win32api
import win32con
import win32gui
import win32ui
from PIL import Image, ImageGrab
from module.log import Log,setup_project_log
from module.rapidocr_onnxruntime import RapidOCR
import numpy as np


INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_union(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_union)]


try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass  

setup_project_log()
_log = Log("controller", "i").logger  # 新增：全局复用

class Controller:
    def __init__(self, target,project_name="Project" ,region_dict=None) -> None:
        self.run_as_admin()
        
        self.target_window = target
        self._target_hwnd: int | None = None
        self.window_rect = None
        self.text2region = region_dict
        self.project_name=project_name
        
        self._running: bool = False
        self._hotkeys: dict[int, callable] = {}
        self._hwnd_warned: bool = False
        

        
        
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        _log.info("=" * 40)
        _log.info("  %s 启动",self.project_name)
    
        _log.info("  Admin: %s", "是" if is_admin else "否")
        _log.info("=" * 40)
        if not is_admin:
            _log.warning("尝试以管理员模式启动失败，需要手动以管理员模式运行")
            _log.info("按 回车 键退出程序")
            input("")
            sys.exit(1)
        else:
            # 等待目标窗口出现
            _log.info("等待目标窗口 '%s' ...", target)
            while True:
                hwnd = self._find_window(target)
                if hwnd is not None:
                    self._target_hwnd = hwnd
                    _log.info("已找到窗口: '%s'", target)
                    break
                sleep(1)

            self._hotkey_thread: threading.Thread | None = None
            self.ocrmodel = RapidOCR()
            self._stop_event = threading.Event()
            self._rect_thread: threading.Thread | None = None
            self._start_rect_watchdog()
            self._init_toast()
            _log.info("初始化完成 | 目标窗口: '%s' | Toast: %s",
                      target, "可用" if self._tk_root is not None else "不可用")
            _log.debug("区域配置: %s 个", len(region_dict) if region_dict else 0)
    def run_as_admin(self) -> None:
        try:
            ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.argv[0],            # 原始 exe 路径
            " ".join(sys.argv[1:]), # 真正的参数
            None,
            1,)

            sys.exit(0)
    def screenshot_text(self, text):
        if self.window_rect is None:
            try:
                left, top, width, height = self.get_window_rect(silent=True)
            except TypeError:
                self.focus_window()
                left, top, width, height = self.get_window_rect(silent=True)
        else:
            left, top, width, height = self.window_rect
        if self.text2region is None or text not in self.text2region.keys():
            img = self.screenshot(region=(left, top, width, height))
        else:
            x1 = int(left + width * self.text2region[text][0])
            y1 = int(top + height * self.text2region[text][1])
            width1 = int(
                width * (self.text2region[text][2] - self.text2region[text][0])
            )
            height1 = int(
                height * (self.text2region[text][3] - self.text2region[text][1])
            )
            region = (x1, y1, width1, height1)
            img = self.screenshot(region=region)

        return img

    
    
    def screenshot(self,
        region: tuple[int, int, int, int] | None = None
    ) -> Image.Image:
        """区域截图 (left, top, width, height)

        优先按 bbox 直接截取指定区域，避免先截全虚拟桌面再裁切的性能浪费。
        - 窗口在主屏或右/下侧副屏(坐标非负)：直接 bbox 截取，高性能。
        - 窗口在左/上侧副屏(坐标为负)：Pillow 对负 bbox 有偏移 bug，
          回退为截全虚拟桌面再裁切。
        """
        if self.window_rect == None:
            self.get_window_rect()
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(self._target_hwnd)
        
        w, h = c_right - c_left, c_bottom - c_top
        hwnd_dc = win32gui.GetWindowDC(self._target_hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)
        ctypes.windll.user32.PrintWindow(self._target_hwnd, save_dc.GetSafeHdc(), 3)
        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4))
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self._target_hwnd, hwnd_dc)
        pic=Image.fromarray(img[:, :, [2,1,0,3]])
        pic.save("full.png")
        
        win_left, win_top, _, _ = self.window_rect
        r_left, r_top, r_w, r_h = region
        rel_left = max(0, r_left - win_left)           # 转相对 + 防越界
        rel_top  = max(0, r_top  - win_top)
        pic = pic.crop((rel_left, rel_top, rel_left + r_w, rel_top + r_h))
        
                
    
        
        hwnd = self._get_hwnd()
        if hwnd is not None and win32gui.IsIconic(hwnd):
            _log.warning("截图前检测到窗口最小化，尝试恢复前台窗口")
            self.focus_window()
            self.screenshot(region)

        
        
        pic.save("output.png")


        

        return pic

    def get_window_rect(self, silent: bool = False):
        hwnd = self._get_hwnd()
        if hwnd is None:
            if not silent:
                _log.warning("未找到窗口: '%s'", self.target_window)
            return None
        if win32gui.IsIconic(hwnd):
            if not silent:
                _log.debug("窗口最小化，沿用上次有效矩形: %s", self.window_rect)
            return self.window_rect
       
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        left, top = win32gui.ClientToScreen(hwnd, (c_left, c_top))
        right, bottom = win32gui.ClientToScreen(hwnd, (c_right, c_bottom))
        width = right - left
        height = bottom - top
        self.window_rect = (left, top, width, height)
        return (left, top, width, height)
    
    def _rect_watchdog(self, interval: float = 0.5) -> None:
        """后台线程：周期性刷新窗口客户区矩形，窗口移动/缩放时保持最新"""
        while not self._stop_event.is_set():
            try:
                self.get_window_rect(silent=True)
            except Exception:
                _log.debug("窗口矩形刷新异常（已忽略）", exc_info=True)
            self._stop_event.wait(interval)

    def _start_rect_watchdog(self, interval: float = 0.5) -> None:
        """启动窗口矩形监听线程（幂等，重复调用不会起多个线程）"""
        if self._rect_thread is not None and self._rect_thread.is_alive():
            return
        self._rect_thread = threading.Thread(
            target=self._rect_watchdog, args=(interval,), daemon=True
        )
        self._rect_thread.start()
        _log.debug("窗口矩形监听线程已启动 (间隔 %.1fs)", interval)

    def stop(self) -> None:
        """停止监听线程（daemon 线程也会随主进程退出，这里用于显式优雅停止）"""
        self._stop_event.set()

    def focus_window(self) -> bool:
        hwnd = self._get_hwnd()
        if hwnd is None:
            _log.warning("聚焦失败，未找到窗口: '%s'", self.target_window)
            return False

        
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
        

        return user32.GetForegroundWindow() == hwnd
    def _get_hwnd(self) -> int | None:
        """返回目标窗口句柄并缓存；窗口句柄失效时自动重新查找

        游戏窗口存活期间 hwnd 稳定，无需每次 EnumWindows 全量枚举。
        仅用 IsWindow 做一次轻量校验（微秒级），窗口被销毁/重建时才重查。
        """
        hwnd = self._target_hwnd
        if hwnd is not None and win32gui.IsWindow(hwnd):
            return hwnd
        hwnd = self._find_window(self.target_window)
        if hwnd is not None:
            self._target_hwnd = hwnd
            self._hwnd_warned = False
            return hwnd
        else:
            if not self._hwnd_warned:
                _log.warning("没有找到窗口: %s ",self.target_window)
                self._hwnd_warned = True
            if self.running == True:
                self.running=False
    
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
    #  热键系统（内部实现，外部通过 set_battle_start/stop_key 使用）
    # ============================================================
    @property
    def running(self) -> bool:
        """战斗循环是否运行中"""
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
        self._running = value

    def set_battle_start_key(self, key: str) -> None:
        """设置战斗开始快捷键（自动注册热键）
        
        :param key: 按键名 (如 'f1', 'f2')
        """
        def _on_start() -> None:
            self._running = True
            _log.info(">> %s 已启动",self.project_name)
            self._show_toast(self.project_name, "已启动")
        _log.info("按 %s 启动",key)
        self._register_hotkey(key, _on_start)

    def set_battle_stop_key(self, key: str) -> None:
        """设置战斗停止快捷键（自动注册热键）

        :param key: 按键名 (如 'f1', 'f2')
        """
        def _on_stop() -> None:
            self._running = False
            _log.info("<< %s 已停止 按启动键重新开始",self.project_name)
            self._show_toast(self.project_name, "已停止，按启动键重新开始")
        _log.info("按 %s 停止",key)
        self._register_hotkey(key, _on_stop)

    # ============================================================
    #  Win11 风格 Toast 通知（tkinter 圆角阴影 + 滑入滑出动画）
    # ============================================================
    def _init_toast(self) -> None:
        """初始化 tkinter 通知系统：在独立 daemon 线程中创建 root 并运行事件循环"""
        self._tk_root: tk.Tk | None = None
        self._tk_ready = threading.Event()

        def _tk_thread() -> None:
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                self._tk_root = root
            except Exception as e:
                msg = f"[WARN] Toast 通知不可用 (tkinter 初始化失败): {e}"
                print(msg)
                try:
                    _log.warning("Toast 通知不可用 (tkinter 初始化失败): %s", e)
                except Exception:
                    pass
                self._tk_root = None
            finally:
                self._tk_ready.set()
            if self._tk_root is not None:
                self._tk_root.mainloop()

        t = threading.Thread(target=_tk_thread, daemon=True)
        t.start()
        self._tk_ready.wait(timeout=3)

    def _show_toast(self, title: str, content: str) -> None:
        """Win11 风格通知：圆角、阴影、滑入滑出动画，总时长 5 秒，非阻塞"""
        if self._tk_root is None:
            return
        # 调度到 tk 主循环线程执行
        self._tk_root.after(0, self._create_toast, title, content)

    def _create_toast(self, title: str, content: str) -> None:
        """（在 tk 线程内运行）创建并播放一条 toast 通知"""
        

        root = self._tk_root

        # —— 样式常量 ——
        MARGIN = 16
        WIN_W = 340
        WIN_H = 90
        RADIUS = 10
        BG = "#1e1e1e"
        BORDER = "#404040"
        TITLE_FG = "#ffffff"
        TEXT_FG = "#b0b0b0"
        SHADOW_ALPHA = 0.25
        SHADOW_DX = 5
        SHADOW_DY = 5

        ENTER_MS = 600
        STAY_MS = 3800  # 5000 - 600 - 600
        EXIT_MS = 600
        ENTER_STEPS = 40  # 15ms/step → ~67fps
        EXIT_STEPS = 30   # 20ms/step → ~50fps

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        final_x = screen_w - WIN_W - MARGIN
        final_y = screen_h - WIN_H - MARGIN - 40  # 任务栏上方

        # —— 辅助：裁剪文字防溢出 ——
        def _clip(text: str, max_chars: int) -> str:
            return text if len(text) <= max_chars else text[: max_chars - 1] + "…"

        # —— 辅助：绘制圆角矩形（polygon + smooth） ——
        def _round_rect(c: tk.Canvas, **kw) -> int:
            x, y, w, h, r = 0, 0, WIN_W, WIN_H, RADIUS
            pts = [
                x + r, y, x + w - r, y,
                x + w, y, x + w, y + r,
                x + w, y + h - r, x + w, y + h,
                x + w - r, y + h, x + r, y + h,
                x, y + h, x, y + h - r,
                x, y + r, x, y,
            ]
            return c.create_polygon(pts, smooth=True, **kw)

        # ===== 阴影窗口 =====
        shadow = tk.Toplevel(root)
        shadow.overrideredirect(True)
        shadow.attributes("-topmost", True)
        shadow.attributes("-alpha", 0.0)
        shadow.configure(bg="black")
        shadow.geometry(f"{WIN_W}x{WIN_H}+{screen_w}+{final_y}")
        sh_canvas = tk.Canvas(shadow, width=WIN_W, height=WIN_H,
                              bg="black", highlightthickness=0)
        sh_canvas.pack(fill="both", expand=True)
        _round_rect(sh_canvas, fill="black", outline="")

        # ===== 主通知窗口 =====
        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.0)
        toast.configure(bg=BG)
        toast.geometry(f"{WIN_W}x{WIN_H}+{screen_w}+{final_y}")

        canvas = tk.Canvas(toast, width=WIN_W, height=WIN_H,
                           bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # 圆角背景 + 边框
        _round_rect(canvas, fill=BG, outline=BORDER, width=1)

        # 标题与内容
        title_text = _clip(title, 30)
        body_text = _clip(content, 45)
        canvas.create_text(20, 22, text=title_text, anchor="w", fill=TITLE_FG,
                           font=("Microsoft YaHei UI", 11, "bold"))
        canvas.create_text(20, 50, text=body_text, anchor="w", fill=TEXT_FG,
                           font=("Microsoft YaHei UI", 10))

        # ===== 进入动画（smoothstep ease-out） =====
        def anim_in(step: int = 0) -> None:
            if step > ENTER_STEPS:
                toast.attributes("-alpha", 1.0)
                shadow.attributes("-alpha", SHADOW_ALPHA)
                root.after(STAY_MS, anim_out)
                return
            t = step / ENTER_STEPS
            # smoothstep: 曲线两端导数为 0，无顿挫感
            eased = t * t * (3 - 2 * t)
            cx = screen_w - int((WIN_W + MARGIN) * eased)
            toast.geometry(f"+{cx}+{final_y}")
            shadow.geometry(f"+{cx + SHADOW_DX}+{final_y + SHADOW_DY}")
            toast.attributes("-alpha", eased)
            shadow.attributes("-alpha", SHADOW_ALPHA * eased)
            root.after(ENTER_MS // ENTER_STEPS, anim_in, step + 1)

        # ===== 退出动画（smoothstep ease-in） =====
        def anim_out(step: int = 0) -> None:
            if step > EXIT_STEPS:
                toast.destroy()
                shadow.destroy()
                return
            t = step / EXIT_STEPS
            eased = t * t * (3 - 2 * t)
            cx = final_x + int((MARGIN + WIN_W) * eased)
            toast.geometry(f"+{cx}+{final_y}")
            shadow.geometry(f"+{cx + SHADOW_DX}+{final_y + SHADOW_DY}")
            toast.attributes("-alpha", 1 - eased)
            shadow.attributes("-alpha", SHADOW_ALPHA * (1 - eased))
            root.after(EXIT_MS // EXIT_STEPS, anim_out, step + 1)

        anim_in()

    def _register_hotkey(self, key: str, callback: callable) -> None:
        """内部注册热键回调，首次调用自动启动监听线程

        :param key:      按键名 (如 'f1', 'f2')，需在 KEY_MAP 中存在
        :param callback: 触发时调用的无参回调函数
        """
        vk = self.KEY_MAP.get(key.lower())
        if vk is None:
            raise ValueError(f"未知的按键名: '{key}'")
        self._hotkeys[vk] = callback
        _log.debug("注册热键: '%s' (0x%02X)", key, vk)
        self._start_hotkey()

    def _start_hotkey(self) -> None:
        """启动后台热键监听线程（幂等）"""
        if self._hotkey_thread is not None:
            return
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._hotkey_thread.start()
        _log.debug("热键监听已启动")

    def _hotkey_loop(self) -> None:
        """后台线程：轮询 GetAsyncKeyState 检测热键按下"""
        prev: dict[int, bool] = {}
        while True:
            for vk, cb in list(self._hotkeys.items()):
                pressed = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                if pressed and not prev.get(vk, False):
                    _log.debug("热键触发: 0x%02X", vk)
                    cb()
                prev[vk] = pressed
            sleep(0.05)

    def ocr(self, pic:Image, confidence=0.6):
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
    def wait(
        self, text, timeout=60, fail_press=None, success_press=None, poll: float = 0.3
    ):
        """等待文字出现在画面中
        :param poll: 轮询间隔(秒)，控制截图+OCR频率，避免CPU占满导致游戏卡顿
        """
        _log.debug("等待文字: '%s' (超时: %ds)", text, timeout)

        deadline = time() + timeout

        while True:
            if not self._running:
                _log.debug("等待中断 (热键停止): '%s'", text)
                return False

            pic = self.screenshot_text(text)
            result = self.ocr(pic)

            if isinstance(result, list) and result:
                if self._find_ocr_match(result, text):
                    elapsed = time() + timeout - deadline
                    _log.debug("已找到: '%s' (%.1fs)", text, elapsed)
                    
                    self._do_press(success_press)
                    return True

            self._do_press(fail_press)
            sleep(poll)

            if time() >= deadline:
                break

        _log.debug("超时未找到: '%s' (%.0fs)", text, timeout)
        return False

    def _do_press(self, press, default_interval=0):
        """执行操作序列"""
        if not press:
            return None

        _log.debug("执行操作: %s", press)
        for item in press:
            delay = default_interval

            if isinstance(item, str):
                if item == "click":
                    self.click()
                else:
                    self.press(item)

            elif isinstance(item, tuple) and item:
                act, *args = item
                if act == "click":
                    delay = self._do_click_action(args, delay)
                else:
                    self.press(act)
                    if args:
                        delay = args[0]

            else:
                _log.warning("无效的操作项（已跳过）: %r", item)
                continue

            sleep(delay)

    def _do_click_action(self, args: list, fallback_delay: float) -> float:
        """解析 (click, ...) 元组的点击逻辑，返回延迟秒数"""
        n = len(args)
        if n == 0:
            self.click()
            return fallback_delay
        if n == 1:
            self.click()
            return args[0]  # (click, delay)
        if n == 2:
            self.click(args[0], args[1])
            return fallback_delay  # (click, x, y)
        # n >= 3
        self.click(args[0], args[1])
        return args[2]  # (click, x, y, delay)

    @staticmethod
    def _find_ocr_match(ocr_list: list[dict], text: str) -> bool:
        """在 OCR 结果列表中查找包含指定文字的条目"""
        ocr_string = ""
        for item in ocr_list:
            ocr_string += item["text"]

        if text in ocr_string:
            return True
        return False

    

    MOUSE_MAP = {
        "left": [win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP],
        "right": [win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP],
        "middle": [win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP],
        "x": [win32con.MOUSEEVENTF_XDOWN, win32con.MOUSEEVENTF_XUP],
    }

    def click(self, x=200, y=200, key="left", times=1, interval=0):
        _log.debug("点击%s: (%d, %d) x%d", key,x, y, times)
        self.focus_window()
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
        "a": 0x41,
        "b": 0x42,
        "c": 0x43,
        "d": 0x44,
        "e": 0x45,
        "f": 0x46,
        "g": 0x47,
        "h": 0x48,
        "i": 0x49,
        "j": 0x4A,
        "k": 0x4B,
        "l": 0x4C,
        "m": 0x4D,
        "n": 0x4E,
        "o": 0x4F,
        "p": 0x50,
        "q": 0x51,
        "r": 0x52,
        "s": 0x53,
        "t": 0x54,
        "u": 0x55,
        "v": 0x56,
        "w": 0x57,
        "x": 0x58,
        "y": 0x59,
        "z": 0x5A,
        # --- 主键盘数字 (也用作别名 '0'-'9') ---
        "0": 0x30,
        "1": 0x31,
        "2": 0x32,
        "3": 0x33,
        "4": 0x34,
        "5": 0x35,
        "6": 0x36,
        "7": 0x37,
        "8": 0x38,
        "9": 0x39,
        # --- 控制键 ---
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "space": 0x20,
        "spacebar": 0x20,
        "backspace": 0x08,
        "bs": 0x08,
        "tab": 0x09,
        "shift": 0x10,
        "lshift": 0xA0,
        "rshift": 0xA1,
        "ctrl": 0x11,
        "lctrl": 0xA2,
        "rctrl": 0xA3,
        "alt": 0x12,
        "lalt": 0xA4,
        "ralt": 0xA5,
        "delete": 0x2E,
        "del": 0x2E,
        "insert": 0x2D,
        "ins": 0x2D,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "capslock": 0x14,
        "numlock": 0x90,
        "scrolllock": 0x91,
        "printscreen": 0x2C,
        "pause": 0x13,
        # --- 方向键 ---
        "left": 0x25,
        "right": 0x27,
        "up": 0x26,
        "down": 0x28,
        # --- F功能键 ---
        "f1": 0x70,
        "f2": 0x71,
        "f3": 0x72,
        "f4": 0x73,
        "f5": 0x74,
        "f6": 0x75,
        "f7": 0x76,
        "f8": 0x77,
        "f9": 0x78,
        "f10": 0x79,
        "f11": 0x7A,
        "f12": 0x7B,
        # --- 小键盘 ---
        "num0": 0x60,
        "num1": 0x61,
        "num2": 0x62,
        "num3": 0x63,
        "num4": 0x64,
        "num5": 0x65,
        "num6": 0x66,
        "num7": 0x67,
        "num8": 0x68,
        "num9": 0x69,
        "num*": 0x6A,
        "num+": 0x6B,
        "num-": 0x6D,
        "num.": 0x6E,
        "num/": 0x6F,
        # --- 符号键 ---
        ";": 0xBA,
        "=": 0xBB,
        ",": 0xBC,
        "-": 0xBD,
        ".": 0xBE,
        "/": 0xBF,
        "`": 0xC0,
        "[": 0xDB,
        "\\": 0xDC,
        "]": 0xDD,
        "'": 0xDE,
    }

    # ---- SendInput 缓存（避免重复 ctypes 属性查找） ----
    _send_input = ctypes.windll.user32.SendInput
    _map_vk_to_scan = ctypes.windll.user32.MapVirtualKeyW

    @classmethod
    def _send_key(cls, vk: int, keyup: bool = False) -> None:
        scan = cls._map_vk_to_scan(vk, 0)
        flags = 0
        if scan & 0x100:  # 扩展键前缀 0xE0
            flags |= KEYEVENTF_EXTENDEDKEY
            scan &= 0xFF
        if keyup:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = scan  # 填扫描码但不设 SCANCODE 标志，与 pynput 一致
        inp.u.ki.dwFlags = flags
        cls._send_input(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def press(
        self,
        key: str,
        times: int = 1,
        interval: float = 0,
        movement: str = "press_and_release",
    ) -> None:
        """使用裸 ctypes SendInput 模拟键盘按键

        :param key:      按键名（同 KEY_MAP 中的键名）
        :param times:    连续按键次数
        :param interval: 每次按键之间的间隔（秒）
        :param movement: "press"仅按下 / "release"仅弹起 / "press_and_release"按下后弹起
        """
        vk = self.KEY_MAP.get(key.lower())
        if vk is None:
            raise ValueError(f"未知的按键名: '{key}'，请检查 KEY_MAP")

        self.focus_window()
        _log.debug("按键: '%s' (0x%02X) x%d", key, vk, times)
        for _ in range(times):
            if movement != "release":
                self._send_key(vk)
            sleep(0.01)
            if movement != "press":
                self._send_key(vk, keyup=True)
            sleep(interval)
    def start(self,func):
        times = 0
        while True:
            # 等待 F1 启动
            while not self.running:
                sleep(0.1)
    
            times += 1
            _log.info("---- 第 %d 次战斗 ----", times)
    
            func(self)
            
