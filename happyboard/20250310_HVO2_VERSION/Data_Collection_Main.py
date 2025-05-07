VERSION = "VO1.02a_light"
# 確保了rtc必須正確的機制 不正確就reset

# import micropython
# print("Debugger:[Data_Collection_Main] 首行，記憶體:")
# micropython.mem_info()
#標準庫
import os
import utime
import gc
import _thread
import ujson
import machine
#外部依賴
from machine import UART, Timer, WDT
#from machine import UART, Pin, SPI, Timer, WDT
from umqtt.simple import MQTTClient
#本地
from uart_handler import UartHandler
from uart_manager import UartManager
from mqtt_manager import MqttManager
from timer_manager import TimerManager
from received_claw_data import ReceivedClawData


# 定義狀態類型
class MainStatus:
    NONE_WIFI = 0       # 還沒連上WiFi
    NONE_INTERNET = 1   # 連上WiFi，但還沒連上外網      現在先不做這個判斷
    NONE_MQTT = 2       # 連上外網，但還沒連上MQTT Broker
    NONE_FEILOLI = 3    # 連上MQTT，但還沒連上FEILOLI娃娃機
    STANDBY_FEILOLI = 4 # 連上FEILOLI娃娃機，正常運行中
    WAITING_FEILOLI = 5 # 連上FEILOLI娃娃機，等待娃娃機回覆
    GOING_TO_OTA = 6    # 接收到要OTA，但還沒完成OTA
    UNEXPECTED_STATE = -1


# 定義狀態機類別
class MainStateMachine:
    def __init__(self):
        self.state = MainStatus.NONE_WIFI
        # 以下執行"狀態機初始化"相應的操作
        print('\n\rInit, MainStatus: NONE_WIFI')
        global main_while_delay_seconds, LCD_update_flag
        main_while_delay_seconds = 1
        LCD_update_flag['Uniform'] = True

    def transition(self, action):
        global main_while_delay_seconds, LCD_update_flag
        if action == 'WiFi is disconnect':
            self.state = MainStatus.NONE_WIFI
            # 以下執行"未連上WiFi後"相應的操作
            print('\n\rAction: WiFi is disconnect, MainStatus: NONE_WIFI')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_WIFI and action == 'WiFi is OK':
            self.state = MainStatus.NONE_INTERNET
            # 以下執行"連上WiFi後"相應的操作
            print('\n\rAction: WiFi is OK, MainStatus: NONE_INTERNET')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_INTERNET and action == 'Internet is OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"連上Internet後"相應的操作
            print('\n\rAction: Internet is OK, MainStatus: NONE_MQTT')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_MQTT and action == 'MQTT is OK':
            self.state = MainStatus.NONE_FEILOLI
            # 以下執行"連上MQTT後"相應的操作
            print('\n\rAction: MQTT is OK, MainStatus: NONE_FEILOLI')
            main_while_delay_seconds = 10
            LCD_update_flag['WiFi'] = True
            LCD_update_flag['Claw_State'] = True

        elif (self.state == MainStatus.NONE_FEILOLI or self.state == MainStatus.WAITING_FEILOLI) and action == 'FEILOLI UART is OK':
            self.state = MainStatus.STANDBY_FEILOLI
            # 以下執行"連上FEILOLI娃娃機後"相應的操作
            print('\n\rAction: FEILOLI UART is OK, MainStatus: STANDBY_FEILOLI')
            main_while_delay_seconds = 10
            LCD_update_flag['Claw_State'] = True

        elif self.state == MainStatus.STANDBY_FEILOLI and action == 'FEILOLI UART is waiting':
            self.state = MainStatus.WAITING_FEILOLI
            # 以下執行"等待FEILOLI娃娃機後"相應的操作
            print('\n\rAction: FEILOLI UART is waiting, MainStatus: WAITING_FEILOLI')
            main_while_delay_seconds = 10

        elif self.state == MainStatus.WAITING_FEILOLI and action == 'FEILOLI UART is not OK':
            self.state = MainStatus.NONE_FEILOLI
            # 以下執行"等待失敗後"相應的操作
            print('\n\rAction: FEILOLI UART is not OK, MainStatus: NONE_FEILOLI')
            main_while_delay_seconds = 10    
            LCD_update_flag['Claw_State'] = True

        elif (self.state == MainStatus.NONE_FEILOLI or self.state == MainStatus.STANDBY_FEILOLI or self.state == MainStatus.WAITING_FEILOLI) and action == 'MQTT is not OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"MQTT失敗後"相應的操作
            print('\n\rAction: MQTT is not OK, MainStatus: NONE_MQTT')
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        else:
            print('\n\rInvalid action:', action, 'for current state:', self.state)
            main_while_delay_seconds = 1
 

def get_file_info(filename):
    try:
        file_stat = os.stat(filename)
        file_size = file_stat[6]  # Index 6 is the file size
        file_mtime = file_stat[8]  # Index 8 is the modification time
        return file_size, file_mtime
    except OSError:
        return None, None

class KindFEILOLIcmd:
    Ask_Machine_status = 210
    Send_Machine_reboot = 215
    Send_Machine_shutdown = 216
    Send_Payment_countdown_Or_fail = 231
    Send_Starting_games = 220
    Send_Starting_once_game = 221
    Ask_Transaction_account = 321 # 查詢:遠端帳目
    Ask_Coin_account = 322 # 查詢:投幣帳目
    
    Send_Clean_transaction_account = 323 # 清除:遠端帳目
    #Clean_Coin_account = 324 ## 清除:投幣帳目
    Ask_Machine_setting = 431


############################################# 初始化 #############################################
print('\n\r開始執行Data_Collection_Main初始化，版本為:', VERSION)
print('開機秒數:', utime.ticks_ms() / 1000)

print('1開機秒數:', utime.ticks_ms() / 1000)

wdt=WDT(timeout=1000*60*10)

print('2開機秒數:', utime.ticks_ms() / 1000)

# 可以獨立
LCD_update_flag = {
    'Uniform': True,
    'WiFi': False,
    'Time': False,
    'Claw_State': False,
    'Claw_Value': False,
}

print('3開機秒數:', utime.ticks_ms() / 1000)

# 創建狀態機
now_main_state = MainStateMachine()

# 創建娃娃機資料
claw_1 = ReceivedClawData()

# 創建 MQTT Client 1 資料
mq_client_1 = None


#==============
# # UART配置(改成初始化UART阜口)
#==============

uart_handler = UartHandler(claw_1, None, LCD_update_flag, now_main_state) # 但先不設定 mqtt_handler=None

# print("Debugger:[Step 2: 初始化 UART Manager] 記憶體:")
# micropython.mem_info()
uart_manager = UartManager(claw_1=claw_1,
    KindFEILOLIcmd=KindFEILOLIcmd,
    uart_handler=uart_handler,
    mqtt_handler=None) # 先不設定 mqtt_handler=None) 

#==============
# 1.mqtt_manager初始化(已含toke取得)
# 涵蓋娃娃機參數 UART類別 KindFEILOLIcmd類別
#==============

#要測試UART_MANAGEr
# print("Debugger:[Step 3: 初始化 MQTT Manager | MqttHandler也在其中初始化] 記憶體:")
# micropython.mem_info()
mqtt_manager = MqttManager(
    mac_id=network_info["mac"],
    claw_1=claw_1,
    KindFEILOLIcmd=KindFEILOLIcmd,
    version=VERSION,
    wifi_manager=wifi_manager,
    uart_manager=uart_manager,
    LCD_update_flag=LCD_update_flag
) #並在其中建立 mqtt_handler()



#==============
# 解決 MQTT Manager、UART Manager、UART Handler 之間的「相互依賴性」問題
# 下面這段是確保 它們在初始化完成後，能夠互相存取彼此的物件，避免「循環依賴
#==============
# print("Debugger:[Step 4: 相互依賴解耦與物件關聯初始化] 記憶體:")
# micropython.mem_info()
gc.collect()

## ==============
# 避免在初始化階段因物件還未建立好就被呼叫，導致 NoneType 錯誤。
# 等到所有物件都建立完成後，再進行後設綁定，確保每個類別都能正確存取到其他類別的實體物件
## ==============
## 這時候 `mqtt_manager` 已經初始化完畢，直接取出 `mqtt_manager.mqtt_handler`
mqtt_handler = mqtt_manager.mqtt_handler  # 直接用 `MqttManager` 內建的 `MqttHandler`

# 已有了mqtt_handler，設定 MQTT Handler 到 UART Manager
uart_manager.mqtt_handler = mqtt_handler

# 已有了mqtt_handler，設定 MQTT Handler 到 UART Handler
uart_handler.mqtt_handler = mqtt_handler

# 已有了uart_manager，，設定 UART Manager 到 MQTT Manager
mqtt_manager.uart_manager = uart_manager

gc.collect()
# ========================
# 初始化timer
# =========================
timer_manager = TimerManager(now_main_state, MainStatus, wifi_manager, uart_manager, mqtt_manager, mqtt_handler, lcd_mgr, wdt, LCD_update_flag, claw_1)

gc.collect()

_thread.stack_size(16 * 1024)  # 只需設置一次
#_thread.stack_size(20 * 1024)  # 只需設置一次
_thread.start_new_thread(uart_manager.receive_packet, ())
utime.sleep(2) 


# ========================
# 執行timer callback
# =========================
timer_manager.start_timers()
# print("Debugger:[start Timer] 記憶體:")
# micropython.mem_info()

last_time = 0
main_while_delay_seconds = 1
while True:

    utime.sleep_ms(500)
    

    current_time = utime.ticks_ms()
    if (utime.ticks_diff(current_time, last_time) >= main_while_delay_seconds * 1000):
        last_time = utime.ticks_ms()


        if now_main_state.state == MainStatus.NONE_WIFI:
            print('\n\rnow_main_state: WiFi is disconnect, 開機秒數:', current_time / 1000)
            # =============================
            # network_info
            # =============================
            print("My IP Address:", network_info['ip'])
            print("My MAC Address:", network_info['mac'])
            now_main_state.transition('WiFi is OK')
            

        elif now_main_state.state == MainStatus.NONE_INTERNET:
            print('\n\rnow_main_state: WiFi is OK, 開機秒數:', current_time / 1000)
            now_main_state.transition('Internet is OK')  # 目前不做判斷，狀態機直接往下階段跳轉

        elif now_main_state.state == MainStatus.NONE_MQTT:
            print('now_main_state: Internet is OK, 開機秒數:', current_time / 1000)
            # =============================
            # 連線mqtt
            # =============================
            # 連線 MQTT
            mqtt_manager.connect_mqtt()
            #print(f"mqtt: {mqtt_manager}")
            #mq_client_1 = connect_mqtt()

            mq_client_1 = mqtt_manager.client
            #print(f"mqtt_client: {mq_client_1}")
            if mq_client_1 is not None:
                try:
                    now_main_state.transition('MQTT is OK')
                except:
                    print('MQTT subscription has failed')

            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.NONE_FEILOLI:
            print('\n\rnow_main_state: MQTT is OK (FEILOLI UART is not OK), 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.STANDBY_FEILOLI:
            print('\n\rnow_main_state: FEILOLI UART is OK, 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.WAITING_FEILOLI:
            print('\n\rnow_main_state: FEILOLI UART is witing, 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())
            

        else:
            print('\n\rInvalid action! now_main_state:', now_main_state.state)
            print('開機秒數:', current_time / 1000)
            gc.collect()
         

        LCD_update_flag['Time'] = True