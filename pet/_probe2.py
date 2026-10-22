# -*- coding: utf-8 -*-
"""第二批角色视频：急急 ×2、云娘 ×2 —— 规格 + 抽帧联络表"""
import sys
import os
import cv2
import numpy as np

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe2"
os.makedirs(OUT, exist_ok=True)

vids = sys.argv[1:] or [
    "9f79a506d19ec0dbe95ba89b4ef8703e.mp4",
    "72a898fbef82275905f8d9aebd5931ce.mp4",
    "43666f9e94ae1b0c02c228a75290f0c9.mp4",
    "eceb7b122626402077de8b2475f27673.mp4",
]

for i, name in enumerate(vids):
    tag = chr(ord("A") + i)
    cap = cv2.VideoCapture(os.path.join(SRC, name))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{tag} {name[:8]}  {w}x{h}  {fps:.0f}fps  {n}帧  {n/fps:.2f}s")
    idxs = [int(k * (n - 1) / 5) for k in range(6)]
    tiles = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if not ok:
            continue
        fr = cv2.resize(fr, (220, 220))
        cv2.putText(fr, f"{tag}{idx}", (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        tiles.append(fr)
    cap.release()
    cv2.imwrite(os.path.join(OUT, f"sheet_{tag}.png"), cv2.hconcat(tiles))
print("done")
