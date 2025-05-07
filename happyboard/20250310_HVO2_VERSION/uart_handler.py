"""負責解析 UART 封包內容 並publish娃娃機當前相關數直到mqtt broker"""
import utime
import gc

class UartHandler:
    def __init__(self, claw_1, mqtt_manager,LCD_update_flag, now_main_state):
        """初始化uart handler"""
        self.claw_1 = claw_1 #娃娃機數據
        self.mqtt_manager = mqtt_manager #用於發送mqtt消息(發佈娃娃機的數據 ==>mqtt_handler在mqtt_manager中初始化的)
        self.LCD_update_flag = LCD_update_flag  # 用於更新LCD顯示的字典
        self.now_main_state = now_main_state  # 狀態機物件

        #機台設定查詢需要的物件
        self.clawsettingdict = {
            "BasicsettingA": 0x00, #基本設定A
            "BasicsettingB": 0x01, #基本設定B
            "BasicsettingC": 0x02, #基本設定C
            "Clawvoltage": 0x03,#抓力電壓
            "Motorspeed": 0x04, #馬達轉速
       }

    def parse_packet(self, packet):
        """解析 收到的UART 封包內容"""
        #self就是uart_manager
        print("debug: 解析uart封包ing:", self._format_packet(packet))

        ### ===二、主控制\機台狀態 | 機台狀態回應 |===
        if packet[2] == 0x81 and packet[3] == 0x01:
            self.claw_1.CMD_Control_Machine = packet[4]
            self.claw_1.Status_of_Current_machine = [packet[5], packet[6]]
            self.claw_1.Time_of_Current_game = packet[7]
            self.claw_1.Game_amount_of_Player = packet[8] * 256 + packet[9]
            self.claw_1.Way_of_Starting_game = packet[10]
            self.claw_1.Cumulation_amount_of_Sale_card = packet[11] * 256 + packet[14]
            self.claw_1.Error_Code_of_Machine = packet[12]

            print(f"Recive 娃娃機 : 二、主控制\機台狀態")
        ### ===CMD => 三、 帳目查詢\遠端帳目 | 帳目查詢回應| ===
        elif packet[2] == 0x82 and packet[3] == 0x01:
            self.claw_1.Number_of_Original_Payment = packet[4] * 256 + packet[5]
            self.claw_1.Number_of_Gift_Payment = packet[6] * 256 + packet[7]
            self.claw_1.Number_of_Coin = packet[8] * 256 + packet[9]
            self.claw_1.Number_of_Award = packet[10] * 256 + packet[11]
            self.claw_1.Error_Code_of_Machine = packet[12]                 # 六、 機台故障代碼表
            print("Recive 娃娃機 : 三、 帳目查詢=>遠端帳目")
        ### ===CMD => 四、 機台設定 | 機台設定回傳數據| ===
        elif packet[2] == 0x83:
            cmd = packet[3]
            setting_name = {v: k for k, v in self.clawsettingdict.items()}.get(cmd)

            if setting_name == "Clawvoltage":
                self.claw_1.Value_of_Hi_voltage = packet[4] * 0.2
                self.claw_1.Value_of_Mid_voltage = packet[5] * 0.2
                self.claw_1.Value_of_Lo_voltage = packet[6] * 0.2
                self.claw_1.Distance_of_Mid_voltage_and_Top = packet[7]
                self.claw_1.Hi_voltage_of_Guaranteed_prize = packet[8] * 0.2
                self.claw_1.Error_Code_of_Machine = packet[12]

                print(f"機台設定 - 抓力電壓")

            elif setting_name == "Motorspeed":
                self.claw_1.Speed_of_Moving_forward = packet[4]
                self.claw_1.Speed_of_Moving_back = packet[5]
                self.claw_1.Speed_of_Moving_left = packet[6]
                self.claw_1.Speed_of_Moving_right = packet[7]
                self.claw_1.Speed_of_Moving_down = packet[8]
                self.claw_1.Speed_of_Moving_up = packet[9]
                self.claw_1.RPM_of_All_horizontal_sides = packet[10]

                print(f"機台設定 - 馬達速度")

            elif setting_name == "BasicsettingA":
                self.claw_1.Time_of_game = packet[4]
                self.claw_1.Amount_of_Award = packet[5] * 256 + packet[6]
                self.claw_1.Amount_of_Present_cumulation = packet[7] * 256 + packet[8]
                self.claw_1.Time_of_Keeping_cumulation = packet[9]
                self.claw_1.Time_of_Show_music = packet[10]
                self.claw_1.Enable_of_Midair_Grip = packet[11]
                self.claw_1.Error_Code_of_Machine = packet[12]

                print(f"機台設定 - 基本設A: ")

            elif setting_name == "BasicsettingB":
                self.claw_1.Delay_of_Push_talon = packet[4]
                self.claw_1.Delay_of_Suspend_pulled_talon = packet[5] * 0.1
                self.claw_1.Enable_random_of_Pushing_talon = packet[6]
                self.claw_1.Enable_random_of_Clamping = packet[7]
                self.claw_1.Time_of_Push_talon = packet[8] * 0.1
                self.claw_1.Time_of_Suspend_and_Pull_talon = packet[9] * 0.1
                self.claw_1.Delay_of_Pull_talon = packet[10] * 0.1
                self.claw_1.Error_Code_of_Machine = packet[12]

                print(f"機台設定 - 基本設B: ")

            elif setting_name == "BasicsettingC":
                self.claw_1.Enable_of_Sales_promotion = packet[4]
                self.claw_1.Which_number_starting_when_Sales_promotion = packet[5]
                self.claw_1.Number_of_Strong_grip_when_Sales_promotion = packet[6]
                self.claw_1.Error_Code_of_Machine = packet[12]

                print(f"機台設定 - 基本設C:")

            print("debug: [UartHandler: 調用self.mqtt_handler.publish_MQTT_claw_data]")
            # 解析完要發送mqtt消息
            #self.mqtt_handler.publish_MQTT_claw_data(self.claw_1, 'commandack-clawmachinesetting', setting_name)
            self.mqtt_handler.publish_MQTT_claw_data('commandack-clawmachinesetting', setting_name)
        #
        #加入這行(還需要傳遞LCD_update_flag和now_main_state進來)
        self.LCD_update_flag['Claw_Value'] = True
        print("debug:[uart_handler] 已處理LCD_update_flag")
        self.now_main_state.transition('FEILOLI UART is OK')  # <== 這一行必須確保存在
        utime.sleep_ms(100) # 休眠一小段時間，避免過度使用CPU資源

    def _format_packet(self, packet):
        """格式化封包輸出"""
        return " ".join(f"{byte:02X}" for byte in packet)