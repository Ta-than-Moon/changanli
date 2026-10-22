# -*- coding: utf-8 -*-
"""抽帧分析 5 个角色动画视频"""
import os
import imageio.v2 as imageio
from PIL import Image

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_video_probe"
os.makedirs(OUT, exist_ok=True)

videos = [f for f in os.listdir(SRC) if f.endswith(".mp4")]
for v in sorted(videos):
    path = os.path.join(SRC, v)
    rdr = imageio.get_reader(path)
    meta = rdr.get_meta_data()
    fps = meta.get("fps", 0)
    dur = meta.get("duration", 0)
    size = meta.get("size", ("?", "?"))
    nframes = rdr.count_frames() if hasattr(rdr, "count_frames") else -1
    print(f"{v}: {size[0]}x{size[1]}, {fps:.1f}fps, {dur:.2f}s, ~{nframes}帧")

    # 抽 6 帧拼一行
    frames = []
    idxs = [int(i * (dur * fps) / 6) for i in range(6)]
    for idx in idxs:
        try:
            frames.append(Image.fromarray(rdr.get_data(idx)))
        except Exception:
            break
    rdr.close()
    if frames:
        w, h = frames[0].size
        sheet = Image.new("RGB", (w * len(frames), h), (200, 200, 200))
        for i, f in enumerate(frames):
            sheet.paste(f, (i * w, 0))
        out = os.path.join(OUT, v.replace(".mp4", "_sheet.png"))
        sheet.save(out)
        print(f"  -> {out} ({len(frames)}帧拼图)")
print("done")
