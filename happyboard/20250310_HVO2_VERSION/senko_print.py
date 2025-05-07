import urequests
import gc
from time import sleep

class Senko:
    raw = "https://raw.githubusercontent.com"
    github = "https://github.com"

    def __init__(self, user, repo, url=None, branch="master", working_dir="app", files=["boot.py", "main.py"], headers={}):
        self.base_url = "{}/{}/{}".format(self.raw, user, repo) if user else url.replace(self.github, self.raw)
        self.url = url if url is not None else "{}/{}/{}".format(self.base_url, branch, working_dir)
        self.headers = headers
        self.files = files

    def _check_hash(self, x, y):
        import uhashlib
        x_hash = uhashlib.sha1(x.encode())
        y_hash = uhashlib.sha1(y.encode())

        x = x_hash.digest()
        y = y_hash.digest()

        ## 取的比對結果
        result = (str(x) == str(y))

        #===== 這裡加入了 del & gc兩個變數  ======
        del x_hash, y_hash, x, y
        gc.collect()
        #===== 這裡加入了 & gc兩個變數  ======
        
        return result


    def _get_file(self, url): 
        gc.collect()
        payload = urequests.get(url, headers=self.headers)
        code = payload.status_code
        gc.collect()
        if code == 200:
            return payload.text
        else:
            return None

    def _check_all(self):
        changes = []

        for file in self.files:
            ## ==== 這行print加一下會比較好 等到執行到while內的gc 比較有餘裕可以釋放記憶體 ====
            print(f"Debugger:[while之前]:{gc.mem_free()}")
            ## ===============================================
            while(gc.mem_free()<60000):
                gc.collect()
            ## ==== 這行print 可以觀察while內清除記憶體是否有正確釋放回來 ====
                print(f"Debugger:[while內清除]:{gc.mem_free()}")
                sleep(1)
            latest_version = self._get_file(self.url + "/" + file)            
            if latest_version is None:
                continue

            try:
                with open(file, "r") as local_file:
                    local_version = local_file.read()
            except:
                local_version = ""

            if not self._check_hash(latest_version, local_version):
                changes.append(file)
             ## ==== del latest_version, local_version & 透過gc來釋放記憶體 ====
            del latest_version, local_version
            gc.collect()
            ## ==== 打印出loop 每行最後記憶體狀況 ====
            print(f"Debugger:[last_line_loop]:{gc.mem_free()}")

        return changes

    def update(self):
        changes = self._check_all()
        gc.collect()
        for file in changes:
            with open(file, "w") as local_file:
                local_file.write(self._get_file(self.url + "/" + file))
            

        if changes:
            ## ==== 打印 知道是有更新清單====
            print(f"Debugger:[update]: 已更新{changes} {gc.mem_free()}")
            return True
        else:
            ## ==== 打印 確認遠端 與本地檔案一致 所以沒有執行更新 ====
            print(f"Debugger:[update]: 遠端與本地檔案一致 no update {gc.mem_free()}")
            return False