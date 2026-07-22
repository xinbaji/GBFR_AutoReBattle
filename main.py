# ============================================================
# GBFR Auto ReBattle — 主入口
# ============================================================

import threading
from time import sleep, time
from module.controller import Controller
from gui import Win11StatusGUI

# ============================================================
#  Relink 战斗逻辑
# ============================================================
def relink_battle(relink: Controller) -> None:
    """单次战斗 → 结算 → 再次挑战 的完整循环"""
    jump_flags = False
    skip_active = False
    last_jump_time: float = 0.0

    def jump_skip_loop() -> None:
        """后台线程：跳跃画面时持续 W+中键连点 跳过动画"""
        while True:
            if not skip_active or not relink.running:
                sleep(0.1)
                continue
            try:
                relink.press("w", movement="press")
                relink.click(key="middle", interval=0.2, times=5)
                relink.press("w", movement="release")
            except Exception:
                pass

    skip_thread = threading.Thread(target=jump_skip_loop, daemon=True)
    skip_thread.start()

    while True:
        if not relink.running:
            skip_active = False
            return

        if relink.wait("继续", timeout=0) and jump_flags:
            skip_active = False
            relink.press("enter", times=20, interval=0.1)
            break

        if relink.wait("跳跃", fail_press=["enter"], timeout=0):
            
            jump_flags = True
            skip_active = True
            last_jump_time = time()
        elif skip_active and time() - last_jump_time > 3:
            skip_active = False

    relink.wait("再次", fail_press=["enter"], timeout=30)
    while True:
        jump_flags = False
        if relink.running == False:
            return

        if relink.wait("撤销", fail_press=[("3", 0.4)], timeout=0):
            relink.press("enter", times=5,interval=0.1)
            break
        if relink.wait(
            "挑战",
            timeout=0,
        ):
            relink.press("w",interval=0.5)
            relink.press("enter", times=5,interval=0.1)
            break


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    RELINK_DICT = {
        "跳跃": [0.733, 0.8681, 0.7595, 0.8938],
        "再次": [0.1121, 0.8916, 0.1742, 0.9145],
        "撤销": [0.1121, 0.8916, 0.1742, 0.9145],
        "继续": [0.8757, 0.9312, 0.9042, 0.959],
        "挑战": [0.4489, 0.3231, 0.5578, 0.3787],
    }

    # 1. 创建 Controller
    relink = Controller("Granblue Fantasy: Relink", "GBFR 自动重战", RELINK_DICT)
    relink.set_battle_start_key("f1")
    relink.set_battle_stop_key("f2")

    # 2. 创建 GUI（传入 controller 让按钮能启停）
    gui = Win11StatusGUI("GBFR 自动重战", ctrl=relink)
    gui.start_in_thread()
    sleep(0.3)
    gui.set_admin_status(gui.check_admin())

    # 3. 后台同步线程：Controller 状态变化 → GUI 更新
    def _gui_sync():
        prev = False
        while True:
            cur = relink.running
            if cur != prev:
                gui.set_running(cur)
                prev = cur
            sleep(0.2)

    threading.Thread(target=_gui_sync, daemon=True).start()

    # 4. 包装战斗函数：统计次数 + 错误上报到 GUI
    def battle_with_gui(ctrl: Controller):
        ct = getattr(battle_with_gui, "_count", 0) + 1
        setattr(battle_with_gui, "_count", ct)
        gui.set_battle_count(ct)
        try:
            relink_battle(ctrl)
        except Exception as exc:
            gui.set_error(exc)

    battle_with_gui._count = 0  # type: ignore[attr-defined]

    relink.start(battle_with_gui)
