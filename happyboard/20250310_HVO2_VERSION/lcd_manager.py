# SingleTon 單例模式
import gc
from machine import Pin, SPI

class LCDManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        """單例模式，獲取 LCDManager 的唯一實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if LCDManager._instance is not None:
            raise Exception("這是一個單例類別，請使用 get_instance() 取得實例")
        
        # 延遲初始化屬性
        self.st7735 = None
        self.dis = None
        self.color = None
        self.spi = None
        self.spleen16 = None

    def initialize(self, baudrate=20000000, sck_pin=14, mosi_pin=13, rotate=0):
        """初始化 LCD 資源"""
        if self.st7735 is not None:
            print("LCD 已初始化")
            return

        try:
            print("初始化 SPI 和 LCD...")
            # 初始化 SPI
            self.spi = SPI(1, baudrate=baudrate, polarity=0, phase=0, sck=Pin(sck_pin), mosi=Pin(mosi_pin))
            
            # 初始化 ST7735
            from dr.st7735.st7735_4bit import ST7735
            self.st7735 = ST7735(self.spi, 4, 15, None, 128, 160, rotate=rotate)
            self.st7735.initb2()
            self.st7735.setrgb(True)

        
            # 初始化顏色和字型
            from gui.colors import colors
            self.color = colors(self.st7735)


            from dr.display import display
            import fonts.spleen16 as spleen16

            #初始化繪製
            self.dis = display(self.st7735, 'ST7735_FB', self.color.WHITE, self.color.BLUE)
            self.spleen16 = spleen16

            print("LCD 初始化完成")
        except Exception as e:
            print("LCD 初始化失敗:", e)
            self.cleanup()
            raise

    def fill(self, bgcolor=None):
        """填充背景顏色"""
        if not self.dis:
            print("LCD 尚未初始化，正在初始化...")
            self.initialize()
        # 預設使用黑色
        bgcolor = bgcolor if bgcolor is not None else self.color.BLACK
        self.dis.fill(bgcolor)
        gc.collect()


    def draw_text(self, x, y, text=None, fg=None, bg=None, bgmode=0, scale=1):
        """在 LCD 上繪製文字"""
        if not self.dis:
            print("LCD 尚未初始化，正在初始化...")
            self.initialize()
        
        fg = fg if fg is not None else self.color.WHITE
        bg = bg if bg is not None else self.color.BLUE
        text = text if text is not None else 'Happy Collector'

        try:
            self.dis.draw_text(self.spleen16, text, x, y, scale, fg, bg, bgmode, True, 0, 0)
        except Exception as e:
            print("繪製文字時發生錯誤:", e)
        gc.collect()

    def show(self):
        """刷新屏幕"""
        if self.dis:
            try:
                self.dis.dev.show()
                # 加入
                gc.collect()
            except Exception as e:
                print("刷新屏幕時發生錯誤:", e)

    def is_initialized(self):
        """檢查 LCD 是否已初始化"""
        return self.st7735 is not None
# 目前覺得不太會需要清除LCD 
    def cleanup(self):
        """清理 LCD 資源"""
        try:
            if self.st7735:
                self.st7735 = None

            if self.spi:
                self.spi.deinit()
                self.spi = None
            
            self.dis = None
            self.color = None
            self.spleen16 = None
            LCDManager._instance = None
            gc.collect()
            print("LCD 資源清理完成")
        except Exception as e:
            print("LCD 資源清理失敗:", e)
