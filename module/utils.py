from module.log import Log
from module.controller import Controller
from time import sleep,time
_log=Log("utils",'d').logger

class Utils:
    def __init__(self,window_title,t,d):
         self.test=Controller(window_title,t,d)
    def gettextposition(self, text):
        result = {"text": text, "region": []}
        appear_text=self.wait(result["text"], timeout=3)
        if isinstance(appear_text,dict):

            r = appear_text["location"]
            s = self.test.window_rect
            x1 = int(r[0] / s[2] * 10000) / 10000
            y1 = int(r[1] / s[3] * 10000) / 10000
            x2 = int(r[2] / s[2] * 10000) / 10000
            y2 = int(r[3] / s[3] * 10000) / 10000

            result["region"] = [x1, y1, x2, y2]
            _log.debug("文字位置: '%s' → %s", text, result["region"])
       
        
    def wait(
            self, text, timeout=60,  poll: float = 0.3
        ):
            """等待文字出现在画面中
            :param poll: 轮询间隔(秒)，控制截图+OCR频率，避免CPU占满导致游戏卡顿
            """
            _log.debug("等待文字: '%s' (超时: %ds)", text, timeout)

            
            start_time=time()
            while time()-start_time <timeout:
                pic = self.test.screenshot_text(text)
                result = self.test.ocr(pic)

                if isinstance(result, list) and result:
                    for i in result:
                        if text in result["text"]:
                            return i

                sleep(poll)


            _log.debug("超时未找到: '%s' (%.0fs)", text, timeout)
            return None

