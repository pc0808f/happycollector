class ReceivedClawData:
    def __init__(self):
        self.CMD_Verification_code_and_Card_function = 0    # for 一、通訊說明\回覆修改驗證碼、刷卡功能的指令
        self.Verification_code = bytearray(4)               # for 一、通訊說明\驗證碼
        self.Machine_Code_number = bytearray(2)             # for 一、通訊說明\機台代號
        self.Machine_FW_version = bytearray(2)              # for 一、通訊說明\程式版本
        self.Feedback_Card_function = 0                     # for 一、通訊說明\回覆目前刷卡功能

        self.CMD_Control_Machine = 0                        # for 二、主控制\機台狀態\回覆控制指令 (機台回覆控制代碼)
        self.Status_of_Current_machine = bytearray(2)       # for 二、主控制\機台狀態\機台目前狀況
        self.Time_of_Current_game = 0                       # for 二、主控制\機台狀態\當機台目前狀況[0]為0x10=遊戲開始(未控制搖桿)時，回傳的遊戲時間
        self.Game_amount_of_Player = 0                      # for 二、主控制\機台狀態\玩家遊戲金額(累加金額)
        self.Way_of_Starting_game = 0                       # for 二、主控制\機台狀態\遊戲啟動方式
        self.Cumulation_amount_of_Sale_card = 0             # for 二、主控制\機台狀態\售價小卡顯示用累加金額

        self.Payment_amount_of_This_order = 0               # for 二、主控制\傳送交易資料\此次扣款金額
        self.Number_of_Original_games_to_Start = 0          # for 二、主控制\傳送交易資料\啟動原局數
        self.Number_of_Gift_games_to_Start = 0              # for 二、主控制\傳送交易資料\啟動贈局數
        self.Number_dollars_of_Per_game = 0                 # for 二、主控制\傳送交易資料\每局幾元
        self.Time_of_Payment_countdown_Or_fail = 0          # for 二、主控制\等待刷卡倒數/交易失敗\IPC倒數時間or失敗
        self.CMD_Mode_of_Payment = 0                        # for 二、主控制\回覆遊戲啟動方式(01=電子支付)

        # 未定義                                            # for 二、主控制\套餐設定、參數回報

        self.Number_of_Original_Payment = 0     # for 三、帳目查詢\遠端帳目\悠遊卡支付次數
        self.Number_of_Gift_Payment = 0         # for 三、帳目查詢\遠端帳目\悠遊卡贈送次數
        self.Number_of_Coin = 0                 # for 三、帳目查詢\遠端帳目\投幣次數
        self.Number_of_Award = 0                # for 三、帳目查詢\遠端帳目、投幣帳目\禮品出獎次數
        self.Bank_of_Award_rate = 0             # for 三、帳目查詢\投幣帳目\中獎率銀行
        self.Number_of_Total_games = 0          # for 三、帳目查詢\投幣帳目\總遊戲次數

        # 基本設定A
        self.Time_of_game = None                       # for 四、機台設定查詢\基本設定A
        self.Time_of_Keeping_cumulation = None         # for 四、機台設定查詢\基本設定A
        self.Time_of_Show_music = None                 # for 四、機台設定查詢\基本設定A
        self.Enable_of_Midair_Grip = None              # for 四、機台設定查詢\基本設定A
        self.Amount_of_Award = None                    # for 四、機台設定查詢\基本設定A
        self.Amount_of_Present_cumulation = None       # for 四、機台設定查詢\基本設定A

        # 抓力電壓
        self.Value_of_Hi_voltage = None                    # for 四、機台設定查詢\抓力電壓
        self.Value_of_Mid_voltage = None                   # for 四、機台設定查詢\抓力電壓
        self.Value_of_Lo_voltage = None                    # for 四、機台設定查詢\抓力電壓
        self.Distance_of_Mid_voltage_and_Top = None        # for 四、機台設定查詢\抓力電壓
        self.Hi_voltage_of_Guaranteed_prize = None         # for 四、機台設定查詢\抓力電壓

        #四 機台設定查詢: 馬達速度
        self.Speed_of_Moving_forward = None                # for 四、機台設定查詢\馬達速度
        self.Speed_of_Moving_back = None                   # for 四、機台設定查詢\馬達速度
        self.Speed_of_Moving_left = None                   # for 四、機台設定查詢\馬達速度
        self.Speed_of_Moving_right = None                  # for 四、機台設定查詢\馬達速度
        self.Speed_of_Moving_up = None                     # for 四、機台設定查詢\馬達速度
        self.Speed_of_Moving_down = None                   # for 四、機台設定查詢\馬達速度
        self.RPM_of_All_horizontal_sides = None            # for 四、機台設定查詢\馬達速度

        self.Time_of_game = None                       # for 四、機台設定查詢\基本設定A
        self.Time_of_Keeping_cumulation = None         # for 四、機台設定查詢\基本設定A
        self.Time_of_Show_music = None                 # for 四、機台設定查詢\基本設定A
        self.Enable_of_Midair_Grip = None              # for 四、機台設定查詢\基本設定A
        self.Amount_of_Award = None                    # for 四、機台設定查詢\基本設定A
        self.Amount_of_Present_cumulation = None       # for 四、機台設定查詢\基本設定A

        self.Delay_of_Push_talon = None                # for 四、機台設定查詢\基本設定B
        self.Delay_of_Suspend_pulled_talon = None      # for 四、機台設定查詢\基本設定B
        self.Enable_random_of_Pushing_talon = None     # for 四、機台設定查詢\基本設定B
        self.Enable_random_of_Clamping = None          # for 四、機台設定查詢\基本設定B
        self.Time_of_Push_talon = None                 # for 四、機台設定查詢\基本設定B
        self.Time_of_Suspend_and_Pull_talon = None     # for 四、機台設定查詢\基本
        self.Delay_of_Pull_talon = None                            # for 四、機台設定查詢\基本設定B

        self.Enable_of_Sales_promotion = None                      # for 四、機台設定查詢\基本設定C
        self.Which_number_starting_when_Sales_promotion = None     # for 四、機台設定查詢\基本設定C
        self.Number_of_Strong_grip_when_Sales_promotion = None     # for 四、機台設定查詢\基本設定C

        self.CMD_State_of_Display = None           # for 五、悠遊卡功能\維修顯示
        self.X_Value_of_02_State = None            # for 五、悠遊卡功能\維修顯示
        self.CMD_Backstage_function = None         # for 五、悠遊卡功能\後台功能
        self.Error_Code_of_IPC_Feedback = None     # for 五、悠遊卡功能\後台功能
        
        self.Error_Code_of_Machine = 99          # for 六、 機台故障代碼表
