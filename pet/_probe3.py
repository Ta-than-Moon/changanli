# -*- coding: utf-8 -*-
"""用户新发的三段视频：规格 + 六帧联络表"""
import cv2
import os

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe3"
os.makedirs(OUT, exist_ok=True)

vids = [
    "273104d0a6236350a45f8873fe29e883.mp4",
    "b78dae41a8d9874bb5eeb5a47440e83e.mp4",
    "86fc9aefcc817b9efb19d3f9345ad275.mp4",
]

for i, name in enumerate(vids):
    tag = chr(ord("A") + i)
    cap = cv2.VideoCapture(os.path.join(SRC, name))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{tag} {name[:8]}  {w}x{h} {fps:.0f}fps {n}帧")
    tiles = []
    for k in range(6):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(k * (n - 1) / 5))
        ok, fr = cap.read()
        if ok:
            fr = cv2.resize(fr, (220, 220))
            cv2.putText(fr, f"{tag}{int(k*(n-1)/5)}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)
            tiles.append(fr)
    cap.release()
    cv2.imwrite(os.path.join(OUT, f"sheet_{tag}.png"), cv2.hconcat(tiles))
print("done")
