# -*- coding: utf-8 -*-
import re

import pymongo
import requests
from lxml import etree


# 抓取本网站的不同底去的经点只需要修改3处链接上的地点即可，同时可以修改相应的数据库集合名称
class Trip(object):
    def __init__(self):
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'www.tripadvisor.cn',
            'Referer': 'https://www.tripadvisor.cn/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'
        }
        self.host = '127.0.0.1'
        self.mongodb = 'Trip'  # 库
        self.mongo_table = 'Chengdu'  # 集合
        self.mongo_table2 = 'Chengdu2'  # 集合2(存储没有照片评论描述的景点)
        self.client = pymongo.MongoClient(host=self.host, port=27017)  # 建立连接

        self.db = self.client[self.mongodb]  # 操作库
        self.tb = self.db[self.mongo_table]  # 操作集合
        self.tb2 = self.db[self.mongo_table2]  # 操作集合2

    # 抓取翻页链接
    def get_page_link(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            tree = etree.HTML(response.text)
            page = tree.xpath('//*[@id="FILTERED_LIST"]/div[36]/div/div/div/a[6]/text()')
            if page:
                page = page[0].replace('\n', '')
                for i in range(1, int(page)+1):
                    if i == 1:
                        url = 'https://www.tripadvisor.cn/Attractions-g297463-Activities-Chengdu_Sichuan.html'  # Chengdu_Sichuan
                    else:
                        page = (i-1) * 30
                        url = 'https://www.tripadvisor.cn/Attractions-g297463-Activities-oa{}-Chengdu_Sichuan.html#FILTERED_LIST'.format(page)  # Chengdu_Sichuan
                    yield url
        else:
            return response.status_code

    # 解析源码货物HTML
    def get_html(self, link):
        response = requests.get(link)
        if response.status_code == 200:
            return response.text

    # 获取每个景点的链接
    def get_links(self, html):
        tree = etree.HTML(html)
        links = tree.xpath('//div[@id="FILTERED_LIST"]/div/div/div/div/div/div[2]/a/@href')
        for i in links:
            url = 'https://www.tripadvisor.cn' + i
            yield url

    # 分析景点页面抓取相应值
    def get_scenic(self, link):
        scenic = {}
        response = requests.get(link)
        tree = etree.HTML(response.text)
        title = tree.xpath('//h1[@id="HEADING"]/text()')
        if title:
            scenic['name'] = title[0].strip()
        else:
            scenic['name'] = ''
        en_title = tree.xpath('//h1[@id="HEADING"]/div/text()')
        if en_title:
            scenic['en_name'] = en_title[0].strip()
        else:
            scenic['en_name'] = ''
        address = tree.xpath('//div[@class="is-hidden-mobile blEntry address  ui_link"]/span[2]//text()')
        address2 = tree.xpath('//div[@class="is-hidden-mobile blEntry address  ui_link showBizHour"]/span[2]//text()')
        if address:
            scenic['address'] = ','.join(address).strip()
        else:
            if address2:
                scenic['address'] = ','.join(address2).strip()
            else:
                scenic['address'] = ''
        picture = tree.xpath('//*[@id="taplc_resp_photo_mosaic_ar_responsive_0"]/div/div[4]/div[2]/div[1]/div/img/@src')
        if picture:
            scenic['picture'] = picture[0]
        else:
            scenic['picture'] = ''
        try:
            intro = re.findall(r'description":"(.*?)"', response.text, re.S)
            if intro:
                scenic['intro'] = intro[0].encode().decode('unicode_escape')
            else:
                scenic['intro'] = '暂无描述...'
        except:
            scenic['intro'] = ''
        comment = tree.xpath('//div[@class="listContainer hide-more-mobile"]//p[@class="partial_entry"]/text()')
        x = {}
        if comment:
            for i, com in enumerate(comment):
                x[i] = com.replace('\n', '')
                scenic['comment'] = str(x)
        else:
            scenic['comment'] = '暂无评论...'

        return scenic

    # 数据保存到MongoDB
    def save_to_mongodb(self, scenic):
        if scenic['picture'] == '' and scenic['intro'] == '暂无描述...' and scenic['comment'] == '暂无评论...':
            self.tb2.insert_one(scenic)
            print('Successful Save Message To Chengdu2')
        else:
            self.tb.insert_one(scenic)  # , check_keys=False 不检测key， 防止有特殊字符 例.
            print('Successful Save Message To Chengdu')

        # documents must have only string keys, key was 0  存储数据中不能有bytes只能是字符串

    # 主程序入口
    def run(self):
        url = 'https://www.tripadvisor.cn/Attractions-g297463-Activities-Chengdu_Sichuan.html'  # Chengdu_Sichuan
        for links in self.get_page_link(url):
            html = self.get_html(links)
            for link in self.get_links(html):
                scenic = self.get_scenic(link)
                self.save_to_mongodb(scenic)
                # print(scenic)


if __name__ == '__main__':
    trip = Trip()
    trip.run()

