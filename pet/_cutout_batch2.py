# -*- coding: utf-8 -*-
"""第二批角色抠图（rembg 版）：急急 + 云娘"""
import os
import cv2
import numpy as np
from rembg import remove, new_session

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe2"

session = new_session("u2net")

JOBS = {
    ("yi", "idle"):  ("9f79a506d19ec0dbe95ba89b4ef8703e.mp4", 24),
    ("yi", "walk"):  ("eceb7b122626402077de8b2475f27673.mp4", 72),
    ("tian", "idle"): ("72a898fbef82275905f8d9aebd5931ce.mp4", 38),
    ("tian", "greet"): ("43666f9e94ae1b0c02c228a75290f0c9.mp4", 57),
}


def grab_frame(video, idx):
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    cap.release()
    assert ok
    return fr


def tight_crop(bgra, margin=8):
    alpha = bgra[..., 3]
    ys, xs = np.where(alpha > 8)
    if len(ys) == 0:
        return bgra
    y0, y1 = max(0, ys.min() - margin), min(bgra.shape[0], ys.max() + margin + 1)
    x0, x1 = max(0, xs.min() - margin), min(bgra.shape[1], xs.max() + margin + 1)
    return bgra[y0:y1, x0:x1]


for (who, pose), (vid, idx) in JOBS.items():
    fr = grab_frame(os.path.join(SRC, vid), idx)
    bgra = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)
    bgra = cv2.cvtColor(bgra, cv2.COLOR_RGBA2BGRA)
    bgra = tight_crop(bgra)
    d = os.path.join(OUT, who)
    os.makedirs(d, exist_ok=True)
    cv2.imencode(".png", bgra)[1].tofile(os.path.join(d, f"{pose}.png"))
    print(f"{who}/{pose}.png  {bgra.shape[1]}x{bgra.shape[0]}")
print("done")
