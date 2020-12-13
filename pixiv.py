import json
import os
import requests
from bs4 import BeautifulSoup as bs
import threading
import datetime


class Pixiv:

    def __init__(self, mode, page, r18, cookie):
        assert mode in ['1', '2', '3']
        assert r18 in ['y', 'n']
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
            'referer': 'https://www.pixiv.net/ranking.php?',
            'cookie': cookie
        }
        self.list_id = []
        self.list_url = []
        self.r18 = '_r18' if r18 == 'y' else ''
        # url = 'https://accounts.pixiv.net/login?return_to=https%3A%2F%2Fwww.pixiv.net%2F&lang=zh&source=touch&view_type=page'
        # html = requests.get(url, headers=headers).text
        # key_soup = bs(html, 'lxml')
        # post_key = key_soup.find('input')['value']  # 查找post_key
        if mode == '1':
            mode = 'daily'
        elif mode == '2':
            mode = 'weekly'
        else:
            mode = 'monthly'
            self.r18 = ''
        self.url_rank = 'https://www.pixiv.net/ranking.php?mode=' + mode + self.r18 + 'content=illust'  # 排行榜url
        self.params_rank = {
            'mode': mode + self.r18,  # 榜名，日榜:daily、周榜:weekly、月榜:monthly
            'content': 'illust',  # 搜索类型
            'p': page,  # 页数
            'format': 'json'
        }
        self.glock = threading.Lock()  # 锁
        self.num = 1

    def id_get(self):
        """从排行榜获取图片id"""
        for page in range(int(self.params_rank['p'])):
            self.params_rank['p'] = str(page + 1)
            self.headers['referer'] += 'mode=' + self.params_rank['mode'] + '&content=' + self.params_rank['content']

            if not self.r18:  # 非r18下载方法
                url_get = requests.get(self.url_rank, headers=self.headers, params=self.params_rank, timeout=5)
                url_json = json.loads(url_get.text)
                for dic in url_json['contents']:  # 获取图片id
                    self.list_id.append(dic['illust_id'])
            else:  # r18下载方法
                url = 'https://www.pixiv.net/touch/ajax/ranking/illust?mode=daily_r18&type=all&page=' + str(page + 1)
                url_get = requests.get(url, headers=self.headers, params=self.params_rank, timeout=5)
                url_json = json.loads(url_get.text)
                for dic in url_json['body']['ranking']:
                    self.list_id.append(dic['illustId'])

    def url_get(self):
        """从id获取url"""
        while True:
            self.glock.acquire()  # 加锁
            if len(self.list_id) == 0:
                self.glock.release()  # 释放锁
                break
            ID = self.list_id.pop(0)  # 提取list_id的第一个元素
            self.glock.release()
            url_page = 'https://www.pixiv.net/ajax/illust/' + str(ID) + '/pages?lang=zh'
            headers = self.headers
            headers['referer'] = 'https://www.pixiv.net/artworks/' + str(ID)

            url_text = requests.get(url_page, headers=headers).text
            url_testjson = json.loads(url_text)

            for dic in url_testjson['body']:
                self.list_url.append(dic['urls']['original'])
                url = dic['urls']['original']
                print(f'获取链接：{url}')

    def download(self):
        """下载图片到本地"""
        str_path = datetime.date.today().strftime('%Y%m%d') + self.params_rank['mode']  # 获取时间作为文件夹
        if not os.path.exists(str_path):  # 如果没有文件夹，则创建文件夹
            os.mkdir(str_path)

        while True:
            self.glock.acquire()  # 加锁
            if len(self.list_url) == 0:
                self.glock.release()
                break

            url = self.list_url.pop(0)  # 获取list_url的第一个元素
            self.glock.release()
            path = str_path + '/' + str(self.num) + url.split('/')[-1]  # 文件名创建
            pixiv_img = requests.get(url, headers=self.headers)
            with open(path, 'wb') as f:
                f.write(pixiv_img.content)
                print(f'图片{self.num}正在保存...')
                self.num += 1


def main():
    print('##————Pixiv————##')
    print('##----如需爬取r18图片请确认保存cookie到cookie.txt----##')

    moder = input('请输入排行榜的时间（日:1/周:2/月:3）:')
    pn = input('请输入你想要多少页(50张图片/页):')
    r18 = input('请输入是否需要r18：(y/n)')
    if os.path.exists('cookie.txt'):
        with open('cookie.txt', 'r') as f:
            cookie = f.read()
    else:
        cookie = ''
    pixiv = Pixiv(moder, pn, r18, cookie)
    pixiv.id_get()

    for j in range(3):
        urlget = threading.Thread(target=pixiv.url_get())
        urlget.start()

    for i in range(3):
        download = threading.Thread(target=pixiv.download())
        download.start()

    print(f'爬取结束,共保存{pixiv.num - 1}张图片')


if __name__ == "__main__":
    main()
