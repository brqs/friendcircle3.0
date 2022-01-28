# -*- coding:utf-8 -*-

import leancloud
import datetime
import settings
import sys
import re
from scrapy.exceptions import DropItem


class HexoCircleOfFriendsPipeline:
    def __init__(self):
        self.userdata = []
        self.nonerror_data = set() # 能够根据友链link获取到文章的人
        self.total_post_num = 0
        self.total_friend_num = 0
        self.err_friend_num = 0
    def open_spider(self, spider):
        if settings.DEBUG:
            leancloud.init(settings.LC_APPID, settings.LC_APPKEY)
        else:
            leancloud.init(sys.argv[1], sys.argv[2])
        self.Friendslist = leancloud.Object.extend('friend_list')
        self.Friendspoor = leancloud.Object.extend('friend_poor')
        self.query_friendslist()

        for query_j in self.query_friend_list:
            delete = self.Friendslist.create_without_data(query_j.get('objectId'))
            delete.destroy()
        self.query_friendslist()
        self.query_friendspoor()

        # print(self.query_post_list)
        # print(self.query_friend_list)

        print("Initialization complete")
    def process_item(self, item, spider):
        if "userdata" in item.keys():
            li = []
            li.append(item["name"])
            li.append(item["link"])
            li.append(item["img"])
            self.userdata.append(li)
            # print(item)
            return item

        if "title" in item.keys():
            if item["name"] in self.nonerror_data:
                pass
            else:
                # 未失联的人
                self.nonerror_data.add(item["name"])

            # print(item)
            for query_item in self.query_post_list:
                try:
                    if query_item.get("link")==item["link"]:
                        item["time"]=min(item['time'], query_item.get('time'))
                        delete = self.Friendspoor.create_without_data(query_item.get('objectId'))
                        delete.destroy()
                        # print("----deleted %s ----"%item["title"])
                except:
                    pass

            self.friendpoor_push(item)

        return item
    def close_spider(self,spider):
        # print(self.nonerror_data)
        # print(self.userdata)

        self.friendlist_push()

        self.outdate_clean(settings.OUTDATE_CLEAN)
        print("----------------------")
        print("友链总数 : %d" %self.total_friend_num)
        print("失联友链数 : %d" % self.err_friend_num)
        print("共 %d 篇文章"%self.total_post_num)

        print("done!")

    def query_friendspoor(self):
        try:
            query = self.Friendspoor.query
            query.select("title",'time', 'link', 'updated')
            query.limit(1000)
            self.query_post_list = query.find()
            # print(self.query_post_list)
        except:
            self.query_post_list=[]
    def query_friendslist(self):
        try:
            query = self.Friendslist.query
            query.select('frindname', 'friendlink', 'firendimg', 'error')
            query.limit(1000)
            self.query_friend_list = query.find()
        except:
            self.query_friend_list=[]

    def outdate_clean(self,time_limit):
        out_date_post = 0
        for query_i in self.query_post_list:

            time = query_i.get('time')
            try:
                query_time = datetime.datetime.strptime(time, "%Y-%m-%d")
                if (datetime.datetime.today() - query_time).days > time_limit:
                    delete = self.Friendspoor.create_without_data(query_i.get('objectId'))
                    out_date_post += 1
                    delete.destroy()
            except:
                delete = self.Friendspoor.create_without_data(query_i.get('objectId'))
                delete.destroy()
                out_date_post += 1
        # print('\n')
        # print('共删除了%s篇文章' % out_date_post)
        # print('\n')
        # print('-------结束删除规则----------')

    def friendlist_push(self):
        for index, item in enumerate(self.userdata):
            friendlist = self.Friendslist()
            friendlist.set('frindname', item[0])
            friendlist.set('friendlink', item[1])
            friendlist.set('firendimg', item[2])
            if item[0] in self.nonerror_data:
                # print("未失联的用户")
                friendlist.set('error', "false")
            elif settings.BLOCK_SITE:
                error = True
                for url in settings.BLOCK_SITE:
                    if re.match(url, item[1]):
                        friendlist.set('error', "false")
                        error = False
                if error:
                    self.err_friend_num += 1
                    print("请求失败，请检查链接： %s" % item[1])
                    friendlist.set('error', "true")
            else:
                self.err_friend_num += 1
                print("请求失败，请检查链接： %s" % item[1])
                friendlist.set('error', "true")
            friendlist.save()
            self.total_friend_num+=1

    def friendpoor_push(self,item):
        friendpoor = self.Friendspoor()
        friendpoor.set('title', item['title'])
        friendpoor.set('time', item['time'])
        friendpoor.set('updated', item['updated'])
        friendpoor.set('link', item['link'])
        friendpoor.set('author', item['name'])
        friendpoor.set('headimg', item['img'])
        friendpoor.set('rule', item['rule'])
        friendpoor.save()
        print("----------------------")
        print(item["name"])
        print("《{}》\n文章发布时间：{}\t\t采取的爬虫规则为：{}".format(item["title"], item["time"], item["rule"]))
        self.total_post_num +=1

class DuplicatesPipeline:
    def __init__(self):
        self.data_set = set() # posts filter set 用于对文章数据的去重
        self.user_set = set() # userdata filter set 用于对朋友列表的去重
    def process_item(self, item, spider):
        if "userdata" in item.keys():
            #  userdata filter
            link = item["link"]
            if link in self.user_set:
                raise DropItem("Duplicate found:%s" % link)
            self.user_set.add(link)
            return item

        title = item['title']

        if title in self.data_set or title=="":
            # 重复数据清洗
            raise DropItem("Duplicate found:%s" % title)
        if not item["link"]:
            raise DropItem("missing fields :'link'")
        elif not re.match("^http.?://",item["link"]):
            # 链接必须是http开头，不能是相对地址
            raise DropItem("invalid link ")

        if not re.match("^\d+",item["time"]):
            # 时间不是xxxx-xx-xx格式，丢弃
            raise DropItem("invalid time ")
        self.data_set.add(title)

        return item