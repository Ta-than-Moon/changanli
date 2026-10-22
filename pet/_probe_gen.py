# -*- coding: utf-8 -*-
"""验收 10 段生成视频：规格 + 中段一帧"""
import cv2
import os
import numpy as np

D = r"E:\changan\pet\_vidgen"
files = sorted(f for f in os.listdir(D) if f.endswith(".mp4"))
tiles = []
for f in files:
    cap = cv2.VideoCapture(os.path.join(D, f))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, n // 2)
    ok, fr = cap.read()
    cap.release()
    tag = "厨" if "厨娘" in f else "账"
    # 从文件名推断姿势
    pose = "idle"
    for kw, p in (("走路", "walk"), ("行礼", "greet"), ("搅动", "work"), ("算盘珠子", "work"),
                  ("打瞌睡", "sleep"), ("站立", "idle")):
        if kw in f:
            pose = p
    print(f"{tag}/{pose}  {w}x{h} {fps:.0f}fps {n}帧")
    fr = cv2.resize(fr, (200, 200))
    cv2.putText(fr, f"{tag}{pose}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    tiles.append((tag, pose, fr))
tiles.sort(key=lambda t: (t[0], t[1]))
row = cv2.hconcat([t[2] for t in tiles])
cv2.imwrite(os.path.join(D, "gen_review.png"), row)
print("done")
