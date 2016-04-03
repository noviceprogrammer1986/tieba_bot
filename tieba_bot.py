#
# 一个简单的贴吧自动回帖机器人，只要被@就会自动回复
#
# 使用seleniumrequests库，使requests共享selenium模拟登陆后的cookies
from seleniumrequests import Chrome
from bs4 import BeautifulSoup
import time
import json
import re

driver = Chrome(executable_path='C:/Program Files (x86)/Google/Chrome/Application/chromedriver.exe')

# 登陆
def login():
    driver.get('https://www.baidu.com')
    driver.find_element_by_xpath('//div[@id="u1"]/a[@name="tj_login"]').click()
    time.sleep(1)
    driver.find_element_by_xpath('//input[@id="TANGRAM__PSP_8__userName"]').send_keys('百度账号')
    driver.find_element_by_xpath('//input[@id="TANGRAM__PSP_8__password"]').send_keys('密码')
    driver.find_element_by_xpath('//input[@id="TANGRAM__PSP_8__submit"]').submit()

# replied.txt存储已回复的帖id
def get_replied():
    f = open('replied.txt', 'r')
    text = f.read()
    f.close()
    replied = text.split('\n')[:-1]
    return replied

# 更新已回复的帖id
def update(data):
    f = open('replied.txt', 'a')
    for i in data:
        f.write(i+'\n')
    f.close()

# 需要回复的贴
def to_do_list(replied):
    li = []
    response = driver.request('GET', 'http://tieba.baidu.com/i/671474965/atme')
    soup = BeautifulSoup(response.content, 'html.parser')
    users = soup.find_all('div', {'class': 'atme_user'})
    for user in users:
        a = user.find('a')
        url = a['href']
        pid = url.split('#')[1]
        who = a.get_text()[:-1]
        if pid not in replied:
            li.append({'url': url, 'pid': pid, 'who': who})
    return li

# “@提到我的”超过5层的楼中楼，点击回复链接不能直接找到需要回复的楼层
#  参照“回复我的”的回复链接的结构，生成新的链接进行定位
def get_floor(soup, pid):
    post_id = None
    post_no = None
    posts = soup.find_all('div', {'class': 'l_post l_post_bright j_l_post clearfix '})
    for post in posts:
        di = json.loads(post['data-field'])
        if di['content']['comment_num']>5:
            tid = di['content']['thread_id']
            p_id = di['content']['post_id']
            new_url = 'http://tieba.baidu.com/p/%s?pid=%s&cid=%s#%s' % (tid, p_id, pid, pid)
            r = driver.request('GET', new_url)
            if BeautifulSoup(r.content, 'html.parser').find('a', {'name': '%s' % pid}):
                post_id = p_id
                post_no = di['content']['post_no']
                break
    return {'post_id': post_id, 'post_no': post_no}

# 对每一条@进行回复
def reply(someone):
    response = driver.request('GET', 'http://tieba.baidu.com'+someone['url'])
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.head.find('script', {'type': None}).text
    tbs = re.search('"tbs": "[\d\w]+"', text).group()[8:-1]
    kw = soup.find('div', {'class': 'search_form'}).find('input')['value']
    di = json.loads(soup.find('div', {'class': 'l_post l_post_bright j_l_post clearfix '})['data-field'])
    fid = di['content']['forum_id']
    tid = di['content']['thread_id']
    # 定位@贴所在楼层
    test = soup.find('a', {'name': '%s' % someone['pid']})
    # 主楼层和5层内的楼中楼可以直接定位到
    if test:
        di = json.loads(test.find_parent()['data-field'])
        post_id = di['content']['post_id']
        post_no = di['content']['post_no']
    # 深层定位
    else:
        floor = get_floor(soup, someone['pid'])
        post_id = floor['post_id']
        post_no = floor['post_no']
    # 回帖需要提交的数据
    form = {
        'ie': 'utf-8',
        'kw': kw,
        'fid': str(fid),
        'tid': str(tid),
        'floor_num': str(post_no),
        'quote_id': str(post_id),
        'rich_text': '1',
        'tbs': tbs,
        # 回帖的内容可以自定义，可以单独写个模块，进行语义分析等等，使机器人更智能
        'content': '@%s 你好' % someone['who'],
        'lp_type': '0',
        'lp_sub_type': '0',
        'new_vcode': '1',
        'tag': '11',
        'repostid': str(post_id),
        'anonymous': '0'}
    driver.request('POST', 'http://tieba.baidu.com/f/commit/post/add', data=form)

# 主程序
login()
while True:
    temp = set()
    replied = get_replied()
    to_reply_list = to_do_list(replied)
    for someone in to_reply_list:
        reply(someone)
        temp.add(someone['pid'])
    update(temp)
    time.sleep(10)
