# -*- coding: utf-8 -*-
"""
v5.6：厨娘 + 账房先生的全身动画精灵图表
- 10 段生成视频 → 每姿势 10 帧横排
- 每帧先取最大连通域（隔离水印碎岛），再取并集裁剪框，防抖动
"""
import os
import json
import glob
import cv2
import numpy as np
from rembg import remove, new_session

SRC = r"E:\changan\pet\_vidgen"
DST = r"E:\changan\pet\assets\sprites"
N = 10
CELL_H = 260

session = new_session("u2net")


def find(keyword, ts=None):
    """按文件名关键词(+时间戳)找生成视频"""
    cands = [f for f in os.listdir(SRC) if keyword in f and (ts is None or ts in f)]
    assert len(cands) == 1, f"{keyword}/{ts} 匹配到 {cands}"
    return os.path.join(SRC, cands[0])


JOBS = {
    ("shi", "idle"):  find("原地站立", "08-56-28"),
    # 用户提供的更优版本（v5.6.1）：厨娘走近款走路、账房走路/站立
    ("shi", "walk"):  r"D:\用完就删\云吞面\273104d0a6236350a45f8873fe29e883.mp4",
    ("shi", "greet"): find("双手交叠"),
    ("shi", "work"):  find("搅动翻炒"),
    ("shi", "sleep"): find("打瞌睡", "08-56-22"),
    ("hu", "idle"):  r"D:\用完就删\云吞面\86fc9aefcc817b9efb19d3f9345ad275.mp4",
    ("hu", "walk"):  r"D:\用完就删\云吞面\b78dae41a8d9874bb5eeb5a47440e83e.mp4",
    ("hu", "greet"): find("眯眼微笑"),
    ("hu", "work"):  find("镜头固定不动"),
    ("hu", "sleep"): find("抱着算盘站着"),
}


def largest_fg(bgra):
    a = (bgra[..., 3] > 10).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(a, 8)
    if n <= 1:
        return bgra
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    bgra = bgra.copy()
    bgra[..., 3] = np.where(labels == biggest, bgra[..., 3], 0).astype(np.uint8)
    return bgra


def bbox(a, thr=8):
    ys, xs = np.where(a > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def build_sheet(video, n=N):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = [round(k * (total - 1) / (n - 1)) for k in range(n)]
    bgras = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        assert ok
        cap2 = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)
        bgras.append(largest_fg(cv2.cvtColor(cap2, cv2.COLOR_RGBA2BGRA)))
    cap.release()
    x0 = min(bbox(b[..., 3])[0] for b in bgras)
    y0 = min(bbox(b[..., 3])[1] for b in bgras)
    x1 = max(bbox(b[..., 3])[2] for b in bgras)
    y1 = max(bbox(b[..., 3])[3] for b in bgras)
    m = 6
    x0, y0 = max(0, x0 - m), max(0, y0 - m)
    x1 = min(bgras[0].shape[1], x1 + m)
    y1 = min(bgras[0].shape[0], y1 + m)
    crops = [b[y0:y1, x0:x1] for b in bgras]
    cw = max(int(round(c.shape[1] * CELL_H / c.shape[0])) for c in crops)
    cells = []
    for c in crops:
        w = int(round(c.shape[1] * CELL_H / c.shape[0]))
        r = cv2.resize(c, (w, CELL_H), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((CELL_H, cw, 4), np.uint8)
        ox = (cw - w) // 2
        canvas[:, ox:ox + w] = r
        cells.append(canvas)
    return cv2.hconcat(cells)


manifests = {}
for (who, pose), vid in JOBS.items():
    sheet = build_sheet(vid)
    d = os.path.join(DST, who)
    os.makedirs(d, exist_ok=True)
    cv2.imencode(".png", sheet)[1].tofile(os.path.join(d, f"{pose}.png"))
    manifests.setdefault(who, {})[pose] = N
    print(f"{who}/{pose}.png  {sheet.shape[1]}x{sheet.shape[0]}")

for who, man in manifests.items():
    json.dump(man, open(os.path.join(DST, who, "sheet.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
print("done")
