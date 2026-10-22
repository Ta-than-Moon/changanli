# -*- coding: utf-8 -*-
"""shi/work 重做：只取烧菜段（52~78），保留人物+灶台两个大连通域"""
import os
import cv2
import numpy as np
from rembg import remove, new_session

N = 10
CELL_H = 260
DST = r"E:\changan\pet\assets\sprites\shi"
VID = r"D:\用完就删\云吞面\a7dd969ca07589a5b1c44f9720a60c1f.mp4"

session = new_session("u2net")


def keep_big_fg(bgra, ratio=0.04):
    """保留所有足够大的前景块（人物+灶台），只丢水印碎岛"""
    a = (bgra[..., 3] > 10).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(a, 8)
    if n <= 1:
        return bgra
    biggest = stats[1:, cv2.CC_STAT_AREA].max()
    keep = np.zeros_like(a)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] > biggest * ratio:
            keep[labels == i] = 1
    bgra = bgra.copy()
    bgra[..., 3] = np.where(keep == 1, bgra[..., 3], 0).astype(np.uint8)
    return bgra


def bbox(a, thr=8):
    ys, xs = np.where(a > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


cap = cv2.VideoCapture(VID)
bgras = []
for k in range(N):
    idx = round(58 + (80 - 58) * k / (N - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    assert ok
    out = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)
    bgras.append(keep_big_fg(cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA)))
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
sheet = cv2.hconcat(cells)
cv2.imencode(".png", sheet)[1].tofile(os.path.join(DST, "work.png"))
print(f"shi/work.png  {sheet.shape[1]}x{sheet.shape[0]}")
