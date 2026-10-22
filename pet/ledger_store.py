# -*- coding: utf-8 -*-
"""
ledger_store.py —— 户部账房
收支流水的读写，存在 ledger.json 里，关掉程序也不会丢。

一条流水长这样：
    {"id": "1021213045123", "date": "2026-10-20", "time": "21:30",
     "kind": "out",            # out=支出  in=收入
     "category": "餐食", "amount": 23.5, "note": "夜宵"}
"""
import json
import datetime

from paths import data_file

STORE_PATH = data_file("ledger.json")

# 支出 / 收入 各自的分科（户部十三清吏司的简化版）
CATS_OUT = ["餐食", "交通", "学习", "娱乐", "购物", "居住", "医疗", "其他"]
CATS_IN = ["生活费", "兼职", "红包", "其他"]

KIND_NAME = {"out": "支出", "in": "收入"}


def load():
    """读取全部流水；文件不存在或损坏时返回空列表"""
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save(records):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add(kind, category, amount, note="", date_str=None):
    """记一笔，返回完整流水（按时间倒序由界面负责排）"""
    records = load()
    now = datetime.datetime.now()
    records.append({
        "id": now.strftime("%Y%m%d%H%M%S%f"),
        "date": date_str or now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "kind": kind if kind in ("in", "out") else "out",
        "category": category,
        "amount": round(float(amount), 2),
        "note": note.strip(),
    })
    save(records)
    return records


def remove(rid):
    records = [r for r in load() if r["id"] != rid]
    save(records)
    return records


def totals(records):
    """收支合计与结余"""
    income = sum(r["amount"] for r in records if r["kind"] == "in")
    expense = sum(r["amount"] for r in records if r["kind"] == "out")
    return round(income, 2), round(expense, 2), round(income - expense, 2)


def by_category(records, kind="out"):
    """按类别汇总，返回 [(类别, 金额)] 从高到低"""
    bucket = {}
    for r in records:
        if r["kind"] == kind:
            bucket[r["category"]] = bucket.get(r["category"], 0) + r["amount"]
    return sorted(bucket.items(), key=lambda kv: -kv[1])


def last_days(records, days=7, kind="out"):
    """近 N 天每日金额，返回 [(月-日, 金额)]，从早到晚"""
    today = datetime.date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        key = d.isoformat()
        amt = sum(r["amount"] for r in records if r["date"] == key and r["kind"] == kind)
        out.append((f"{d.month}/{d.day}", round(amt, 2)))
    return out


def month_records(records=None):
    """本月流水"""
    records = load() if records is None else records
    prefix = datetime.date.today().strftime("%Y-%m")
    return [r for r in records if r["date"].startswith(prefix)]


# ========== 对比分析（师爷看账） ==========
def daily_expense(records, date):
    """某一天的支出合计"""
    return round(sum(r["amount"] for r in records
                     if r["date"] == date and r["kind"] == "out"), 2)


def category_day(records, date):
    """某一天各科目支出 {(科目, 金额)}"""
    bucket = {}
    for r in records:
        if r["date"] == date and r["kind"] == "out":
            bucket[r["category"]] = bucket.get(r["category"], 0) + r["amount"]
    return {k: round(v, 2) for k, v in bucket.items()}


def compare_report(records=None):
    """
    本地算好「今日 vs 往日」的对比数据（结论性判断由本地规则先做一版，
    AI 只负责润色成师爷口吻 + 追加建议——掉线时本地结论照样能用）。
    """
    records = load() if records is None else records
    today = datetime.date.today()
    t_str = today.isoformat()
    today_amt = daily_expense(records, t_str)
    yesterday_amt = daily_expense(records, (today - datetime.timedelta(days=1)).isoformat())

    # 近七日（不含今天）的日均值与科目占比
    week_days = [(today - datetime.timedelta(days=i)).isoformat() for i in range(1, 8)]
    week_amts = [daily_expense(records, d) for d in week_days]
    active_days = [a for a in week_amts if a > 0]
    week_avg = round(sum(active_days) / len(active_days), 2) if active_days else 0.0
    week_total = round(sum(week_amts), 2)

    # 科目占比：今日 vs 往日均值
    today_cats = category_day(records, t_str)
    past_cats = {}
    for d in week_days:
        for k, v in category_day(records, d).items():
            past_cats[k] = past_cats.get(k, 0) + v
    for k, v in past_cats.items():
        past_cats[k] = round(v / max(1, len(active_days)), 2)  # 往日日均

    # 本地先下一版"硬结论"（AI 掉线时直接显示）
    facts, verdict = [], []
    if week_avg > 0:
        diff = round(today_amt - week_avg, 2)
        pct = round(diff / week_avg * 100)
        if diff > 0:
            verdict.append(f"今日支出比近七日日均多 ¥{diff}（+{pct}%），手头偏松。")
        elif diff < 0:
            verdict.append(f"今日支出比近七日日均少 ¥{-diff}（-{abs(pct)}%），花销收敛。")
        else:
            verdict.append("今日支出与近七日日均持平。")
    else:
        verdict.append("往日无账可对——今日起记账，来日方长。")
    if yesterday_amt > 0:
        d_y = round(today_amt - yesterday_amt, 2)
        if abs(d_y) >= 1:
            verdict.append(
                f"较昨日{'多' if d_y > 0 else '少'}花 ¥{abs(d_y)}"
                f"（昨日 ¥{yesterday_amt}）。")
    # 科目异动：今日占比明显高于往日均值占比的
    top_today = sorted(today_cats.items(), key=lambda kv: -kv[1])
    for cat, amt in top_today[:2]:
        past = past_cats.get(cat, 0)
        if past > 0 and amt > past * 1.8 and amt >= 10:
            verdict.append(f"「{cat}」今日 ¥{amt}，明显高于往日日均 ¥{past}，需留意。")
    facts.append(f"今日支出 ¥{today_amt}｜昨日 ¥{yesterday_amt}｜近七日日均 ¥{week_avg}（共 ¥{week_total}）")
    if top_today:
        facts.append("今日科目：" + "，".join(f"{c} ¥{v}" for c, v in top_today))
    if past_cats:
        facts.append("往日日均科目：" + "，".join(
            f"{c} ¥{v}" for c, v in sorted(past_cats.items(), key=lambda kv: -kv[1])[:5]))
    # 本月结余与剩余天数（给 AI 做建议的原料）
    inc, exp, bal = totals(month_records(records))
    left_days = (datetime.date(today.year, today.month, 1)
                 + datetime.timedelta(days=32)).replace(day=1) - today
    facts.append(f"本月：收入 ¥{inc}｜支出 ¥{exp}｜结余 ¥{bal}｜距月末还有 {left_days.days} 天")
    return "\n".join(facts), "\n".join(verdict), {
        "today": today_amt, "yesterday": yesterday_amt,
        "week_avg": week_avg, "balance": bal, "left_days": left_days.days,
    }
