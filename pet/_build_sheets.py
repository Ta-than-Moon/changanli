# -*- coding: utf-8 -*-
"""
把角色视频切成「精灵图表」——每个姿势 10 帧横排一张图，供引擎逐帧播放。
要点：所有帧统一裁剪框（取所有帧的并集），避免播放时人物抖动漂移。
"""
import os
import json
import cv2
import numpy as np
from rembg import remove, new_session

SRC = r"D:\用完就删\云吞面"
DST = r"E:\changan\pet\assets\sprites"
N = 10            # 每套动画帧数
CELL_H = 260      # 单帧高度

session = new_session("u2net")

# 角色/姿势 → 视频 + 取帧区间
JOBS = {
    ("hu", "idle"):  ("0e36816ead8c43c3e462896c08abd745.mp4", 24, 56),
    ("hu", "greet"): ("68ce54df3f97b6c1fac74e8d9827f038.mp4", 60, 96),
    ("hu", "work"):  ("7bf75c06bae06a609aaee40f20832d5d.mp4", 40, 72),
    ("yi", "idle"):  ("eceb7b122626402077de8b2475f27673.mp4", 0, 30),
    ("yi", "walk"):  ("eceb7b122626402077de8b2475f27673.mp4", 40, 76),
    ("tian", "idle"): ("72a898fbef82275905f8d9aebd5931ce.mp4", 16, 48),
    ("tian", "greet"): ("43666f9e94ae1b0c02c228a75290f0c9.mp4", 24, 64),
}


def grab(video, idx):
    cap = cv2.VideoCapture(os.path.join(SRC, video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    cap.release()
    assert ok, f"{video} #{idx}"
    return fr


def bbox(a, thr=8):
    ys, xs = np.where(a > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def build_sheet(video, i0, i1, n=N):
    idxs = [round(i0 + (i1 - i0) * k / (n - 1)) for k in range(n)]
    bgras = []
    for idx in idxs:
        fr = grab(video, idx)
        out = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)
        bgras.append(cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
    # 统一裁剪框：覆盖这套动画里人物出现过的所有位置
    x0 = min(bbox(b[..., 3])[0] for b in bgras)
    y0 = min(bbox(b[..., 3])[1] for b in bgras)
    x1 = max(bbox(b[..., 3])[2] for b in bgras)
    y1 = max(bbox(b[..., 3])[3] for b in bgras)
    m = 6
    x0, y0 = max(0, x0 - m), max(0, y0 - m)
    x1, y1 = min(bgras[0].shape[1], x1 + m), min(bgras[0].shape[0], y1 + m)
    crops = [b[y0:y1, x0:x1] for b in bgras]
    # 统一缩放高度，宽度取最大者居中对齐，防止播放时左右晃
    ch = CELL_H
    cw = max(int(round(c.shape[1] * ch / c.shape[0])) for c in crops)
    cells = []
    for c in crops:
        w = int(round(c.shape[1] * ch / c.shape[0]))
        r = cv2.resize(c, (w, ch), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((ch, cw, 4), np.uint8)
        ox = (cw - w) // 2
        canvas[:, ox:ox + w] = r
        cells.append(canvas)
    sheet = cv2.hconcat(cells)
    return sheet


for (who, pose), (vid, i0, i1) in JOBS.items():
    sheet = build_sheet(vid, i0, i1)
    d = os.path.join(DST, who)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{pose}.png")
    cv2.imencode(".png", sheet)[1].tofile(p)
    # 没有视频的姿势沿用这套图（保证五姿势齐全、动作统一）
    print(f"{who}/{pose}.png  {sheet.shape[1]}x{sheet.shape[0]}  ({N}帧)")
    # 登记帧数
    man_path = os.path.join(d, "sheet.json")
    man = {}
    if os.path.exists(man_path):
        man = json.load(open(man_path, encoding="utf-8"))
    man[pose] = N
    json.dump(man, open(man_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("done")
