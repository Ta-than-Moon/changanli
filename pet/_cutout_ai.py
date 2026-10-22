# -*- coding: utf-8 -*-
"""账房先生三姿势：rembg AI 抠图（黑底黑袍泛洪搞不定的场景）"""
import os
import cv2
import numpy as np
from rembg import remove, new_session

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe"

session = new_session("u2net")   # 首次运行自动下载模型

HU = {
    "idle":  ("0e36816ead8c43c3e462896c08abd745.mp4", 38),
    "greet": ("68ce54df3f97b6c1fac74e8d9827f038.mp4", 96),
    "work":  ("7bf75c06bae06a609aaee40f20832d5d.mp4", 57),
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


os.makedirs(os.path.join(OUT, "hu2"), exist_ok=True)
for pose, (vid, idx) in HU.items():
    fr = grab_frame(os.path.join(SRC, vid), idx)
    # 遮水印：右下角涂黑（黑底下水印是白字，涂黑即隐身）
    h, w = fr.shape[:2]
    cv2.rectangle(fr, (int(w * 0.78), int(h * 0.86)), (w, h), (0, 0, 0), -1)
    bgra = remove(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), session=session)  # rembg 要 RGB
    bgra = cv2.cvtColor(bgra, cv2.COLOR_RGBA2BGRA)
    bgra = tight_crop(bgra)
    cv2.imencode(".png", bgra)[1].tofile(os.path.join(OUT, "hu2", f"{pose}.png"))
    print(f"hu2/{pose}.png  {bgra.shape[1]}x{bgra.shape[0]}")
print("done")
