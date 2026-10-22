# -*- coding: utf-8 -*-
"""
memo_store.py —— 驿站文书库
备忘录的读取和保存，存在 memos.json 里，关掉程序也不会丢。
"""
import json
import os
import datetime

from paths import data_file

# memos.json 的"最终住址"：exe 旁边优先，用户目录兜底（详见 paths.py）
STORE_PATH = data_file("memos.json")

# 四档加急程度：索引即优先级（0 最缓，3 最急）
URGENCY = ["普快", "三百里加急", "五百里加急", "八百里加急"]


def load():
    """读取全部备忘；文件不存在或损坏时返回空列表"""
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save(memos):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)


def add(content, time_str, urgency_idx, duration, date_str=None):
    """新增一条备忘，返回完整列表。date_str 缺省=今天；多日行程可指定各自日期"""
    memos = load()
    memos.append({
        "id": datetime.datetime.now().strftime("%H%M%S%f") + f"{len(memos)}",  # 唯一编号
        "date": date_str or datetime.date.today().isoformat(),  # 归属日期
        "time": time_str,        # "HH:MM"
        "content": content,
        "urgency": urgency_idx,  # 0~3
        "urgency_name": URGENCY[urgency_idx],
        "duration": duration,    # 分钟
        "reminded": False,       # 是否已提醒过
    })
    save(memos)
    return memos


def remove(memo_id):
    memos = [m for m in load() if m["id"] != memo_id]
    save(memos)
    return memos


def due_soon(minutes=10):
    """
    找出「今天、还剩不到 N 分钟就截止、还没提前警示过」的备忘，
    返回后把它们标记 warned=True（避免反复放烟花）。
    """
    memos = load()
    now = datetime.datetime.now()
    today = now.date().isoformat()
    soon = []
    changed = False
    for m in memos:
        if m["date"] != today or m.get("reminded") or m.get("done") or m.get("warned"):
            continue
        try:
            target = datetime.datetime.combine(now.date(), datetime.time.fromisoformat(m["time"]))
        except Exception:
            continue
        left = (target - now).total_seconds()
        if 0 <= left <= minutes * 60:
            m["warned"] = True
            changed = True
            soon.append(m)
    if changed:
        save(memos)
    return soon


def due_reminders():
    """
    找出「今天、到点了、还没提醒过」的备忘，并把它们标记为已提醒。
    返回需要提醒的备忘列表。
    """
    memos = load()
    now = datetime.datetime.now()
    today = now.date().isoformat()
    current = now.strftime("%H:%M")
    due = []
    changed = False
    for m in memos:
        if m["date"] == today and not m["reminded"] and m["time"] <= current:
            m["reminded"] = True
            changed = True
            due.append(m)
    if changed:
        save(memos)
    return due


# ========== 智能排序与本地排程 ==========
def _minutes_left(m, now=None):
    """距截止还剩几分钟（负数=已逾期）；非今日文书返回 None"""
    now = now or datetime.datetime.now()
    if m["date"] != now.date().isoformat():
        return None
    try:
        target = datetime.datetime.combine(now.date(), datetime.time.fromisoformat(m["time"]))
    except Exception:
        return None
    return (target - now).total_seconds() / 60


def smart_score(m, now=None):
    """
    综合紧迫分（越高越该先办）：
    加急档位为纲（×100），当下时间为目——
    已逾期的冲到最前（逾期越久越靠前），一小时内到期的按剩余时间加分。
    """
    score = m["urgency"] * 100
    left = _minutes_left(m, now)
    if left is None:
        return score
    if left < 0:
        score += 200 + min(100.0, -left)      # 已逾期：冲到最前，逾期越久越靠前
    elif left <= 30:
        score += 320 + (30 - left)            # 迫在眉睫：火烧眉毛，越过寻常加急
    elif left <= 60:
        score += 60 - left                    # 一小时内到期：越近越靠前
    return score


def smart_sorted(memos, now=None):
    """综合紧迫分排序（高→低）；已办讫的押尾"""
    return sorted(memos,
                  key=lambda m: (m.get("done", False), -smart_score(m, now), m["time"]))


def local_plan(events):
    """
    无网络 / 无 Key 时的兜底排程：本地算法也能排出合理的日程，
    并逐条给出排程理由——演示日断网，驿站照样开张。
    """
    now = datetime.datetime.now()
    pending = sorted(events, key=lambda m: -smart_score(m, now))
    lines = ["【今日行程 · 驿丞就地急排】"]
    reasons = []
    cursor = now
    for i, e in enumerate(pending):
        left = _minutes_left(e, now)
        start = cursor
        end = start + datetime.timedelta(minutes=e["duration"])
        lines.append(
            f"- {start.strftime('%H:%M')}~{end.strftime('%H:%M')} ｜ "
            f"【{e['urgency_name']}】{e['content']}（{e['duration']}分钟）")
        if left is not None and left < 0:
            reasons.append(f"「{e['content']}」已过时辰 {-int(left)} 分钟，逾期文书置前补办。")
        elif left is not None and left <= 30:
            reasons.append(f"「{e['content']}」时限迫在眉睫（余 {int(left)} 分钟），火速提前。")
        elif e["urgency"] == 3:
            if i == 0:
                reasons.append(f"「{e['content']}」乃八百里加急，金牌在手，万事让路。")
            else:
                reasons.append(f"「{e['content']}」乃八百里加急，仅让于更火烧眉毛者，紧随其上。")
        elif left is not None and left <= 60:
            reasons.append(f"「{e['content']}」时限将至（余 {int(left)} 分钟），靠前安排。")
        else:
            reasons.append(f"「{e['content']}」时限宽裕、加急平缓，押后徐办。")
        cursor = end + datetime.timedelta(minutes=5)  # 件与件之间留 5 分钟喘息
    lines.append("")
    lines.append("【排程理由】")
    lines += ["- " + r for r in reasons]
    lines.append("")
    lines.append("【冲突警示】驿道通畅，并无冲突。（本地急排，供主人参考）")
    return "\n".join(lines)
