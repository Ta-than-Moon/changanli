# -*- coding: utf-8 -*-
"""
paths.py —— 路径小管家
解决"exe 被单独拷走后找不到数据文件"的问题：
数据文件（config.json / memos.json）的查找顺序：
  1. exe（或代码）所在目录 —— 优先
  2. 用户目录 %LOCALAPPDATA%\\长安吏\\ —— 兜底
这样无论 exe 被拷到哪里、从哪里启动，都能找到配置和备忘录。
"""
import os
import sys

APP_NAME = "长安吏"


def exe_dir():
    """程序本体所在目录：打包后是 exe 旁边，开发时是代码目录"""
    if getattr(sys, "frozen", False):  # frozen = 已被 PyInstaller 打包
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def roaming_dir():
    """用户数据目录（Windows 上类似 C:\\Users\\你\\AppData\\Local\\长安吏）"""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def data_file(name):
    """
    找一个数据文件的"最终住址"：
    - exe 旁边有 → 用它（方便整个文件夹拷给别人）
    - 否则用户目录里有 → 用它（exe 被单独拷走时的兜底）
    - 都没有 → 返回 exe 旁边的路径（首次运行时会在那里新建）
    """
    local = os.path.join(exe_dir(), name)
    if os.path.exists(local):
        return local
    backup = os.path.join(roaming_dir(), name)
    if os.path.exists(backup):
        return backup
    return local
