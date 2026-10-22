# -*- coding: utf-8 -*-
"""细粒度抽帧：每个视频抽 12 帧，标注帧号，拼 4x3 图"""
import os
import imageio.v2 as imageio
from PIL import Image, ImageDraw

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_video_probe"

videos = {
    "0e36816ead8c43c3e462896c08abd745.mp4": "zhang_idle",
    "68ce54df3f97b6c1fac74e8d9827f038.mp4": "zhang_beard",
    "7bf75c06bae06a609aaee40f20832d5d.mp4": "zhang_abacus",
    "a7dd969ca07589a5b1c44f9720a60c1f.mp4": "cook_scene",
    "c18cba8b1239c31d4d2ca178fde20674.mp4": "cook_basket",
}

for v, tag in videos.items():
    rdr = imageio.get_reader(os.path.join(SRC, v))
    meta = rdr.get_meta_data()
    total = int(meta["fps"] * meta["duration"])
    idxs = [int(i * (total - 1) / 11) for i in range(12)]
    thumbs = []
    for idx in idxs:
        try:
            im = Image.fromarray(rdr.get_data(idx)).resize((240, 240))
        except (IndexError, StopIteration):
            continue
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 52, 20], fill=(255, 255, 255))
        d.text((4, 3), f"f{idx}", fill=(200, 0, 0))
        thumbs.append(im)
    rdr.close()
    sheet = Image.new("RGB", (240 * 4, 240 * 3), (128, 128, 128))
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % 4) * 240, (i // 4) * 240))
    out = os.path.join(OUT, f"fine_{tag}.png")
    sheet.save(out)
    print(out)
print("done")
