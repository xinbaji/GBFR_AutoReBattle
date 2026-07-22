"""
GBFR Auto ReBattle — Win11 风格状态监控 GUI
============================================
独立模块，可配合 main.py 使用或单独测试运行。

用法:
    from gui import Win11StatusGUI

    gui = Win11StatusGUI("GBFR 自动重战", ctrl=relink)
    gui.start_in_thread()
"""

import ctypes
import os
import re
import threading
import traceback
import tkinter as tk
from typing import Optional
from datetime import datetime


# ── DPI 感知 ──
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


# ═══════════════════════════════════════════════════════════
#  配色
# ═══════════════════════════════════════════════════════════

class C:
    BG          = "#F3F3F3"
    CARD_BG     = "#FFFFFF"
    CARD_BORDER = "#E8E8E8"
    TEXT        = "#1A1A1A"
    TEXT_SEC    = "#616161"
    TEXT_DIM    = "#8A8A8A"
    ACCENT      = "#0078D4"
    ACCENT_BG   = "#E6F1FB"
    GREEN       = "#107C10"
    GREEN_BG    = "#DFF6DD"
    RED         = "#C42B1C"
    RED_BG      = "#FDE7E6"
    RED_HOVER   = "#D93732"
    YELLOW      = "#8A6D00"
    YELLOW_BG   = "#FFF4CE"
    SPINNER     = "#0078D4"
    SPINNER_TRK = "#E0E0E0"
    SEP         = "#EDEDED"
    BTN_START   = "#0078D4"
    BTN_START_H = "#106EBE"
    BTN_STOP    = "#C42B1C"
    BTN_STOP_H  = "#D93732"
    BTN_DISABLED = "#CCCCCC"


W = 400
PAD = 14
GAP = 5
CP = 16                              # 卡片内边距
ICON_SZ = 24                         # 图标/spinner 固定宽度
ICON_CH = 2                          # emoji Label 字符宽度，与 ICON_SZ 对齐

# ── 字体（模拟 Windows 设置风格，固定值不读取系统） ──
EMOJI = ("Segoe UI Emoji", 12)       # 图标 emoji
TITLE  = ("Microsoft YaHei UI", 9, "bold")   # 卡片标题（等同设置页面标题）
LABEL  = ("Microsoft YaHei UI", 9)           # 标签（管理员权限 / 操作说明）
BADGE  = ("Microsoft YaHei UI", 9, "bold")   # 徽标值（已获取/未获取）
STATUS = ("Microsoft YaHei UI", 14, "bold")  # 状态文字 + 战斗次数（大号展示）
HINT   = ("Microsoft YaHei UI", 9)           # 热键提示
BTN    = ("Microsoft YaHei UI", 9, "bold")   # 按钮
ERR    = ("Microsoft YaHei UI", 9)           # 错误信息

ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "granblue_fantasy_relink.ico")


# ═══════════════════════════════════════════════════════════
#  错误归类
# ═══════════════════════════════════════════════════════════

_ERROR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"未找到窗口|窗口.*未|EnumWindows|hwnd|窗口.*关闭|窗口.*消失", re.I),
     "游戏窗口未找到或已关闭，请确认游戏已启动"),
    (re.compile(r"ocr|识别失败|未识别到文本|rapidocr", re.I),
     "OCR 文字识别失败，检查游戏窗口是否可见且未被遮挡"),
    (re.compile(r"screenshot|截图|ImageGrab|grab", re.I),
     "截图异常，检查显示器配置及窗口状态"),
    (re.compile(r"admin|管理员|权限|IsUserAnAdmin|runas", re.I),
     "缺少管理员权限，请右键以管理员身份运行"),
    (re.compile(r"hotkey|热键|按键|press|SendInput|keybd", re.I),
     "按键模拟异常，检查是否有其他程序占用热键"),
    (re.compile(r"timeout|超时|deadline", re.I),
     "操作超时，确认游戏画面状态正常且未被遮挡"),
    (re.compile(r"最小化|minimized|IsIconic", re.I),
     "游戏窗口已最小化，恢复窗口或不要最小化"),
    (re.compile(r"AttributeError|NoneType|'None'", re.I),
     "程序内部状态异常，窗口可能未正确初始化"),
]


def _classify_error(msg: str) -> list[str]:
    causes: list[str] = []
    for pat, cause in _ERROR_PATTERNS:
        if pat.search(msg):
            causes.append(cause)
    if not causes:
        causes.append("发生了未预料的异常，请查看完整错误信息")
    return causes


# ═══════════════════════════════════════════════════════════
#  Win11StatusGUI
# ═══════════════════════════════════════════════════════════

class Win11StatusGUI:
    """Win11 风格状态监控小窗口 — 单卡片布局"""

    def __init__(self, project_name: str = "GBFR 自动重战",
                 ctrl: object = None) -> None:
        self.project_name = project_name
        self.ctrl = ctrl
        self.battle_count = 0
        self.is_admin = False
        self._running = False

        self._error_msg: str = ""
        self._error_tb: str = ""
        self._error_causes: list[str] = []
        self._error_time: str = ""
        self._error_dismissed: bool = True
        self._last_error_shown = False

        self._root: Optional[tk.Tk] = None
        self._ready = threading.Event()
        self._w: dict[str, object] = {}
        self._lock = threading.Lock()
        self._spinner_angle = 0
        self._spinner_id: Optional[str] = None

    # ═══════════════════════════════════════════════════════
    #  Public API
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def check_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def set_running(self, running: bool) -> None:
        with self._lock:
            self._running = running
        self._schedule()

    def set_error(self, exc: Exception) -> None:
        msg = str(exc) or type(exc).__name__
        tb = traceback.format_exc()
        causes = _classify_error(msg + "\n" + tb)
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._running = False
            self._error_msg = msg
            self._error_tb = tb
            self._error_causes = causes
            self._error_time = ts
            self._error_dismissed = False
        self._schedule()

    def dismiss_error(self) -> None:
        with self._lock:
            self._error_dismissed = True
        self._schedule()

    def set_battle_count(self, count: int) -> None:
        with self._lock:
            self.battle_count = count
        self._schedule()

    def set_admin_status(self, admin: bool) -> None:
        with self._lock:
            self.is_admin = admin
        self._schedule()

    # ═══════════════════════════════════════════════════════
    #  Lifecycle
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        self.is_admin = self.check_admin()
        self._build()
        self._ready.set()
        self._refresh()
        self._root.mainloop()

    def start_in_thread(self) -> None:
        t = threading.Thread(target=self.start, daemon=True, name="gui-thread")
        t.start()
        self._ready.wait(timeout=5)

    def stop(self) -> None:
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    def _schedule(self) -> None:
        if self._root:
            try:
                self._root.after(0, self._refresh)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════
    #  Build — 单卡片
    # ═══════════════════════════════════════════════════════

    def _icon_cell(self, parent: tk.Frame, emoji: str) -> tk.Label:
        """固定字符宽度的 emoji Label，高度自然不裁剪"""
        lbl = tk.Label(parent, text=emoji, bg=C.CARD_BG, font=EMOJI,
                       width=ICON_CH, anchor="center")
        return lbl

    def _build(self) -> None:
        root = tk.Tk()
        self._root = root
        root.title(self.project_name)
        root.configure(bg=C.BG)
        root.resizable(False, False)

        # Windows 默认位置
        root.geometry(f"{W}x200")
        root.minsize(W, 180)

        if os.path.exists(ICON):
            try:
                root.iconbitmap(ICON)
            except Exception:
                pass

        # ── 唯一卡片 ──
        card = tk.Frame(root, bg=C.CARD_BG,
                        highlightbackground=C.CARD_BORDER,
                        highlightthickness=1)
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # 卡片内部容器（加内边距）
        inner = tk.Frame(card, bg=C.CARD_BG)
        inner.pack(fill="both", expand=True, padx=CP, pady=(CP - 2, 0))

        # ── 标题 ──
        tk.Label(inner, text="运行状态", bg=C.CARD_BG, fg=C.TEXT_SEC,
                 font=TITLE, anchor="w").pack(fill="x", pady=(0, 6))

        # ── 第一行: [icon24] 管理员权限 — 左对齐 ──
        r1 = tk.Frame(inner, bg=C.CARD_BG)
        r1.pack(fill="x", pady=(0, 4))

        self._icon_cell(r1, "🔑").pack(side="left")
        tk.Label(r1, text="管理员权限", bg=C.CARD_BG, fg=C.TEXT,
                 font=LABEL).pack(side="left", padx=(8, 0))

        self._w["admin_badge"] = tk.Label(
            r1, text="检查中...", bg=C.CARD_BG, fg=C.TEXT,
            font=BADGE, padx=8, pady=1)
        self._w["admin_badge"].pack(side="right")

        # ── 第二行: [spinner24] 状态文字 + 战斗次数 — 左对齐 ──
        r2 = tk.Frame(inner, bg=C.CARD_BG)
        r2.pack(fill="x", pady=(6, 8))

        canvas = tk.Canvas(r2, width=ICON_SZ, height=ICON_SZ,
                           bg=C.CARD_BG, highlightthickness=0)
        canvas.pack(side="left")
        self._w["spinner"] = canvas

        sv = tk.Label(r2, text="已停止", bg=C.CARD_BG, fg=C.TEXT_DIM,
                      font=STATUS, anchor="w")
        sv.pack(side="left", padx=(8, 0))
        self._w["status_val"] = sv

        # 战斗次数 — 紧贴右侧，与状态同字体
        bc = tk.Label(r2, text="", bg=C.CARD_BG, fg=C.TEXT_DIM,
                      font=STATUS, anchor="e")
        bc.pack(side="right")
        self._w["battle_count"] = bc

        # ── 分隔 ──
        sep = tk.Frame(inner, bg=C.SEP, height=1)
        sep.pack(fill="x", pady=(0, 8))

        # ── 第三/四行: 操作说明 + 按钮 — 共享 grid 列对齐 ──
        tk.Label(inner, text="操作", bg=C.CARD_BG, fg=C.TEXT_SEC,
                 font=TITLE, anchor="w").pack(fill="x", pady=(0, 4))

        grid_frame = tk.Frame(inner, bg=C.CARD_BG)
        grid_frame.grid_columnconfigure(0, minsize=ICON_SZ)   # icon 列
        grid_frame.grid_columnconfigure(1, weight=1)           # F1 / 启动按钮
        grid_frame.grid_columnconfigure(2, weight=1)           # F2 / 暂停按钮
        grid_frame.pack(fill="x", pady=(0, CP - 4))

        # ── row 0: 热键 ──
        self._icon_cell(grid_frame, "🎮").grid(row=0, column=0, sticky="w")

        f1_area = tk.Frame(grid_frame, bg=C.CARD_BG)
        f1_area.grid(row=0, column=1, sticky="w", padx=(8, 0))
        tk.Label(f1_area, text="F1", bg=C.ACCENT_BG, fg=C.ACCENT,
                 font=("Microsoft YaHei UI", 10, "bold"),
                 padx=8, pady=1).pack(side="left")
        tk.Label(f1_area, text="启动", bg=C.CARD_BG, fg=C.TEXT_SEC,
                 font=HINT).pack(side="left", padx=(3, 0))

        f2_area = tk.Frame(grid_frame, bg=C.CARD_BG)
        f2_area.grid(row=0, column=2, sticky="w")
        tk.Label(f2_area, text="F2", bg=C.RED_BG, fg="white",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 padx=8, pady=1).pack(side="left")
        tk.Label(f2_area, text="中止", bg=C.CARD_BG, fg=C.TEXT_SEC,
                 font=HINT).pack(side="left", padx=(3, 0))

        # ── row 1: 按钮（同一 grid，列宽自动对齐） ──
        btn_start = tk.Label(grid_frame, text="▶  启动战斗",
                             bg=C.BTN_START, fg="white",
                             font=BTN, padx=14, pady=4, cursor="hand2")
        btn_start.grid(row=1, column=0, columnspan=2, sticky="ew",
                      padx=(0, 4), pady=(8, 0))
        btn_start.bind("<Button-1>", lambda e: self._on_start_click())
        btn_start.bind("<Enter>",
                       lambda e, b=btn_start: b.config(bg=C.BTN_START_H))
        btn_start.bind("<Leave>",
                       lambda e, b=btn_start: b.config(bg=C.BTN_START))
        self._w["btn_start"] = btn_start

        btn_stop = tk.Label(grid_frame, text="⏸  暂停",
                            bg=C.BTN_DISABLED, fg="white",
                            font=BTN, padx=14, pady=4, cursor="hand2")
        btn_stop.grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=(8, 0))
        btn_stop.bind("<Button-1>", lambda e: self._on_stop_click())
        self._w["btn_stop"] = btn_stop

        self._w["card"] = card
        self._w["inner"] = inner

        # ── 异常卡片（在主体卡片下方，默认隐藏） ──
        self._build_error_card(root)

        # DWM 圆角
        try:
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(ctypes.c_int(2)),
                ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

    def _build_error_card(self, parent) -> None:
        ef = tk.Frame(parent, bg=C.BG)

        ec = tk.Frame(ef, bg=C.RED_BG,
                      highlightbackground="#E0BAB0", highlightthickness=1)

        hdr = tk.Frame(ec, bg=C.RED_BG)
        hdr.pack(fill="x", padx=CP, pady=(CP - 2, 0))

        tk.Label(hdr, text="⚠️", bg=C.RED_BG, font=EMOJI).pack(side="left")
        tk.Label(hdr, text="  运行异常", bg=C.RED_BG, fg=C.RED,
                 font=TITLE).pack(side="left")

        ts_lbl = tk.Label(hdr, text="", bg=C.RED_BG, fg=C.TEXT_DIM,
                          font=LABEL)
        ts_lbl.pack(side="left", padx=(10, 0))
        self._w["err_time"] = ts_lbl

        # 关闭按钮
        dismiss = tk.Label(hdr, text="✕", bg=C.RED_BG,
                           fg=C.RED, font=("Microsoft YaHei UI", 12),
                           padx=6, cursor="hand2")
        dismiss.pack(side="right")
        dismiss.bind("<Button-1>", lambda e: self.dismiss_error())

        em = tk.Label(ec, text="", bg=C.RED_BG, fg=C.TEXT,
                      font=ERR, wraplength=W - 56, justify="left", anchor="w")
        em.pack(fill="x", padx=CP, pady=(2, 4))
        self._w["err_msg"] = em

        ecs = tk.Label(ec, text="", bg=C.RED_BG, fg=C.TEXT_SEC,
                       font=ERR, wraplength=W - 56, justify="left", anchor="w")
        ecs.pack(fill="x", padx=CP, pady=(0, 4))
        self._w["err_causes"] = ecs

        btn_bar = tk.Frame(ec, bg=C.RED_BG)
        btn_bar.pack(fill="x", padx=CP - 2, pady=(0, CP - 4))

        detail_btn = tk.Label(btn_bar, text="📋  查看完整信息",
                              bg=C.BG, fg=C.ACCENT,
                              font=LABEL, padx=10, pady=3, cursor="hand2")
        detail_btn.pack(side="right")
        detail_btn.bind("<Button-1>", lambda e: self._show_detail())
        detail_btn.bind("<Enter>",
                        lambda e: detail_btn.config(bg="#F5F5F5"))
        detail_btn.bind("<Leave>",
                        lambda e: detail_btn.config(bg=C.BG))
        self._w["detail_btn"] = detail_btn

        self._w["err_frame"] = ef
        self._w["err_card"] = ec

    # ═══════════════════════════════════════════════════════
    #  按钮事件
    # ═══════════════════════════════════════════════════════

    def _on_start_click(self) -> None:
        with self._lock:
            self._running = True
            self._error_dismissed = True
        if self.ctrl is not None:
            try:
                self.ctrl.running = True  # type: ignore[attr-defined]
            except Exception:
                pass
        self._schedule()

    def _on_stop_click(self) -> None:
        with self._lock:
            self._running = False
        if self.ctrl is not None:
            try:
                self.ctrl.running = False  # type: ignore[attr-defined]
            except Exception:
                pass
        self._schedule()

    # ═══════════════════════════════════════════════════════
    #  Refresh
    # ═══════════════════════════════════════════════════════

    def _refresh(self) -> None:
        if not self._root:
            return
        with self._lock:
            running = self._running
            count = self.battle_count
            admin = self.is_admin
            err_msg = self._error_msg
            err_causes = list(self._error_causes)
            err_time = self._error_time
            err_dismissed = self._error_dismissed

        # ── 管理员徽标 ──
        badge: tk.Label = self._w["admin_badge"]
        if admin:
            badge.config(text="已获取", fg=C.GREEN, bg=C.GREEN_BG)
        else:
            badge.config(text="未获取", fg=C.YELLOW, bg=C.YELLOW_BG)

        # ── 战斗次数（与状态同字体，靠右显示 "已战斗 N 次"） ──
        if running and count > 0:
            self._w["battle_count"].config(text=f"已战斗 {count} 次")
        else:
            self._w["battle_count"].config(text="")

        # ── 状态 ──
        sv: tk.Label = self._w["status_val"]
        bc: tk.Label = self._w["battle_count"]
        btn_start: tk.Label = self._w["btn_start"]
        btn_stop: tk.Label = self._w["btn_stop"]
        has_error = not err_dismissed and bool(err_msg)

        if running:
            sv.config(text="正在运行", fg=C.GREEN)
            bc.config(fg=C.GREEN)
            self._start_spinner()
            btn_start.config(bg=C.BTN_DISABLED, cursor="arrow")
            btn_start.unbind("<Enter>"); btn_start.unbind("<Leave>")
            btn_start.unbind("<Button-1>")
            btn_stop.config(bg=C.BTN_STOP, cursor="hand2")
            btn_stop.unbind("<Enter>"); btn_stop.unbind("<Leave>")
            btn_stop.bind("<Enter>",
                          lambda e, b=btn_stop: b.config(bg=C.BTN_STOP_H))
            btn_stop.bind("<Leave>",
                          lambda e, b=btn_stop: b.config(bg=C.BTN_STOP))
            btn_stop.bind("<Button-1>", lambda e: self._on_stop_click())
        elif has_error:
            sv.config(text="发生错误", fg=C.RED)
            bc.config(fg=C.RED)
            self._stop_spinner_error()
            btn_start.config(bg=C.BTN_DISABLED, cursor="arrow")
            btn_start.unbind("<Enter>"); btn_start.unbind("<Leave>")
            btn_start.unbind("<Button-1>")
            btn_stop.config(bg=C.BTN_DISABLED, cursor="arrow")
            btn_stop.unbind("<Enter>"); btn_stop.unbind("<Leave>")
            btn_stop.unbind("<Button-1>")
        else:
            sv.config(text="已停止", fg=C.TEXT_DIM)
            bc.config(text="", fg=C.TEXT_DIM)
            self._stop_spinner_idle()
            btn_start.config(bg=C.BTN_START, cursor="hand2")
            btn_start.unbind("<Enter>"); btn_start.unbind("<Leave>")
            btn_start.bind("<Enter>",
                           lambda e, b=btn_start: b.config(bg=C.BTN_START_H))
            btn_start.bind("<Leave>",
                           lambda e, b=btn_start: b.config(bg=C.BTN_START))
            btn_start.bind("<Button-1>", lambda e: self._on_start_click())
            btn_stop.config(bg=C.BTN_DISABLED, cursor="arrow")
            btn_stop.unbind("<Enter>"); btn_stop.unbind("<Leave>")
            btn_stop.unbind("<Button-1>")

        # ── 错误卡片 ──
        self._refresh_error(err_msg, err_causes, err_time, err_dismissed)

    def _refresh_error(self, msg: str, causes: list[str],
                       ts: str, dismissed: bool) -> None:
        ef = self._w["err_frame"]
        ec = self._w["err_card"]
        show = not dismissed and bool(msg)
        was_shown = self._last_error_shown

        if show:
            if not ef.winfo_ismapped():
                ef.pack(fill="x", padx=PAD, pady=(2, PAD))
                ec.pack(fill="x")
            short = msg[:100] + ("..." if len(msg) > 100 else "")
            self._w["err_msg"].config(text=short)
            self._w["err_causes"].config(
                text="\n".join(f"  {c}" for c in causes))
            self._w["err_time"].config(text=ts if ts else "")
        else:
            if ef.winfo_ismapped():
                ef.pack_forget()
                ec.pack_forget()

        self._last_error_shown = show

        # 自动调整窗口高度
        self._root.update_idletasks()
        if was_shown and not show:
            self._root.geometry(f"{W}x1")
            self._root.update_idletasks()
        req = self._root.winfo_reqheight()
        h = max(req, 230)
        cur_x, cur_y = self._root.winfo_x(), self._root.winfo_y()
        self._root.geometry(f"{W}x{h}+{cur_x}+{cur_y}")

    # ═══════════════════════════════════════════════════════
    #  Spinner
    # ═══════════════════════════════════════════════════════

    def _start_spinner(self) -> None:
        if self._spinner_id is not None:
            return
        self._spinner_angle = 0
        self._animate_spinner()

    def _stop_spinner_idle(self) -> None:
        if self._spinner_id is not None:
            self._root.after_cancel(self._spinner_id)
            self._spinner_id = None
        canvas = self._w["spinner"]
        canvas.delete("all")
        canvas.create_oval(3, 3, 21, 21, outline=C.TEXT_DIM,
                           width=2, tags="ring")

    def _stop_spinner_error(self) -> None:
        if self._spinner_id is not None:
            self._root.after_cancel(self._spinner_id)
            self._spinner_id = None
        canvas = self._w["spinner"]
        canvas.delete("all")
        canvas.create_oval(3, 3, 21, 21, outline=C.RED,
                           width=2, dash=(3, 2), tags="ring")
        canvas.create_line(7, 7, 17, 17, fill=C.RED, width=2, tags="x")
        canvas.create_line(17, 7, 7, 17, fill=C.RED, width=2, tags="x")

    def _animate_spinner(self) -> None:
        canvas = self._w["spinner"]
        canvas.delete("all")
        s = 24; m = 3; w = 2.5
        canvas.create_oval(m, m, s - m, s - m,
                           outline=C.SPINNER_TRK, width=w, tags="ring")
        canvas.create_arc(m, m, s - m, s - m,
                          start=self._spinner_angle, extent=280,
                          outline=C.SPINNER, width=w,
                          style="arc", tags="arc")
        self._spinner_angle = (self._spinner_angle + 18) % 360
        self._spinner_id = self._root.after(50, self._animate_spinner)

    # ═══════════════════════════════════════════════════════
    #  Error detail popup
    # ═══════════════════════════════════════════════════════

    def _show_detail(self) -> None:
        with self._lock:
            msg = self._error_msg
            tb = self._error_tb
            causes = list(self._error_causes)

        win = tk.Toplevel(self._root)
        win.title("错误详情")
        win.configure(bg=C.BG)
        win.minsize(480, 360)
        win.geometry("560x460")

        win.update_idletasks()
        px, py = self._root.winfo_x(), self._root.winfo_y()
        pw, ph = self._root.winfo_width(), self._root.winfo_height()
        win.geometry(f"+{px + (pw - 560) // 2}+{py + (ph - 460) // 2}")

        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(ctypes.c_int(2)),
                ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

        tab_frame = tk.Frame(win, bg=C.BG)
        tab_frame.pack(fill="x", padx=PAD, pady=(PAD, 0))

        tabs: dict[str, tk.Label] = {}
        pages: dict[str, tk.Frame] = {}

        def _tab(text: str, key: str) -> tk.Label:
            lbl = tk.Label(tab_frame, text=text,
                           bg=C.BG, fg=C.TEXT_SEC,
                           font=LABEL, padx=12, pady=4, cursor="hand2")
            lbl.pack(side="left", padx=(0, 2))
            tabs[key] = lbl
            return lbl

        _tab("可能原因", "causes")
        _tab("错误堆栈", "stack")

        content = tk.Frame(win, bg=C.CARD_BG,
                           highlightbackground=C.CARD_BORDER,
                           highlightthickness=1)
        content.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        page_causes = tk.Frame(content, bg=C.CARD_BG)
        clines = ("\n".join(f"  {i + 1}.  {c}" for i, c in enumerate(causes))
                  if causes else "  无法自动分析错误原因")
        tk.Label(page_causes, text=clines, bg=C.CARD_BG, fg=C.TEXT,
                 font=LABEL, justify="left", anchor="nw",
                 wraplength=520).pack(fill="both", expand=True,
                                      padx=16, pady=16)
        pages["causes"] = page_causes

        page_stack = tk.Frame(content, bg=C.CARD_BG)
        txt = tk.Text(page_stack, bg=C.BG, fg=C.TEXT,
                      insertbackground=C.TEXT,
                      font=("Cascadia Code", 9), wrap="word",
                      relief="flat", borderwidth=0,
                      padx=12, pady=10)
        sb = tk.Scrollbar(page_stack, orient="vertical",
                          command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.insert("1.0", f"错误信息:\n{msg}\n\n{'─' * 56}\n\n完整堆栈:\n{tb}")
        txt.config(state="disabled")
        pages["stack"] = page_stack

        def show_page(key):
            for k, p in pages.items():
                p.pack_forget()
            pages[key].pack(fill="both", expand=True)
            for k, lbl in tabs.items():
                lbl.config(bg=C.CARD_BG if k == key else C.BG,
                           fg=C.ACCENT if k == key else C.TEXT_SEC)

        tabs["causes"].bind("<Button-1>", lambda e: show_page("causes"))
        tabs["stack"].bind("<Button-1>", lambda e: show_page("stack"))
        show_page("causes")

        bar = tk.Frame(win, bg=C.BG, height=32)
        bar.pack(fill="x", padx=PAD, pady=(0, PAD))
        bar.pack_propagate(False)

        def _copy():
            win.clipboard_clear()
            win.clipboard_append(f"{msg}\n\n{tb}")
            copy_btn.config(text="✓  已复制")
            win.after(2000, lambda: copy_btn.config(text="📋  复制错误信息"))

        copy_btn = tk.Label(bar, text="📋  复制错误信息",
                            bg=C.CARD_BG, fg=C.ACCENT,
                            font=LABEL, padx=12, pady=4, cursor="hand2")
        copy_btn.pack(side="right")
        copy_btn.bind("<Button-1>", lambda e: _copy())
        copy_btn.bind("<Enter>",
                      lambda e: copy_btn.config(bg="#F5F5F5"))
        copy_btn.bind("<Leave>",
                      lambda e: copy_btn.config(bg=C.CARD_BG))


# ═══════════════════════════════════════════════════════════
#  单例 & 测试
# ═══════════════════════════════════════════════════════════

_GLOBAL: Optional[Win11StatusGUI] = None


def get_gui(project_name: str = "GBFR 自动重战") -> Win11StatusGUI:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = Win11StatusGUI(project_name)
        _GLOBAL.start_in_thread()
    return _GLOBAL


if __name__ == "__main__":
    import time
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    print("[TEST] 启动 GUI...")
    gui = Win11StatusGUI("GBFR 自动重战")
    gui.start_in_thread()
    time.sleep(0.6)

    gui.set_admin_status(True)
    time.sleep(0.5)

    print("[TEST] 运行中...")
    gui.set_running(True)
    gui.set_battle_count(1)
    time.sleep(0.6)
    gui.set_battle_count(2)
    time.sleep(0.6)
    gui.set_battle_count(5)

    time.sleep(1)
    print("[TEST] 暂停")
    gui.set_running(False)
    time.sleep(1.5)

    print("[TEST] 再次运行")
    gui.set_running(True)
    gui.set_battle_count(6)
    time.sleep(0.8)
    gui.set_battle_count(10)

    time.sleep(1)
    print("[TEST] 触发错误")
    try:
        raise RuntimeError(
            "OCR 文字识别超时: 未在区域 (0.733, 0.868, 0.760, 0.894) "
            "中检测到目标文字'跳跃'"
        )
    except Exception as exc:
        gui.set_error(exc)

    time.sleep(3)
    print("[TEST] 关闭错误 — 窗口应自动缩小")
    gui.dismiss_error()

    time.sleep(2)
    print("[TEST] 完成 — 10 秒后关闭")
    time.sleep(10)
    gui.stop()
