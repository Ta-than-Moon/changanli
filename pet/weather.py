# -*- coding: utf-8 -*-
"""
weather.py —— 天气探子
三重保险查地名：
  ① 内置"大唐舆地图"（全国省份/省会/热门城市经纬度表，离线秒查）
  ② Open-Meteo 地理编码接口（国外库，补充小众地名）
  ③ OpenStreetMap Nominatim 接口（中文地名收录更全，最后兜底）
天气数据来自 Open-Meteo 免费接口（不需要注册、不需要 Key）。
"""
import requests

# ---------- 大唐舆地图：地名 → (纬度, 经度, 显示名) ----------
CITY_DB = {
    # 四大直辖市
    "北京": (39.90, 116.41, "北京"), "上海": (31.23, 121.47, "上海"),
    "天津": (39.13, 117.20, "天津"), "重庆": (29.56, 106.55, "重庆"),
    # 省会 / 首府 / 特别行政区
    "石家庄": (38.04, 114.51, "石家庄"), "太原": (37.87, 112.55, "太原"),
    "呼和浩特": (40.84, 111.75, "呼和浩特"), "沈阳": (41.80, 123.43, "沈阳"),
    "长春": (43.90, 125.32, "长春"), "哈尔滨": (45.80, 126.53, "哈尔滨"),
    "南京": (32.06, 118.80, "南京"), "杭州": (30.27, 120.16, "杭州"),
    "合肥": (31.82, 117.23, "合肥"), "福州": (26.07, 119.30, "福州"),
    "南昌": (28.68, 115.86, "南昌"), "济南": (36.65, 117.12, "济南"),
    "郑州": (34.75, 113.63, "郑州"), "武汉": (30.59, 114.31, "武汉"),
    "长沙": (28.23, 112.94, "长沙"), "广州": (23.13, 113.26, "广州"),
    "南宁": (22.82, 108.37, "南宁"), "海口": (20.02, 110.35, "海口"),
    "成都": (30.57, 104.07, "成都"), "贵阳": (26.65, 106.63, "贵阳"),
    "昆明": (24.88, 102.83, "昆明"), "拉萨": (29.65, 91.14, "拉萨"),
    "西安": (34.34, 108.94, "西安"), "兰州": (36.06, 103.83, "兰州"),
    "西宁": (36.62, 101.78, "西宁"), "银川": (38.49, 106.23, "银川"),
    "乌鲁木齐": (43.83, 87.62, "乌鲁木齐"),
    "台北": (25.03, 121.57, "中国台北"),
    "香港": (22.32, 114.17, "中国香港"), "澳门": (22.20, 113.55, "中国澳门"),
    # 热门旅游城市
    "深圳": (22.54, 114.06, "深圳"), "苏州": (31.30, 120.58, "苏州"),
    "厦门": (24.48, 118.09, "厦门"), "青岛": (36.07, 120.38, "青岛"),
    "大连": (38.91, 121.61, "大连"), "洛阳": (34.62, 112.45, "洛阳"),
    "开封": (34.80, 114.31, "开封"), "桂林": (25.23, 110.30, "桂林"),
    "大理": (25.59, 100.23, "大理"), "丽江": (26.86, 100.23, "丽江"),
    "敦煌": (40.14, 94.66, "敦煌"), "三亚": (18.25, 109.51, "三亚"),
    "珠海": (22.27, 113.58, "珠海"), "无锡": (31.49, 120.31, "无锡"),
    "宁波": (29.87, 121.55, "宁波"), "淄博": (36.81, 118.05, "淄博"),
}

# 省份 → 省会（用户输入省份时，定位到省会并在显示名中说明）
_PROVINCE_CAPITALS = {
    "河北": "石家庄", "山西": "太原", "内蒙古": "呼和浩特", "辽宁": "沈阳",
    "吉林": "长春", "黑龙江": "哈尔滨", "江苏": "南京", "浙江": "杭州",
    "安徽": "合肥", "福建": "福州", "江西": "南昌", "山东": "济南",
    "河南": "郑州", "湖北": "武汉", "湖南": "长沙", "广东": "广州",
    "广西": "南宁", "海南": "海口", "四川": "成都", "贵州": "贵阳",
    "云南": "昆明", "西藏": "拉萨", "陕西": "西安", "甘肃": "兰州",
    "青海": "西宁", "宁夏": "银川", "新疆": "乌鲁木齐", "台湾": "台北",
}


def _geocode(city):
    """把地名变成经纬度，返回 (纬度, 经度, 显示名)。三重保险依次尝试。"""
    name = city.strip()

    # 保险①：内置舆地图（先原样查，再去掉"市/省/自治区"后缀查，再按省份查省会）
    for candidate in (name, name.removesuffix("市"), name.removesuffix("省"), name.removesuffix("自治区")):
        if candidate in CITY_DB:
            return CITY_DB[candidate]
        if candidate in _PROVINCE_CAPITALS:
            capital = _PROVINCE_CAPITALS[candidate]
            lat, lon, _ = CITY_DB[capital]
            return lat, lon, f"{candidate}（以省会{capital}为例）"

    # 保险②：Open-Meteo 地理编码
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 1, "language": "zh"},
            timeout=10,
        )
        results = resp.json().get("results")
        if results:
            r = results[0]
            return r["latitude"], r["longitude"], r.get("name", name)
    except Exception:
        pass

    # 保险③：OpenStreetMap Nominatim（中文地名更全）
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": name, "format": "json", "limit": 1, "accept-language": "zh"},
            headers={"User-Agent": "changanli-desktop-pet/1.0"},
            timeout=10,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"]), name
    except Exception:
        pass

    raise ValueError(f"翻遍舆地图也没找到「{name}」，换个写法试试？（如：西安、湖南、大理）")


# 天气代码 → 中文描述（Open-Meteo 的 WMO 标准代码）
WEATHER_TEXT = {
    0: "晴空万里", 1: "大致晴朗", 2: "云影疏疏", 3: "阴云密布",
    45: "雾气朦胧", 48: "雾凇凝霜",
    51: "毛毛微雨", 53: "细雨绵绵", 55: "密雨如织",
    61: "小雨淅沥", 63: "中雨潇潇", 65: "大雨滂沱",
    71: "小雪簌簌", 73: "中雪纷飞", 75: "大雪漫天",
    80: "阵雨阵阵", 81: "骤雨急落", 82: "暴雨倾盆",
    95: "雷公发威", 96: "雷雨挟雹", 99: "雷霆冰雹",
}


def get_weather(city):
    """
    获取城市当前天气 + 今日温度范围。
    返回一段中文描述，例如："西安｜晴空万里｜当前 18℃（今日 12~24℃）｜风速 5km/h｜湿度 40%"
    """
    lat, lon, name = _geocode(city)
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
        },
        timeout=15,
    )
    data = resp.json()
    cur = data["current"]
    day = data["daily"]
    code = cur.get("weather_code", 0)
    text = WEATHER_TEXT.get(code, "天象莫测")
    return (
        f"{name}｜{text}｜当前 {round(cur['temperature_2m'])}℃"
        f"（今日 {round(day['temperature_2m_min'][0])}~{round(day['temperature_2m_max'][0])}℃）"
        f"｜风速 {round(cur['wind_speed_10m'])}km/h｜湿度 {cur['relative_humidity_2m']}%"
    )
