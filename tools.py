import json
import os
import random
import re
import socket
import subprocess
import threading
import time
import tkinter as tk
import tkinter.font as tkFront
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from urllib import parse

pools = [  # 结点池，支持b64编码的Trojan、Vmess，Vless和ss协议
    "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt",
    "https://nodefree.org/dy/2023/10/20231022.txt",
    # "https://raw.githubusercontent.com/pojiezhiyuanjun/2023/master/1022.txt",
    "https://clashnode.com/wp-content/uploads/2023/10/20231023.txt",
    "https://gitlab.com/mfuu/v2ray/-/raw/master/v2ray",
    "https://raw.fastgit.org/ZywChannel/free/main/sub",
    "https://v2ray.neocities.org/v2ray.txt",
    "https://raw.fastgit.org/Pawdroid/Free-servers/main/sub",
    "https://youlianboshi.netlify.com",
    "https://free.jingfu.cf/vmess/sub",
    "https://jiang.netlify.app/",
    "https://sub.pmsub.me/base64",
    "https://nodefree.org/dy/2023/11/20231121.txt",
    "https://clashnode.com/wp-content/uploads/2023/11/20231122.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.fastgit.org/freefq/free/master/v2",
    # "https://raw.githubusercontent.com/pojiezhiyuanjun/2023/master/1121.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/free",
    # "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
    # "https://raw.githubusercontent.com/vveg26/get_proxy/main/dist/v2ray.config.txt",
    # "https://raw.githubusercontent.com/openrunner/clash-freenode/main/v2ray.txt",
    "https://tt.vg/freev2",
    # "https://kxswa.tk/v2ray"
]

testResource = [r'"http://drive.google.com/uc?export=download&id=1SasaZhywEOXpVl61a7lqSXppCTSmj3pU"',
                r'"http://drive.google.com/uc?export=download&id=1rGfa8eK_3wb4uuQHT1uvitXOHxD4uh51"',
                r'"http://drive.google.com/uc?export=download&id=1TQEDtoAOU75aPKi4-f4ZmUI1eW8qbH_9"',
                r'"http://drive.google.com/uc?export=download&id=12asg8djJtWQireWma1nRuSnJI969tNNP"',
                r'"http://drive.google.com/uc?export=download&id=1dAyib4HtOTfyy_WARIxLthQQYOiKENX2"',
                r'"http://drive.google.com/uc?export=download&id=170CpxgVRk8yrb6FjFmnTJDHP-qWgeHZz"'
                ]  # 测速用，谷歌云盘文件]

# 核心参数，影响能不能用，最大支持V2rayN版本3.29
configDir = "v2ray_win_temp/"  # 自定义配置文件所在文件夹
NGConfigName = "36ad1899-d3d4-49f1-9dd2-7e2052059f81.json"  # 指向自定义配置文件
NGSocksPort = 23333  # 本地监听Socks端口
NGHttpPort = NGSocksPort + 1  # 本地监听HTTP端口

# 影响体验
testSpeed = True  # 若设为否，则不使用谷歌盘测速，仅测试是否能访问谷歌
testTime = 15  # 测速时间
maxProcess = 50  # 最大测速线程数
nodeLimit = 5  # 目标结点个数
spdLimit = 666  # 速度限制
minSpeed = 50  # 目标结点最小速度
fallBackTimeout = 90  # 超时未检测到结点，触发降级，启用备用方案

# 无关紧要
testPort = 33333  # 测速线程起始端口
debug = False
useExclude = False  # 开启后会排除下列地区的结点
exclude = re.compile('HK|TW|US')
update = True  # 自动升级
version = "Auto config v3.0, 2023-11-27 "
pools = list(set(pools))  # 去重复
lock = threading.Lock()


def log(str):
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " -- " + str + "\n")


class Data():
    def __init__(self):
        self.nodes = None
        self.fallback = False
        self.spdNodes = []
        self.testPort = testPort

    def decode_base64(self, data):
        missing_padding = 4 - len(data) % 4
        if missing_padding:
            data += '=' * missing_padding
            try:
                r = b64decode(data).decode("utf-8")
            except UnicodeDecodeError:
                try:
                    r = b64decode(data).decode("gbk")
                except UnicodeDecodeError:
                    return None
            return r

    def isPortOpen(self, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", int(port)))
            sock.close()
            return True
        except ConnectionRefusedError:
            return False
        finally:
            sock.close()

    def doTest(self, param):
        port, vrayid, count, node = param[0], param[1], param[2], param[3]
        waitCount = 0
        while not self.isPortOpen(port):
            time.sleep(1)
            waitCount += 1
            if waitCount > 5:
                log("warning: port " + str(port) + " open failed")
                vrayid.kill()
                return 0
        if self.fallback:
            state = False
            for i in range(0, 2):
                google = os.popen(
                    "curl -x http://localhost:" + str(port) + " -skLI www.google.com  -m 8").read(150)
                if str(google).find("ISO-8859-1") != -1:
                    state = True
                    break
                twitter = os.popen(
                    "curl -x http://localhost:" + str(port) + " -skI www.twitter.com  -m 8").read(50)
                if str(twitter).find("301 Moved Permanently") != -1:
                    state = True
                    break
            if state:
                log("fallback: port " + str(port) + " √")
                node["speed"] = minSpeed + 1
            else:
                if port % 5 == 0:
                    log("fallback: port " + str(port) + " ×")
                    node["speed"] = -1
        else:
            targetSrc = testResource[random.randint(0, len(testResource) - 1)]
            driver = subprocess.Popen(
                'curl -x http://localhost:' + str(port) + ' -m ' + str(
                    testTime) + ' -skL -o c:/windows/nul ' + targetSrc + ' --limit-rate ' + str(
                    spdLimit) + 'k -w "%{speed_download}"',
                stdout=subprocess.PIPE)
            res = int(float(driver.stdout.read().decode()) / 1024)
            node["speed"] = res
            if res == 0:
                if port % 10 == 0:
                    log("normal: port " + str(port) + " " + str(res) + "KB/s")
            else:
                log("normal: port " + str(port) + " " + str(res) + "KB/s")
        if node["speed"] > minSpeed:
            try:
                info = json.loads(
                    os.popen("curl -x http://localhost:" + str(
                        port) + " http://ip-api.com/json/?fields=61439 -skL -m 8").read())
                node["region"] = str(info["countryCode"])
                if useExclude and exclude.search(node["region"]) is not None:
                    log("port " + str(port) + " exclude" + node["region"])
                    vrayid.kill()
                    return
            except Exception as e:
                node["region"] = "-1"
            ping = os.popen("tcping -n 1 -w 1 -p " + node["port"] + " " + node["add"]).read()
            if ping.find("Average") != -1:  # 通
                try:
                    temp = ping.split("=")
                    delay = temp[len(temp) - 1]
                    ddelay = int(delay[:-7])  # str->float
                    node["delay"] = ddelay
                except:
                    node["delay"] = -1
                    pass
            else:
                node["delay"] = -1
            node["inbound"] = port
            node["state"] = "-"
            self.spdNodes.append(node)
        vrayid.kill()
        count[0] -= 1
        if debug:
            with open(configDir + str(port) + "v2ray.log", "w+") as file:
                file.write(vrayid.stdout.read().decode())

    def generateConfig(self):
        fbk_start = self.fallback
        runs = []
        count = [0]
        executes = ThreadPoolExecutor(max_workers=maxProcess)
        unTestIndex = 0
        if fbk_start:
            log("fallback: total to test " + str(len(self.nodes)))
        else:
            log("normal: total to test " + str(len(self.nodes)))
        for index in range(0, len(self.nodes) - 1):
            if count[0] > maxProcess:
                time.sleep(3)
            node = self.nodes[index]
            try:
                self.doGenerate(node, self.testPort)
            except Exception as e:
                log("warning: cannot generate config on")
                log(json.dumps(node))
                log(str(e))
                continue
            count[0] += 1
            if fbk_start != self.fallback:  # 激活了emg，需要关闭非emg
                log("normal: terminate since fallback activated")
                break
            if len(self.spdNodes) > nodeLimit:
                unTestIndex = index + 1
                if fbk_start:
                    log("fallback: obtain " + str(nodeLimit) + " available, stop testing")
                else:
                    log("normal: obtain " + str(nodeLimit) + " available, stop testing")
                break
            process = subprocess.Popen("v2ray.exe -config " + configDir + str(self.testPort) + ".json",
                                       stdout=subprocess.PIPE)
            runs.append(executes.submit(self.doTest, (self.testPort, process, count, node)))
            self.testPort += 1
        unTestedNode = self.nodes[unTestIndex:]
        while True:
            ok = True
            for tester in runs:
                ok = tester.done() and ok
            if ok:
                break
            time.sleep(2)
        for i in unTestedNode:  # normal结束过程中，fallback已经拿走部分unTest并加上了speed，此处防止normal改回-1
            try:
                i["speed"]
            except KeyError:
                i["speed"], i["delay"], i["region"] = -1, -1, -1
        self.nodes = self.spdNodes + unTestedNode
        if fbk_start:
            log("fallback: done, next to test " + str(len(self.nodes)))
        else:
            log("normal: done, next to test " + str(len(self.nodes)))

    def doGenerate(self, node, port, forNG=False):
        baseConfig = {
            "outbounds": [
                {"tag": "proxy", "protocol": "", "settings": {"vnext": [{}], "servers": [{}], },
                 "streamSettings": {}}],
            "inbounds": [{"protocol": "http", "listen": "0.0.0.0", "port": 0}],
            "log": {},
            "origin": {}
        }
        outbounds = baseConfig["outbounds"][0]
        if node["clazz"] == "vmess":
            outbounds["protocol"] = "vmess"
            outbounds["settings"]["vnext"][0] = {
                "address": node["add"],
                "port": int(node["port"]),
                "users": [
                    {
                        "id": node["id"],
                        "alterId": int(node["aid"])
                    }
                ]
            }
            outbounds["streamSettings"] = {
                "network": node["net"],  # tcp ws
                "security": node["tls"],  # none tls
                "tlsSettings": {
                    "allowInsecure": True,
                    "serverName": node["host"]
                },
                "wsSettings": {
                    "path": node["path"],
                    "headers": {
                        "Host": node["host"]
                    }
                }
            }
        elif node["clazz"] == "vless":
            outbounds["protocol"] = "vless"
            outbounds["settings"]["vnext"][0] = {
                "address": node["add"],
                "port": int(node["port"]),
                "users": [
                    {
                        "id": node["id"],
                        "encryption": "none",
                    }
                ]
            }
            outbounds["streamSettings"] = {
                "network": node["type"][0],
                "security": node["security"][0],
                "tlsSettings": {
                    "allowInsecure": True,
                    "serverName": node["sni"][0]
                },
                "wsSettings": {
                    "path": node["path"][0],
                    "headers": {
                        "Host": node["sni"][0]
                    }
                }
            }
        elif node["clazz"] == "trojan":
            outbounds["protocol"] = "trojan"
            outbounds["settings"]["servers"][0] = {
                "address": node["add"],
                "password": node["password"],
                "port": int(node["port"]),
            }

            outbounds["streamSettings"] = {
                "network": node["type"][0],
                "security": node["security"][0],
                "tlsSettings": {
                    "allowInsecure": node["allowInsecure"][0],
                    "serverName": node["sni"][0]
                }
            }
        elif node["clazz"] == "ss":
            outbounds["protocol"] = "shadowsocks"
            outbounds["settings"]["servers"][0] = {
                "address": node["add"],
                "method": node["method"],
                "password": node["password"],
                "port": int(node["port"]),
            }
        baseConfig["outbounds"] = [outbounds]
        baseConfig["inbounds"][0]["port"] = port

        if debug:
            baseConfig["log"] = {"loglevel": "info"}
            baseConfig["origin"] = node
        if forNG:
            self.killNG()
            baseConfig["inbounds"][0]["protocol"] = "socks"
            with open(configDir + NGConfigName, "w+") as file:
                file.write(json.dumps(baseConfig))
            NGconfig = {
                "inbound": [
                    {
                        "localPort": NGSocksPort,
                        "protocol": "socks",
                        "udpEnabled": True,
                        "sniffingEnabled": True
                    }
                ],
                "logEnabled": False,
                "loglevel": "warning",
                "index": 0,
                "vmess": [
                    {
                        "configVersion": 2,
                        "address": NGConfigName,
                        "port": 0,
                        "id": "",
                        "alterId": 0,
                        "security": "",
                        "network": "",
                        "remarks": "import custom@2023/11/30",
                        "headerType": "",
                        "requestHost": "",
                        "path": "",
                        "streamSecurity": "",
                        "allowInsecure": "",
                        "configType": 2,
                        "testResult": "",
                        "subid": "",
                        "flow": ""
                    }
                ],
                "muxEnabled": True,
                "domainStrategy": "AsIs",
                "routingMode": "0",
                "useragent": [],
                "userdirect": [],
                "userblock": [],
                "kcpItem": {
                    "mtu": 1350,
                    "tti": 50,
                    "uplinkCapacity": 12,
                    "downlinkCapacity": 100,
                    "congestion": False,
                    "readBufferSize": 2,
                    "writeBufferSize": 2
                },
                "listenerType": 2,
                "speedTestUrl": "http://cachefly.cachefly.net/10mb.test",
                "speedPingTestUrl": "https://www.google.com/generate_204",
                "urlGFWList": "https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt",
                "allowLANConn": False,
                "enableStatistics": False,
                "keepOlderDedupl": False,
                "statisticsFreshRate": 2000,
                "remoteDNS": "",
                "defAllowInsecure": True,
                "subItem": [],
                "uiItem": {
                    "mainSize": "1287, 788",
                    "mainLvColWidth": {
                        "def": 30,
                        "configType": 80,
                        "remarks": 245,
                        "address": 547,
                        "port": 50,
                        "security": 90,
                        "network": 70,
                        "subRemarks": 50,
                        "testResult": 70
                    }
                },
                "userPacRule": [
                    "github.com"
                ]
            }
            with open("guiNConfig.json", "w+") as file:
                file.write(json.dumps(NGconfig))
        with open(configDir + str(port) + ".json", "w+") as file:
            file.write(json.dumps(baseConfig))

    def retrieveFromPools(self, conn):
        executes = ThreadPoolExecutor(max_workers=8)
        retrievers, nodes = [], []
        if conn:
            log("proxy ready, connect by proxy")
        else:
            log("proxy not ready, connect directly")
        for pool in pools:
            retrievers.append(executes.submit(self.doRetrieve, (pool, conn, NGHttpPort, nodes)))
        while True:
            ok = True
            for retriever in retrievers:
                ok = retriever.done() and ok
            if ok:
                break
            time.sleep(2)
        log("get nodes: " + str(len(nodes)))
        nodes = set([str(i) for i in nodes])
        log("remove duplicates: " + str(len(nodes)))
        nodes = list([eval(i) for i in nodes])
        self.nodes = nodes

    def killNG(self):
        file = os.popen("tasklist | findstr \"v2rayN.exe\" ")
        try:
            pid = (str(int(file.read(34).split("v2rayN.exe")[1])))
            os.popen("taskkill -pid " + pid + " -f")
        except IndexError:
            pass
        time.sleep(0.8)

    def doRetrieve(self, param):
        available = False
        src, ispx, pxport, nodes = param[0], param[1], param[2], param[3]
        for i in range(0, 2):  # 两次机会
            if ispx:  # 代理就绪，使用代理获取结点
                r = os.popen("curl -x http://localhost:" + str(pxport) + " " + src + " -skL -m 10").read()
            else:  # 代理不就绪，直接获取结点
                r = os.popen("curl " + src + " -skL -m 10").read()
            if len(r) < 100:
                if r == "":
                    r = "return nothing"
                log("warning: " + src.replace("https://", "") + " " + r)
                continue
            available = True
            break
        if available:
            try:
                count = 0
                content = self.decode_base64(r)
                if content is None:
                    log("warning: src " + src.replace("https://", "") + " decode error")
                    return
                content = content.split("\n")
                for link in content:
                    if link.startswith("vmess://"):
                        messlink = link.replace("vmess://", "")
                        messraw = self.decode_base64(messlink)
                        if messraw is None:
                            continue
                        vmess = json.loads(messraw)
                        messkeys = ['add', 'port', 'id', 'aid', 'net', 'host', 'path', 'tls']
                        for k in messkeys:
                            try:
                                vmess[k]
                            except KeyError:
                                vmess[k] = ""
                        vmess["clazz"], vmess["from"] = "vmess", src
                        nodes.append(vmess)
                        count += 1

                    if link.startswith("trojan://"):
                        lesslink = link.replace("trojan://", "")
                        tjraw = re.split('[@,:,?,#]', lesslink)
                        for i in range(-4, -1):
                            trojan = parse.parse_qs(tjraw[-6 - i])  # 找到参数
                            if trojan != {}:
                                break
                        for k in ["allowInsecure", "sni", "security", "type"]:
                            try:
                                trojan[k]
                            except KeyError:
                                trojan[k] = [""]

                        trojan["password"], trojan["add"], trojan["port"] = tjraw[0], tjraw[1], tjraw[2]
                        if trojan["allowInsecure"] == 0:
                            trojan["allowInsecure"] = [False]
                        else:
                            trojan["allowInsecure"] = [True]
                        if trojan["type"][0] == "":
                            trojan["type"] = ["tcp"]
                        trojan["clazz"], trojan["from"] = "trojan", src
                        nodes.append(trojan)
                        count += 1

                    if link.startswith("vless://"):
                        lesslink = link.replace("vless://", "")
                        lessraw = re.split('[@,:,?,#]', lesslink)
                        for i in range(-4, -1):
                            vless = parse.parse_qs(lessraw[-6 - i])
                            if vless != {}:
                                break
                        for k in ["path", "sni", "security", "type"]:
                            try:
                                vless[k]
                            except KeyError:
                                vless[k] = [""]
                        vless["id"], vless["add"], vless["port"] = lessraw[0], lessraw[1], lessraw[2]
                        if vless["type"][0] == "":
                            vless["type"][0] = "ws"
                        vless["clazz"], vless["from"] = "vless", src
                        nodes.append(vless)
                        count += 1

                    if link.startswith("ss://"):
                        ok = False
                        try:
                            sslink = link.replace("ss://", "")
                            ssraw = re.split('[@,:,#]', sslink)
                            ss = {"add": ssraw[1], "port": ssraw[2]}
                            con = self.decode_base64(ssraw[0])
                            if con is None:
                                continue
                            ss["method"] = con.split(":")[0]  # 以另一种方式分享，取不到
                            ss["password"] = con.split(":")[1]
                            ok = True
                        except:
                            try:
                                con = self.decode_base64(ssraw[0])
                                if con is None:
                                    continue
                                ssraw2 = re.split('[:,@,:]', con)
                                ss = {"add": ssraw2[2], "port": ssraw2[-1], "method": ssraw2[0],
                                      "password": ssraw2[1]}
                                ok = True
                            except:
                                pass
                        if ok:
                            ss["clazz"], ss["from"] = "ss", src
                            nodes.append(ss)
                            count += 1
                log(src.replace("https://", "") + " : " + str(count) + "/" + str(len(content)))
            except Exception as e:
                log("warning: " + src + str(e))
                return


def addData(self, spdNodes):
    for i in range(0, 20):
        spdNodes.append(
            {"speed": random.randint(1, 2000), "state": "o", "delay": random.randint(100, 500), "region": "US",
             "add": "xxx",
             "clazz": "ss" + str(random.randint(1, 200)), "from": "xxx"})
        time.sleep(1)


class Gui():
    def __init__(self):
        self.data = Data()
        self.lastSeen = 0
        self.update = update
        self.fallBackTime = fallBackTimeout
        self.clean = True
        if not debug:
            conn = self.detectConn(NGHttpPort, True)
            self.data.retrieveFromPools(conn)
            if not testSpeed:
                self.doFallback()
            else:
                gc = threading.Thread(target=self.data.generateConfig)
                gc.daemon = True
                gc.start()
                while len(self.data.spdNodes) == 0:
                    if self.fallBackTime % 5 == 0:
                        log("normal: testing... " + str(self.fallBackTime))
                    self.fallBackTime -= 1
                    if self.fallBackTime == 0:
                        self.doFallback()
                        break
                    time.sleep(1)
        else:
            t = threading.Thread(target=addData, args=(self, self.data.spdNodes))
            t.daemon = True
            t.start()

        root = tk.Tk()
        self.var = tk.StringVar()
        t2 = threading.Thread(target=self.nodeListener)
        t2.daemon = True
        t2.start()
        ft1 = tkFront.Font(family="Consolas", size=11)
        root.title(version)
        root.geometry("400x300")

        msg = "  Tag Region Speed Delay Protocol Source"
        tittle = tk.Label(root, text=msg, anchor="w", font=ft1)
        tittle.pack(side="top", expand=True, fill=tk.BOTH)
        middle = tk.Frame(root)
        middle.pack(expand=True, fill=tk.BOTH)
        sc = tk.Scrollbar(middle)
        sc.pack(side="right", fill=tk.Y)

        self.box = tk.Listbox(middle, listvariable=self.var, font=ft1, yscrollcommand=sc.set)  # 条随表动
        sc.config(command=self.box.yview)  # 表随条动

        self.box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipadx=5, ipady=5)
        self.box.insert(0, "Hello")
        btnFrame = tk.Frame(root)
        self.btnOK = tk.Button(btnFrame, text="确定", width=9, height=2, command=lambda: self.btnOk())
        self.btnOK.pack(side="right", padx=10)

        self.btnRetest = tk.Button(btnFrame, text="重测", width=9, height=2, command=lambda: self.reTest())
        self.btnRetest.pack(side="right", padx=0)
        btnFrame.pack(fill=tk.BOTH, expand=True, pady=10)

        stateFrame = tk.Frame(btnFrame)

        self.state = tk.Label(stateFrame, bg="red")
        self.hint = tk.Label(stateFrame, text="测试中...")

        self.state.pack(side="left")
        self.hint.pack(side="left")
        stateFrame.pack(side="left", padx=30)
        root.quit()
        tk.mainloop()

    def doFallback(self):
        log("trigger fallback")
        self.data.fallback = True  # 通知normal，fallback已启动
        self.fallBackTime = fallBackTimeout
        gc = threading.Thread(target=self.data.generateConfig)
        gc.daemon = True
        gc.start()
        fallBackError = False
        while len(self.data.spdNodes) == 0:
            if self.fallBackTime % 5 == 0:
                log("fallback: testing... " + str(self.fallBackTime))
            self.fallBackTime -= 1
            if self.fallBackTime == 0:
                fallBackError = True
                break
            time.sleep(1)
        if fallBackError:
            log("error: no available nodes in fallback mode, check settings")
            exit()

    def changeBtn(self, btn, to):
        if to == "enable":
            btn["state"] = tk.ACTIVE
        elif to == "disable":
            btn["state"] = tk.DISABLED

    def changeState(self, state, info=""):
        if state == "test":
            self.state["bg"] = "red"
            self.hint["text"] = "测试中..."
        elif state == "config":
            self.state["bg"] = "red"
            self.hint["text"] = "配置中: " + info
        elif state == "ok":
            self.state["bg"] = "green"
            self.hint["text"] = "OK: " + info
        elif state == "fail":
            self.state["bg"] = "red"
            self.hint["text"] = "FAILED: " + info
        elif state == "reset":
            self.state["bg"] = "red"
            self.hint["text"] = "RESET: " + info
        elif state == "standby":
            self.state["bg"] = "green"
            self.hint["text"] = "请选择"
        elif state == "end":
            self.state["bg"] = "red"
            self.hint["text"] = "nothing to do"

    def configNG(self, current_select):
        node = self.data.spdNodes[current_select]
        lock.acquire()
        self.data.doGenerate(node, NGSocksPort, True)
        self.startNG()
        info = node["region"] + ", " + str(node["speed"]) + "K/s, " + str(node["delay"]) + "ms"
        if self.detectConn(NGHttpPort):
            self.changeState("ok", info)
            self.data.spdNodes[current_select]["state"] = "o"
            log("OK: " + info)
            if self.clean:
                if not debug:
                    self.clearTestConfig()
            if self.update:
                self.update = False
                gc = threading.Thread(target=self.update_tools)
                gc.daemon = True
                gc.start()
        else:
            self.changeState("fail", info)
            self.data.spdNodes[current_select]["state"] = "x"
            self.data.spdNodes[current_select]["speed"] = -1
            log("FAILED: " + info)
        self.var.set(self.prepareBoxMsg(sorted(self.data.spdNodes, reverse=True, key=lambda x: x["speed"])))
        lock.release()

    def btnOk(self):
        if len(self.box.curselection()) == 0:
            return
        val = self.box.get(self.box.curselection())
        val = re.sub(r"\s+", "*", val).split("*")
        selectState, selectRegin, selectSpeed, selectDelay = val[1], val[2], int(val[3]), int(val[4])
        current_select = None
        for i in range(0, len(self.data.spdNodes)):
            node = self.data.spdNodes[i]
            if node["region"] == selectRegin and node["speed"] == selectSpeed and node["delay"] == selectDelay:
                current_select = i
                break
        gc = threading.Thread(target=self.configNG, args=(current_select,))
        gc.daemon = True
        gc.start()
        info = selectRegin + ", " + str(selectSpeed) + "K/s, " + str(selectDelay) + "ms"
        self.changeState("config", info)
        log("your choice " + info)

    def update_tools(self):
        for i in range(0, 2):
            rawres = os.popen("curl -x http://localhost:" + str(
                NGHttpPort) + " -skL https://raw.githubusercontent.com/dahong404/tools/master/tools.py")
            res = rawres.buffer.read().decode('utf-8')
            if res.find("version") != -1:
                with open("tools.py", "w", encoding='utf-8') as file:
                    file.write(res)
                log("update success: tools.py")
                return
            else:
                log("update failed: tools.py")

    def nodeListener(self):
        while True:
            nowSeen = len(self.data.spdNodes)
            if self.lastSeen != nowSeen:
                self.var.set(self.prepareBoxMsg(sorted(self.data.spdNodes, reverse=True, key=lambda x: x["speed"])))
                self.lastSeen = nowSeen
            if nowSeen > 0:
                if self.hint["text"] == "测试中...":
                    self.changeBtn(self.btnOK, "enable")
                    self.changeBtn(self.btnRetest, "enable")
                    if nowSeen > nodeLimit:
                        self.changeState("standby")
            time.sleep(1)

    def omitSrc(self, src):
        if len(src) <= 9:
            return src
        return src[:3] + "..." + src[-3:]

    def prepareBoxMsg(self, nodes):
        msg = ""
        for node in nodes:
            nodemsg = "\" " + "{:^6} {:<5} {:<5} {:<5} {:<8} {:<10}".format(node["state"], node["region"],
                                                                            node["speed"],
                                                                            node["delay"],
                                                                            node["clazz"],
                                                                            node["from"].replace("https://",
                                                                                                 "")) + "\"" + " "
            msg += nodemsg
        return msg

    def reTest(self):
        if len(self.data.nodes) == 0:
            self.changeState("end")
            return
        self.data.spdNodes = []
        gc = threading.Thread(target=self.data.generateConfig)
        gc.daemon = True
        gc.start()
        self.changeBtn(self.btnOK, "disable")
        self.changeBtn(self.btnRetest, "disable")
        self.changeState("test")

    def killNG(self):
        file = os.popen("tasklist | findstr \"v2rayN.exe\" ")
        try:
            pid = (str(int(file.read(34).split("v2rayN.exe")[1])))
            os.popen("taskkill -pid " + pid + " -f")
        except Exception:
            pass
        time.sleep(0.5)

    def startNG(self):
        subprocess.Popen("v2rayN.exe", stdout=subprocess.PIPE)
        time.sleep(0.5)

    def clearTestConfig(self):
        list = os.listdir(configDir)
        list2 = os.listdir("guiLogs/")
        for i in list:
            if i.endswith(".json"):
                try:
                    int(i.replace(".json", ""))
                    os.remove(configDir + i)
                except Exception:
                    pass
            if i.endswith("v2ray.log"):
                try:
                    int(i.replace("v2ray.log", ""))
                    os.remove(configDir + i)
                except Exception:
                    pass
        for j in list2:
            os.remove("guiLogs/" + j)

    def detectConn(self, port, forPoolAccess=False):
        failCount = 0
        if not forPoolAccess:
            opp = 2
            timeout = str(5)
            while not self.data.isPortOpen(port):  # 等待v2ray启动
                log("connecting v2rayN ...")
                time.sleep(1)
                failCount += 1
                if failCount > 3:
                    log("connect v2rayN failed on port " + str(port))
                    return False
        else:
            timeout = str(5)
            opp = 1
        for i in range(0, opp):
            google = os.popen(
                "curl -x http://localhost:" + str(port) + " -skLI www.google.com  -m " + timeout).read(150)
            if str(google).find("ISO-8859-1") != -1:
                return True
            if not forPoolAccess:
                twitter = os.popen(
                    "curl -x http://localhost:" + str(port) + " -skI www.twitter.com  -m " + timeout).read(50)
                if str(twitter).find("301 Moved Permanently") != -1:
                    return True
        return False


if __name__ == '__main__':
    log(version)
    Gui()
