# 获取各个直播平台的直播源并且在本地播放器中打开。


import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser

import execjs
import requests


class BiliBili:
    def __init__(self, rid, o_qn):
        """
        有些地址无法在PotPlayer播放，建议换个播放器试试
        Args:
            rid:
        """
        rid = rid
        self.current_qn = o_qn
        self.header = {  # 要获取原画请自行填写cookie
            'User-Agent': 'Mozilla/5.0 (iPod; CPU iPhone OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                          'like Gecko) CriOS/87.0.4280.163 Mobile/15E148 Safari/604.1',
            'Cookie': FileManager.temp_file('cookie.txt')
        }
        # 先获取直播状态和真实房间号
        r_url = 'https://api.live.bilibili.com/room/v1/Room/room_init'
        param = {
            'id': rid
        }
        with requests.Session() as self.s:
            res = self.s.get(r_url, headers=self.header, params=param).json()
        if res['msg'] == '直播间不存在':
            raise Exception(f'bilibili {rid} {res["msg"]}')
        live_status = res['data']['live_status']
        if live_status != 1:
            raise Exception(f'bilibili {rid} 未开播')
        self.real_room_id = res['data']['room_id']

    def get_real_url(self) -> dict:
        url = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo'
        param = {
            'room_id': self.real_room_id,
            'protocol': '0,1',
            'format': '0,1,2',
            'codec': '0,1',
            'qn': self.current_qn,
            'platform': 'h5',
            'ptype': 8,
        }
        res = self.s.get(url, headers=self.header, params=param).json()
        stream_info = res['data']['playurl_info']['playurl']['stream']
        qn_max = 0

        for data in stream_info:
            accept_qn = data['format'][0]['codec'][0]['accept_qn']
            for qn in accept_qn:
                qn_max = qn if qn > qn_max else qn_max
        if qn_max != self.current_qn:
            param['qn'] = self.current_qn
            res = self.s.get(url, headers=self.header, params=param).json()
            stream_info = res['data']['playurl_info']['playurl']['stream']

        stream_urls = {}
        # flv流无法播放，暂修改成获取hls格式的流，
        for data in stream_info:
            format_name = data['format'][0]['format_name']
            if format_name == 'ts':
                base_url = data['format'][-1]['codec'][0]['base_url']
                url_info = data['format'][-1]['codec'][0]['url_info']
                for i, info in enumerate(url_info):
                    host = info['host']
                    extra = info['extra']
                    stream_urls[f'线路{i + 1}'] = f'{host}{base_url}{extra}'
                break
        return stream_urls


class HuYa:
    def __init__(self, *args, **kwargs):
        raise TypeError('Banned Instantiate')

    @staticmethod
    def get_real_url(room_id):
        try:
            room_url = 'https://m.huya.com/' + str(room_id)
            header = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/121.0.0.0 Safari/537.36'
            }
            response = requests.get(url=room_url, headers=header).text
            info = 'var info = ' + re.findall(r'var hyPlayerConfig = ([\s\S]*?)};', response)[0] + '};'
            room_js = execjs.compile(info)
            if not room_js.eval(f'info.stream.vMultiStreamInfo'):
                raise Exception(f'{room_id}未开播')
            stream = 1  # choose stream
            url = room_js.eval(f'info.stream.data[0].gameStreamInfoList[{stream}].sFlvUrl') + '/'
            url = url + room_js.eval(f'info.stream.data[0].gameStreamInfoList[{stream}].sStreamName') + '.'
            url = url + room_js.eval(f'info.stream.data[0].gameStreamInfoList[{stream}].sHlsUrlSuffix') + '?ver=1&'
            url = url + room_js.eval(f'info.stream.data[0].gameStreamInfoList[{stream}].sFlvAntiCode')
        except IndexError:
            raise Exception(f'HuYa {room_id}未开播')
        return url


class DouYu:
    """
    可用来替换返回链接中的主机部分
    两个阿里的CDN：
    dyscdnali1.douyucdn.cn
    dyscdnali3.douyucdn.cn
    墙外不用带尾巴的akm cdn：
    hls3-akm.douyucdn.cn
    hlsa-akm.douyucdn.cn
    hls1a-akm.douyucdn.cn
    """

    def __init__(self, rid):
        """
        房间号通常为1~8位纯数字，浏览器地址栏中看到的房间号不一定是真实rid.
        Args:
            rid:
        """
        self.did = '10000000000000000000000000001501'
        self.t10 = str(int(time.time()))
        self.t13 = str(int((time.time() * 1000)))

        self.s = requests.Session()
        self.res = self.s.get('https://m.douyu.com/' + str(rid)).text
        result = re.search(r'rid":(\d{1,8}),"vipId', self.res)

        if result:
            self.rid = result.group(1)
        else:
            raise Exception(f'DouYu {rid} 房间号错误')

    @staticmethod
    def md5(data):
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_pc_js(self, cdn='ws-h5', rate=0):
        """
        通过PC网页端的接口获取完整直播源。
        :param cdn: 主线路ws-h5、备用线路tct-h5
        :param rate: 1流畅；2高清；3超清；4蓝光4M；0蓝光8M或10M
        :return: JSON格式
        """
        res = self.s.get('https://www.douyu.com/' + str(self.rid)).text
        result = re.search(r'(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function', res).group(1)
        func_ub9 = re.sub(r'eval.*?;}', 'strc;}', result)
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')

        v = re.search(r'v=(\d+)', res).group(1)
        rb = DouYu.md5(self.rid + self.did + self.t10 + v)

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')

        js = execjs.compile(func_sign)
        params = js.call('sign', self.rid, self.did, self.t10)

        params += '&cdn={}&rate={}'.format(cdn, rate)
        url = 'https://www.douyu.com/lapi/live/getH5Play/{}'.format(self.rid)
        res = self.s.post(url, params=params).json()
        if res['msg'] != 'ok':
            raise Exception('房间未开播')
        real_url = res['data']['rtmp_url'] + '/' + res['data']['rtmp_live']

        return real_url


class Get:
    def __init__(self, *args, **kwargs):
        raise TypeError('Banned Instantiate')

    @staticmethod
    def bili_url(rid: str, qn):
        try:
            bilibili = BiliBili(rid, qn)
            return bilibili.get_real_url()
        except Exception as e:
            print('\033[%s;40mException: \033[0m' % 31, e)
            return False

    @staticmethod
    def huya_url(rid: str):
        try:
            return HuYa.get_real_url(rid)
        except Exception as e:
            print('\033[%s;40mException: \033[0m' % 31, e)
            return False

    @staticmethod
    def douyu_url(rid: str):
        try:
            douyu = DouYu(rid)
            return douyu.get_pc_js()
        except Exception as e:
            print('\033[%s;40mException: \033[0m' % 31, e)
            return False


class FileManager:
    def __init__(self, *args, **kwargs):
        raise TypeError('Banned Instantiate')

    @staticmethod
    def temp_file(cookie_file):
        # 读取文件并返回内容
        if not os.path.exists(cookie_file):
            print('\033[%s;40m没有检测到cookie文件,已经自动创建，画质将受到影响。\033[0m' % 33)
            with open(cookie_file, 'w') as f:
                f.write('')
        with open(cookie_file, 'r', encoding='utf-8') as fp:
            cookie = fp.read()
            if cookie == '':
                print('\033[%s;40mcookie文件为空，画质将受到影响。\033[0m' % 33)
            return cookie

    @staticmethod
    def room_list(room_file) -> dict:
        # 按照特定规则读取文件并返回字典
        lines = {}
        if not os.path.exists(room_file):
            with open(room_file, 'w', encoding='utf-8') as fp:
                fp.write('格式要求：\n')
                fp.write('注释:房间号\n')
                fp.write('如果要进行修改请将本文件所有内容删除干净后再填写。确保自己已经知晓上面的填写方法\n')
                return {}
        else:
            empty_line = 0
            with open(room_file, 'r', encoding='utf-8') as fp:
                fp_lines = fp.readlines()
                for line in fp_lines:
                    if line == '\n':
                        empty_line = empty_line + 1
                        continue
                    try:
                        temp_line = line.split(':')
                        lines[temp_line[0].strip()] = temp_line[1].strip()
                    except IndexError:
                        # print('未检测到有效列表')
                        pass
                if len(lines) < len(fp_lines) - empty_line:
                    print('\033[%s;40mroom.txt 文件内存在错误，请检查是否按照规则填写。\033[0m' % 33)
                return lines

    @staticmethod
    def resource_path(relative_path) -> str:
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    @staticmethod
    def fix_vlc():
        # 修复vlc播放器不能使用浏览器'vlc://'协议
        vlc_address = input('请输入vlc安装目录（纯地址，不要包含前后引号，输入q退出）：')
        if vlc_address == 'q' or vlc_address == 'Q':
            return False
        vlc_fix = FileManager.resource_path('./vlc_fix/')
        try:
            for filename in os.listdir(vlc_fix):
                try:
                    shutil.copy(vlc_fix + filename, vlc_address)
                except shutil.Error:
                    print(f'\033[%s;40m 文件{filename}已存在，跳过 \033[0m' % 33)
        except FileNotFoundError:
            print(f'\033[%s;40m 程序目录下不存在vlc_fix文件夹，请自行去github源代码处下载 \033[0m' % 33)
            return False
        command = vlc_address + '/vlc-protocol-register.bat'
        subprocess.Popen(["start", "cmd", "/k", command], shell=True)


class MainFunction:
    # 主功能

    def __init__(self) -> None:
        if os.name == 'nt':
            self.clear_command = "cls"
        else:
            self.clear_command = "clear"
        self.platforms = ['surprise', 'bilibili', 'HuYa', 'DouYu']
        self.platform = 'bilibili'
        self.player = 'potplayer'
        self.func_status = None
        self.qn = 10000     # 清晰度
        while not self.func_status:
            if self.qn == 150:
                self.resolution_str = '高清'
            elif self.qn == 250:
                self.resolution_str = '超清'
            elif self.qn == 400:
                self.resolution_str = '蓝光'
            elif self.qn == 10000:
                self.resolution_str = '原画'
            if self.platform != 'bilibili':
                self.resolution_str = 'N/A'
            func = input('1. 直接输入房间号\n2. 读取room.txt文件\n3. 测试room.txt内所有房间的状态(bilibili)\n'
                         f'4. 更改清晰度(当前{self.resolution_str})\n5. 更换平台，当前为{self.platform}\n'
                         f'6. 更换播放器，当前为{self.player}\n7. vlc无法正常调用选我修复\n8. 清屏\n9. 毁灭吧世界！\n'
                         '\033[%s;40mPS : 目前虎牙和斗鱼不支持清晰度选择和开播检测\n:\033[0m' % 33)
            try:
                if int(func) == 1:
                    self.func_status = self.enter_id()
                elif int(func) == 2:
                    self.func_status = self.exist_id()
                elif int(func) == 3:
                    self.func_status = self.check_status()
                elif int(func) == 4:
                    self.func_status = self.change_bit()
                elif int(func) == 5:
                    choose = input('1. bilibili\n2. HuYa\n3. DouYu\n:')
                    try:
                        self.platform = self.platforms[int(choose)]
                    except IndexError:
                        print('\033[%s;40m超出可选范围\033[0m' % 31)

                elif int(func) == 6:
                    if self.player == 'potplayer':
                        self.player = 'vlc'
                    else:
                        self.player = 'potplayer'
                elif int(func) == 7:
                    FileManager.fix_vlc()
                elif int(func) == 8:
                    os.system(self.clear_command)
                elif int(func) == 9:
                    exit(114514)

            except ValueError:
                print('\033[%s;40m请输入数字！\033[0m' % 33)

    def enter_id(self) -> bool:
        # 输入房间号功能
        self.re_choose = True
        self.status = None
        os.system(self.clear_command)
        while self.re_choose:
            self.re_choose = False
            r = input('请输入房间号(输入q返回上一级):')
            if r == 'q' or r == 'Q':
                return False
            self.status = open_potplayer(r, self.qn, self.platform, self.player)
            if not self.status:
                self.re_choose = True
        return True

    def exist_id(self, *args) -> bool:
        # 读取文件功能
        self.re_choose = True
        self.status = None
        os.system(self.clear_command)
        while self.re_choose:
            self.re_choose = False
            self.room_list = FileManager.room_list('room.txt')
            if self.platform == 'bilibili':
                self.check_status()
            else:
                print('序号  备注  房间号')
                print('-----------------')
                for num, room in enumerate(self.room_list):
                    num = 'No.{}'.format(num)
                    print(num, room, self.room_list[room])
            room_num = input('请输入序号加入房间(输入q返回上一级): ')
            if room_num == 'q' or room_num == 'Q':
                return False
            try:
                self.status = open_potplayer(list(self.room_list.values())[int(room_num)],
                                             self.qn, self.platform, self.player)
            except IndexError:
                print('\033[%s;40m序号不存在\033[0m' % 31)
            except AttributeError:
                print('\033[%s;40m文件里面还没有内容，请重新选择\033[0m' % 31)
                return False
            except ValueError:
                print('\033[%s;40m请输入数字！\033[0m' % 33)
            if not self.status:
                self.re_choose = True
        return True

    def check_status(self):
        # 检查状态功能，目前只适配了bilibili
        self.room_list = FileManager.room_list('room.txt')
        print('序号  备注  房间号  状态')
        print('-----------------------')
        for num, room in enumerate(self.room_list):
            num = 'No.{}'.format(num)
            try:
                bilibili = BiliBili(self.room_list[room], self.qn)
                self.room_status = '已开播'
            except Exception as e:
                # print('\033[%s;40mException: \033[0m' % 31, e)
                if '未开播' in str(e):
                    self.room_status = '未开播'
                elif '不存在' in str(e):
                    self.room_status = '不存在'
            print(num, room, self.room_list[room], self.room_status)
        print('\n')
        return False

    def change_bit(self):
        # 更改清晰度，目前只有bilibili可以更改清晰度
        self.resolution = input('1. 高清\n2. 超清\n3. 蓝光\n4. 原画\n:')
        if self.resolution == '1':
            self.qn = 150
        if self.resolution == '2':
            self.qn = 250
        if self.resolution == '3':
            self.qn = 400
        if self.resolution == '4':
            self.qn = 10000
        return False


def open_potplayer(room_id: str, qn, platform, player):
    if platform == 'bilibili':
        stream = Get.bili_url(room_id, qn)
    elif platform == 'HuYa':
        stream = Get.huya_url(room_id)
    elif platform == 'DouYu':
        stream = Get.douyu_url(room_id)
    else:
        stream = Get.bili_url(room_id, qn)
    if stream and platform == 'bilibili' or platform == 'surprise':
        print(f'一共有{len(stream)}个源')
        if len(stream) > 1:
            choose = input('请问要选哪个，默认第一个(输入q返回上一级): ')
        else:
            choose = 1
        if choose == 'q' or choose == 'Q':
            return False
        if choose == '':
            choose = 1
        if int(choose) > len(stream) or int(choose) <= 0:
            print('\033[47;%sm请重新选择\033[0m' % 42)
            return False
        stream = stream['线路{}'.format(str(choose))]
    elif not stream:
        print('\033[47;%sm请重新选择\033[0m' % 42)
        return False
    webbrowser.open(f'{player}://{stream}')
    # print(f'{player}://{stream}')
    if platform == 'DouYu':     # 斗鱼直播不稳定，显示直播源然后返回上一级
        print(stream)
        return False
    return True


if __name__ == '__main__':
    func = MainFunction()
