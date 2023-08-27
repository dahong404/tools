from concurrent.futures import ThreadPoolExecutor
import warnings

# new file
warnings.filterwarnings("ignore")
import subprocess
from collections import OrderedDict
import random
import time
import pickle
import threading
import os
from base64 import b64decode
import json
import tkinter
import re

hiddenURL = "https://f.kxyz.eu.org/f.php?r=aHR0cHM6Ly9iLmx1eHVyeS9saW5rL25EcWdlQlh4NUl5SjJ2RnQ/c3ViPTM="
version = "AutoConfig v2.2"
# 结点设置
minNodes = 200  # 从结点池中获取的结点数小于N就累加到大于N为止
acceptNodes = 400  # ping的结点个数
useRandom = True  # 结点池的访问次序是否随机
minDelay = 0  # 丢弃时延小于N ms的结点，避免遇到国内中转
passPing = False  # 跳过ping，以加快速度
useCache = False  # 开启后，节点会保存cacheTime秒供下次使用
cacheTime = 3600
useExclude = False  # 开启后会排除下列地区的结点
exclude = re.compile('HK|TW|US')
autoLoginFlag = True  # 校园网自动登录
updateFlag = True  # 自动更新

# 测速设置
maxTime = 12  # 测速时间：N 秒
minSpeed = 50  # 小于N K/s的不要，=-1表示不进行速度筛选，能访问谷歌就要. 当全部测速都不通过时需要设置成-1，或者更换testResource
testResource = r'"http://drive.google.com/uc?export=download&id=1SasaZhywEOXpVl61a7lqSXppCTSmj3pU"'  # 一个谷歌云盘文件，文件可以换

basePort = 20000  # 多线程测速起始端口
maxProcess = 20  # 同时运行的测速线程数
limitNodes = 10  # 测到N个可用结点后结束测速

debug = False  # 检查各代理线程工作状态用
daemonProxy = True  # 开启后，每隔daemonTime秒检查代理状态，若断开则尝试自动重新配置
daemonTime = 600

useRemote = False  # 从远程获取结点，加快获取结点的速度
remoteSocket = ("192.168.123.1", 22)

pxport = 23334  # 代理端口，需要等于v2rayN的socks端口+1，等于v2rayN的http端口

try:
    import paramiko
except:
    useRemote = False

# 结点池获取 https://github.com/WilliamStar007/ClashX-V2Ray-TopFreeProxy/blob/main/v2ray.md
Avmess = [  # 普通结点池，可直接访问，仅接受b64
    "https://gitlab.com/mfuu/v2ray/-/raw/master/v2ray",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.fastgit.org/ZywChannel/free/main/sub",
    "https://v2ray.neocities.org/v2ray.txt",
    # "https://nodefree.org/dy/2023/08/20230825.txt",
    # "https://clashnode.com/wp-content/uploads/2023/08/20230825.txt",
    "https://raw.fastgit.org/Pawdroid/Free-servers/main/sub",
    "https://freefq.neocities.org/free.txt",
    "https://youlianboshi.netlify.com",
    "https://free.jingfu.cf/vmess/sub",
    "https://tt.vg/freev2",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/free",
    # "https://raw.githubusercontent.com/pojiezhiyuanjun/2023/master/0826.txt",
    "https://raw.fastgit.org/freefq/free/master/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
]

vmess = [  # 屏蔽结点池，需要代理才可访问，仅接受b64
    "https://raw.githubusercontent.com/openrunner/clash-freenode/main/v2ray.txt",
    "https://jiang.netlify.app/",
    "https://sub.pmsub.me/base64",
    "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
    "https://raw.githubusercontent.com/xieshunxi1/subscribe_clash_v2ray/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/vveg26/get_proxy/main/dist/v2ray.config.txt"
]

for i in Avmess:
    vmess.insert(0, i)

if useRandom:
    random.shuffle(vmess)

confdir = "v2ray_win_temp/"  # 服务器配置文件目录
path = confdir + "36ad1899-d3d4-49f1-9dd2-7e2052059f81.json"  # 自定义服务器配置文件
v2rayNPath = "v2rayN.exe"  # v2rayN图形界面
curlPath = "curl.exe"  # 网络请求工具
v2rayPath = "v2ray.exe"  # v2ray内核


def log(str, showTime=True):
    if showTime:
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " -- " + str + "\n")
    else:
        print(str + "\n")


class Node:
    def __init__(self, delay, config):
        self.delay = delay  # int
        self.config = config  # 字典
        self.speed = None
        self.location = None
        self.index = None


avalist = []


def testSpeed(i, port=pxport, maxTime=maxTime):
    try:
        driver = os.popen(
            'curl -x http://localhost:' + str(port) + ' -m ' + str(
                maxTime) + ' -skL -o c:/windows/nul ' + testResource + ' --limit-rate 1000k -w "%{speed_download}"')
        res = int(float(driver.read()) / 1024)
        log("[" + str(i) + "/" + str(len(avalist)) + "]" + " : " + str(res) + "KB/s")
        if res == 0:
            count = 0
            for i in range(0, 4):
                accessTime = os.popen('curl -x http://localhost:' + str(
                    port) + ' -o /dev/null -skL www.google.com -m 3 -w "%{time_total}"').read()
                time.sleep(0.1)
                daccessTime = float(accessTime[:-4])
                if daccessTime < 2.0:
                    count += 1
            if count >= 2:
                res = 100
    except Exception as e:
        return -1
    return res


def pingNodes(configs):  # 入：字符串数组
    if len(configs) > acceptNodes:
        random.shuffle(configs)
        configs = configs[:acceptNodes]

    log("pinging " + str(len(configs)) + " nodes... ")
    start = time.time()

    left = 0
    gap = len(configs) // 32 + 1  # 把所有结点均分成32组
    threads = []
    for i in range(0, 32):  # 开32个线程，每线程ping一组
        try:
            t = threading.Thread(target=doTCPing, args=(configs[left:left + gap],))
            left += gap
            threads.append(t)
        except Exception as e:
            break
    for i in threads:
        i.setDaemon(True)
        i.start()
        # time.sleep(0.1)
    for i in threads:
        try:
            i.join()  # 等待全部ping结束
        except Exception:
            pass
    g = time.time() - start
    if g == 0:
        ave = 999
    else:
        ave = len(configs) / g
    log("speed: " + ("%.2f" % ave) + " pics/s")


info = ""


def doTCPing(Nconfigs):
    global avalist, info
    if not passPing:
        for config in Nconfigs:
            res = 'res'
            try:
                cfg = json.loads(config)  # 字典
                addr = cfg["add"]
                port = str(cfg["port"])
                f = os.popen("tcping -n 1 -w 1 -p " + port + " " + addr)
                res = f.read()
            except Exception:
                continue
            if res.find("Average") != -1:  # 通
                temp = res.split("=")
                delay = temp[len(temp) - 1]
                ddelay = int(delay[:-7])  # str->float，倒数第三个要
                avalist.append(Node(ddelay, cfg))
    else:
        for config in Nconfigs:
            try:
                cfg = json.loads(config)  # 字典
            except Exception as e:
                continue
            avalist.append(Node(100, cfg))


def autoLogin():
    res = os.popen("login.sh").read()
    log(res)


def detectV2(port):
    baidu = os.popen("tcping -n 2 -w 1 -p " + str(port) + " localhost").read()
    if baidu.find("Average") != -1:
        return True
    else:
        return False


# -L 重定向 -A "header" -I只要头 -s静默模式 -m超时秒数
def detectConn(port=pxport, check=False):
    failCount = 0
    opp = 2
    if not check:
        time.sleep(random.randint(1, 4) + random.randint(0, 5) * 0.1)
        while not detectV2(port):  # 等待v2ray启动
            time.sleep(2)
            failCount += 1
            if failCount > 3:
                # log("error: cannot start proxy in port " + str(port))
                return False
        timeout = str(6 + failCount)
    else:
        timeout = str(5)
        opp = 1
    for i in range(0, opp):
        google = os.popen(
            curlPath + " -x http://localhost:" + str(port) + " -skLI www.google.com  -m " + timeout).read(150)
        if str(google).find("ISO-8859-1") != -1:
            return True
        twitter = os.popen(
            curlPath + " -x http://localhost:" + str(port) + " -skI www.twitter.com  -m " + timeout).read(50)
        if str(twitter).find("301 Moved Permanently") != -1:
            return True
    # if debug:
    #     lock.acquire()
    #     info = "port " + str(port) + ": \n google: " + google + "twitter: " + twitter
    #     log(info)
    #     lock.release()

    # facebook=os.popen("curl -x http://localhost:"+str(port)+" -I http://www.facebook.com -s ")
    # log("-->>" + google + "<<-- -->>" + twitter + "<<--")
    # if twitter.find("200") != -1:
    #     return True
    return False


def killV2ray():
    file = os.popen("tasklist | findstr \"v2rayN.exe\" ")
    try:
        pid = (str(int(file.read(34).split("v2rayN.exe")[1])))
        os.popen("taskkill -pid " + pid + " -f")
    except IndexError:
        pass


def restartV2ray():
    file = os.popen("tasklist | findstr \"v2rayN.exe\" ")
    try:
        pid = (str(int(file.read(34).split("v2rayN.exe")[1])))
        os.popen("taskkill -pid " + pid + " -f")
        time.sleep(1)
        os.popen(v2rayNPath)
    except IndexError:
        os.popen(v2rayNPath)
    # time.sleep(3)


def writeConfig(newcfg: dict, rpath=path):
    with open(rpath, "w") as file:
        file.write(json.dumps(newcfg))


def genConfig(e: Node, port=pxport):  # 生成配置
    try:
        with open(path, "r") as file:
            basecfg = json.loads(file.read(), object_pairs_hook=OrderedDict)
        proxy = basecfg["outbounds"][0]  # 代理服务器配置
        if port == pxport:
            basecfg["inbounds"] = [{
                "protocol": "socks",
                "listen": "0.0.0.0",
                "port": pxport - 1
            }, {
                "protocol": "http",
                "listen": "0.0.0.0",
                "port": pxport
            }]
        else:
            basecfg["inbounds"] = [
                {
                    "protocol": "http",
                    "listen": "0.0.0.0",
                    "port": port
                }
            ]
        basecfg["current"]["delay"] = str(e.delay)  # debug用附加信息
        basecfg["current"]["config"] = e.config
        basecfg["current"]["speed"] = e.speed
        basecfg["current"]["location"] = e.location
        basecfg["current"]["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        proxySetting = {
            "vnext": [
                {
                    "address": e.config["add"],
                    "port": int(e.config["port"]),
                    "users": [
                        {
                            "id": e.config["id"],
                            "alterId": int(e.config["aid"]),
                            "email": "t@t.tt",
                            "security": "auto"
                        }
                    ]
                }
            ],
            "servers": None,
            "response": None
        }
        streamSettings = {
            "network": e.config["net"],
            "security": e.config["tls"],
            "tlsSettings": {
                "allowInsecure": True,
                "serverName": e.config["host"]
            },
            "tcpSettings": None,
            "kcpSettings": None,
            "wsSettings": None,
            "httpSettings": None,
            "quicSettings": None
        }
        protocolSetting = {
            "connectionReuse": True,
            "path": e.config["path"],
            "headers": {
                "Host": e.config["host"]
            }
        }

        if e.config["tls"] == "":  # 安全配置
            streamSettings["security"] = None
        else:
            streamSettings["security"] = "tls"
            streamSettings["tlsSettings"] = {
                "allowInsecure": True,
                "serverName": e.config["host"]
            }
        if e.config["net"] == "tcp":  # 协议配置
            streamSettings["tcpSettings"] = protocolSetting
            streamSettings["wsSettings"] = None
        elif e.config["net"] == "ws":
            streamSettings["wsSettings"] = protocolSetting
            streamSettings["tcpSettings"] = None
        proxy["settings"] = proxySetting
        proxy["streamSettings"] = streamSettings
        basecfg["outbounds"][0] = proxy
    except Exception as e:
        return basecfg
    return basecfg


def customizeNode(avalist):  # 筛选且排序
    Discardlist = []
    Alist = []
    for e in avalist:
        if e.delay < minDelay:
            Discardlist.append(e)
        else:
            Alist.append(e)
    for i in range(0, len(Alist)):
        for j in range(0, len(Alist) - i - 1):
            if Alist[j].delay > Alist[j + 1].delay:
                Alist[j], Alist[j + 1] = Alist[j + 1], Alist[j]
    log("customize complete, discard: " + str(len(Discardlist)) + ", accept: " + str(len(Alist)))
    return Alist


def getCountry(port=pxport):
    try:
        info = json.loads(
            os.popen(curlPath + " -x http://localhost:" + str(
                port) + "  http://ip-api.com/json/?fields=61439 -skL -m 8").read())
        if port == pxport:
            return str(info["countryCode"])
        else:
            return str(info["countryCode"])
    except:
        return "Unknown"


running = 0
speedList = []

keepon = False


def mulitTest(nodes):
    global running, basePort, chooseBtn, keeponBtn, label, speedList, unavailableCount, keepon
    i = 0
    for e in nodes:
        while running >= maxProcess:
            log("running process: " + str(maxProcess) + ", obtain [" + str(len(speedList)) + "/" + str(
                limitNodes) + "] available")
            time.sleep(3)
            if unavailableCount > maxProcess:
                log("warning: too many unavailable nodes, check settings")
                # exit(-1)
        else:
            if len(speedList) >= limitNodes:
                log("stop testing, [" + str(len(speedList)) + "/" + str(limitNodes) + "] available obtained")
                break
            running += 1
            # log("add a process, now: " + str(running))
            writeConfig(genConfig(e, basePort), rpath=confdir + str(basePort) + ".json")
            i += 1
            time.sleep(random.randint(0, 5) * 0.1)
            # log("testing node: " + str(i) + "/" + str(len(nodes)) + " on port " + str(basePort))
            startTest(basePort, e, i)
            basePort += 1
    while chooseBtn is None:
        time.sleep(0.5)
    chooseBtn["state"] = tkinter.ACTIVE
    keeponBtn["state"] = tkinter.ACTIVE
    if label["text"] == "测试中":
        label["text"] = "请选择"
    while running > 0:
        log("wait running process done, now: " + str(running))
        time.sleep(5)
    log("done, " + str(i) + " tested: " + str(len(speedList)) + " available, " + str(
        i - len(speedList)) + " unavailable")
    traffic = 0
    for e in speedList:
        traffic += e.speed * 0.8 * maxTime / 1024
    for e in zeroSpeedList:
        traffic += e.speed * 0.8 * maxTime / 1024

    log("consume traffic: " + ("%.2f" % traffic) + "MB")
    saveNode(speedList + zeroSpeedList + avalist)

    clearTestConfig()
    if len(speedList) == 0:
        log("error: no nodes available, check settings")
    try:
        while True:
            while not keepon:
                time.sleep(1)
            else:
                log("continue testing ...")
                for j in range(i + 1, len(nodes)):
                    e = nodes[j]
                    if running >= maxProcess:
                        break
                    else:
                        running += 1
                        basePort += 1
                        writeConfig(genConfig(e, basePort), rpath=confdir + str(basePort) + ".json")
                        time.sleep(random.randint(0, 5) * 0.1)
                        # log("testing node: " + str(i) + "/" + str(len(nodes)) + " on port " + str(basePort))
                        startTest(basePort, e, j)
                while running > 0:
                    log("wait running process done, now: " + str(running))
                    time.sleep(5)
                log("done, " + str(j - 1) + " tested: " + str(len(speedList)) + " available, " + str(
                    j - 1 - len(speedList)) + " unavailable")
                keeponBtn["state"] = tkinter.ACTIVE
                if label["text"] == "测试中":
                    label["text"] = "请选择"
                i += maxProcess
                keepon = False
    except Exception as e:
        log("All nodes tested, nothing to do, bye")
        pass


zeroSpeedList = []
lock = threading.Lock()

unavailableCount = 0


def singleSpeedTest(port, process, e: Node, index):
    global speedList, running, box, zeroSpeedList, attention, unavailableCount
    if not detectConn(port):
        log("[" + str(index) + "/" + str(len(avalist)) + "] : ×")
        unavailableCount += 1
    else:
        if passPing:
            res = os.popen("tcping -n 1 -w 1 -p " + str(e.config["port"]) + " " + str(e.config["add"])).read()
            if res.find("Average") != -1:  # 通
                temp = res.split("=")
                delay = temp[len(temp) - 1]
                ddelay = int(delay[:-7])  # str->float，倒数第三个要
                e.delay = ddelay
            else:
                e.delay = 100
        unavailableCount = 0
        speed = testSpeed(index, port)
        e.speed = speed
        e.location = getCountry(port)
        e.index = index
        if useExclude and exclude.search(e.location) is not None:
            zeroSpeedList.append(e)
            log(" discard node " + str(index) + ": in the exclusion list (" + e.location + ")")
        else:
            if speed >= minSpeed:
                unavailableCount = 0
                info = e.location + ": " + str(speed) + "K/s: " + str(e.delay) + "ms"
                lock.acquire()
                speedList.append(e)
                while box is None:
                    time.sleep(1)
                box.insert('end', info)
                lock.release()
            else:
                unavailableCount += 1
                zeroSpeedList.append(e)
                # log("port " + str(port) + " : discard node " + str(index) + ": too slow (" + str(e.speed) + "KB/s)")
    if not debug:
        process.kill()
    running -= 1
    # log("terminate a process, now: " + str(running))


def startTest(port, e, index):
    process = subprocess.Popen(v2rayPath + " -config " + confdir + str(port) + ".json", stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    # time.sleep(2)
    b = threading.Thread(target=singleSpeedTest, args=(port, process, e, index))
    b.setDaemon(True)
    b.start()


def saveNode(nodes):
    if len(nodes) > 50:
        with open(confdir + "save.bin", "wb") as file:
            pickle.dump(nodes, file)
    else:
        pass


def readNodes():
    log("retrieving nodes from cache ... ")
    with open(confdir + "save.bin", "rb") as file:
        content = pickle.load(file)
        log("cached nodes: " + str(len(content)))
    return content


def continueTest():
    global keepon, keeponBtn, label, chooseBtn, state
    keepon = True
    chooseBtn["state"] = tkinter.ACTIVE
    keeponBtn["state"] = tkinter.DISABLED
    label["text"] = "测试中"


def doConfig(e: Node):
    writeConfig(genConfig(e))
    restartV2ray()


def chooseNode():
    global label, box, state, threads
    if len(box.curselection()) == 0:
        label['text'] = "请选择"
        return
    index = box.curselection()[0]
    e = speedList[index]
    info = e.location + ", " + str(e.speed) + "K/s, " + str(e.delay) + "ms"
    log("your choice: " + info)
    t = threading.Thread(target=doConfig, args=(e,))
    t.setDaemon(True)
    t.start()
    label['text'] = "配置中: " + info
    state['bg'] = "red"
    checker = threading.Thread(target=stateChecker, args=(info,))
    checker.setDaemon(True)
    checker.start()


def getTimeGap():
    with open(path, "r") as file:
        content = json.loads(file.read())
    pretime = content["current"]["time"]
    pre = int(time.mktime(time.strptime(pretime, "%Y-%m-%d %H:%M:%S")))
    now = time.time()
    return now - int(pre)


def clearTestConfig():
    list = os.listdir(confdir)
    list2 = os.listdir("guiLogs/")
    for i in list:
        if i.endswith("json"):
            try:
                int(i[:-5])
                os.remove(confdir + i)
            except Exception:
                pass
    for j in list2:
        os.remove("guiLogs/" + j)


clearTestConfig()

label = None
box = None
keeponBtn = None
chooseBtn = None
state = None


def gui():
    global label, box, chooseBtn, keeponBtn, speedList, state
    root = tkinter.Tk()
    root.title(version)
    root.geometry("300x400")
    top = tkinter.PanedWindow(width=230, height=250)
    middle = tkinter.PanedWindow(width=200, height=50)
    bottom = tkinter.PanedWindow(width=200, height=50)

    box = tkinter.Listbox(font=("Helvetica", 12))
    top.add(box)

    keeponBtn = tkinter.Button(root, width=10, text="继续",
                               command=lambda: continueTest())
    chooseBtn = tkinter.Button(root, width=10, text="确定",
                               command=lambda: chooseNode())

    middle.add(keeponBtn)
    middle.add(chooseBtn)
    chooseBtn["state"] = tkinter.ACTIVE
    keeponBtn["state"] = tkinter.ACTIVE

    state = tkinter.Label(root, bg="red")
    label = tkinter.Label(root, text="测试中")
    bottom.add(state)
    bottom.add(label)

    top.pack()
    middle.pack()
    bottom.pack()

    if daemonProxy:
        t = threading.Thread(target=proxyDaemon)
        t.setDaemon(True)
        t.start()
    root.mainloop()


def proxyDaemon():  # 检查连接状态，若中断则自动重新配置
    global state, label, box, speedList, updateFlag
    while str(label['text']).find("OK") == -1:
        time.sleep(5)
    log("proxy daemon thread activate")
    Alist = speedList[:]
    for i in range(0, len(Alist)):
        for j in range(0, len(Alist) - i - 1):
            if Alist[j].speed < Alist[j + 1].speed:
                Alist[j], Alist[j + 1] = Alist[j + 1], Alist[j]
    starter = 0
    fixed = True
    while True:
        if not detectConn():
            log("connection: failed")
            label['text'] = "fixing..."
            state['bg'] = "yellow"
            log("fixing ...")

            current = box.curselection()[0]
            fixed = False
            for i in range(starter, len(Alist)):
                if autoLoginFlag:
                    log("try auto login")
                    autoLogin()
                # if i >= 5:
                #     log("5 attempts to reconnect failed, give up")
                #     break
                e = Alist[i]
                add = e.config["add"]
                pt = e.config["port"]
                log("try: " + str(i) + ": " + str(add) + " " + str(pt))
                if current == e:
                    continue
                else:
                    doConfig(e)
                    time.sleep(2)
                    if not detectConn():
                        log("Failed")
                        continue
                    else:
                        info = e.location + ", " + str(e.speed) + "K/s, " + str(e.delay) + "ms"
                        log("success: " + info)
                        label['text'] = "FIXED: " + info
                        state['bg'] = "green"
                        fixed = True
                        starter = i + 1
                        break
        if not fixed:
            log("failed")
            label['text'] = "FAILED"
            state['bg'] = "red"
            log("connection: failed")
            break
        else:
            log("connection: ok")
            if updateFlag:
                updateFlag = False
                update_tools()
        time.sleep(daemonTime)
    log("proxy daemon thread exit")


def update_tools():
    for i in range(0, 2):
        rawres = os.popen("curl -x http://localhost:" + str(
            pxport) + " -skL https://raw.githubusercontent.com/dahong404/tools/master/tools.py")
        res = rawres.buffer.read().decode('utf-8')
        if res.find("version") != -1:
            with open("tools.py", "w", encoding='utf-8') as file:
                file.write(res)
            log("self update success: tools.py")
            return
        else:
            log("self update failed: tools.py")


def cmdMode(nodes: list):
    i = 0
    for e in nodes:
        i += 1
        log("trying ... [" + str(i) + "/" + str(len(nodes)) + "]")
        doConfig(e)
        time.sleep(2)
        log("Configuration completed, testing speed ...")
        testSpeed(i, maxTime=12)
        log("current country: " + getCountry() + ", delay:" + str(e.delay) + "ms")
        if input("Are you satisfied with this result ? [y/n] \n") == "n":
            continue
        break
    if i == len(nodes):
        log("no nodes available, consider set useCache=False or reduce minSpeed or set minSpeed=-1")
    log("thanks for using this script, bye ")


def guiMode(nodes):
    t = threading.Thread(target=mulitTest, args=(nodes,))
    t.setDaemon(True)
    t.start()
    failCount = 0
    while len(speedList) == 0:
        time.sleep(0.5)
        failCount += 1
        if failCount > 480:
            log("error: speed testing failed, check settings")
            break
    gui()


rawNodes = []


def retrieveFromRemote():
    global rawNodes
    log("retrieving nodes from remote ... ")
    try:
        sf = paramiko.Transport(remoteSocket)
        sf.connect(username="admin", password="admin")
        sftp = paramiko.SFTPClient.from_transport(sf)
        sftp.get("list.txt", os.path.join("list.txt"))  # 下载目录中文件
    except Exception as e:
        log("error: remote failed, check settings")
        exit()
        # print(e)
    finally:
        sf.close()
    with open("list.txt", "r", encoding="utf-8") as file:
        st = file.read()
    log("latest: " + str(st.split("Hello")[-1]))
    raw = st.split("Hello")[:-1]
    log("partition: " + str(len(raw)))
    for r in raw:
        try:
            vmess = b64decode(r).decode().split("\n")  # vmess链接
        except Exception:
            log(": decode error")
            continue
        for temp in vmess:
            try:
                b64content = temp[8:]  # 分离地址端口
                content = b64decode(b64content).decode()  # 明文地址端口
                rawNodes.append(content)
            except Exception as e:
                pass
    log("total nodes: " + str(len(rawNodes)))
    return rawNodes


def retrieveFromUrl(param):
    global rawNodes
    available = False
    for i in range(0, 2):  # 两次机会
        try:
            if param[1]:  # 代理就绪，使用代理获取结点
                r = os.popen(curlPath + " -x http://localhost:" + str(pxport) + " " + param[0] + " -skL -m 10").read()
            else:  # 代理不就绪，直接获取结点
                r = os.popen(curlPath + " " + param[0] + " -skL -m 10").read()
            if len(r) < 100:
                raise RuntimeError
            available = True
            break
        except Exception as e:
            pass
    if available:
        try:
            vmess = b64decode(r).decode().split("\n")  # vmess链接
        except Exception:
            log(param[0] + ": decode error")
            return
        lock.acquire()
        for temp in vmess:
            try:
                b64content = temp[8:]  # 分离地址端口
                content = b64decode(b64content).decode()  # 明文地址端口
                rawNodes.append(content)
            except Exception as e:
                pass
        log(param[0] + ": " + str(len(vmess)) + ", total: " + str(len(rawNodes)))
        # log("after " + url[0] + ": " + str(len(rawNodes)))
        lock.release()
    else:
        log(param[0] + ": unavailable")


def retrieveNodes():
    log("retrieving nodes from pools ... ")
    conn = detectConn(check=True)
    if conn:
        log("proxy ready, use proxy")
    else:
        log("proxy not ready, use direct")
    global vmess, rawNodes
    executes = ThreadPoolExecutor(max_workers=4)
    running = []
    for i in vmess:
        r = executes.submit(retrieveFromUrl, (i, conn))
        running.append(r)
    out = 0
    count = 0
    while len(rawNodes) < minNodes:
        out += 1
        time.sleep(1)
        doneFlag = True
        for i in running:
            currDone = i.done()
            if currDone:
                count += 1
            doneFlag = (doneFlag and currDone)
        log("waiting ... [" + str(count) + "/" + str(len(running)) + "]")
        count = 0
        if doneFlag or out > 30:
            break
    for i in running:
        i.cancel()
    if len(rawNodes) < 10:
        log("error: cannot retrieve nodes, need update pools")
        exit(-1)
    log("total nodes: " + str(len(rawNodes)))
    # exit(-1)
    return rawNodes


def stateChecker(info):
    global state, label
    if not detectConn():
        label['text'] = "FAILED : " + info
    else:
        label['text'] = "OK : " + info
        state['bg'] = "green"


if __name__ == '__main__':
    print(version + "\n")
    # mode = input("select mode: 1---Manual, 2---Auto, 3---Fast Auto. recommend: 2/3\n")
    mode = "3"
    if mode == "3":
        passPing = True
        maxProcess = int(maxProcess * 1.5)
    # killV2ray()
    if getTimeGap() < cacheTime and useCache:
        log("cache enable")
        nodes = readNodes()
    else:
        log("cache disable")
        # pingNodes(getconfigsFromURL())
        if useRemote:
            pingNodes(retrieveFromRemote())
        else:
            pingNodes(retrieveNodes())

        log("Pingable nodes: " + str(len(avalist)))
        nodes = customizeNode(avalist)
        saveNode(nodes)
        log("these nodes can access from cache in " + str(cacheTime) + "s")
    if mode == "3":
        log("Activate mode: Fast Auto")
        guiMode(nodes)
    elif mode == "1":
        log("Activate mode: Manual")
        cmdMode(nodes)
    else:
        log("Activate mode: Auto")
        guiMode(nodes)
    clearTestConfig()
