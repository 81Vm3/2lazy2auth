import sys
import requests
import socket
import json
import time
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlencode


class profile:
    account = "0",
    password = "changeme"
    heartbeat = 1000

    def read(self, path):
        with open(path, "r") as f:
            j = json.load(f)
            self.account = j["account"]
            self.password = j["password"]
            self.heartbeat = int(j["heartbeat"])


profile_path = "profile.json"
auth_web_lnk = "http://2.2.2.2"
m_profile = profile()
run_first_time = True
auth_fail = True

proxies = {
    "http": "",
    "https": "",
}

header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connectin": "keep-alive",
    "Host": "2.2.2.2",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53",
}


def printError(error):
    print("ERROR: " + error)


# 认证
def auth(response, profile):
    global auth_fail
    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find('script')

    if script:
        script_content = script.text
        # 获取js中的重定向URL
        start = script_content.find('location.replace("') + len('location.replace("')
        end = script_content[start:].find('&url')
        new_url = script_content[start:end]

        parsed_url = urlparse(new_url)
        wlanuserip = parse_qs(parsed_url.query)['wlanuserip'][0]
        wlanacname = parse_qs(parsed_url.query)['wlanacname'][0]
        mac = parse_qs(parsed_url.query)['mac'][0]
        hostname = parse_qs(parsed_url.query)['hostname'][0]
        vlan = parse_qs(parsed_url.query)['vlan'][0]
        server = parsed_url.hostname

        # print(new_url)
        print(f"服务器:{server}\nIP={wlanuserip}\nMAC地址={mac}\n主机名={hostname}")
        print("-----正在登录中-----")

        postdata = {
            'userid': profile.account,
            'passwd': profile.password,
            'wlanuserip': wlanuserip,
            'wlanuseripv6': "",
            'wlanacname': wlanacname,
            'wlanacIp': server,
            'ssid': "",
            'vlan': vlan,
            'mac': mac,
            "version": "",
            'portalpageid': "",
            "validateCode": "#validateCode",
            "timestamp": "",
            "uuid": "",
            "portaltype": "#portaltype",
            "hostname": hostname,
        }
        constructed = f"http://{server}/quickauth.do?{urlencode(postdata)}"
        header["Host"] = server
        response = requests.post(constructed, headers=header, proxies=proxies)

        j = json.loads(response.text)
        code = int(j["code"])
        message = j["message"]
        if code == 0:
            print(f"---> 校园网验证成功啦 ({datetime.datetime.now()})")
            auth_fail = False
        elif code == 235:
            printError("账号密码错误")
        elif code == 7:
            printError("账号或密码错误，(错5次将会锁定账号30分钟)")
        elif message:
            printError("登录失败 " + message)
        else:
            printError("登录失败，原因未知")
    else:
        printError("没有找到JavaScript")


# 持久化
def persist(response):
    global auth_fail
    redirect_url = response.headers['Location']
    # print(f"Redirected to: {redirect_url}")

    server = urlparse(redirect_url).hostname
    header["Host"] = server
    redirected_response = requests.get(redirect_url, proxies=proxies, headers=header)

    if redirected_response.status_code != 200:
        print(f"服务器错误: 状态码 = {redirected_response.status_code}")
        return
    soup = BeautifulSoup(redirected_response.text, "html.parser")
    btn_close = soup.find('button', class_='btn_close')
    if btn_close:
        if btn_close.get_text() == "认证成功":
            print(f"认证成功 ({datetime.datetime.now()})")
            auth_fail = False
    else:
        print("服务器验证错误")


# 连接到谷歌的dns服务器，用来检查是否有网
def internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False


def periodicCheck():
    while True:
        global run_first_time, auth_fail
        if not internet():
            run_first_time = False
            auth_fail = True
            print("网络不可用，正在重新验证校园网..")
            try:
                response = requests.get(auth_web_lnk, allow_redirects=False, proxies=proxies, headers=header)
                if response.status_code == 200:  # 未认证的时候使用了基于JS的重定向
                    auth(response, m_profile)
                elif response.status_code == 302:  # 认证后的重定向是标准的 (虽然不知道为什么认证后仍没有网络)
                    persist(response)
            except requests.ConnectionError as e:
                print("无法连接，是否连接到了校园网???")
        elif run_first_time:
            print("已有网络连接，脚本待命中..")
            auth_fail = False
            run_first_time = False
        elif auth_fail:
            print(f"---> 重新接入到校园网 ({datetime.datetime.now()})")
            auth_fail = False
        time.sleep(profile.heartbeat)

def main():
    try:
        m_profile.read(profile_path)
    except (FileNotFoundError, KeyError) as e:
        printError(profile_path + " 读取失败")
        sys.exit()

    print(f"心跳设置: {m_profile.heartbeat}秒")
    try:
        periodicCheck()
    except KeyboardInterrupt:
        print("Exit.")

if __name__ == '__main__':
    main()
