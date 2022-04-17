import random
from typing import Tuple, List, Dict, Union
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import asyncio
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.log import logger
from .config import tkk_config, TKK_PATH

class RandomTkkHandler:
    
    def __init__(self):
        self.tkk_config = tkk_config
        self.Font: ImageFont.FreeTypeFont = ImageFont.truetype(str(TKK_PATH / "msyh.ttc"), 16)
        self.timers: Dict[str, asyncio.TimerHandle] = {}
        self.tkk_status: Dict[str, Union[bool, List[int], bytes]] = {}
        
        if not TKK_PATH.exists():
            logger.warning(f"随机唐可可资源路径错误，请检查")
        
    def tkk_size_config(self, level: str) -> int:
        '''
            确认tkk大小: [10, 80]
        '''
        if level == "简单":
            return self.tkk_config.easy_size
        elif level == "普通":
            return self.tkk_config.normal_size
        elif level == "困难":
            return self.tkk_config.hard_size
        elif level == "地狱":
            return self.tkk_config.extreme_size
        else:
            try:
                tkk_size = int(level) if int(level) <= self.tkk_config.max_size else self.tkk_config.normal_size
                if tkk_size < 5:
                    tkk_size = self.tkk_config.easy_size
                return tkk_size
            except:
                return self.tkk_config.easy_size
    
    def get_tkk_pos(self, tkk_size: int) -> Tuple[int, int]:
        col = random.randint(1, tkk_size)   # 列
        row = random.randint(1, tkk_size)   # 行
        return row, col
    
    def get_waiting_time(self, tkk_size: int) -> int:
        if tkk_size > 30:
            time = int(0.1 * (tkk_size - 30)**2 + 50)
        else:
            time = int(1.7 * (tkk_size - 10) + 15)
        
        return time
    
    def check_tkk_playing(self, gid: str) -> bool:
        try:
            result = self.tkk_status[gid]["playing"]
            return result
        except:
            return False
    
    async def draw_tkk(self, row: int, col: int, tkk_size: int) -> Tuple[bytes, bytes]:
        '''
            画图
        '''
        temp = 0
        base = Image.new("RGB",(64 * tkk_size, 64 * tkk_size))
        
        for r in range(0, tkk_size):
            for c in range(0, tkk_size):
                if r == row - 1 and c == col - 1:
                    tkk = Image.open(TKK_PATH / "tangkuku.png")
                    tkk = tkk.resize((64, 64), Image.ANTIALIAS)      #加载icon
                    if self.tkk_config.show_coordinate:
                        draw = ImageDraw.Draw(tkk)
                        draw.text((20,40), f"({c+1},{r+1})", font=self.Font, fill=(255, 0, 0, 0))
                    base.paste(tkk, (r * 64, c * 64))
                    temp += 1
                else:
                    icon = Image.open(TKK_PATH /(str(random.randint(1, 22)) + '.png'))
                    icon = icon.resize((64,64), Image.ANTIALIAS)
                    if self.tkk_config.show_coordinate:
                        draw = ImageDraw.Draw(icon)
                        draw.text((20,40), f"({c+1},{r+1})", font=self.Font, fill=(255, 0, 0, 0))
                    base.paste(icon, (r * 64, c * 64))
        
        buf = BytesIO()
        base.save(buf, format='png')
        
        base2 = base.copy()
        mark = Image.open(TKK_PATH / "mark.png")
        # Python是反的
        base2.paste(mark,((row - 1) * 64, (col - 1) * 64), mark)
        buf2 = BytesIO()
        base2.save(buf2, format='png')
        
        return buf.getvalue(), buf2.getvalue()
    
    async def one_go(self, gid: str, level: str) -> Tuple[bytes, int]:
        '''
            记录每个群组如下属性：
                "playing": False,   当前是否在进行游戏
                "waiting": 0,       等待时间
                "anwser": [0, 0],   答案
        '''
        tkk_size = self.tkk_size_config(level)
        row, col = self.get_tkk_pos(tkk_size)
        img_file, mark_file = await self.draw_tkk(row, col, tkk_size)
        self.tkk_status[gid] = {
            "playing": True,
            "answer": [col, row],
            "mark_img": mark_file
        }
        
        return img_file, self.get_waiting_time(tkk_size)
    
    def check_answer(self, gid: str, pos: List[int]) -> bool: 
        return pos == self.tkk_status[gid]["answer"]
    
    async def over_game(self, matcher: Matcher, gid: str) -> bool:
        try:
            timer = self.timers.get(gid, None)
            if timer:
                timer.cancel()
        except:
            return False
        
        self.settle_game(matcher, gid)
        
        return True
    
    async def settle_game(self, matcher: Matcher, gid: str) -> None:
        self.timers.pop(gid, None)
        
        # 超时仍未结束说明未给出正确答案
        if self.check_tkk_playing(gid):
            answer = self.tkk_status[gid]["answer"]
            msg = "没人找出来，好可惜啊☹\n" + f"答案是{answer[0]}行{answer[1]}列" + MessageSegment.image(self.tkk_status[gid]["mark_img"])
            self.close_game(gid)
            
            await matcher.finish(msg)

    def start_timer(self, matcher: Matcher, gid: str, timeout: int) -> None:
        timer = self.timers.get(gid, None)
        if timer:
            timer.cancel()
        loop = asyncio.get_running_loop()
        timer = loop.call_later(
            timeout, lambda: asyncio.ensure_future(self.settle_game(matcher, gid))
        )
        self.timers[gid] = timer
    
    def close_game(self, gid: str) -> None:
        try:
            self.tkk_status.pop(gid, None)
        except KeyError:
            pass

random_tkk_handler = RandomTkkHandler()