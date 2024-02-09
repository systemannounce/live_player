# 获取哔哩哔哩直播的真实流媒体地址，默认获取直播间提供的最高画质
# qn=150高清
# qn=250超清
# qn=400蓝光
# qn=10000原画
from typing import Union
import requests
import webbrowser
import os


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


class FileManager:
    def __init__(self, *args, **kwargs):
        raise TypeError('Banned Instantiate')

    @staticmethod
    def temp_file(cookie_file):
        if not os.path.exists(cookie_file):
            print('没有检测到cookie文件,已经自动创建，画质将受到影响。')
            with open(cookie_file, 'w') as f:
                f.write('')
        with open(cookie_file, 'r', encoding='utf-8') as fp:
            cookie = fp.read()
            if cookie == '':
                print('cookie文件为空，画质将受到影响。')
            return cookie

    @staticmethod
    def room_list(room_file):
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


class MainFunction:
    def __init__(self) -> None:
        self.func_status = None
        self.qn = 10000
        while not self.func_status:
            if self.qn == 150:
                self.resolution_str = '高清'
            elif self.qn == 250:
                self.resolution_str = '超清'
            elif self.qn == 400:
                self.resolution_str = '蓝光'
            elif self.qn == 10000:
                self.resolution_str = '原画'
            func = input(f'1. 直接输入房间号\n2. 读取room.txt文件\n3. 测试room.txt内所有房间的状态\n4. 更改清晰度(当前{self.resolution_str})\n')
            try:
                if int(func) == 1:
                    self.func_status = self.enter_id()
                elif int(func) == 2:
                    self.func_status = self.exist_id()
                elif int(func) == 3:
                    self.func_status = self.check_status()
                elif int(func) == 4:
                    self.func_status = self.change_bit()
            except ValueError:
                print('\033[%s;40m请输入数字！\033[0m' % 33)


    def enter_id(self) -> bool:
        self.re_choose = True
        self.status = None
        while self.re_choose:
            self.re_choose = False
            r = input('请输入bilibili房间号(输入q返回上一级):')
            if r == 'q' or r == 'Q':
                return False
            self.status = open_potplayer(r, self.qn)
            if not self.status:
                self.re_choose = True
        return True

    def exist_id(self, *args) -> bool:
        self.re_choose = True
        self.status = None
        while self.re_choose:
            self.re_choose = False
            self.room_list = FileManager.room_list('room.txt')
            # print('序号  备注  房间号')
            # print('-----------------')
            # for num, room in enumerate(self.room_list):
            #     num = 'No.{}'.format(num)
            #     print(num, room, self.room_list[room])
            self.check_status()
            room_num = input('请输入序号加入房间(输入q返回上一级): ')
            if room_num == 'q' or room_num == 'Q':
                return False
            try:
                self.status = open_potplayer(list(self.room_list.values())[int(room_num)], self.qn)
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
        self.resolution = input('1. 高清\n2. 超清\n3. 蓝光\n4. 原画\n')
        if self.resolution == '1':
            self.qn = 150
        if self.resolution == '2':
            self.qn = 250
        if self.resolution == '3':
            self.qn = 400
        if self.resolution == '4':
            self.qn = 10000
        return False


def get_real_url(rid: str, qn):
    try:
        bilibili = BiliBili(rid, qn)
        return bilibili.get_real_url()
    except Exception as e:
        print('\033[%s;40mException: \033[0m' % 31, e)
        return False


def open_potplayer(room_id: str, qn) -> Union[bool]:
    stream = get_real_url(room_id, qn)
    if stream:
        print(f'一共有{len(stream)}个源')
        choose = input('请问要选哪个，默认第一个(输入q返回上一级): ')
        if choose == 'q' or choose == 'Q':
            return False
        if choose == '':
            choose = 1
        if int(choose) > len(stream) or int(choose) <= 0:
            print('\033[47;%sm请重新选择\033[0m' % 42)
            return False
    else:
        print('\033[47;%sm请重新选择\033[0m' % 42)
        return False
    webbrowser.open('potplayer://{}'.format(stream['线路{}'.format(str(choose))]))
    return True


if __name__ == '__main__':
    func = MainFunction()
