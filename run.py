'''
!/usr/bin/env python3
-*- coding: utf-8 -*-
Github    : https://github.com/Rock-Candy-Tea
team      : Rock-Candy-Tea
vindicator: 
 - Zour     : https://github.com/Zfour
 - RaXianch : https://github.com/DeSireFire
 - noionion : https://github.com/2X-ercha

主程序

业务流程：
主程序-->（处理器handlers）控件—->组件(component)

组件作为最底层，单向调用。
处理器可以调用组件，组件不可以反向调用处理器或主程序里的代码块。
避免产生双向调用，执行流程不清。

处理器之间，不能互相调用。
避免出现处理器相互依赖，做到移除单一处理器时，不会导致其他处理器出错。
(特例：coreSettings.py，其他处理器可以单向调用coreSettings.py的值，
但coreSettings.py不能调用其他处理器的函数/类来处理)。
处理器避免直接调用外部settings.py里的参数，而是使用coreSettings.py来调用设置的值。
如要全局设置中的值，由coreSettings.py处理器统筹，使调用收束。

主程序
只负责：
调用处理器；
程序的整体执行流程；
打印执行信息.

todo:
request_data 组件化
request_data 多线程
theme 组件化

'''

from operator import itemgetter
import leancloud
import sys

# component
from theme import butterfly,matery,volantis,sakura,fluid

# handlers
from handlers.coreSettings import configs
from handlers.coreLink import delete_same_link
from handlers.coreLink import block_link
from handlers.coreLink import kang_api
from handlers.coreLink import github_issuse
from handlers.coreLink import atom_get
from handlers.coreLink import rss2_get
from handlers.coreLink import config_friendlink
from handlers.coreDatas import leancloud_push_userinfo
from handlers.coreDatas import leancloud_push

# threads
from queue import Queue
from threading import Thread

# theme fit massage
themes = [
    butterfly,
    matery,
    volantis,
    sakura,
    fluid
]

# get friendpage_link
def verification():
    # 引入leancloud验证
    if configs.DEBUG:
        leancloud.init(configs.LC_APPID, configs.LC_APPKEY)
        friendpage_link = configs.FRIENPAGE_LINK
    else:
        leancloud.init(sys.argv[1], sys.argv[2])
        friendpage_link = sys.argv[3]
    return friendpage_link

# get friend_link
def get_link(friendpage_link, config):
    friend_poor = []

    #  get setting.py_links
    if configs.CONFIG_FRIENDS_LINKS['enable']:
        config_friendlink(friend_poor, config)

    #　get gitee_issue
    if configs.GITEE_FRIENDS_LINKS['enable'] and configs.GITEE_FRIENDS_LINKS['type'] == 'normal':
        try:
            kang_api(friend_poor, config)
        except:
            pass
    
    # get github_issue
    if configs.GITHUB_FRIENDS_LINKS['enable'] and configs.GITHUB_FRIENDS_LINKS['type'] == 'normal':
        try:
            github_issuse(friend_poor, config)
        except:
            pass

    # get theme_link
    for themelinkfun in themes:
        try:
            themelinkfun.get_friendlink(friendpage_link, friend_poor)
        except:
            pass
    print("----------------------")
    friend_poor = delete_same_link(friend_poor)
    friend_poor = block_link(friend_poor)

    print("----------------------")
    print('当前友链数量', len(friend_poor))
    print("----------------------")
    return friend_poor

# get each_link_last_post
def get_post(friend_poor):
    total_count = 0
    error_count = 0
    post_poor = []

    def spider(item):
        nonlocal total_count
        nonlocal post_poor
        nonlocal error_count
        error = True
        try:
            total_count += 1
            error, post_poor = atom_get(item, post_poor)
            if error:
                # print("-----------获取atom信息失败，采取rss2策略----------")
                error, post_poor = rss2_get(item, post_poor)
            if error:
                # print("-----------获取rss2信息失败，采取主页爬虫策略----------")
                for themelinkfun in themes:
                    if not error:
                        break
                    error = themelinkfun.get_last_post(item, post_poor)
            '''     
            if error: 
                # print("-----------获取主页信息失败，采取sitemap策略----------")
                error, post_poor = sitmap_get(item, post_poor)
            '''
            if error:
                # print('\n')
                print(item[0]+"\n所有规则爬取失败！请检查: "+item[1])
                # print('\n')
                error_count += 1
        except Exception as e:
            # print('\n')
            print(item[0]+"\n所有规则爬取失败！请检查: "+item[1])
            # print('\n')
            # print(e)
            error_count += 1
        
        if error: error = 'true'
        else: error = 'false'
        item.append(error)
        return item

    # multithread process
    # ---------- #
    Q = Queue()

    for i in range(len(friend_poor)):
        Q.put(i)

    def multitask():
        while not Q.empty():
            i= Q.get()
            item = friend_poor[i]
            item = spider(item)

    cores = 128
    threads = []
    for _ in range(cores):
        t = Thread(target=multitask)
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # ---------- #
    
    print('\n----------------------\n一共进行{}次\n一共失败{}次\n----------------------\n'.format(total_count, error_count))
    return post_poor

def main():
    config = configs.yml
    friendpage_link = verification()
    friend_poor = get_link(friendpage_link, config)
    post_poor = get_post(friend_poor)
    leancloud_push_userinfo(friend_poor) 
    post_poor.sort(key=itemgetter('name'), reverse=True)
    person = ""
    for post in post_poor:
        if(post["name"] != person):
            print("----------------------")
            print(post["name"])
            person = post["name"]
        print("《{}》\n文章发布时间：{}\t\t采取的爬虫规则为：{}".format(post["title"], post["time"], post["rule"]))
    print("----------------------")
    leancloud_push(post_poor)

# ---------- #

if __name__ == '__main__':
    main()