import platform
import queue
import json
import os
import threading
from .plugin_class import MsgPluginTemplate
from py_process_hooker.winapi import GetWeChatVersion
from .offset import CALL_OFFSET


if "64" in platform.architecture()[0]:
    from .sendmsg64 import SendMsg
    from .hooklog64 import HookLog
    from .anti_revoke64 import AntiRevoke
    from .hookmsg64 import HookMsg
    from .get_contact_list import GetContacts
else:
    from .sendmsg32 import SendMsg
    from .hooklog32 import HookLog
    from .anti_revoke32 import AntiRevoke
    from .hookmsg32 import HookMsg


__version__ = "1.3.0"

__all__ = [
    "SendMsg",
    "HookLog",
    "HookMsg",
    "AntiRevoke",
    "GetContacts",
    "get_on_startup"
]


def get_on_startup(msg_plugins=[], other_plugins=[]):
    '''注入后立即执行的函数'''
    msg_queue = queue.Queue()
    
    def msg_callback(json_msg_str:str):
        '''消息回调函数'''
        msg_queue.put(json_msg_str)

    def msg_thread_func(_msg_queue:queue.Queue, pwd:str):
        # 初始化消息插件类
        plugins_ojb = []
        for plugin_class in msg_plugins:
            if not issubclass(plugin_class, MsgPluginTemplate):
                continue
            plugin_obj = plugin_class(pwd=pwd)
            print(f"插件({plugin_obj.name})初始化完成!")
            plugins_ojb.append(plugin_obj)
        # 消费队列内的消息
        while True:
            json_msg_str = _msg_queue.get()
            if not json_msg_str:
                continue
            msg_dict = json.loads(json_msg_str)
            for obj in plugins_ojb:
                obj.deal_msg(msg_dict)

    def _on_startup(main_file_path=None):
        # 增加版本检测
        wx_version = GetWeChatVersion()
        if wx_version not in CALL_OFFSET:
            raise Exception(f"当前微信的版本({wx_version})不在支持的列表，目前支持的版本列表: {list(CALL_OFFSET.keys())}")

        pwd_path = os.path.dirname(main_file_path)
        # hook消息
        hooker = HookMsg(msg_callback)
        hooker.hook() 
        # 防撤回
        ar = AntiRevoke()
        ar.hook()
        # 处理消息队列
        msg_thread = threading.Thread(target=msg_thread_func, args=(msg_queue, pwd_path))
        msg_thread.start()
        # 启动其他类型插件
        for other_plugin in other_plugins:
            other_plugin().start()

    return _on_startup







