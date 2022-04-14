from concurrent.futures import ThreadPoolExecutor
import subprocess
from collections import OrderedDict
import random
import time
import pickle
import threading
import os
from base64 import *
import json
import tkinter
import re

# 两个找节点池的地方
# https://androidrepo.com/repo/Leon406-Sub
# https://i.sqeven.me/q

version = "AutoConfig v2.0"
# 结点设置
minNodes = 400  # 从结点池中获取的结点数小于N就累加到大于N为止
acceptNodes = 400  # ping的结点个数
useRandom = True  # 结点池的访问次序是否随机
minDelay = 0  # 丢弃时延小于N ms的结点，有时候过小时延的结点不好用

useCache = False  # 开启后，节点会保存cacheTime秒供下次使用
cacheTime = 14400

useExclude = False  # 开启后会排除下列地区的结点
exclude = re.compile('HK|TW|US')

# 测速设置
maxTime = 8  # 测速时间：N 秒
minSpeed = 50  # 小于N K/s的不要，=-1表示不进行速度筛选，能访问谷歌就要. 当全部测速都不通过时需要设置成-1，或者更换testResource
testResource = r'"http://drive.google.com/uc?export=download&id=1SasaZhywEOXpVl61a7lqSXppCTSmj3pU"'  # 一个谷歌云盘文件，文件可以换，两端的单双引号不能改

basePort = 20000  # 多线程测速起始端口
maxProcess = 24  # 同时运行的测速线程数[仅模式2会使用多线程测速]
limitNodes = 5  # 测到N个可用结点后自动结束测速

debug = False  # 查看各代理线程工作状态用
daemonProxy = True  # 开启后，每隔daemonTime秒检查代理状态，若断开则尝试自动重新配置
daemonTime = 300

Aurls = [  # 优质结点池
    "https://proxies.bihai.cf/vmess/sub",
    "https://free.kingfu.cf/vmess/sub",
    "https://sspool.herokuapp.com/vmess/sub",
    "https://proxypool.remon602.ga/vmess/sub",
    "https://ednovas.design/vmess/sub",
    "https://proxy.51798.xyz/vmess/sub",
]

urls = [  # 普通结点池
    "https://v2ray.banyunxiaoxi.ml/",
    "https://jiang.netlify.app/",
    "https://youlianboshi.netlify.com/",
    "https://jiedian.faka77.tk/vmess/sub",
    "https://gooii.ml/v2ray/sub",
    # "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt"
    "https://etproxypool.ga/vmess/sub",
    "https://dlj.li/oq112r",
    "https://free.dswang.ga/vmess/sub",
    "http://8.135.91.61/vmess/sub",
    "https://www.linbaoz.com/vmess/sub",
    "https://fq.lonxin.net/vmess/sub",
    "https://hello.stgod.com/vmess/sub",
    "https://proxypool.fly.dev/vmess/sub",
    "https://free.zdl.im/vmess/sub",
    "https://ss.dswang.ga:8443/vmess/sub"

]

if useRandom:
    random.shuffle(urls)

for i in Aurls:
    urls.insert(0, i)

# 失效或暂时失效
# "https://emby.luoml.eu.org/vmess/sub",
# "https://hm2019721.ml/vmess/sub",# "https://raw.fastgit.org/Leon406/Sub/master/sub/share/v2",
# "https://raw.githubusercontent.com/Leon406/Sub/master/sub/share/v2",
# "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray"
# "https://6166888.xyz/vmess/sub"
# "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray"
# "https://v2.tjiasu.xyz/api/v2/client/subscribe?token=07288400e6328b51398f264cffe222de"
# "https://raw.githubusercontent.com/ssrsub/ssr/master/ss-sub",
# "https://bulink.xyz/api/subscribe/?token=fjdqq&sub_type=vmess"
# 'https://www.233660.xyz/vmess/sub'


confdir = "v2ray_win_temp/"
path = confdir + "36ad1899-d3d4-49f1-9dd2-7e2052059f81.json"
v2rayNPath = "v2rayN.exe"
curlPath = "curl/curl.exe"
v2rayPath = "v2ray.exe"


def log(str, showTime=True):
    if showTime:
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " -- " + str + "\n")
    else:
        print(str + "\n")


class Node:
    def __init__(self, delay, config,src=""):
        self.src=src
        self.delay = delay  # int
        self.config = config  # 字典
        self.speed = None
        self.location = None
        self.index = None


avalist = []


def timeTest(i, port):
    pass


def testSpeed(i, port=1080, maxTime=maxTime):
    try:
        driver = os.popen(
            'curl -x http://localhost:' + str(port) + ' -m ' + str(
                maxTime) + ' -skL -o c:/windows/nul ' + testResource + ' --limit-rate 1000k -w "%{speed_download}"')
        res = int(float(driver.read()) / 1024)
        log("★★★INFO★★★: node " + str(i) + " on port " + str(port) + ": " + str(res) + "KB/s")
        if res == 0:
            count = 0
            for i in range(0, 5):
                accessTime = os.popen('curl -x http://localhost:' + str(
                    port) + ' -o /dev/null -skL www.google.com -m 3 -w "%{time_total}"').read()
                daccessTime = float(accessTime[:-4])
                if daccessTime < 1.0:
                    count += 1
            if count >= 2:
                res = 500
    except Exception as e:

        return -1
    return res


def pingNodes(configs):  # 入：字符串数组
    if len(configs) > acceptNodes:
        configs = configs[:acceptNodes]
    log("pinging " + str(len(configs)) + " nodes... ")
    start = time.time()
    random.shuffle(configs)
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
    ave = len(configs) / (time.time() - start)
    log("speed: " + ("%.2f" % ave) + " pics/s")


# def doPing(Nconfigs):  # 入：字典数组
#     global avalist
#     for config in Nconfigs:
#         res = 'res'
#         try:
#             cfg = json.loads(config)  # str->字典
#             if str(cfg["ps"]).find("CN") != -1 and not acceptCN:
#                 log("A CN node, discard")
#                 continue
#             addr = cfg["add"]
#             f = os.popen("ping " + addr + " -w 500 -n 1")
#             res = f.read()
#         except Exception:
#             pass
#         if res.find("平均") != -1:  # 通
#             temp = res.split("=")
#             delay = temp[len(temp) - 1]
#             ddelay = int(delay[:-3])  # str->int
#             avalist.append(Node(ddelay, cfg))


def doTCPing(Nconfigs):
    global avalist
    # log("len: " + str(len(Nconfigs)))
    for config in Nconfigs:
        res = 'res'
        try:
            cfg = json.loads(config)  # 字典
            addr = cfg["add"]
            port = str(cfg["port"])
            f = os.popen("tcping -n 2 -w 1 -p " + port + " " + addr)
            res = f.read()
        except Exception:
            continue
        if res.find("Average") != -1:  # 通
            temp = res.split("=")
            delay = temp[len(temp) - 1]
            ddelay = int(delay[:-7])  # str->float，倒数第三个要
            avalist.append(Node(ddelay, cfg))


def getconfigsFromURL():  # 回：字符串数组
    configs = []
    for url in urls:
        available = False
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'}
        log("retrieving nodes from " + url)
        for i in range(0, 2):  # 两次机会
            try:
                # req = request.Request(url=url, headers=headers)
                # r = request.urlopen(req, timeout=4).read().decode("utf-8")
                r = os.popen(curlPath + " " + url + " -skL -m 10").read()
                if len(r) < 100:
                    raise RuntimeError
                available = True
                break
            except Exception as e:
                log("request timeout, retrying...")
                pass
        if available:
            try:
                vmess = b64decode(r).decode().split("\n")  # vmess链接
            except Exception:
                log("decode error, pass it")
                continue
            for temp in vmess:
                try:
                    b64content = temp[8:]  # 分离地址端口
                    content = b64decode(b64content).decode()  # 明文地址端口
                    configs.append(content)
                except Exception as e:
                    pass
            count = len(configs)
            if count < minNodes:
                log("no more than " + str(minNodes) + " node, actually: " + str(count) + ", do append")
                continue
            break
    log("total nodes: " + str(len(configs)))
    return configs


def detectBaidu(port):
    baidu = os.popen(curlPath + " -x http://localhost:" + str(port) + " -skLI www.baidu.com -m 8").read(40)
    if str(baidu).find("200 OK") != -1:
        return True, baidu
    else:
        return False, baidu


# -L 重定向 -A "header" -I只要头 -s静默模式 -m超时秒数
def detectConn(port=1080):
    failCount = 0
    time.sleep(random.randint(1, 4) + random.randint(0, 5) * 0.1)
    while not detectBaidu(port)[0]:  # 等待v2ray启动
        time.sleep(2)
        failCount += 1
        if failCount > 3:
            log("error: cannot start proxy in port " + str(port))
            return False
    timeout = str(6 + failCount)
    for i in range(0, 2):
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


basecfg = None


def genConfig(e: Node, port=1080):  # 生成配置
    global basecfg
    if basecfg is None:
        lock.acquire()
        if basecfg is None:  # 双重检查避免错误
            with open(path, "r") as file:
                basecfg = json.loads(file.read(), object_pairs_hook=OrderedDict)
        lock.release()

    proxy = basecfg["outbounds"][0]  # 代理服务器配置

    if port == 1080:
        basecfg["inbounds"] = [{
            "protocol": "socks",
            "listen": "0.0.0.0",
            "port": 1079
        }, {
            "protocol": "http",
            "listen": "0.0.0.0",
            "port": 1080
        }]
    else:
        basecfg["inbounds"] = [
            {
                "protocol": "http",
                "listen": "0.0.0.0",
                "port": port
            }
        ]
    try:
        host = e.config["host"]
    except KeyError:
        log("port " + str(port) + ": key error in genconfig")
        return basecfg

    # basecfg["current"]["delay"] = str(e.delay)  # debug用附加信息
    # basecfg["current"]["config"] = e.config
    # basecfg["current"]["speed"] = e.speed
    # basecfg["current"]["location"] = e.location
    # basecfg["current"]["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

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


def getCountry(port=1080):
    try:
        info = json.loads(
            os.popen(curlPath + " -x http://localhost:" + str(port) + "  https://api.myip.la/en?json -skL -m 8").read())
        if port == 1080:
            return str(info["location"]["country_name"] + "(" + info["location"]["country_code"] + ")")
        else:
            return str(info["location"]["country_code"])
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
            log("main: sleep, running process max to " + str(maxProcess))
            time.sleep(3)
            if unavailableCount > 24:
                log("too many unavailable nodes detected, try another mode please")
                exit(-1)
        else:
            if len(speedList) >= limitNodes:
                log(">>>>INFO>>>>: available nodes max to " + str(limitNodes) + ", stop adding test process")
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
    label["text"] = "请选择"
    while running > 0:
        log(">>>>INFO>>>>: waiting running process done, now: " + str(running))
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
        log("no nodes available, consider reduce minSpeed or set minSpeed=-1")

    try:
        while True:
            while not keepon:
                time.sleep(1)
            else:
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
                    log(">>>>INFO>>>>: waiting running process done, now: " + str(running))
                    time.sleep(5)
                log("finish ")
                keeponBtn["state"] = tkinter.ACTIVE
                label["text"] = "请选择"
                i += 32
                keepon = False
    except Exception as e:
        print(e)
        pass


zeroSpeedList = []
lock = threading.Lock()

unavailableCount = 0


def singleSpeedTest(port, process, e: Node, index):
    global speedList, running, box, zeroSpeedList, attention, unavailableCount
    if not detectConn(port):
        log("★★★INFO★★★: node " + str(index) + " on port " + str(port) + ": Unavailable")
        unavailableCount += 1
    else:
        unavailableCount = 0
        speed = testSpeed(index, port)
        e.speed = speed
        e.location = getCountry(port)
        e.index = index
        if useExclude and exclude.search(e.location) is not None:
            zeroSpeedList.append(e)
            log("port " + str(port) + " : discard node " + str(index) + ": in the exclusion list (" + e.location + ")")
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
    with open(confdir + "save.bin", "rb") as file:
        content = pickle.load(file)
        log("cache node: " + str(len(content)))
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
    try:
        pretime = content["current"]["time"]
    except:
        return 99999
    pre = int(time.mktime(time.strptime(pretime, "%Y-%m-%d %H:%M:%S")))
    now = time.time()
    return now - int(pre)


def clearTestConfig():
    list = os.listdir(confdir)
    for i in list:
        if i.endswith("json"):
            try:
                int(i[:-5])
                os.remove(confdir + i)
            except Exception:
                pass


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

    keeponBtn = tkinter.Button(root, width=12, text="继续",
                               command=lambda: continueTest())
    chooseBtn = tkinter.Button(root, width=10, text="确定",
                               command=lambda: chooseNode())

    middle.add(keeponBtn)
    middle.add(chooseBtn)
    chooseBtn["state"] = tkinter.ACTIVE
    keeponBtn["state"] = tkinter.ACTIVE

    state = tkinter.Label(root, bg="red")
    label = tkinter.Label(root, text="测试中...")
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
    global state, label, box, speedList
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
                if i >= 5:
                    log("5 attempts to reconnect failed, give up")
                    break
                log("try: " + str(i))
                e = Alist[i]
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
        time.sleep(daemonTime)
    log("proxy daemon thread exit")


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
            log("there may something wrong with gui mode, try set minSpeed = -1 please")
            break
    gui()


rawNodes = []


def retrieveFromUrl(url):
    # log("parameter: " + str(url))
    global rawNodes
    available = False
    for i in range(0, 2):  # 两次机会
        try:
            r = os.popen(curlPath + " " + url[0] + " -skL -m 10").read()
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
            log(url[0] + ": decode error")
            return
        lock.acquire()
        for temp in vmess:
            try:
                b64content = temp[8:]  # 分离地址端口
                content = b64decode(b64content).decode()  # 明文地址端口
                rawNodes.append(content)
            except Exception as e:
                pass
        log(url[0] + ": " + str(len(vmess)) + ", total: " + str(len(rawNodes)))
        # log("after " + url[0] + ": " + str(len(rawNodes)))
        lock.release()
    else:
        log(url[0] + ": unavailable")


def retrieveNodes():
    log("retrieving nodes ... ")
    global urls, rawNodes
    executes = ThreadPoolExecutor(max_workers=4)
    running = []
    for i in urls:
        r = executes.submit(retrieveFromUrl, (i,))
        running.append(r)
    out = 0
    while len(rawNodes) < minNodes:
        out += 1
        time.sleep(1)
        if out > 30:
            break
    for i in running:
        i.cancel()
    if len(rawNodes) < 10:
        log("error: cannot retrieve nodes, update pool please")
        exit(-1)
    log("total nodes: " + str(len(rawNodes)))

    return rawNodes


def stateChecker(info):
    global state, label
    if not detectConn():
        label['text'] = "FAILED : " + info
    else:
        label['text'] = "OK : " + info
        state['bg'] = "green"


if __name__ == '__main__':
    print(version)
    # gui()
    mode = input("select mode: 1---Manual, 2---Automatic. default: 2\n")
    if mode == "2":
        if len(mode.split(" ")) == 2:
            minDelay = int(mode.split(" ")[1])
            log("set min delay = " + mode.split(" ")[1])
    mode = mode.split(" ")[0]
    killV2ray()
    if getTimeGap() < cacheTime and useCache:
        log("using cache")
        nodes = readNodes()
    else:
        log("passing cache")
        # pingNodes(getconfigsFromURL())
        pingNodes(retrieveNodes())
        log("Pingable nodes: " + str(len(avalist)))
        nodes = customizeNode(avalist)
        saveNode(nodes)
        log("these nodes can access from cache in " + str(cacheTime) + "s")
    if mode != "1":
        log("Automatic mode")
        guiMode(nodes)
    else:
        log("Manual mode")
        cmdMode(nodes)
    clearTestConfig()
