import ctypes
import sys
from time import sleep
from module.controller import Controller
from module.log import Log, setup_project_log

# ---- 初始化统一日志文件（每次运行覆盖旧日志） ----
setup_project_log()

log = Log("relink", mode="i").logger


def run_as_admin() -> None:
    """以管理员权限重新启动当前程序"""
    try:
        ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,
        )
        sys.exit(0)


# ============================================================
#  Relink 战斗逻辑（纯游戏逻辑，不涉及热键）
# ============================================================
def relink_battle(relink) -> None:
    """单次战斗 → 结算 → 再次挑战 的完整循环"""
    jump_flags = True
    while True:
        if relink.running == False:
            return
        if relink.wait("继续", timeout=0) and jump_flags == False:
            relink.press("enter", times=20)
            break
        if relink.wait("跳跃", fail_press=["enter"], timeout=0):
            jump_flags = False
            relink.click(key="middle")
            relink.press("w", movement="press")
            sleep(2)
            relink.press("w", movement="release")

    relink.wait("再次", fail_press=["enter"], timeout=30)
    while True:
        jump_flags = True
        if relink.running == False:
            return

        if relink.wait("撤销", fail_press=[("3", 0.4)], timeout=0):
            relink.press("enter", times=5)
            break
        if relink.wait(
            "挑战",
            timeout=0,
        ):
            relink.press("w")
            sleep(0.5)
            relink.press("enter", times=5)
            break


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    run_as_admin()

    RELINK_DICT = {
        "跳跃": [0.733, 0.8681, 0.7595, 0.8938],
        "再次": [0.1121, 0.8916, 0.1742, 0.9145],
        "撤销": [0.1121, 0.8916, 0.1742, 0.9145],
        "继续": [0.8757, 0.9312, 0.9042, 0.959],
        "挑战": [0.4489, 0.3231, 0.5578, 0.3787],
    }

    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    log.info("=" * 40)
    log.info("  GBFR 自动重战 启动")

    log.info("  Admin: %s", "是" if is_admin else "否")
    log.info("=" * 40)

    relink = Controller("Granblue Fantasy: Relink", RELINK_DICT)

    # ---- 注册热键 ----
    def on_f1():
        log.info(">> 战斗循环启动")
        relink.running = True

    def on_f2():
        relink.running = False

    relink.register_hotkey("f1", on_f1)
    relink.register_hotkey("f2", on_f2)
    relink.start_hotkey()

    log.info("按 F1 开始战斗循环, F2 停止")

    times = 0
    while True:
        # 等待 F1 启动
        while not relink.running:
            sleep(0.1)

        times += 1
        log.info("---- 第 %d 次战斗 ----", times)

        relink_battle(relink)

        # 如果 F2 被按下，running 为 False，退出战斗循环
        if not relink.running:
            log.info("<< 战斗循环停止 按 F1 重新开始")
