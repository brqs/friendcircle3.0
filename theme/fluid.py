# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import datetime
from component import getWeb as request

# fluid 友链规则
def get_friendlink(friendpage_link, friend_poor):
    result = request.get_data(friendpage_link)
    soup = BeautifulSoup(result, 'html.parser')
    main_content = soup.find_all('div', {"class": "card-content"})
    for item in main_content:
        img = item.find('img').get('src')
        link = item.find('div', {"class": "link-intro"}).text
        name = item.find('div', {"class": "link-title"}).text
        if "#" in link:
            pass
        else:
            user_info = []
            user_info.append(name)
            user_info.append(link)
            user_info.append(img)
            print('----------------------')
            try:
                print('好友名%r' % name)
            except:
                print('非法用户名')
            print('头像链接%r' % img)
            print('主页链接%r' % link)
            friend_poor.append(user_info)

# 从fluid主页获取文章
def get_last_post(user_info,post_poor):
            error_sitmap = False
            link = user_info[1]
            # print('\n')
            # print('-------执行fluid主页规则----------')
            # print('执行链接：', link)
            result = request.get_data(link)
            soup = BeautifulSoup(result, 'html.parser')
            main_content = soup.find_all(id = 'board')
            time_excit = soup.find_all('div',{"class": "post-meta mr-3"})
            if main_content and time_excit:
                error_sitmap = True
                link_list = main_content[0].find_all('div', {"class": "post-meta mr-3"})
                lasttime = datetime.datetime.strptime('1970-01-01', "%Y-%m-%d")
                for index, item in enumerate(link_list):
                    time = item.text
                    time = time.replace("|","")
                    time = time.replace(" ", "")
                    time = time.replace("\n", "")
                    try: datetime.datetime.strptime(time, "%Y-%m-%d")
                    except: continue
                    if lasttime < datetime.datetime.strptime(time, "%Y-%m-%d"):
                        lasttime = datetime.datetime.strptime(time, "%Y-%m-%d")
                lasttime = lasttime.strftime('%Y-%m-%d')
                # print('最新时间是', lasttime)
                last_post_list = main_content[0].find_all('div', {"class": "row mx-auto index-card"})

                for item in last_post_list:
                    time_created = item.find('div', {"class": "post-meta mr-3"}).text.strip()

                    if time_created == lasttime:
                        error_sitmap = False
                        a = item.find('a')
                        # # print(item.find('a'))
                        stralink = a['href']
                        if link[-1] != '/':
                            link = link + '/'
                        # print(item.find('h1', {"class": "index-header"}).text.strip().encode("gbk", 'ignore').decode('gbk', 'ignore'))
                        # print(link + stralink)
                        # print("-----------获取到匹配结果----------")
                        post_info = {
                            'title': item.find('h1', {"class": "index-header"}).text.strip(),
                            'time': lasttime,
                            'updated': lasttime,
                            'link': link + stralink,
                            'name': user_info[0],
                            'img': user_info[2],
                            'rule': "fluid"
                        }
                        post_poor.append(post_info)
            else:
                error_sitmap = True
                # print('貌似不是类似fluid主题！')
            # print("-----------结束fluid主页规则----------")
            # print('\n')
            return error_sitmap
