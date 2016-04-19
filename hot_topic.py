# coding=utf-8

from __future__ import unicode_literals, print_function

import os
import re

from zhihu_oauth import ZhihuClient
from zhihu_oauth import Topic
from zhihu_oauth import exception


TOKEN_FILE = 'token.cache'
TOP_SIZE = 50

# Login 
client = ZhihuClient()

if os.path.isfile(TOKEN_FILE):
    client.load_token(TOKEN_FILE)
else:
    client.login_in_terminal()
    client.save_token(TOKEN_FILE)

# The topest root of topic
root_topic = client.topic(19776749)
# The array to store top hot topic
hot_topics = list()
# Whether the hot_topics is full
hot_topics_full = False
# The fewest topic in hot_topics
last_topic = {}
# The file to output
file_name = 'result'
# The number of topics has been searched
search_count = 0
# How many times output once
output_time = 500
# How many logs to researve
log_num = 100
# 程序暂定活着中断后重新开始的树的层数
continue_deep = 3
# 目前遍历的树的层数
current_deep = 0
# 程序暂定活着中断后每一层所在的位置
continue_pos = []
# 是否需要重新开始遍历
restart = False
# 记录上次程序中断时的信息的文件名
continue_filename = 'continue.log'
# 一些不存在的主题id，不知为何会出现，暂时规避掉
# unkown_topic_id = [19742819, 19619918]
# 当前主题的路径,用于出错时调试用
current_route = []

#test_topic = client.topic(20016366)
#print(str(root_topic.children))
#print(root_topic.children._extra_params)
#print((test_topic.children.next()== None))
#print((root_topic.children.next()))
#print("Topic name:", topic.name)
#print("The follow count:", topic.follower_count)
#
#for child in topic.children:
#    print("Topic name:", child.name)
#    print("The follow count:", child.follower_count)

# 初始化continue_pos
def initial_continue_pos():
    global  continue_deep
    global  continue_pos
    idx = 0
    while idx < continue_deep:
        continue_pos.append(0)
        idx += 1

def restore_continue_pos():
    global  continue_filename
    global  continue_deep
    global  continue_pos
    global  last_topic
    global  TOP_SIZE
    global  hot_topics
    fp = open(continue_filename, 'r')
    content = fp.read()
    continue_deep_str = re.search('continue deep:([0-9]*)', content, re.S).group(1)
    continue_deep = int(continue_deep_str)
    continue_pos_str = re.search('continue position:(.*?)\n', content, re.S).group(1)
    continue_pos_items = re.findall('@([0-9]*)', continue_pos_str, re.S)
    for item in continue_pos_items:
        continue_pos.append(int(item))
    continue_topics = re.findall('The topic ID:([0-9]*) -- The topic name:(.*?)'
                                 ' -- The follow number:([0-9]*)', content, re.S)
    for item in continue_topics:
        hot_topics.append({'id':int(item[0]),
                           'follow_num':int(item[2]),
                           'name':item[1]})
    if len(hot_topics) == TOP_SIZE:
        last_topic = hot_topics[TOP_SIZE - 1]

# 检查主题在队列中是否存在
def topic_exist(topic, topic_list):
    for item in topic_list:
        if item['id'] == topic.id:
            return True
    return False

# 深度优先遍历主题的子主题
def find_hot_topics(topic):
    from functools import cmp_to_key
    key = cmp_to_key(lambda x,y: cmp_follower_count(x, y))
    global search_count
    global output_time
    global hot_topics_full
    global last_topic
    global current_deep
    global TOP_SIZE
    global hot_topics
    global continue_deep
    global continue_pos
    #print('The topic ID:', topic.id, ' -- The follow number:', topic.follower_count)
    child_count = 0
    # 检查话题是否存在
    try:
        topic_children = topic.children
    except exception.GetDataErrorException as e:
        if e._reason == '话题不存在':
            return
        else:
            raise e
    for child_topic in topic_children:
        # current_deep只需要计算一次
        if child_count == 0:
            current_deep += 1
        child_count += 1
        # 如果是之前遍历过的,就直接跳过
        if restart == False and current_deep <= continue_deep and child_count <= continue_pos[current_deep-1]:
            continue
#        if unkown_topic_id.count(int(child_topic.id)) > 0:
#            continue
        current_route.append(child_topic.id)
        find_hot_topics(child_topic)
        current_route.pop()
        if current_deep <= continue_deep:
            continue_pos[current_deep-1] += 1
    # 只有当主题有孩子主题时,才需要将当前层数减1
    if child_count != 0:
        current_deep -= 1
    # 当主题没有孩子主题时
    else:
        topic_item = {'id':topic.id, 'follow_num':topic.follower_count, 'name':topic.name}
        # 判断次换题hot_topics没有时才会考虑是否加入到hot_topics中
        if topic_exist(topic, hot_topics) == False:
            search_count += 1
            #print('The child topic ID:', topic.id, ' -- The follow number:', topic.follower_count)
            if len(hot_topics) < TOP_SIZE:
                hot_topics.append(topic_item)
            else:
                # hot_topics第一次集满时，排序并设置last_topic
                if hot_topics_full == False:
                    hot_topics.sort(key=key)
                    hot_topics_full = True
                    last_topic = hot_topics[TOP_SIZE-1]
                # 此时last_topic已被赋值，比较新元素是否比last_topic的关注者多
                if topic.follower_count > last_topic['follow_num']:
                    hot_topics.append(topic_item)
                    hot_topics.sort(key=key)
                    hot_topics.pop()
                if search_count%output_time == 0:
                    output_result()

def cmp_follower_count(x, y):
    if x['follow_num'] < y['follow_num']:
        return 1
    elif x['follow_num'] > y['follow_num']:
        return -1
    else:
        return 0

def output_result():
    global hot_topics
    global file_name
    global search_count
    fp = open(file_name,'a')
    fp.write('++++++++++++++++++++++++++++++\n')
    fp.write(str(search_count) + ' topics has been search\n')
    for topic in hot_topics:
        fp.write('The topic ID:'+ str(topic['id']) + 
                 ' -- The topic name:' + topic['name'] +
                 ' -- The follow number:' + str(topic['follow_num'])+'\n')
    fp.write('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n\n')
    fp.close()

def ouput_continue(error_information):
    global  continue_pos
    global  hot_topics
    global continue_deep
    global current_route
    fp = open(continue_filename, 'w')
    fp.write('++++++++++ continue position ++++++++++\n')
    fp.write('continue deep:' + str(continue_deep))
    fp.write('\ncontinue position:')
    for item in continue_pos:
        fp.write('@' + str(item))
    fp.write('\n\n')
    fp.write('++++++++++ continue topics ++++++++++\n')
    for topic in hot_topics:
        fp.write('The topic ID:'+ str(topic['id']) +
                 ' -- The topic name:' + topic['name'] +
                 ' -- The follow number:' + str(topic['follow_num'])+'\n')
    fp.write('\n\n')
    fp.write('++++++++++ crash information ++++++++++\n')
    fp.write(str(error_information))
    fp.write('\n\n')
    fp.write('++++++++++ current route ++++++++++\n')
    for item in current_route:
        fp.write('ID(' + str(item) + ') => ')
    fp.write('End\n')
    fp.close()


if __name__ == '__main__':
    # 如果中断信息的文件存在但是解析时错误,则也需要重新计算
    if restart == False:
        if os.path.isfile(continue_filename):
            if restore_continue_pos() == False:
                initial_continue_pos()
        else:
            initial_continue_pos()
    else:
        initial_continue_pos()
    try:
        find_hot_topics(root_topic)
    except BaseException as e:
        ouput_continue(e)
    else:
        output_result()

# FIXME
# 1.当检索在主题还未到达TOP_SIZE时停止,继续的时候可能会有bug,因为会导致产出重复的项