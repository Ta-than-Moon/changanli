# -*- coding: utf-8 -*-
"""账房先生三段视频：各抽 6 帧拼联络表供选帧"""
import cv2
import numpy as np
import os

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe"

vids = {
    "0e36816ead8c43c3e462896c08abd745.mp4": "A",   # 站立抱算盘
    "68ce54df3f97b6c1fac74e8d9827f038.mp4": "B",   # 抚须微笑
    "7bf75c06bae06a609aaee40f20832d5d.mp4": "C",   # 认真拨算盘
}

for name, tag in vids.items():
    cap = cv2.VideoCapture(os.path.join(SRC, name))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = [int(i * (n - 1) / 5) for i in range(6)]
    tiles = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if not ok:
            continue
        fr = cv2.resize(fr, (240, 240))
        cv2.putText(fr, f"{tag}{idx}", (8, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 255, 0), 2)
        tiles.append(fr)
    cap.release()
    sheet = cv2.hconcat(tiles)
    cv2.imwrite(os.path.join(OUT, f"sheet_{tag}.png"), sheet)
print("done")
