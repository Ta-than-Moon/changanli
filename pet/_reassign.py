# -*- coding: utf-8 -*-
"""
v5.7 角色归位：
- 云娘(tian) ← 用 img_045 生成的 5 姿势全身动画（从 shi 搬过来）
- 厨娘(shi) ← walk=提篮走路、work=灶台烧菜（水彩视频）；idle/greet/sleep=Q版立绘(img_031024)
"""
import os
import json
import shutil
import cv2
import numpy as np
from rembg import remove, new_session

DST = r"E:\changan\pet\assets\sprites"
N = 10
CELL_H = 260

session = new_session("u2net")


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


def build_sheet(video, i0, i1, n=N):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    i1 = min(i1, total - 1)
    idxs = [round(i0 + (i1 - i0) * k / (n - 1)) for k in range(n)]
    bgras = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        assert ok
        out = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)
        bgras.append(largest_fg(cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA)))
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
        canvas[:, (cw - w) // 2:(cw - w) // 2 + w] = r
        cells.append(canvas)
    return cv2.hconcat(cells)


# ---- ① 云娘归位：shi 的 045 动画整套搬给 tian ----
for p in ("idle", "walk", "greet", "work", "sleep"):
    shutil.copyfile(os.path.join(DST, "shi", f"{p}.png"), os.path.join(DST, "tian", f"{p}.png"))
json.dump({p: N for p in ("idle", "walk", "greet", "work", "sleep")},
          open(os.path.join(DST, "tian", "sheet.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("tian <= 045 动画")

# ---- ② 厨娘：水彩两段 ----
S = r"D:\用完就删\云吞面"
jobs = {
    "walk": (os.path.join(S, "c18cba8b1239c31d4d2ca178fde20674.mp4"), 0, 999),
    "work": (os.path.join(S, "a7dd969ca07589a5b1c44f9720a60c1f.mp4"), 0, 80),  # 只取烧菜段，末尾跪坐不要
}
for pose, (vid, i0, i1) in jobs.items():
    sheet = build_sheet(vid, i0, i1)
    cv2.imencode(".png", sheet)[1].tofile(os.path.join(DST, "shi", f"{pose}.png"))
    print(f"shi/{pose}.png  {sheet.shape[1]}x{sheet.shape[0]}")

# ---- ③ 厨娘 idle/greet/sleep：Q版立绘单帧 ----
img = cv2.imdecode(np.fromfile(os.path.join(S, "微信图片_20261022031024_303_1535.jpg"),
                               dtype=np.uint8), cv2.IMREAD_COLOR)
out = remove(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), session=session)
bgra = largest_fg(cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
x0, y0, x1, y1 = bbox(bgra[..., 3])
bgra = bgra[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6]
h = CELL_H
w = int(round(bgra.shape[1] * h / bgra.shape[0]))
bgra = cv2.resize(bgra, (w, h), interpolation=cv2.INTER_AREA)
for pose in ("idle", "greet", "sleep"):
    cv2.imencode(".png", bgra)[1].tofile(os.path.join(DST, "shi", f"{pose}.png"))
print("shi/idle,greet,sleep 单帧")

json.dump({"idle": 1, "walk": N, "greet": 1, "work": N, "sleep": 1},
          open(os.path.join(DST, "shi", "sheet.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("done")
