# -*- coding:utf-8 -*-

import calendar
import datetime
import time
import scrapy
import queue
from scrapy.http.request import Request
from hexo_circle_of_friends import settings
from bs4 import BeautifulSoup
from hexo_circle_of_friends.utils.get_theme_url import *
from hexo_circle_of_friends.utils.regulations import *
import sys


# from hexo_circle_of_friends import items todo use items
class FriendpageLinkSpider(scrapy.Spider):
    name = 'hexo_circle_of_friends'
    allowed_domains = ['*']
    start_urls = []

    def __init__(self, name=None, **kwargs):
        self.friend_poor = queue.Queue()
        self.friend_list = queue.Queue()

        super().__init__(name, **kwargs)

    def start_requests(self):
        # 从配置文件导入友链列表
        if settings.SETTINGS_FRIENDS_LINKS['enable']:
            for user_info in settings.SETTINGS_FRIENDS_LINKS["list"]:
                # print('----------------------')
                # print('好友名%r' % user_info[0])
                # print('头像链接%r' % user_info[2])
                # print('主页链接%r' % user_info[1])
                self.friend_poor.put(user_info)
        if settings.GITEE_FRIENDS_LINKS['enable']:
            for number in range(1, 100):
                domain = 'https://gitee.com'
                dic = settings.GITEE_FRIENDS_LINKS
                url = domain + "/" + dic["owner"] + "/" + dic["repo"] + '/issues?state=' + dic[
                    "state"] + '&page=' + str(number)
                yield Request(url, callback=self.friend_poor_parse, meta={"gitee": {"domain": domain}})
        if settings.GITHUB_FRIENDS_LINKS['enable']:
            for number in range(1, 100):
                domain = 'https://github.com'
                dic = settings.GITHUB_FRIENDS_LINKS
                url = domain + "/" + dic["owner"] + "/" + dic["repo"] + "/issues?q=is%3A" + dic[
                    "state"] + '&page=' + str(number)
                yield Request(url, callback=self.friend_poor_parse, meta={"github": {"domain": domain}})
        if settings.DEBUG:
            friendpage_link = settings.FRIENPAGE_LINK
        else:
            friendpage_link = []
            friendpage_link.append(sys.argv[3])
            if settings.EXTRA_FRIENPAGE_LINK:
                friendpage_link.extend(settings.EXTRA_FRIENPAGE_LINK)

        self.start_urls.extend(friendpage_link)
        for url in self.start_urls:
            yield Request(url, callback=self.friend_poor_parse, meta={"theme": url})

    def friend_poor_parse(self, response):
        # 获取朋友列表
        # print("friend_poor_parse---------->" + response.url)

        if "gitee" in response.meta.keys():
            main_content = response.css("#git-issues a.title::attr(href)").extract()
            if main_content:
                for item in main_content:
                    issueslink = response.meta["gitee"]["domain"] + item
                    yield Request(issueslink, self.friend_poor_parse, meta={"gitee-issues": None},dont_filter=True)
        if "gitee-issues" in response.meta.keys():
            try:
                content = ''.join(response.css("code *::text").extract())
                user_info = []
                if settings.GITHUB_FRIENDS_LINKS["type"] == "volantis":
                    reg_volantis(user_info, content)
                    self.friend_poor.put(user_info)
                else:
                    info_list = ['name', 'link', 'avatar']
                    reg_normal(info_list, user_info, content)
                    if user_info[1] != '你的链接':
                        self.friend_poor.put(user_info)
            except:
                pass

        if "github" in response.meta.keys():
            main_content = response.css("div[aria-label=Issues] a.Link--primary::attr(href)").extract()
            if main_content:
                for item in main_content:
                    issueslink = response.meta["github"]["domain"] + item
                    yield Request(issueslink, self.friend_poor_parse, meta={"github-issues": None},dont_filter=True)
        if "github-issues" in response.meta.keys():
            try:
                content = ''.join(response.css("pre *::text").extract())
                if content!='':
                    user_info = []
                    if settings.GITHUB_FRIENDS_LINKS["type"] == "volantis":
                        reg_volantis(user_info, content)
                        self.friend_poor.put(user_info)
                    else:
                        info_list = ['name', 'link', 'avatar']
                        reg_normal(info_list, user_info, content)
                        if user_info[1] != '你的链接':
                            self.friend_poor.put(user_info)
            except:
                pass

        if "theme" in response.meta.keys():
            user_info = []
            link = get_link_url(response)
            avatar = get_avatar_url(response)
            name = get_name_url(response)
            # print(link)
            # print(avatar)
            # print(name)
            if len(link) == len(avatar) == len(name):

                for i in range(len(link)):
                    if link[i] == "":
                        continue
                    user_info.append(name[i])
                    user_info.append(link[i])
                    user_info.append(avatar[i])
                    self.friend_poor.put(user_info)
                    user_info = []
                    # print("""------------------------\n
                    # name:%s
                    # avatar:%s
                    # link_list:%s
                    # """%(name[i],avatar[i],link[i]))
                    # print("total:%d"%i)

        # print(self.friend_poor)

        # 要添加主题扩展，在这里添加一个请求
        while not self.friend_poor.empty():
            friend = self.friend_poor.get()
            self.friend_list.put(friend)
            friend[1] += "/" if not friend[1].endswith("/") else ""
            yield Request(friend[1] + "atom.xml", callback=self.post_atom_parse, meta={"friend": friend},
                          dont_filter=True, errback=self.errback_handler)
            yield Request(friend[1] + "feed/atom", callback=self.post_atom_parse, meta={"friend": friend},
                          dont_filter=True, errback=self.typecho_errback_handler)
            yield Request(friend[1] + "rss.xml", callback=self.post_rss2_parse, meta={"friend": friend},
                          dont_filter=True, errback=self.errback_handler)
            yield Request(friend[1] + "rss2.xml", callback=self.post_rss2_parse, meta={"friend": friend},
                          dont_filter=True, errback=self.errback_handler)
            yield Request(friend[1] + "feed", callback=self.post_wordpress_parse, meta={"friend": friend},
                          dont_filter=True, errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_butterfly_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_fluid_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_matery_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_sakura_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_volantis_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_nexmoe_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_Yun_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_stun_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
            yield Request(friend[1], callback=self.theme_stellar_parse, meta={"friend": friend}, dont_filter=True,
                          errback=self.errback_handler)
        # friend = ['小冰博客', 'https://example.com', 'https://zfe.space/images/headimage.png']
        # [[1,1,1],[2,3,2]]
        # 将获取到的朋友列表传递到管道
        while not self.friend_list.empty():
            friend = self.friend_list.get()
            userdata = {}
            userdata["name"] = friend[0]
            userdata["link"] = friend[1]
            userdata["img"] = friend[2]
            userdata["userdata"] = "userdata"
            yield userdata

    def post_atom_parse(self, response):
        # print("post_atom_parse---------->" + response.url)
        friend = response.meta.get("friend")
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("entry")
        if items:
            if 0 < len(items) < 5:
                l = len(items)
            else:
                l = 5
            try:
                for i in range(l):
                    post_info = {}
                    item = items[i]
                    title = item.find("title").text
                    url = item.find("link")['href']
                    date = item.find("published").text[:10]
                    updated = item.find("updated").text[:10]
                    post_info['title'] = title
                    post_info['time'] = date
                    post_info['updated'] = updated
                    post_info['link'] = url
                    post_info['name'] = friend[0]
                    post_info['img'] = friend[2]
                    post_info['rule'] = "atom"
                    yield post_info
            except:
                pass

    def post_rss2_parse(self, response):
        # print("post_rss2_parse---------->" + response.url)
        friend = response.meta.get("friend")
        soup = BeautifulSoup(response.text, "lxml")
        items = soup.find_all("item")
        if not items:
            items = soup.find_all("entry")
        if items:
            if 0 < len(items) < 5:
                l = len(items)
            else:
                l = 5
            try:
                for i in range(l):
                    post_info = {}
                    item = items[i]
                    title = item.find("title").text
                    url = item.find("link").text
                    timedata = item.find("pubdate").text.split(" ")
                    y, m, d = int(timedata[3]), list(calendar.month_abbr).index(timedata[2]), int(timedata[1])
                    date = "{:02d}-{:02d}-{:02d}".format(y, m, d)
                    post_info['title'] = title
                    post_info['time'] = date
                    post_info['updated'] = date
                    post_info['link'] = url
                    post_info['name'] = friend[0]
                    post_info['img'] = friend[2]
                    post_info['rule'] = "rss2"
                    yield post_info
            except:
                pass

    def post_wordpress_parse(self, response):
        # print("post_wordpress_parse---------->" + response.url)
        friend = response.meta.get("friend")
        sel = scrapy.Selector(text=response.text)
        title = sel.css("item title::text").extract()
        link = [comm.split("#comments")[0] for comm in sel.css("item link+comments::text").extract()]
        pubDate = sel.css("item pubDate::text").extract()
        if len(title) == len(link) == len(pubDate):
            l = len(title) if len(title) < 5 else 5
            try:
                for i in range(l):
                    m = pubDate[i].split(" ")
                    ts = time.strptime(m[3] + "-" + m[2] + "-" + m[1], "%Y-%b-%d")
                    date = time.strftime("%Y-%m-%d", ts)
                    post_info = {
                        'title': title[i],
                        'time': date,
                        'updated': date,
                        'link': link[i],
                        'name': friend[0],
                        'img': friend[2],
                        'rule': "wordpress"
                    }
                    yield post_info
            except:
                pass

    def theme_butterfly_parse(self, response):
        # print("theme_butterfly_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]
        soup = BeautifulSoup(response.text, "lxml")
        main_content = soup.find(id='recent-posts')
        if main_content and soup.find_all('time'):
            lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
            link_list = main_content.find_all('time', {"class": "post-meta-date-created"})
            if not link_list:
                link_list = main_content.find_all('time')
            for item in link_list:
                date = item.text
                date = date.replace("|", "")
                date = date.replace(" ", "")

                if lasttime < datetime.datetime.strptime(date, "%Y-%m-%d"):
                    lasttime = datetime.datetime.strptime(date, "%Y-%m-%d")
            lasttime = lasttime.strftime('%Y-%m-%d')
            last_post_list = main_content.select(".recent-post-info")

            for item in last_post_list:
                time_created = item.find('time', {"class": "post-meta-date-created"})
                if time_created:
                    pass
                else:
                    time_created = item
                if time_created.find(text=lasttime):
                    title = item.find('a').get("title")
                    a = item.find('a').get("href")
                    alinksplit = a.split("/", 1)
                    stralink = alinksplit[1].strip()
                    try:
                        post_info = {
                            'title': title,
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + stralink,
                            'name': friend[0],
                            'img': friend[2],
                            'rule': "butterfly"
                        }
                        yield post_info
                    except:
                        pass

    def theme_fluid_parse(self, response):
        # print("theme_fluid_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]
        soup = BeautifulSoup(response.text, "lxml")
        main_content = soup.find_all(id='board')
        time_excit = soup.find_all('div', {"class": "post-meta mr-3"})
        if main_content and time_excit:
            link_list = main_content[0].find_all('div', {"class": "post-meta mr-3"})
            lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
            for index, item in enumerate(link_list):
                date = item.text
                date = date.replace("|", "")
                date = date.replace(" ", "")
                date = date.replace("\n", "")
                try:
                    datetime.datetime.strptime(date, "%Y-%m-%d")
                except:
                    continue
                if lasttime < datetime.datetime.strptime(date, "%Y-%m-%d"):
                    lasttime = datetime.datetime.strptime(date, "%Y-%m-%d")
            lasttime = lasttime.strftime('%Y-%m-%d')
            # print('最新时间是', lasttime)
            last_post_list = main_content[0].find_all('div', {"class": "row mx-auto index-card"})
            for item in last_post_list:
                time_created = item.find('div', {"class": "post-meta mr-3"}).text.strip()
                if time_created == lasttime:
                    a = item.find('a')
                    stralink = a['href']
                    if link[-1] != '/':
                        link = link + '/'
                    try:
                        post_info = {
                            'title': item.find('h1', {"class": "index-header"}).text.strip(),
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + stralink,
                            'name': friend[0],
                            'img': friend[2],
                            'rule': "fluid"
                        }
                        yield post_info
                    except:
                        pass

    def theme_matery_parse(self, response):
        # print("theme_matery_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]
        soup = BeautifulSoup(response.text, "lxml")
        main_content = soup.find_all(id='articles')
        time_excit = soup.find_all('span', {"class": "publish-date"})
        try:
            if main_content and time_excit:
                link_list = main_content[0].find_all('span', {"class": "publish-date"})
                lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
                for index, item in enumerate(link_list):
                    time = item.text
                    time = time.replace("|", "")
                    time = time.replace(" ", "")
                    time = time.replace("\n", "")
                    if lasttime < datetime.datetime.strptime(time, "%Y-%m-%d"):
                        lasttime = datetime.datetime.strptime(time, "%Y-%m-%d")
                lasttime = lasttime.strftime('%Y-%m-%d')
                # print('最新时间是', lasttime)
                last_post_list = main_content[0].find_all('div', {"class": "card"})
                for item in last_post_list:
                    time_created = item.find('span', {"class": "publish-date"}).text.strip()
                    if time_created == lasttime:
                        a = item.find('a')
                        alink = a['href']
                        alinksplit = alink.split("/", 1)
                        stralink = alinksplit[1].strip()
                        if link[-1] != '/':
                            link = link + '/'
                        post_info = {
                            'title': item.find('span', {"class": "card-title"}).text.strip(),
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + stralink,
                            'name': friend[0],
                            'img': friend[2],
                            'rule': "matery"
                        }
                        yield post_info
        except:
            pass

    def theme_sakura_parse(self, response):
        # print("theme_sakura_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]
        soup = BeautifulSoup(response.text, "lxml")
        main_content = soup.find_all(id='main')
        time_excit = soup.find_all('div', {"class": "post-date"})
        if main_content and time_excit:
            link_list = main_content[0].find_all('div', {"class": "post-date"})
            lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
            for index, item in enumerate(link_list):
                date = item.text
                date = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", date).group(0)
                if lasttime < datetime.datetime.strptime(date, "%Y-%m-%d"):
                    lasttime = datetime.datetime.strptime(date, "%Y-%m-%d")
            lasttime = lasttime.strftime('%Y-%m-%d')
            # print('最新时间是', lasttime)
            last_post_list = main_content[0].find_all('article', {"class": "post"})
            for item in last_post_list:
                time_created = item.find('div', {"class": "post-date"}).text.strip()
                time_created = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", time_created).group(0)
                time_created = datetime.datetime.strptime(time_created, "%Y-%m-%d").strftime("%Y-%m-%d")
                if time_created == lasttime:
                    a = item.find('a')
                    alink = a['href']
                    alinksplit = alink.split("/", 1)
                    stralink = alinksplit[1].strip()
                    if link[-1] != '/':
                        link = link + '/'
                    link = link.split('/')[0]
                    try:
                        post_info = {
                            'title': item.find('h3').text.strip(),
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + '/' + stralink,
                            'name': friend[0],
                            'img': friend[2],
                            'rule': "sakura"
                        }
                        yield post_info
                    except:
                        pass

    def theme_volantis_parse(self, response):
        # print("theme_volantis_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]
        soup = BeautifulSoup(response.text, "lxml")
        main_content = soup.find_all('section', {"class": "post-list"})
        time_excit = soup.find_all('time')
        if main_content and time_excit:
            link_list = main_content[0].find_all('time')
            lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
            for index, item in enumerate(link_list):
                date = item.text
                date = date.replace("|", "")
                date = date.replace(" ", "")
                date = date.replace("\n", "")
                if lasttime < datetime.datetime.strptime(date, "%Y-%m-%d"):
                    lasttime = datetime.datetime.strptime(date, "%Y-%m-%d")
            lasttime = lasttime.strftime('%Y-%m-%d')
            # print('最新时间是', lasttime)
            last_post_list = main_content[0].find_all('div', {"class": "post-wrapper"})
            for item in last_post_list:
                if item.find('time'):
                    time_created = item.find('time').text.strip()
                else:
                    time_created = ''
                if time_created == lasttime:
                    a = item.find('a')
                    alink = a['href']
                    alinksplit = alink.split("/", 1)
                    stralink = alinksplit[1].strip()
                    if link[-1] != '/':
                        link = link + '/'
                    try:
                        post_info = {
                            'title': item.find('h2', {"class": "article-title"}).text.strip(),
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + stralink,
                            'name': friend[0],
                            'img': friend[2],
                            'rule': "volantis"
                        }
                        yield post_info
                    except:
                        pass

    def theme_nexmoe_parse(self, response):
        # print("theme_nexmoe_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = friend[1]

        partial_l = response.css("section.nexmoe-posts .nexmoe-post>a::attr(href)").extract()
        title = response.css("section.nexmoe-posts .nexmoe-post h1::text").extract()
        date = response.css("section.nexmoe-posts .nexmoe-post-meta a:first-child::text").extract()
        if len(partial_l) == len(title) == len(date):
            for i in range(len(partial_l)):
                partial_l[i] = partial_l[i].lstrip("/")
                r = re.split(r"[年月日]", date[i])
                y, m, d = r[0], r[1], r[2]
                date = y + "-" + m + "-" + d
                try:
                    post_info = {
                        'title': title[i],
                        'time': date,
                        'updated': date,
                        'link': link + partial_l[i],
                        'name': friend[0],
                        'img': friend[2],
                        'rule': "nexmoe"
                    }
                    yield post_info
                except:
                    pass

    def theme_Yun_parse(self, response):
        # print("theme_Yun_parse---------->" + response.url)
        friend = response.meta.get("friend")
        link = response.css("article link::attr(href)").extract()
        title = response.css("article .post-title a::text").extract()
        date = response.css("article time[itemprop*=dateCreated]::text").extract()
        updated = response.css("article time[itemprop=dateModified]::text").extract()
        if len(link) == len(title) == len(date):
            for i in range(len(link)):
                try:
                    post_info = {
                        'title': title[i],
                        'time': date[i],
                        'updated': updated[i] if updated else date[i],
                        'link': link[i],
                        'name': friend[0],
                        'img': friend[2],
                        'rule': "Yun"
                    }
                    yield post_info
                except:
                    pass

    def theme_stun_parse(self, response):
        # print("theme_stun_parse---------->" + response.url)
        friend = response.meta.get("friend")
        partial_l = response.css("article .post-title__link::attr(href)").extract()
        title = response.css("article .post-title__link::text").extract()
        date = response.css("article .post-meta .post-meta-item--createtime .post-meta-item__value::text").extract()
        updated = response.css("article .post-meta .post-meta-item--updatetime .post-meta-item__value::text").extract()
        if len(partial_l) == len(title) == len(date):
            for i in range(len(partial_l)):
                partial_l[i] = partial_l[i].lstrip("/")
                try:
                    post_info = {
                        'title': title[i],
                        'time': date[i],
                        'updated': updated[i] if updated else date[i],
                        'link': friend[1] + partial_l[i],
                        'name': friend[0],
                        'img': friend[2],
                        'rule': "stun"
                    }
                    yield post_info
                except:
                    pass

    def theme_stellar_parse(self, response):
        # print("theme_stellar_parse---------->" + response.url)
        friend = response.meta.get("friend")
        partial_l = response.css(".post-list .post-card::attr(href)").extract()
        title = response.css(".post-list .post-title::text").extract()
        date = response.css("#post-meta time::attr(datetime)").extract()
        if len(partial_l) == len(title) == len(date):
            for i in range(len(partial_l)):
                partial_l[i] = partial_l[i].lstrip("/")
                date[i] = date[i].split("T")[0]
                try:
                    post_info = {
                        'title': title[i],
                        'time': date[i],
                        'updated': date[i],
                        'link': friend[1] + partial_l[i],
                        'name': friend[0],
                        'img': friend[2],
                        'rule': "stellar"
                    }
                    yield post_info
                except:
                    pass

    def errback_handler(self, error):
        # 错误回调
        # todo error???
        # print("errback_handler---------->")
        # print(error)
        # request = error.request
        # meta = error.request.meta
        pass
    def typecho_errback_handler(self,error):
        yield Request(error.request.url,callback=self.post_atom_parse,dont_filter=True,meta=error.request.meta,errback=self.errback_handler)
