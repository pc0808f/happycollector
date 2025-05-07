
import ujson
import utime
import gc
import machine

#from machine import RTC
#from mqtt_helper import process_fota, process_commands  # 引入訂閱處理函數

class MqttHandler:
    def __init__(self, mqtt_manager, claw_1, uart_manager, wifi_manager, LCD_update_flag):
        """
        初始化 MQTT 處理器
        :param mqtt_manager: MQTT 管理器
        :param claw_1: 娃娃機資料對象
        :param uart_FEILOLI_send_packet: 傳送 UART 指令的函數
        :param uart_manager.py
        """
        self.mqtt_manager = mqtt_manager
        self.claw_1 = claw_1
        #self.uart_FEILOLI_send_packet = uart_FEILOLI_send_packet  # 用於發送 UART 指令(把uart物件類也傳進來)
        self.uart_manager = uart_manager
        self.wifi_manager = wifi_manager
        self.LCD_update_flag = LCD_update_flag
   
        

    def process_fota(self, data):
        """ 處理 FOTA 訊息 """
        otafile = 'otalist.dat'
        try:
            if 'file_list' in data and 'password' in data:
                if data['password'] == 'c0b82a2c-4b03-42a5-92cd-3478798b2a90':
                    ## 當 ESP32 確認收到 FOTA 指令，會透過 MQTT 發布 "fotaack"
                    ## 這讓 伺服器或 MQTT Broker 知道 ESP32 準備開始更新
                    self.publish_MQTT_claw_data("fotaack")

                    with open(otafile, 'w') as f:
                        f.write(''.join(data['file_list']))
                    print("FOTA file saved. Rebooting...")
                    utime.sleep(3)
                    import machine
                    machine.reset()
                else:
                    print("debug:[process_fota] Invalid FOTA password")
            else:
                print("debug:[process_fota] Incomplete FOTA data received")
        except Exception as e:
            print(f"debug:[process_fota] Error handling FOTA: {e}")
    # 先處理commands
    def process_commands(self, data):
        """ 專門處理 接收到 /commands 的訊息 並進行下一步"""
        commands_handler = {
            'ping': self.handle_ping, # 收到ping的mqtt訊息 ==> 回應pong OK
            #'getTimeNow': self.handle_getTimeNow, # 收到getTimeNow的mqtt訊息 ==> 回應時間
            'version': self.handle_version, # 收到version的mqtt訊息 ==> 回應version OK
            'clawreboot': self.handle_clawreboot, # 涉及到UART =>
            'clawstartgame': self.handle_clawstartgame,
            'clawcleantransaccount': self.handle_clawcleantransaccount,
            'clawmachinesetting': self.handle_clawmachinesetting
        }

        command = data.get('commands') # 取出訊息(物件中)的commands欄位的值
        handler = commands_handler.get(command) #例如: 'ping' ===> 值是 self.handle_ping 這個函式的調用

        if handler:
            handler(data) # 調用self.handle_ping(ping') 
        else:
            print(f"指令有誤: {command}")
    ### ========= 處理時間  =============###
    def process_time_response(self, data):
        """處理 MQTT 來的時間回應，更新 RTC 之後自動退訂"""
        import machine
        import utime

        try:
            if "timestamp" in data: #轉換為utc+8
                timestamp = int(data["timestamp"]) + (8 * 3600)
                print(f"收到時間戳: {timestamp}")

                # 將 UNIX 時間轉換成 RTC 格式
                self.set_rtc_from_unix(timestamp)

                # 確保lcd會更新時間
                self.LCD_update_flag['Time'] = True
                print(f"設定 LCD_update_flag['Time'] = True，LCD 將更新時間{timestamp}")

                # **這裡退訂 MQTT 時間主題**
                topic = self.mqtt_manager.sub_response_time_topic
                print(f"退訂 MQTT 主題: {topic}")
                self.mqtt_manager.unsubscribe_response_time(topic)  # **確保退訂**
            else:
                print("無法解析時間戳: JSON 中沒有 'timestamp'")
        except Exception as e:
            print(f"處理時間戳錯誤: {e}")
            machine.reset()  # **強制重啟**


    ### ========= commands_handle 指令 所對應的函式  =============###
    def handle_ping(self, data):
        #'ping': self.handle_ping
        self.publish_MQTT_claw_data("commandack-pong")

    def handle_version(self, data):
        #'version': self.handle_version
        self.publish_MQTT_claw_data('commandack-version')

    def handle_clawstartgame(self, data):
        #'clawstartgame': self.handle_clawstartgame
        try:
            epays = data.get('epays',0) #從mqtt的主題物件取出epays值|沒有預設就是0
            freeplays = data.get('freeplays',0)

            #限制epays 和freeplays的參數(否則娃娃機回傳封包會錯誤)
            if not (0 <= epays <= 40):
                raise ValueError(f"Invalid epays (0-40): {epays}")
            if not (0 <= freeplays <= 10):
                raise ValueError(f"Invalid freeplays (0-10): {freeplays}")

            #組好訊息
            game_data = {"epays": epays, "freeplays": freeplays}
            print(f"[mqtt_handler(handle_clawstartgame)]:  {game_data}")

            #發佈訊息
            self.publish_MQTT_claw_data("commandack-clawstartgame",data.get("state"))
            print(f"[mqtt_handler(handle_clawstartgame)] -> publish_MQTT commandack-clawstartgame")
            #發送uart封包 啟動遊戲指令
            # self.uart_func(KindFEILOLIcmd.Send_Starting_once_game, game_data)
            # 暫時先用函式
            #self.uart_FEILOLI_send_packet(KindFEILOLIcmd.Send_Starting_once_game, game_data)
            # 用類
            print(f"[mqtt_handler(handle_clawstartgame)] self.uart_manager 狀態: {self.uart_manager}")
            
            # **這裡加強錯誤檢查**
            if not hasattr(self.uart_manager, 'KindFEILOLIcmd'):
                raise AttributeError("[mqtt_handler(handle_clawstartgame)] self.uart_manager 缺少 KindFEILOLIcmd 屬性")

            self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Send_Starting_games, game_data)
            print(f"[mqtt_handler(handle_clawstartgame)] 發送uart 封包給娃娃機Starting_games")
       
        except AttributeError as ae:
            print(f"[mqtt_handler(handle_clawstartgame)] 屬性錯誤: {ae}")
        except ValueError as ve:
            print(f"[mqtt_handler(handle_clawstartgame)] 數值錯誤: {ve}")
        except Exception as e:
            print(f"[mqtt_handler(handle_clawstartgame)] 錯誤處理 Error handling clawstartgame: {e}")
    
    def handle_clawreboot(self,data):
        self.publish_MQTT_claw_data("commandack-clawreboot", data.get("state"))
        self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Send_Machine_reboot)
        print(f"[mqtt_handler(handle_clawreboot)] 發送uart封包給娃娃機:clawreboot")


    def handle_clawmachinesetting(self,data):
        setting = data.get('setting', '').strip()

        valid_settings = ["BasicsettingA", "BasicsettingB", "BasicsettingC", "Clawvoltage", "Motorspeed"]
        if setting in valid_settings:
            self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Ask_Machine_setting, setting)
            print(f"debug:[mqtt_handler] 已發送clawmachinesetting uart封包: {setting}")
        else:
            print(f"Invalid machine setting: {setting}")

    def handle_clawcleantransaccount(self,data):
        account = data.get('account', '').split(", ")
        if account:
            self.publish_MQTT_claw_data("commandack-clawcleantransaccount", data.get("state"))
            self.uart_manager.send_packet(self.uart_manager.KindFEILOLIcmd.Send_Clean_transaction_account, account)
            print(f"debug:[mqtt_handler] 已發送clawcleantransaccount uart封包: {account}")
        else:
            print(f"Invalid machine setting: {account}")

    ### ========= 發佈 publish＿MQTT_claw_data函式  =============###
    def publish_MQTT_claw_data(self, api, para1=""):
        """
        發佈 MQTT 娃娃機數據
        :param api: API 路由名稱 (e.g., 'sales', 'status', 'commandack-*')
        :param para1: 可能的附加參數
        """
        if api == 'sales':
            data = self.build_sales_data(self.claw_1)
        elif api == ("status"):
            data = self.build_status_data(self.claw_1)
        #先做嚴謹的api比對
        elif api == ("commandack-clawmachinesetting"):
            data = self.build_clawmachinesetting_data(self.claw_1, para1)
        #elif api == ("commandack-clawcleantransaccount"):
        #     data = self.handle_clawcleantransaccount_data(self.claw_1, para1)

        # elif api == ("commandack-fileinfo"):
        #     data = self.build_fileinfo_data(??)
        # elif api == ("commandack-fileremove"):
        #     data = self.build_fileremove_data(??)   
        elif api.startswith("commandack") or api == ('fotaack'): #剩下的前綴api都在這裡做處理
            data = self.handle_ack_with_state(api, para1)
        else:
            print(f"無此MQTT發佈的API: {api}")
            return
        
        ## 發佈消息 到 MQTT 
        ## 調用mqtt_manager的發佈方法
        self.mqtt_manager.publish_data(f"{self.mqtt_manager.mac_id}/{self.mqtt_manager.token}/{api}", data)
        gc.collect()
        
    def set_rtc_from_unix(self, unix_time):
        """將 UNIX 時間轉換成 RTC 格式並設置並進行防呆重啟"""
        

        rtc = machine.RTC()

        # 轉換 UNIX 時間為年月日時分秒
        t = utime.localtime(unix_time)
        year, month, day, hour, minute, second = t[0:6]

        # 設置 ESP32 RTC
        rtc.datetime((year, month, day, 0, hour, minute, second, 0))
        
        print(f"RTC 時間已更新: {year}-{month}-{day} {hour}:{minute}:{second}")

    ### 收到mqtt發布sales主題 ==> 啟動回調訂閱=> 再發佈主題 ==>娃娃機數據 相關的主題 #####
    def build_sales_data(self, claw_1):
        WCU_Freeplaytimes = max (
                claw_1.Number_of_Total_games -
                claw_1.Number_of_Original_Payment -
                claw_1.Number_of_Coin -
                claw_1.Number_of_Gift_Payment,
                0
        )

        return {
            "Epayplaytimes": claw_1.Number_of_Original_Payment,
            "Coinplaytimes": claw_1.Number_of_Coin,
            "Giftplaytimes": claw_1.Number_of_Gift_Payment,
            "GiftOuttimes": claw_1.Number_of_Award,
            "Freeplaytimes": WCU_Freeplaytimes,
            "time": utime.time(),        
        }
    ### 收到mqtt發布status主題 ==> 啟動回調訂閱=> 再發佈主題 ==>status 相關的主題 #####    
    def build_status_data(self, claw_1):
        return {
            "status": f"{self.claw_1.Error_Code_of_Machine:02d}",
            "wifirssi": f"{self.wifi_manager.get_signal_strength()} dbm",
            "time": utime.time(),
        }
    ### 收到mqtt發布commands machinesetting相關主題 ==> 啟動回調訂閱=> 再發佈主題 ==>machinesetting 相關的主題 ##### 
    def build_clawmachinesetting_data(self, claw_1, para1):
        # 透過參數來判斷封包data
        # 抓力電壓
        if para1 == "Clawvoltage": 
            return {
                "HiVoltageValue": claw_1.Value_of_Hi_voltage,
                "MidVoltageValue": claw_1.Value_of_Mid_voltage,
                "LoVoltageValue": claw_1.Value_of_Lo_voltage,
                "MidVoltageTopDistance": claw_1.Distance_of_Mid_voltage_and_Top,
                "GuaranteedPrizeHiVoltage": claw_1.Hi_voltage_of_Guaranteed_prize,
                "time": utime.time(),           
            }
        # 馬達轉速
        elif para1 == "Motorspeed":
            return {
                "SpeedMovingforward": claw_1.Speed_of_Moving_forward,
                "SpeedMovingback": claw_1.Speed_of_Moving_back,
                "SpeedMovingleft": claw_1.Speed_of_Moving_left,
                "SpeedMovingright": claw_1.Speed_of_Moving_right,
                "SpeedMovingup": claw_1.Speed_of_Moving_up,
                "SpeedMovingdown": claw_1.Speed_of_Moving_down,
                "RPMAllhorizontalsides": claw_1.RPM_of_All_horizontal_sides,
                "time": utime.time(),            
            }

        # 基本設定A
        elif para1 == 'BasicsettingA':
            return {
                "TimeOfGame": claw_1.Time_of_game,  # 遊戲時間
                "AmountOfAward": claw_1.Amount_of_Award,  # 禮品售價
                "AmountOfPresentCumulation": claw_1.Amount_of_Present_cumulation,  # 目前累加金額
                "TimeOfKeepingCumulation": claw_1.Time_of_Keeping_cumulation,  # 累加保留時間
                "TimeOfShowMusic": claw_1.Time_of_Show_music,  # 展示音樂時間
                "EnableOfMidairGrip": claw_1.Enable_of_Midair_Grip,  # 空中取物
                "time": utime.time()
            }
        # 基本設定B
        elif para1 == 'BasicsettingB':
            return {
                "DelayofPushtalon": claw_1.Delay_of_Push_talon,  # 下抓延遲
                "DelayofSuspendpulledtalon": claw_1.Delay_of_Suspend_pulled_talon,  # 上停延遲
                "EnablerandomofPushingtalon": claw_1.Enable_random_of_Pushing_talon,  # 下抓夾亂數
                "EnablerandomofClamping": claw_1.Enable_random_of_Clamping,  # 夾亂數
                "TimeofPushtalon": claw_1.Time_of_Push_talon,  # 下抓長度時間
                "TimeofSuspendandPulltalon": claw_1.Time_of_Suspend_and_Pull_talon,  # 上停上拉時間
                "DelayofPulltalon": claw_1.Delay_of_Pull_talon,  # 上拉延遲
                "time": utime.time()
            }
        # 基本設定C
        elif para1 == 'BasicsettingC':
            return {
                "Enable_of_Sales_promotion": claw_1.Enable_of_Sales_promotion,  # 促銷功能
                "Which_number_starting_when_Sales_promotion": claw_1.Which_number_starting_when_Sales_promotion,  # 促銷功能第幾局
                "Number_of_Strong_grip_when_Sales_promotion": claw_1.Number_of_Strong_grip_when_Sales_promotion,  # 促銷功能強抓次數
                "time": utime.time()
            }
        else: 
            return {
                "ack": "wrong!!only_ask_one_machinesetting_cmd", 
                "state": para1, 
                "time": utime.time()
            }
    
    ### 整合原本 helper 的數據處理函數  ###
    # def handle_clawcleantransaccount_data(self, claw_1,para1):
    #     if para1:
    #         return {
    #             "ack": ack_value,
    #             "state": para1,
    #             "time": utime.time()
    #         }
    #     else: 
    #         return {
    #             "ack": ack_value,
    #             "time": utime.time()
    #         }
    ## 發佈"commandack"為前綴的消息(回傳相關資料)
    def handle_ack_with_state(self, api_select, para1=""):
        ack_value = {
            "commandack-clawcleantransaccount": "OK",
            "commandack-pong": "pong",
            "commandack-version": self.mqtt_manager.version,
            "fotaack": "OK",
        }.get(api_select, "OK")
        
        if para1:
            return {
                "ack": ack_value,
                "state": para1,
                "time": utime.time()
            }
        else: 
            return {
                "ack": ack_value,
                "time": utime.time()
            }
