from machine import Timer, WDT
import utime
import gc

class TimerManager:
    def __init__(self, now_main_state, MainStatus, wifi_manager, uart_manager, mqtt_manager, mqtt_handler, lcd_mgr, wdt, LCD_update_flag, claw_1):
        self.now_main_state = now_main_state
        self.MainStatus = MainStatus
        self.wifi_manager = wifi_manager
        self.uart_manager = uart_manager
        self.mqtt_manager = mqtt_manager
        self.mqtt_handler = mqtt_handler
        self.lcd_mgr = lcd_mgr
        self.wdt = wdt
        self.LCD_update_flag = LCD_update_flag
        self.claw_1 = claw_1
        # 定義時間計數
        ## server_report
        self.server_report_sales_period = 180 # 3分鐘 = 3*60 單位秒
        self.server_report_sales_counter = self.server_report_sales_period - 30  # 開機後第一次送MQTT會縮短到30秒

        self.counter_of_WAITING_FEILOLI = 0

        #設置timer 
        self.server_report_timer = Timer(0)
        self.claw_check_timer = Timer(1)
        self.LCD_update_timer = Timer(2)

    def server_report_timer_callback(self, timer):
 
        if self.mqtt_manager.client is not None:
                self.mqtt_manager.check_messages()

        self.server_report_sales_counter = (self.server_report_sales_counter + 1) % self.server_report_sales_period
        if self.server_report_sales_counter == 0:
            print(f"Debugger:[timer_manager] wdt: {self.wdt} ")
            self.wdt.feed()
            if self.now_main_state.state in [4, 5]:
                self.mqtt_manager.mqtt_handler.publish_MQTT_claw_data('sales')
            self.mqtt_manager.mqtt_handler.publish_MQTT_claw_data('status')
        gc.collect()

    def claw_check_timer_callback(self, timer):
        if self.now_main_state.state in [3]: 
            print("Updating 娃娃機 機台狀態 ...")
            self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Ask_Machine_status)
        # STANDBY_FEILOLI = 4
        elif self.now_main_state.state in [4]:
            print("Updating 娃娃機 遠端帳目、投幣帳目 ...")
            #uart_FEILOLI_send_packet(KindFEILOLIcmd.Ask_Transaction_account)
            self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Ask_Transaction_account)
            # uart_FEILOLI_send_packet(KindFEILOLIcmd.Ask_Coin_account)
            self.now_main_state.transition('FEILOLI UART is waiting')
            self.counter_of_WAITING_FEILOLI = 0
        #WAITING_FEILOLI = 5
        if self.now_main_state.state in [5]:
            self.counter_of_WAITING_FEILOLI = self.counter_of_WAITING_FEILOLI + 1
            if self.counter_of_WAITING_FEILOLI >= 2:
                if self.counter_of_WAITING_FEILOLI == 2:
                    print("Updating 娃娃機 失敗 ...")
                    self.now_main_state.transition('FEILOLI UART is not OK')
                print("Updating 娃娃機 機台狀態 ...")
                #uart_FEILOLI_send_packet(KindFEILOLIcmd.Ask_Machine_status)
                self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Ask_Machine_status)

    def LCD_update_timer_callback(self, timer):
        import binascii
        import machine
        if self.LCD_update_flag['Uniform']:
            self.LCD_update_flag['Uniform'] = False
            # mac_id吧
            unique_id_hex = binascii.hexlify(machine.unique_id()).decode().upper()

            # 清空屏幕並繪製基本資訊
            self.lcd_mgr.fill()  # 使用黑色清空整個畫面

            self.lcd_mgr.draw_text(0, 0, text='Happy Collector', bg=self.lcd_mgr.color.BLUE, bgmode=-1)

            self.lcd_mgr.draw_text(5, 8 * 16 + 5, text=unique_id_hex, fg=self.lcd_mgr.color.RED, bg=self.lcd_mgr.color.WHITE,bgmode=-1, scale=1.3)


            self.lcd_mgr.draw_text(0, 1 * 16, text='IN:--------', fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
            self.lcd_mgr.draw_text(0, 2 * 16, text='OUT:--------')
            self.lcd_mgr.draw_text(0, 3 * 16, text='EP:--------')
            self.lcd_mgr.draw_text(0, 4 * 16, text='GP:--------')
            self.lcd_mgr.draw_text(0, 5 * 16, text='ST:--')
            self.lcd_mgr.draw_text(0, 6 * 16, text='Time:mm/dd hh:mm')
            self.lcd_mgr.draw_text(0, 7 * 16, text='Wifi:-----')
            
        elif self.LCD_update_flag['WiFi']:
            self.LCD_update_flag['WiFi'] = False
            #
            if self.now_main_state.state == self.MainStatus.NONE_WIFI or self.now_main_state.state == self.MainStatus.NONE_INTERNET:
                #顯示wifi和MQTT狀態
                self.lcd_mgr.draw_text(5*8, 7*16, text='dis  ',fg=self.lcd_mgr.color.RED, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
            elif self.now_main_state.state == self.MainStatus.NONE_MQTT:
                #顯示wifi和MQTT狀態
                self.lcd_mgr.draw_text(5*8, 7*16, text='error',fg=self.lcd_mgr.color.RED, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
            elif self.now_main_state.state == self.MainStatus.NONE_FEILOLI or self.now_main_state.state == self.MainStatus.STANDBY_FEILOLI or self.now_main_state.state == self.MainStatus.WAITING_FEILOLI:
                #顯示wifi和MQTT狀態
                self.lcd_mgr.draw_text(5*8, 7*16, text='OK   ',fg=self.lcd_mgr.color.GREEN, bg=self.lcd_mgr.color.BLACK, bgmode=-1)

        elif self.LCD_update_flag['Claw_State']:
            self.LCD_update_flag['Claw_State'] = False  
            if self.now_main_state.state == self.MainStatus.NONE_FEILOLI :
                self.lcd_mgr.draw_text(3 * 8, 5 * 16, text="%02d" % 99)   
                #顯示娃娃機狀態
            elif self.now_main_state.state == self.MainStatus.STANDBY_FEILOLI or self.now_main_state.state == self.MainStatus.WAITING_FEILOLI:
                #self.lcd_mgr.draw_text(3 * 8, 5 * 16, text="%02d" % self.claw_1.Error_Code_of_Machine)
                self.lcd_mgr.draw_text(3 * 8, 5 * 16, text="%02d" % self.claw_1.Error_Code_of_Machine,fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK,bgmode=-1)
                #顯示娃娃機狀態
            else:
                self.lcd_mgr.draw_text(3 * 8, 5 * 16, text="--")

        elif self.LCD_update_flag['Claw_Value']:
            self.LCD_update_flag['Claw_Value'] = False
            if self.now_main_state.state == self.MainStatus.STANDBY_FEILOLI or self.now_main_state.state == self.MainStatus.WAITING_FEILOLI:
                self.lcd_mgr.draw_text(3 * 8, 1 * 16, text="%-8d" % self.claw_1.Number_of_Coin, fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
                self.lcd_mgr.draw_text(4 * 8, 2 * 16, text="%-8d" % self.claw_1.Number_of_Award, fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
                self.lcd_mgr.draw_text(3 * 8, 3 * 16, text="%-8d" % self.claw_1.Number_of_Original_Payment, fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
                self.lcd_mgr.draw_text(3 * 8, 4 * 16, text="%-8d" % self.claw_1.Number_of_Gift_Payment, fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)

        elif (self.LCD_update_flag['Time']):
            self.LCD_update_flag['Time'] = False  
            # 获取当前时间戳
            timestamp = utime.time()
            # 转换为本地时间
            local_time = utime.localtime(timestamp)
            # 格式化为 "mm/dd hh:mm" 格式的字符串
            formatted_time = "{:02d}/{:02d} {:02d}:{:02d}".format(local_time[1], local_time[2], local_time[3], local_time[4])

            print(f"更新 LCD 顯示時間: {formatted_time}")  # 除錯訊息
            self.lcd_mgr.draw_text(5 * 8, 6 * 16, text=formatted_time,fg=self.lcd_mgr.color.WHITE, bg=self.lcd_mgr.color.BLACK, bgmode=-1)
            #顯示時間
        self.lcd_mgr.show()
        gc.collect()

    def start_timers(self):
        # 設定1秒鐘 = 1000（單位：毫秒）
        self.server_report_timer.init(period=1000, mode=Timer.PERIODIC, callback=self.server_report_timer_callback)

        # 設定10秒鐘 = 10*1000（單位：毫秒）
        self.claw_check_timer.init(period=10000, mode=Timer.PERIODIC, callback=self.claw_check_timer_callback)

        # 設定1秒鐘 = 1000（單位：毫秒）
        self.LCD_update_timer.init(period=1000, mode=Timer.PERIODIC, callback=self.LCD_update_timer_callback)
        gc.collect()

