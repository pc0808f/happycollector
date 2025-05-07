""" 負責MQTT broker連線 發布 與訂閱 回調訂閱 """
from umqtt.simple import MQTTClient
import ujson
import utime
import gc
from mqtt_handler import MqttHandler
from machine import RTC
import time


class MqttManager:
    def __init__(
            self, 
            mac_id=None, 
            server="happycollect.propskynet.com",
            user="myuser",
            password="propskymqtt",
            claw_1=None,
            KindFEILOLIcmd=None,
            version=None,
            wifi_manager="wifi_manager",
            uart_manager='uart_manager',
            LCD_update_flag="LCD_update_flag"
            ):
        
        """ 初始化 MQTT Manager """
        self.server = server
        self.user = user
        self.password = password
        self.mac_id = mac_id
        self.client = None  # MQTT 物件
        self.token = self.load_token()  # 自動取得 token

        # 娃娃機與 UART 發送函式
        self.claw_1 = claw_1
        # self.uart_FEILOLI_send_packet = uart_FEILOLI_send_packet
        self.KindFEILOLIcmd = KindFEILOLIcmd

        #儲存wifi強度訊號
        self.version = version
        #print(f"Debug: MqttManager received version={self.version}")
        self.wifi_manager = wifi_manager

        #直接在這裡初始化MqttHandler實例 處理mqtt訂閱的消息後再發佈的邏輯 (不需要再主程式中實例化了)
        #而這裡的self指的就是MqttManager

        # 傳入`uart_manager` 
        self.uart_manager = uart_manager
        self.LCD_update_flag = LCD_update_flag

        #這裡直接初始化 mqtt_handler 再將uart_manager傳入
        self.mqtt_handler = MqttHandler(self, self.claw_1, self.uart_manager, self.wifi_manager, self.LCD_update_flag)

        # # 訂閱時間的 MQTT 主題
        self.sub_response_time_topic = "000000000000/00000000-0000-0000-0000-000000000000/response_time"
        

    def load_token(self):
        """從 token.dat讀取token"""
        try: 
            with open("token.dat") as f:
                token = f.readline().strip()
            if len(token) == 36:
                print(f"Get token: {token}")
                return token
            else:
                print(f"token長度不對: {len(token)}")
        except Exception as e:
            print(f"無法讀取 token.dat: {e}")
        while True:
            print('遺失token檔案')
            utime.sleep(30)


    
    def connect_mqtt(self, max_retries=5):
        """ 嘗試連線至 MQTT Broker，設置訂閱回調，允許最大重試次數 """
        retries = 0
        while retries < max_retries:
            try:
                self.client = MQTTClient(self.mac_id, self.server, user=self.user, password=self.password)
                self.client.set_callback(self._mqtt_callback)  # 設定 MQTT 訂閱回調函式 # 設定 MQTT 訂閱回調函式  # 確保這行 **在 connect() 之前**
                self.client.connect()
                print("MQTT broker connection OK!")

                print("debug: [Step 5: MQTT 訂閱主題]")
                self.subscribe_topics()  # 連線成功後訂閱主題

                # RTC檢查防呆
                self.check_rtc_on_startup()
                return True
            except Exception as e:
                print(f"MQTT connect fail: {e}")
                retries += 1
                utime.sleep(5)  # 等待 5 秒後重試
        print("無法連線 MQTT broker，請檢查網路或伺服器狀態")
        return False  # 連線失敗時回傳 False

    def subscribe_topics(self):
        """ 訂閱 MQTT 指令主題 """
        if not self.client:
            print("MQTT 客戶端未初始化，無法訂閱主題")
            return

        topics = [
            f"{self.mac_id}/{self.token}/commands", 
            f"{self.mac_id}/{self.token}/fota",
            #f"{self.sub_response_time_prefix}/response_time" #訂閱 time_response
        ]
        for topic in topics:
            try:
                self.client.subscribe(topic)
                print(f"MQTT Subscribe topic: {topic}")
            except Exception as e:
                print(f"訂閱 {topic} 失敗: {e}")
                
    def check_rtc_on_startup(self):
        import machine
        """首次運行時檢查 RTC，如異常則訂閱 MQTT 時間同步主題"""
        if self.is_rtc_valid():
            print("[mqtt_manager(check_rtc_on_startup)]: RTC 時間正常，無需同步")
            return  # RTC 正常，不需要訂閱時間主題
        
        print("[mqtt_manager(check_rtc_on_startup)]: RTC 異常，開始訂閱 MQTT 時間同步主題...")
        self.subscribe_response_time()

        timeout = 10  # 設定 timeout
        while timeout > 0:
            print(f"[mqtt_manager(check_rtc_on_startup)]: timeout 剩餘 {timeout} 秒")  # 確保 timeout 正常遞減
            self.check_messages()  # 檢查是否收到 MQTT 訊息
            if self.is_rtc_valid():
                print("[mqtt_manager(check_rtc_on_startup)]: RTC 設置成功，退訂 MQTT 時間主題")
                self.unsubscribe_response_time(self.sub_response_time_topic)
                print("[mqtt_manager(check_rtc_on_startup)]: 退訂 MQTT `response_time` 主題")
                return  # RTC 設置成功，返回
            
            utime.sleep(1)  
            timeout -= 1

        # **超時仍然無法獲得正確時間，強制重啟 ESP32**
        print("[mqtt_manager(check_rtc_on_startup)]: 超時未獲取時間，設備即將重啟...")
        machine.reset()  # **強制重啟 ESP32**


    
    def is_rtc_valid(self):
        """檢查 RTC 時間是否正常"""
        year, month, day, hour, minute, second, _, _ = time.localtime()
        return year > 2000   # 避免異常時間（如2000 / 1970)    

    
    def reconnect_mqtt(self):
        """ 如果 MQTT 斷線，則重新連線 """
        print("MQTT 連線中斷，重新嘗試連線...")
        self.connect_mqtt()

    def publish_data(self, topic, data):
        try:
            data_json = ujson.dumps(data)
            print("MQTT Publish topic:", topic)
            print("MQTT Publish data(JSON_str):", data_json)
            self.client.publish(topic, data_json)
            utime.sleep(0.2)
            print("MQTT Publish Successful")
        except Exception as e:
            print("MQTT Publish Error:", e)
            #需要再新增這段
            #now_main_state.transition('MQTT is not OK')

    def _mqtt_callback(self, topic, message):
        """ MQTT 訂閱回調函式 (內建於類別)"""
        print("mqtt received new topic")
        print("MQTT Subscribe topic:", topic)
        print("MQTT Subscribe data(JSON_str):", message)

        try:
            data = ujson.loads(message)
            print("MQTT Subscribe data (parsed):", data)

            ## 取得 topic 前綴
            mq_topic_prefix = f"{self.mac_id}/{self.token}"

            #  **防止無限循環**(需要這行不然會出現遞迴#)
            if topic.decode().startswith(mq_topic_prefix + "/commandack"):
                print("跳過自己訂閱自己的訊息")
                return  # 直接返回，不處理這個訊息

            # 根據不同 topic 執行對應處理
            if topic.decode() == f"{mq_topic_prefix}/fota":
                #這裡就可以調用mqtt_handler 中的方法了
                self.mqtt_handler.process_fota(data)

            elif topic.decode() == f"{mq_topic_prefix}/commands":
                #這裡就可以調用mqtt_handler 中的方法了
                self.mqtt_handler.process_commands(data)
                print(f"debug: 有完成發送MQTT主題:{data}")
                ##加入時間
            elif topic.decode() == self.sub_response_time_topic:
                print(f"[MQTT Received] topic: {topic.decode()}, message: {data}")
                # 如果已經退訂 response_time，卻還收到這個主題，就顯示警告
                if topic.decode() == "000000000000/00000000-0000-0000-0000-000000000000/response_time":
                    print("[WARNING] ESP32 如果一直收到 response_time，退訂可能失敗！")
                self.mqtt_handler.process_time_response(data)
            else:
                print(f"收到未知 topic: {topic.decode()}")
        # except ValueError as ve:
        #     print(f"JSON 解析錯誤: {ve}")
        except Exception as e:
            print(f"MQTT 回調函式錯誤: {e}")


    
    def check_messages(self):
        """確認是否有新的mqtt訊息"""
        try:
            if self.client:
                self.client.check_msg()
        except OSError as e:
            print("MQTT connection lost, reconnecting...")
            self.connect_mqtt()

    def subscribe_response_time(self):
        """ 訂閱 MQTT response_time 主題 """
        if not self.client:
            print("[MQTT] 客戶端未初始化，無法訂閱時間同步主題")
            return
        try:
            self.client.subscribe(self.sub_response_time_topic)  # 設定回調
            print(f"[MQTT 訂閱] {self.sub_response_time_topic}")
        except Exception as e:
            print(f"[MQTT 訂閱錯誤] {e}")

    def unsubscribe_response_time(self, topic):
        """手動發送取消訂閱的封包 mqtt.simple沒有提供退訂 只有robust有"""
        
        try:
            if not self.client or not self.client.sock:
                print("MQTT 客戶端未連線，無法退訂主題")
                return
        
            # 產生packet id 避免重複
            packet_id = utime.ticks_ms() & 0XFFFF

            # 組合 UNSUBSCRIBE 封包 (MQTT 固定 Header + 可變 Header + 負載
            pkt = bytearray() #

            #MQTT UNSUBSCRIBE 固定 Header (0xA2) & 預留長度 (0x00)
            pkt.extend(b"\xA2\x00")

            #封包識別碼(Packet Identifier, 2 bytes)
            pkt.append((packet_id >> 8) & 0xFF) # 高8位
            pkt.append(packet_id & 0xFF) # 低8位
                
            #計算topic 長度 並加入
            topic_len = len(topic)
            pkt.append((topic_len >> 8) & 0xFF)# 主題長度高8位
            pkt.append(topic_len & 0xFF)# 主題長度低8位
                    
            # 加入主題名稱
            pkt.extend(topic.encode())

            #設定mqtt長度 # 設定 MQTT 長度 (Variable Length)
            pkt[1] = len(pkt) - 2 # 計算並填入 MQTT Variable Length

            #發送unsubscrib 封包
            self.client.sock.send(pkt)
            print(f"成功手動退訂主題: {topic}")


        except Exception as e:
            print(f"手動退訂 MQTT 主題失敗: {e}")   


