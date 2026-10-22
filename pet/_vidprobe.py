# -*- coding: utf-8 -*-
"""剖析 5 段角色动画视频：规格 + 抽帧预览"""
import cv2
import os

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe"
os.makedirs(OUT, exist_ok=True)

vids = [
    "0e36816ead8c43c3e462896c08abd745.mp4",
    "68ce54df3f97b6c1fac74e8d9827f038.mp4",
    "7bf75c06bae06a609aaee40f20832d5d.mp4",
    "a7dd969ca07589a5b1c44f9720a60c1f.mp4",
    "c18cba8b1239c31d4d2ca178fde20674.mp4",
]

for name in vids:
    path = os.path.join(SRC, name)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = n / fps if fps else 0
    print(f"{name[:8]}  {w}x{h}  {fps:.1f}fps  {n}帧  {dur:.2f}s")
    # 抽头/中/尾三帧拼图
    frames = []
    for idx in (0, n // 2, max(0, n - 1)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if ok:
            frames.append(fr)
    if frames:
        strip = cv2.hconcat([cv2.resize(f, (w // 2, h // 2)) for f in frames])
        cv2.imwrite(os.path.join(OUT, f"{name[:8]}_strip.png"), strip)
    cap.release()
print("done")
