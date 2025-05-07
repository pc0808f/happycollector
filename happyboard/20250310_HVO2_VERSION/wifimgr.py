import network
import socket
import ure
import time
import binascii
import machine
import random

class WiFiManager:
    def __init__(self):
        """Wi-Fi 管理類，負責 Wi-Fi 連線 (STA) 並提供 AP 設定模式"""
        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)

        self.ap_ssid, self.ap_password = self.generate_ap_credentials()

        # 讀取 wifi.dat 中的 SSID & 密碼
        self.ssid, self.password = self.load_wifi_config()

    def generate_ap_credentials(self):
        """根據 ESP32 的唯一 ID 產生 AP 熱點名稱"""
        unique_id_hex = binascii.hexlify(machine.unique_id()[-3:]).decode().upper()
        ap_ssid = "HappyWifi" + unique_id_hex
        ap_password = "happywifi"
        return ap_ssid, ap_password

    def load_wifi_config(self):
        """從 wifi.dat 讀取 Wi-Fi 設定，讀取失敗則返回 (None, None)"""
        try:
            with open('wifi.dat', 'r') as f:
                lines = f.read().strip().split("\n")
                for line in lines:
                    parts = line.split(";")
                    if len(parts) == 2:
                        ssid, password = parts
                        print(f"讀取 Wi-Fi 設定: SSID={ssid}")
                        return ssid, password
        except Exception as e:
            print("無法讀取 wifi.dat:", e)

        return None, None  # 讀取失敗則回傳 `(None, None)`

    def save_wifi_config(self, ssid, password):
        """將新的 Wi-Fi 設定寫入檔案"""
        try:
            with open('wifi.dat', 'w') as f:
                f.write(f"{ssid};{password}\n")
            print(f"Wi-Fi 設定已更新: SSID={ssid}, PASSWORD=******")
        except Exception as e:
            print("無法寫入 Wi-Fi 設定:", e)
    
    def disconnect(self):
        """確保 Wi-Fi 連線被清除，避免 Wi-Fi 內部錯誤"""
        if self.wifi.isconnected():
            self.wifi.disconnect()
            time.sleep(1)
        self.wifi.active(True)

    def connect(self, timeout=60, retry_interval=3):
        """嘗試連線 Wi-Fi，失敗時=>
        => 增加 Timeout 機制
        => 自動偵測 Wi-Fi 連線狀態
        => 才啟動 AP 設定模式"""

        #wifi.dat是空的時候的情況
        if not self.ssid or not self.password:
            print("Wi-Fi 設定檔讀取失敗，啟動 AP 設定模式...")
            self.start_ap_web()
            return None

        if self.wifi.isconnected():
            print("Wi-Fi connected!")
            return self.get_ip_mac()

        print(f"嘗試連線 Wi-Fi {self.ssid} ...")
        self.disconnect()
        self.wifi.connect(self.ssid, self.password)
        
        # 嘗試10次
        for retry in range(10):
            if self.wifi.isconnected():
                print("Wi-Fi 連線成功！")
                return self.get_ip_mac()
            print(f"嘗試連線中... {retry+1}/10")
            time.sleep(2)

        print("Wi-Fi 嘗試連線10次失敗！啟動 AP 設定模式")
        self.start_ap_web()
        return None
    
    def get_signal_strength(self):
        """取得 Wi-Fi 訊號強度 (RSSI)"""
        if self.wifi.isconnected():
            # print(f"WiFi Signal Strength: {self.wifi.status('rssi')} dBm")
            return self.wifi.status('rssi')  # 取得訊號強度
        else:
            print("Unable to retrieve signal strength.")
            return None
    
    def get_ip_mac(self):
        """取得 IP 和 MAC 地址 並將 MAC 轉換為 12 碼 HEX 格式"""
        if self.wifi.isconnected():
            ip_info = self.wifi.ifconfig()  # 獲取完整的 IP 設定
            ip_address = ip_info[0] # IP位置
            raw_mac = self.wifi.config('mac')  # 取得 MAC 位元組
            mac_address = binascii.hexlify(raw_mac).decode().upper()  # 轉換為 12 碼格式
            # mac_address = ":".join(f"{b:02X}" for b in self.wifi.config('mac'))
            #print(f"IP 地址: {ip_address}, MAC: {mac_address}")
            print(f"Network config: {ip_info}")
            return {"ip": ip_address, "mac": mac_address}
        else:
            print("Wi-Fi 未連線，無法獲取 IP/MAC")
            return None

    def start_ap_web(self, port=80):
        """啟動 AP 模式，提供 Web 介面讓使用者輸入 SSID/PASSWORD"""
        wlan_ap = network.WLAN(network.AP_IF)
        wlan_ap.active(True)
        wlan_ap.config(essid=self.ap_ssid, password=self.ap_password, authmode=3)

        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        server_socket = socket.socket()
        server_socket.bind(addr)
        server_socket.listen(1)

        print(f"AP 模式啟動: SSID={self.ap_ssid}, 密碼={self.ap_password}")
        print("開啟瀏覽器，連線到 192.168.4.1 來設定 Wi-Fi")

        while True:
            if self.wifi.isconnected():
                wlan_ap.active(False)
                return

            client, addr = server_socket.accept()
            print('客戶端連線:', addr)
            self.handle_web_requests(client)

    def handle_web_requests(self, client):
        """處理 Web Server 的 HTTP 請求"""
        try:
            request = client.recv(1024).decode('utf-8')  # 明確指定 UTF-8 解碼
            print("請求:", request)

            if "POST" in request:
                match = ure.search("ssid=([^&]*)&password=([^ ]+)", request)  # 避免換行問題
                if match:
                    ssid = match.group(1).replace("%3F", "?").replace("%21", "!").replace("%20", " ")
                    password = match.group(2).replace("%3F", "?").replace("%21", "!").replace("%20", " ")

                    self.save_wifi_config(ssid, password)

                    # 傳送成功回應（確保換行格式正確）
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/plain; charset=utf-8\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "Wi-Fi 設定成功！設備將重新啟動..."
                    )
                    client.send(response.encode('utf-8'))
                    time.sleep(3)
                    machine.reset()
                else:
                    # 400 Bad Request 回應
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain; charset=utf-8\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "無效的 Wi-Fi 設定，請檢查輸入格式！"
                    )
                    client.send(response.encode('utf-8'))
            else:
                # 回傳 Wi-Fi 設定的 HTML 頁面
                html = """\
                    HTTP/1.1 200 OK\r
                    Content-Type: text/html; charset=utf-8\r
                    Connection: close\r
                    \r
                    <!DOCTYPE html>
                    <html lang="zh-TW">
                    <head>
                        <meta charset="UTF-8">
                        <title>Wi-Fi 設定</title>
                    </head>
                    <body>
                        <h1>請輸入 Wi-Fi 設定</h1>
                        <form method="POST">
                            SSID: <input name="ssid"><br>
                            密碼: <input type="password" name="password"><br>
                            <button type="submit">儲存</button>
                        </form>
                    </body>
                    </html>
                """
                client.send(html.encode('utf-8'))  # 使用 UTF-8 編碼傳送
        except Exception as e:
            print(f"處理請求時發生錯誤: {e}")
        finally:
            client.close()  # 確保關閉連線

    # http_time 備援
    def get_http_time(self):
        import usocket
        from machine import RTC
        try:
            # ex:[(2, 1, 6, '', ('142.250.190.196', 80))]
            addr = usocket.getaddrinfo("www.google.com", 80)[0][-1]
            # 建立 TCP 連線
            s = usocket.socket() #建立一個 TCP socket 物件
            s.connect(addr) #連線到 www.google.com，埠號 80（HTTP）
            # 發送head請求(輕量 ) #scoket傳輸
            s.send(b"HEAD / HTTP/1.1\r\nHost: www.google.com\r\nConnection: close\r\n\r\n")
            # 接收+解析伺服器回應
            ## recv(512) 最多 512 字節 的資料（將接收到的二進位資料轉換為 UTF-8 文字)
            response = s.recv(512).decode("utf-8")  # **減少 buffer，節省 RAM**
            # 關閉 TCP 連線，釋放資源
            s.close()

            for line in response.split("\r\n"):
                if line.startswith("Date: "):
                    date_str = line[6:].strip()
                    print("Google 時間:", date_str)

                    try:
                        months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
                        
                        parts = date_str.split(" ")
                        day, month, year = int(parts[1]), months[parts[2]], int(parts[3])
                        hour, minute, second = map(int, parts[4].split(":")) 

                        # 轉換 UTC → 台北時間 (UTC+8)
                        hour += 8
                        if hour >= 24:
                            hour -= 24
                            day += 1  

                            if month in [4, 6, 9, 11] and day > 30:  # **30 天的月份**
                                day, month = 1, month + 1
                            elif month == 2 and day > 28:  # **2 月 (簡化處理，假設不考慮閏年)**
                                day, month = 1, 3
                            elif day > 31:  # **31 天的月份 & 跨年**
                                day, month = 1, (month + 1) if month < 12 else (1, year + 1)

                        # RTC
                        RTC().datetime((year, month, day, 0, hour, minute, second, 0))
                        print(f"ESP32 時間已更新: {year}-{month}-{day} {hour}:{minute}:{second}")
                        return True
                    except Exception as e:
                        print("解析時間失敗:", e)
                        return None
            print("無法獲取 Google 時間")
            return None
        except Exception as e:
            print("Google 時間 API 失敗:", e)
            return None 