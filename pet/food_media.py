# -*- coding: utf-8 -*-
"""
food_media.py —— 尚食局的「探店图鉴」
帮小尝把荐单上的招牌菜搜出真实照片（必应图片搜索，无需任何 Key），
再配上「高德地图」官方跳转链接看商户位置。

合规说明（讲给新手听）：
- 图片来自必应图片搜索的公开缩略图（ts*.mm.bing.net），只是展示参考；
- 地图不自己画，直接跳转「高德地图官方网页」——高德是具备测绘资质的合规图商，
  我们只递上一个"店铺名+城市"的搜索链接（uri.amap.com），零 Key、零越界。

搜图的门道（踩过坑总结）：
- 必须先访问一次必应首页拿会话 Cookie，否则返回的是垃圾结果；
- 查询词用「招牌菜名」（如：羊肉泡馍），不要用"城市+店名"——
  小众店名网上没图，菜名才有海量真图。
"""
import html
import json
import re

import requests

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 模块级会话：整个应用共用一个"浏览器身份"，只热身一次
_session = None


def _get_session():
    """拿到带会话 Cookie 的 requests 会话（首次调用时先去必应首页热身）"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_HEADERS)
        try:
            _session.get("https://cn.bing.com/", timeout=8)   # 热身：拿 Cookie
        except Exception:
            pass
    return _session


def search_images(query, count=1, keyword=None, strict=False, timeout=8):
    """
    在必应图片搜索里查 query，返回最多 count 个缩略图 URL。

    keyword（如「葫芦鸡」）给定时按标题做相关性排序；
    strict=True 时更严格：整页标题没有一个含关键词的，就返回空列表——
    实测必应的垃圾结果页（袋鼠/证书/表情包）标题全都不含菜名，
    严格过滤能整页剔除，宁可"图未寻得"也不给错图。
    """
    pairs = []
    for _attempt in range(2):          # 必应偶发抽风，重试一次
        try:
            r = _get_session().get(
                "https://cn.bing.com/images/search",
                params={"q": query, "form": "HDRSC2", "first": 1},
                timeout=timeout)
            for m in re.findall(r'm="({&quot;.*?})"', r.text):
                try:
                    d = json.loads(html.unescape(m))
                    turl, title = d.get("turl", ""), d.get("t", "")
                    if turl:
                        pairs.append((html.unescape(turl), title))
                except Exception:
                    continue
            if pairs:
                break
        except Exception:
            continue
    if keyword:
        hit = [(u, t) for u, t in pairs if keyword in t]
        if strict:
            if not hit:
                return []              # 整页无相关 → 判定为垃圾页，宁可空手而归
            pairs = hit
        else:
            miss = [(u, t) for u, t in pairs if keyword not in t]
            pairs = hit + miss
    urls, seen = [], set()
    for u, _t in pairs:
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls[:count]


def fetch_thumb(url, timeout=8):
    """下载一张缩略图，返回二进制数据；失败返回 None"""
    try:
        r = _get_session().get(url, timeout=timeout)
        if r.status_code == 200 and len(r.content) > 1000:  # 太小的多半是坏图
            return r.content
    except Exception:
        pass
    return None


def amap_link(name, city):
    """
    生成高德地图官方搜索链接：点开后就是这家店在地图上的位置。
    用 urllib.parse.quote 而不是手拼，保证中文店名不出错。
    """
    from urllib.parse import quote
    keyword = quote(f"{city} {name}")
    return f"https://uri.amap.com/search?keyword={keyword}"
