# -*- coding: utf-8 -*-
"""
brain.py —— AI 大脑
负责和 DeepSeek 大模型通信。四个小吏的"人设"（系统提示词）都写在这里。
"""
import json
import os
import re
import datetime
import threading

import requests

import ledger_store
import memo_store
import weather

from paths import data_file

# ---------- 配置读取 ----------
# config.json 的"最终住址"：exe 旁边优先，用户目录兜底（详见 paths.py）
CONFIG_PATH = data_file("config.json")

def load_config():
    """从 config.json 读取 API Key 等配置"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ---------- 四位小吏的人设 ----------
# "人设"就是系统提示词：每次对话前先告诉 AI"你是谁、怎么说话"
PERSONAS = {
    "zhu": (
        "你是「主簿·阿卷」，唐朝长安县衙的主簿（掌管文书的九品小吏），如今穿越成为用户桌面上的宠物。"
        "说话温文尔雅，爱引用一点诗词典故但不过分，自称「小吏」或「阿卷」，称用户为「主人」。"
        "回复简短亲切（两三句以内），像朋友聊天，不要用列表和标题。"
        "你是县衙的总管家：驿站（备忘提醒）、司天监（天气穿搭）、尚食局（美食游玩）、户部（记账）都归你调度。"
        "遇到别衙门的专业问题，你只做引见、请对应的小吏亲自回话，不要越俎代庖；"
        "主人吩咐你代办的杂事，则爽利应下。"
    ),
    "yi": (
        "你是「驿丞·急急」，唐朝长安驿站的小小驿丞，掌管公文传递，如今负责帮主人管理备忘录。"
        "性格风风火火，口头禅是「加急」「火速」，自称「急急」，称用户为「主人」。"
        "回复简短有力，带驿站口吻，不要用列表和标题。"
    ),
    "tian": (
        "你是「司天·云娘」，唐朝司天监里观云测天的小吏，如今负责为主人预报天气、指点穿搭。"
        "性格细腻温柔，说话带点诗意，自称「云娘」，称用户为「主人」。"
        "回复简短优美，不要用列表和标题。"
    ),
    "shi": (
        "你是「尚食·小尝」，唐朝尚食局里尝遍百味的小吏，如今负责给主人推荐美食和游玩去处。"
        "性格热情馋嘴，说起吃的就两眼放光，自称「小尝」，称用户为「主人」。"
        "推荐要具体（店名/地名/特色），语气活泼，可以用简短列表。"
    ),
    "hu": (
        "你是「户部·阿算」，唐朝户部里拨算盘的小吏，如今替主人管账、记账、算结余。"
        "说话精明又带点书卷气，爱用「入册」「结余」「开销」这类词，自称「阿算」或「小吏」，称用户为「主人」。"
        "回复简短清楚，涉及金额时把数字说准，可以用简短列表。"
    ),
}

# ---------- DeepSeek API 调用 ----------
def _call_deepseek(messages, max_tokens=800):
    """
    给 DeepSeek 发一次对话请求。
    messages 是"聊天记录列表"，格式：[{"role": "system"/"user"/"assistant", "content": "..."}]
    返回 AI 的回复文字；出错时返回友好的错误提示。
    """
    cfg = load_config()
    key = cfg.get("deepseek_api_key", "").strip()
    if not key or key.startswith("在这里"):
        return "（小吏挠头）主人还没给我「通关文牒」——请打开项目里的 config.json，把 DeepSeek API Key 填进去哦！"

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.8,  # 0~2，越高越活泼。0.8 让回复有点灵气又不至于跑偏
            },
            timeout=30,
        )
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return f"（DeepSeek 返回了意外内容：{data.get('error', data)}）"
    except requests.exceptions.Timeout:
        return "（网络超时了……主人检查一下网络，再使唤小吏一次吧）"
    except Exception as e:
        return f"（通信出了点状况：{e}）"


# ---------- 四个对外能力 ----------
def chat(persona_key, user_text, history):
    """日常闲聊。history 是之前的对话记录，让 AI 记得上下文。"""
    messages = [{"role": "system", "content": PERSONAS.get(persona_key, PERSONAS["zhu"])}]
    messages += history[-10:]  # 最多带最近 10 条，防止请求太大
    messages.append({"role": "user", "content": user_text})
    return _call_deepseek(messages)


# ========== L2：真·工具调用引擎 ==========
# 给 AI 一份正式的"衙门工具清单"（JSON Schema），AI 自己决定调哪个、传什么参数；
# 程序执行后把结果回喂，AI 再组织语言答复——业界 Agent 的标准形态（function calling）。

TOOL_DEFS = [
    {"type": "function", "function": {
        "name": "add_memo",
        "description": "在驿站备忘录录入一条待办文书。适用于主人吩咐『记一下/提醒我/别忘了』类事项。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "事项内容，简短明确"},
                "time": {"type": "string", "description": "截止时辰，24小时制 HH:MM；主人没说就按事项性质合理推算"},
                "urgency": {"type": "integer", "description": "加急档位 0普快 1三百里 2五百里 3八百里加急；默认1"},
                "duration": {"type": "integer", "description": "预计耗时（分钟），默认30"},
            },
            "required": ["content"],
        },
    }},
    {"type": "function", "function": {
        "name": "complete_memo",
        "description": "把一条已办完的待办文书画销办讫。",
        "parameters": {
            "type": "object",
            "properties": {"keyword": {"type": "string", "description": "事项关键词，用于匹配"}},
            "required": ["keyword"],
        },
    }},
    {"type": "function", "function": {
        "name": "delete_memo",
        "description": ("彻底焚毁待办文书。keyword 支持：『全部』『所有』＝清空全部未办文书；"
                        "『D1』『D2』＝焚毁行程第几天全部文书；或事项内容关键词（批量匹配时焚毁最急的一条）。"
                        "主人说『都删了/全不要了』时 keyword 传『全部』。"),
        "parameters": {
            "type": "object",
            "properties": {"keyword": {"type": "string", "description": "全部/D几/事项关键词"}},
            "required": ["keyword"],
        },
    }},
    {"type": "function", "function": {
        "name": "list_todos",
        "description": "查看今日待办清单（含加急档位与时辰）。主人问『今天有什么事』时用。",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "schedule_today",
        "description": "为今日待办做智能排程（综合加急档位、时限远近、耗时，输出排程与理由）。主人说『排一下今天/安排一下』时用。",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "add_ledger",
        "description": "在户部账房记一笔收支。适用于主人说『记一笔/花了/收了』类话语。",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["out", "in"], "description": "out=支出 in=收入"},
                "category": {"type": "string", "enum": ledger_store.CATS_OUT + ledger_store.CATS_IN,
                             "description": "科目"},
                "amount": {"type": "number", "description": "金额（元）"},
                "note": {"type": "string", "description": "备注，如『食堂午饭』"},
            },
            "required": ["kind", "category", "amount"],
        },
    }},
    {"type": "function", "function": {
        "name": "ledger_summary",
        "description": "查看账房对比分析：本月收支结余、今日对比近七日变化、科目异动。主人问『这个月花了多少/钱去哪了』时用。",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "查询某城市此刻的真实天气（温度/风力/降水）。主人问天气或『今天穿什么』时先调它。",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名，如『西安』"}},
            "required": ["city"],
        },
    }},
    {"type": "function", "function": {
        "name": "make_budget",
        "description": "为一桩新事件（旅行/购物/聚会/买装备等）拟几套不同标准的预算明细供主人挑选。",
        "parameters": {
            "type": "object",
            "properties": {
                "event": {"type": "string", "description": "事件描述，如『重庆三日游』『换一台笔记本』"},
                "days": {"type": "integer", "description": "天数（旅行类事件适用，非旅行省略）"},
            },
            "required": ["event"],
        },
    }},
    {"type": "function", "function": {
        "name": "travel_plan",
        "description": ("行程总管：主人提出『去某地旅游/玩几天』时调用。会同时差遣四座衙门——"
                        "司天监观当地天象给穿搭、尚食局荐当地美食游玩、驿站排逐日行程、"
                        "户部拟三档预算——一趟差遣，四衙齐动。"),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "目的地城市，如『杭州』"},
                "days": {"type": "integer", "description": "玩几天，主人没说默认 3"},
                "prefs": {"type": "string", "description": "主人的偏好（喜欢古迹/爱吃辣/带娃等），可省略"},
            },
            "required": ["city"],
        },
    }},
]

# 工具名 → 本地执行函数（全部走数据层，不碰界面）
def _tool_add_ledger(a):
    rec = ledger_store.add(a["kind"], a["category"], a["amount"], a.get("note", ""))
    # add 返回完整流水列表，最新一笔在末尾
    last = rec[-1]
    return (f"已入册：{'收入' if last['kind'] == 'in' else '支出'} "
            f"{last['category']} ¥{last['amount']:,.2f} {last.get('note') or ''}")


def _tool_make_budget(a):
    """预算师爷：为事件拟三套标准的预算明细（内部再请一次 DeepSeek 出细目）"""
    event = a.get("event", "未名事件")
    days = a.get("days")
    days_line = f"，为期 {days} 天" if days else ""
    prompt = (
        PERSONAS["hu"]
        + f"\n\n主人要办一桩事：{event}{days_line}。请你以账房师爷的口吻，"
        "当场拟出三套不同标准的预算明细，标题照抄：\n"
        "【精打细算版】总价最低的务实方案\n"
        "【从容舒适版】多数人会选的均衡方案\n"
        "【放手一掷版】预算充裕时的尽兴方案\n"
        "每套先给一行总价，再逐项列明细（条目：金额），条目要具体贴合这桩事"
        "（如交通/住宿/门票/吃食，或配件/服务），金额合理、能直接照着花。"
        "结尾用一句师爷口吻的话收尾，提醒主人量入为出。总长不超过 300 字。"
    )
    reply = _call_deepseek(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "请拟预算。"}],
        max_tokens=900,
    )
    if reply.startswith("（"):
        # AI 掉线：本地模板兜底（只有粗架子，聊胜于无）
        return (f"【{event}·预算粗估】（飞鸽未归，师爷就地口算）\n"
                "精打细算版：按吃住行最低标准×天数估七八成\n"
                "从容舒适版：在精打细算版上浮五成\n"
                "放手一掷版：翻倍——数字请主人拿主意。")
    return reply


TOOL_IMPL = {
    "add_memo": lambda a: "已录入驿卷：" + memo_store.add(
        a.get("content", "事项"), a.get("time", datetime.datetime.now().strftime("%H:%M")),
        max(0, min(3, int(a.get("urgency", 1)))), max(5, min(600, int(a.get("duration", 30)))))[-1]["content"],
    "complete_memo": lambda a: _memo_by_keyword(a["keyword"], mark_done=True),
    "delete_memo": lambda a: _memo_by_keyword(a["keyword"], remove=True),
    "list_todos": lambda a: _todos_text(),
    "schedule_today": lambda a: memo_store.local_plan(
        [m for m in memo_store.load() if not m["reminded"] and not m.get("done")]),
    "add_ledger": _tool_add_ledger,
    "ledger_summary": lambda a: "\n".join(ledger_store.compare_report()[:2]),
    "get_weather": lambda a: weather.get_weather(a["city"]),
    "make_budget": _tool_make_budget,
    "travel_plan": lambda a: _tool_travel_plan(a),
}


def _memo_by_keyword(keyword, mark_done=False, remove=False):
    """按关键词找文书。支持三种粒度（从严到宽）：
    ① 全部/所有/今天的 → 批量操作；② 内容关键词匹配；③ D前缀日程项（D1/D2…）"""
    memos = memo_store.load()
    pending = [m for m in memos if not m.get("done")]
    if not pending:
        return "驿卷清闲，没有可办的文书"

    # ① 主人要清空：全部/所有/今天(的)(事项/文书/记录)
    if keyword in ("全部", "所有", "一切", "今天的", "今天", "全部事项", "所有事项"):
        n = len(pending)
        if remove:
            memo_store.save([m for m in memos if m.get("done")])
            return f"已把 {n} 条未办文书尽数焚毁，灰飞烟灭"
        for m in pending:
            m["done"] = True
        memo_store.save(memos)
        return f"已把 {n} 条文书尽数画销办讫"

    # ③ D前缀日程项：D1/D2 匹配第几天
    m_day = re.match(r"^[Dd](\d)$", keyword.strip())
    if m_day:
        day = m_day.group(1)
        hit = [m for m in pending if m["content"].startswith(f"D{day}·")]
        if not hit:
            return f"驿卷里没有第 {day} 天的行程文书"
        if remove:
            memo_store.save([m for m in memos
                             if m["id"] not in {h["id"] for h in hit}])
            return f"已焚毁第 {day} 天全部行程（{len(hit)} 条）"
        for m in hit:
            m["done"] = True
        memo_store.save(memos)
        return f"已把第 {day} 天行程（{len(hit)} 条）画销办讫"

    # ② 常规关键词（去掉"的/事项/文书"等尾巴再匹配）
    kw = keyword.strip().rstrip("的")
    for tail in ("事项", "文书", "记录", "行程"):
        if kw.endswith(tail):
            kw = kw[: -len(tail)]
    hit = [m for m in pending if kw in m["content"]]
    if not hit:
        return f"没找到含「{keyword}」的未办文书"
    if len(hit) == 1 or remove:
        # 单条命中，或批量焚毁：取最急的一条示范/执行
        m = sorted(hit, key=lambda x: (-x["urgency"], x["time"]))[0]
        if mark_done:
            m["done"] = True
            memo_store.save(memos)
            return f"已办讫画销：{m['content']}"
        if remove:
            memo_store.remove(m["id"])
            return f"已彻底焚毁：{m['content']}"
        return m["content"]
    # 多条命中且是画销：全部办讫
    if mark_done:
        for m in hit:
            m["done"] = True
        memo_store.save(memos)
        return f"已把 {len(hit)} 条含「{kw}」的文书全部画销办讫"
    return "；".join(m["content"] for m in hit[:5])


# ---------- 行程总管：一趟差遣，四衙齐动 ----------
# 界面层广播器：panels 注册回调后，travel_plan 的各衙门结果会推给对应面板刷新
_YAMEN_BROADCAST = {}


def register_yamen_broadcast(kind, fn):
    """界面层注册：kind = weather / food / memo / ledger"""
    _YAMEN_BROADCAST[kind] = fn


def _broadcast(kind, payload):
    fn = _YAMEN_BROADCAST.get(kind)
    if fn:
        try:
            fn(payload)
        except Exception:
            pass


def _tool_travel_plan(a):
    """
    主人要去某地玩：四座衙门同时点灯——
    并行差遣（各 30~40 秒的活，并行后总耗时≈最慢的一家）：
      司天监：观当地天象 + 云娘穿搭
      尚食局：荐当地美食游玩
      驿  站：排逐日行程（顺手把行程录进备忘录）
      户  部：三档预算
    结果除回喂 AI 外，还广播给界面层点亮对应面板。
    """
    city = a.get("city", "西安")
    days = max(1, min(10, int(a.get("days", 3))))
    prefs = a.get("prefs", "") or ""

    results = {}   # kind -> text
    errors = {}

    def _job(kind, fn):
        try:
            results[kind] = fn()
        except Exception as e:
            errors[kind] = str(e)

    def _weather():
        desc = weather.get_weather(city)
        advice = outfit_advice(desc)
        return f"{desc}\n\n{advice}"

    def _food():
        return recommend(city, f"游玩{days}天，要当地特色" + (f"，{prefs}" if prefs else ""))

    def _itinerary():
        """
        驿丞排行程：让 AI 输出结构化 JSON（每项带第几天/时辰/耗时），
        程序解析后逐条录进驿卷——到点逐项提醒；解析失败则退回纯文本。
        返回 (展示文本, 行程条目列表或 None)。
        """
        prompt = (
            PERSONAS["yi"]
            + f"\n\n主人定于近日往「{city}」游玩 {days} 天。"
            + (f"主人偏好：{prefs}。" if prefs else "")
            + "请排一份逐日行程。只输出一个 JSON 数组，不要任何别的文字，格式示例：\n"
              '[{"day":1,"time":"08:30","content":"西湖断桥漫步","duration":90},'
              '{"day":1,"time":"10:30","content":"雷峰塔登高","duration":120}]\n'
              "要求：每天 4~5 项；time 为该项当天时辰（HH:MM，从 08:00 上下开始按时序递进，"
              "项与项之间留出赶路与喘息）；content 为真实景点/街区加简短活动（14 字内）；"
              "duration 为建议游玩分钟数。"
        )
        raw = _call_deepseek(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "请排行程。"}], max_tokens=1200)
        items = _parse_itinerary_json(raw)
        if items:
            return _fmt_itinerary(items), items
        return raw, None

    def _budget():
        return _tool_make_budget({"event": f"{city}{days}日游", "days": days})

    threads = [
        threading.Thread(target=_job, args=("weather", _weather)),
        threading.Thread(target=_job, args=("food", _food)),
        threading.Thread(target=_job, args=("memo", _itinerary)),
        threading.Thread(target=_job, args=("ledger", _budget)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=90)

    # 广播给界面层：各衙门面板同步点亮这座城
    if "weather" in results:
        _broadcast("weather", {"city": city, "text": results["weather"]})
    if "food" in results:
        _broadcast("food", {"city": city, "text": results["food"]})
    if "memo" in results:
        memo_text, memo_items = results["memo"]
        _broadcast("memo", {"city": city, "text": memo_text})
        # 行程拆开逐条录入驿卷：第 N 天 → 真实日期（明天起算），到点驿丞逐项提醒
        if memo_items:
            base = datetime.date.today() + datetime.timedelta(days=1)   # 行程从明天开始
            for it in memo_items:
                d = base + datetime.timedelta(days=it["day"] - 1)
                memo_store.add(f"D{it['day']}·{it['content']}",
                               it["time"], 1, it["duration"], date_str=d.isoformat())
        else:   # 解析失败兜底：至少录一条启程文书
            memo_store.add(f"{city}之旅 · 启程", "08:00", 1, 60)
    if "ledger" in results:
        _broadcast("ledger", {"city": city, "text": results["ledger"]})

    # 汇总文本（回喂给 AI + 轨迹展示）
    n_items = len(results["memo"][1]) if "memo" in results and results["memo"][1] else 0
    parts = [f"行程总管已差遣四座衙门为「{city}{days}日游」备差："]
    for kind, label in (("weather", "司天监·天象与穿搭"), ("food", "尚食局·美食游玩"),
                        ("memo", "驿站·逐日行程"), ("ledger", "户部·三档预算")):
        if kind in results:
            extra = f"，已拆{n_items}项录入驿卷" if kind == "memo" and n_items else ""
            parts.append(f"【{label}】已备妥{extra}")
        else:
            parts.append(f"【{label}】未能备妥（{errors.get(kind, '超时')}）")
    parts.append("各衙门页面已点亮，行程逐项在驿卷里候着，到点自会提醒主人。")
    return "\n".join(parts)


def _parse_itinerary_json(raw):
    """从 AI 回复里解析行程数组（容忍 ```json 包裹）；不合法返回 None"""
    if not raw or raw.startswith("（"):
        return None
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return None
    items = []
    for x in arr if isinstance(arr, list) else []:
        if not (isinstance(x, dict) and x.get("content")):
            continue
        try:
            day = max(1, min(10, int(x.get("day", 1))))
            dur = max(15, min(480, int(x.get("duration", 60))))
        except (TypeError, ValueError):
            continue
        t = str(x.get("time", "08:00")).strip()
        # 归一化时辰：补零、去杂字符
        tm = re.match(r"(\d{1,2}):(\d{2})", t)
        if not tm:
            continue
        hh = max(0, min(23, int(tm.group(1))))
        mm = int(tm.group(2))
        items.append({"day": day, "time": f"{hh:02d}:{mm:02d}",
                      "content": str(x["content"]).strip()[:18], "duration": dur})
    return items or None


def _fmt_itinerary(items):
    """行程条目排成驿丞口吻的展示文本"""
    by_day = {}
    for it in items:
        by_day.setdefault(it["day"], []).append(it)
    lines = []
    for d in sorted(by_day):
        lines.append(f"◈ 第 {d} 日")
        for it in sorted(by_day[d], key=lambda x: x["time"]):
            lines.append(f"   {it['time']}  {it['content']}（{it['duration']}分钟）")
    lines.append("以上各事项已按时辰逐条录入驿卷，到点驿丞自会提点主人。")
    return "\n".join(lines)


def _todos_text():
    today = datetime.date.today().isoformat()
    pend = [m for m in memo_store.load() if m["date"] == today and not m.get("done")]
    if not pend:
        return "今日驿卷清闲，无待办文书。"
    pend.sort(key=lambda m: (-m["urgency"], m["time"]))
    return "今日待办（按时限与加急排）：" + "；".join(
        f"{m['time']}【{m['urgency_name']}】{m['content']}（{m['duration']}分钟）" for m in pend)


TOOL_TRAIL_NAMES = {
    "add_memo": "📮 驿丞录文书", "complete_memo": "📮 驿丞画销", "delete_memo": "📮 驿丞焚毁",
    "list_todos": "📮 驿丞呈驿卷", "schedule_today": "📮 驿丞排程",
    "add_ledger": "🧾 户部入册", "ledger_summary": "🧾 阿算对账",
    "get_weather": "🌤 司天监观天", "make_budget": "🧾 阿算拟预算",
    "travel_plan": "🏛 行程总管·四衙齐动",
}


def _post(messages, tools=None, max_tokens=800):
    """底层请求：返回原生 message 对象（含 tool_calls），失败返回 None"""
    cfg = load_config()
    key = cfg.get("deepseek_api_key", "").strip()
    if not key or key.startswith("在这里"):
        return None
    body = {"model": "deepseek-chat", "messages": messages,
            "max_tokens": max_tokens, "temperature": 0.8}
    if tools:
        body["tools"] = tools
    try:
        resp = requests.post("https://api.deepseek.com/chat/completions",
                             headers={"Authorization": f"Bearer {key}"}, json=body, timeout=40)
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]
    except Exception:
        pass
    return None


def chat_with_tools(persona_key, user_text, history):
    """
    L2 引擎：带工具循环的对话。
    返回 (答复文本, 工具调用轨迹)。
    轨迹形如 [("📮 驿丞录文书", "add_memo", "已录入：..."), ...]——
    界面层把它显示成"小吏回执"，路演时评委能亲眼看见 AI 在调工具。
    """
    messages = [{"role": "system",
                 "content": PERSONAS.get(persona_key, PERSONAS["zhu"]) + _TOOL_BRIEF}]
    messages += [dict(m) for m in history[-10:]]
    messages.append({"role": "user", "content": user_text})
    trace = []
    for _round in range(4):                       # 最多四轮调用，防打转
        msg = _post(messages, tools=TOOL_DEFS)
        if msg is None:
            # AI 掉线：若已执行过工具，至少把结果交代了
            if trace:
                return ("（飞鸽未归，小吏就地回禀——）\n" +
                        "\n".join(f"· {t[2]}" for t in trace), trace)
            return "（飞鸽未归……主人检查一下网络，再使唤小吏一次吧）", trace
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip(), trace
        # 执行每个工具调用，结果回喂
        messages.append({"role": "assistant", "content": msg.get("content") or "",
                         "tool_calls": calls})
        for tc in calls:
            fn = tc["function"]
            name, raw = fn["name"], fn.get("arguments", "{}")
            try:
                args = json.loads(raw)
            except Exception:
                args = {}
            try:
                result = TOOL_IMPL[name](args)
            except Exception as e:
                result = f"工具执行出错：{e}"
            trace.append((TOOL_TRAIL_NAMES.get(name, f"🔧 {name}"), name, str(result)))
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                             "content": str(result)})
            # 数据变了就广播刷新：对应面板立即重画（数据层删了，界面不能装不知道）
            if name in ("add_memo", "complete_memo", "delete_memo"):
                _broadcast("memo_refresh", {})
            elif name in ("add_ledger", "make_budget"):
                _broadcast("ledger_refresh", {})
            elif name == "travel_plan":
                _broadcast("memo_refresh", {})
                _broadcast("ledger_refresh", {})
    # 轮数用尽：让 AI 收尾
    msg = _post(messages, max_tokens=600)
    return ((msg.get("content") or "").strip() if msg else
            "（小吏衙门跑了个遍，主人且看回执～）", trace)


_TOOL_BRIEF = (
    "\n\n【衙门工具】你手里有十件衙门工具（add_memo / complete_memo / delete_memo / "
    "list_todos / schedule_today / add_ledger / ledger_summary / get_weather / make_budget / travel_plan）。"
    "主人吩咐的实事——记事、销事、查事、排程、记账、查账、问天气、为旅行购物等新事拟预算——"
    "不论主人在哪座衙门里说，都直接调工具去办，办完以你的口吻简短回禀（一两句即可）；"
    "主人没给全的信息（如时辰、天数）你自行合理补全。"
    "尤其：主人说『去某地旅游/玩几天』时，必须调 travel_plan——它会一次性差遣四座衙门"
    "（观天穿搭、荐味、行程、预算）并点亮各页面，你不可只荐美食。"
    "纯闲聊时不调工具；主人只要美食荐单时写 [[请|shi]] 引见尚食局。"
)


def arrange_schedule(events):
    """
    驿站智能排程：把今天的事项连同「当下时刻」发给 AI，
    综合加急档位、时限远近、耗时长短重排日程，并逐条给出排程理由。
    events: [{"time": "14:30", "content": "开会", "urgency_name": "八百里加急",
              "urgency": 3, "duration": 30}]
    """
    now = datetime.datetime.now()
    lines = "\n".join(
        f"- 截止时辰 {e['time']}｜{e['content']}｜{e['urgency_name']}｜预计耗时 {e['duration']} 分钟"
        for e in events
    )
    prompt = (
        PERSONAS["yi"]
        + f"\n\n当下时刻：{now.strftime('%H:%M')}。\n主人今日在驿站登记的文书如下：\n" + lines
        + "\n\n请你为主人重排今日行程，规矩如下：\n"
        "一、排序不可只看加急档位——须结合当下时刻通盘考量：已逾期的立即置前补办；"
        "时限将至的靠前；时限宽裕、加急平缓的押后；并参照耗时长短安排先后。\n"
        "二、给出每件事的建议起止时辰：从当下时刻往后排，件与件之间留 5 分钟喘息；"
        "安排尽量赶在各自截止时辰之前。\n"
        "三、输出分三段，标题照抄：\n"
        "【今日行程】每行一条：起止时辰 ｜ 【加急档位】事项（耗时）—— 一句驿站风叮嘱\n"
        "【排程理由】逐条说明为何这样排（哪件因逾期置前、哪件因加急让路、哪件因时限宽裕押后）\n"
        "【冲突警示】若有用时相撞或明显来不及的，指出并给补救建议；没有就写「驿道通畅，并无冲突」。"
    )
    return _call_deepseek(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "请开始排程。"}],
        max_tokens=1200,
    )


def outfit_advice(weather_desc, style_pref=""):
    """
    根据天气实况，让司天监云娘给一整套「今日着装策」。
    四段式：今日天色 → 推荐风格（含理由）→ 整套搭配单（上装/下装/外套/鞋/配饰+颜色）
    → 点睛提醒（小心机 + 降水防风硬提醒）。
    style_pref: 主人的风格偏好（如"喜欢新中式"/"要通勤得体"），可为空。
    """
    pref_line = f"\n主人偏好的风格：{style_pref}——推荐时优先贴合这份偏好。" if style_pref else ""
    prompt = (
        PERSONAS["tian"]
        + f"\n\n主人所在之处此刻天象如下：{weather_desc}\n"
        + pref_line
        + "\n请以司天监观天台的名义，献上一份「今日着装策」，分四段，标题照抄：\n"
        "【今日天色】一句诗意的话总括今日天气与体感（温冷/干湿/风力）。\n"
        "【推荐风格】结合天气、时节与温度推荐 1~2 种具体穿衣风格"
        "（如：轻通勤风 / 学院风 / 户外机能风 / 新中式 / 法式松弛风 / 美式复古），"
        "各用一句话说明为何今日适合。\n"
        "【搭配方案】给出 1~2 套从头到脚的完整搭配，每套按上装 / 下装 / 外套（如需）/ 鞋 / 配饰分行，"
        "写明单品与颜色（如：燕麦色针织开衫 + 直筒牛仔裤 + 白色德训鞋），实用、可照着穿。\n"
        "【点睛与提醒】一两条穿搭小心机（叠穿层次 / 帽子丝巾 / 材质选择），"
        "若天气有降水或风大，务必给硬提醒（带伞 / 防风外套）。\n"
        "整体保持云娘温柔诗意的口吻，总长不超过 300 字。"
    )
    return _call_deepseek(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "今日该穿什么？"}],
        max_tokens=900,
    )


def ledger_analysis(facts, verdict, stats):
    """
    账房对比分析：本地已算好数字与硬结论（facts/verdict），
    阿算只需核对数字、以师爷口吻总结，并给出 2~3 条可执行的省钱/持家建议。
    AI 掉线时界面层直接显示本地结论——账房不关门。
    """
    prompt = (
        PERSONAS["hu"]
        + "\n\n户部账房已把账目核对完毕，数据如下（以此为据，不得编造数字）：\n"
        + f"【账目事实】\n{facts}\n\n【本地核对结论】\n{verdict}\n\n"
        + "请你以账房师爷的口吻输出「今日账评」，分三段，标题照抄：\n"
        "【今日对账】用两三句复述核心数字：今日对昨日、对近七日日均的变化。\n"
        "【变化解读】指出变化主要来自哪些科目、是否合理（结合上面的科目异动）。\n"
        "【师爷建议】给 2~3 条具体可执行的建议（结合结余与距月末天数，"
        "比如某科目按今日速度月底会花多少、该收敛还是该宽心），语气精明务实。"
        "总长不超过 220 字。"
    )
    return _call_deepseek(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "请出账评。"}],
        max_tokens=700,
    )


def recommend(city, prefs):
    """尚食局推荐：按城市 + 偏好推荐美食或游玩。"""
    prompt = (
        PERSONAS["shi"]
        + f"\n\n主人想在「{city}」找乐子。偏好：{prefs or '没有特别偏好，美食和游玩都可以'}。\n"
        "请推荐 3~4 个真实存在的具体去处（真实店铺/景点/街区），规矩如下：\n"
        "一、每个去处单独一行，编号开头，格式严格照抄：\n"
        "N. 「店名」【招牌：招牌菜或看点】—— 一两句说清特色与大致价位。\n"
        "其中「店名」用于地图定位；【招牌】填最具代表性的一道菜/一种吃食/一个看点"
        "（如：羊肉泡馍、葫芦鸡、摔碗酒），它会用于搜真实照片，务必具体、是广为人知的名词。\n"
        "二、结尾用一句尚食局口吻的话收个尾。\n"
        "三、开头加一句总起。推荐要真实可查——小吏会拿招牌去搜真图和地图。"
    )
    return _call_deepseek(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "快给主人推荐！"}],
        max_tokens=1000,
    )
