# ============================================================
# GBFR Auto ReBattle — 主入口
# ============================================================

import threading
from time import sleep, time
from module.controller import Controller
from module.log import Log
import argparse

# ============================================================
#  Relink 战斗逻辑
# ============================================================
def relink_battle(relink: Controller) -> None:
    """单次战斗 → 结算 → 再次挑战 的完整循环"""
    battle_active = False
    last_jump_time: float = 0.0
    fast_skip_remaining_times= 0
    fast_skip_active=False
    jump_flags=True
    def skip_result() ->None:
        while True:
            if not fast_skip_active or not relink.running or battle_active:
                sleep(0.1)
                continue
            try:
                relink.press("enter",interval=0.1)
            except Exception:
                pass
            
    def battle_loop() -> None:
        """后台线程：跳跃画面时持续 W+中键连点 跳过动画"""
        while True:
            if not battle_active or not relink.running:
                sleep(0.1)
                continue
            try:
                relink.press("w", movement="press")
                relink.click(key="middle", interval=0.5, times=3)
                relink.press("w", movement="release")
            except Exception:
                 pass
    
    battle_thread = threading.Thread(target=battle_loop, daemon=True)
    battle_thread.start()
    skip_result_thread = threading.Thread(target=skip_result, daemon=True)
    skip_result_thread.start()
    times = 1
    while True:
        if not relink.running:
            battle_active = False
            fast_skip_active =False
            return
        
        while True:
            if not relink.running:
                battle_active = False
                fast_skip_active =False
                return
            if relink.wait("跳跃", fail_press=["enter"], timeout=0):
                fast_skip_active=False
                battle_active = True
                last_jump_time = time()
            elif battle_active and time() - last_jump_time > 3:
                battle_active = False
                log.info("--- 第 %d 场战斗结算 ---",times)
                times+=1
                break
            
        while True:
            if relink.running == False:
                return
            if fast_skip_remaining_times>0:
                fast_skip_active=True
                break
            
            if relink.wait("再次",fail_press=["enter"],timeout=1800):
                break
                
        while True:
            
            if relink.running == False:
                return
            
            if fast_skip_remaining_times>0 and jump_flags:
                fast_skip_remaining_times -=1
                break
            
            if not relink.wait("撤销", timeout=0):
                
                relink.press("3",interval=0.5)
                fast_skip_remaining_times=8
                jump_flags=False
                
                
            else:
                
                fast_skip_active=True
                break
            if relink.wait("挑战",timeout=0):
                relink.press("enter")
                while relink.wait("挑战",timeout=0):
                    relink.press("enter")
            if relink.wait("结算",timeout=0):
                relink.press("enter")
                while relink.wait("结算",timeout=0):
                    relink.press("enter")
                
        jump_flags=True
                
        


        
def relink_battle_silent(relink: Controller):
    
        
        times = 1
        
        log.info("--- 第 %d 场战斗开始 ---",times)
        while True:
            if relink.running == False:
                return
            
            if relink.wait("再次",timeout=0):
                break
                
        while True:
            
            if relink.running == False:
                return
            
            
            if not relink.wait("撤销", timeout=0):
                
                relink.press("3",interval=0.5)
                
                
            else:
                relink.press("enter",times=6,interval=0.1)
                break
            if relink.wait("挑战",timeout=0):
                relink.press("enter")
                while relink.wait("挑战",timeout=0):
                    relink.press("enter")
            if relink.wait("结算",timeout=0):
                relink.press("enter")
                while relink.wait("结算",timeout=0):
                    relink.press("enter")
                
            
    
def parse_args():
    parser = argparse.ArgumentParser(
        prog="GBFR_AutoReBattle",
        description="GBFR 自动重战工具",
    )
    parser.add_argument("--silent", action="store_true",
                        help="静默模式")
    return parser.parse_args()

# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    args = parse_args()
    RELINK_DICT = {
        "跳跃": [0.733, 0.8681, 0.7595, 0.8938],
        "再次": [0.1121, 0.8916, 0.1742, 0.9145],
        "撤销": [0.1121, 0.8916, 0.1742, 0.9145],
        "结算": [0.4489, 0.3231, 0.5578, 0.3787],
        "挑战": [0.4489, 0.3231, 0.5578, 0.3787],
    }

    # 1. 创建 Controller
    relink = Controller("Granblue Fantasy: Relink", "GBFR 自动重战", RELINK_DICT)
    log=Log("GBFR","i").logger
    relink.set_battle_start_key("f1")
    relink.set_battle_stop_key("f2")

    # 2. 直接启动战斗循环（控制台模式）
    if args.silent:
        relink.show_toast("GBFR 自动重战","静默模式已开启")
        relink.start(relink_battle_silent)
    else:
        
        relink.start(relink_battle)
