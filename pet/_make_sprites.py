# -*- coding: utf-8 -*-
"""
_make_sprites.py —— 视频 → 透明精灵帧序列
流程：抽帧（每2帧取1）→ 漫水填充去背景 → 连通域滤掉水印/碎屑
     → 序列统一取景框（防跳动）→ 限高 360px 存 PNG
"""
import os
import shutil
import numpy as np
import cv2
import imageio.v2 as imageio
from PIL import Image

SRC = r"D:\用完就删\云吞面"
DST = r"E:\changan\pet\assets\sprites"
QA = r"E:\changan\pet\_video_probe"

# (角色, 动作, 视频文件, 起始帧, 结束帧, 背景容差)
JOBS = [
    ("zhangfang", "idle",  "0e36816ead8c43c3e462896c08abd745.mp4", 0,  96,  22),
    ("zhangfang", "greet", "68ce54df3f97b6c1fac74e8d9827f038.mp4", 43, 96,  22),
    ("zhangfang", "work",  "7bf75c06bae06a609aaee40f20832d5d.mp4", 8,  96,  22),
    ("zhangfang", "sleep", "68ce54df3f97b6c1fac74e8d9827f038.mp4", 78, 96,  22),
    ("cook", "idle",  "c18cba8b1239c31d4d2ca178fde20674.mp4", 0,  120, 30),
    ("cook", "greet", "a7dd969ca07589a5b1c44f9720a60c1f.mp4", 22, 55,  30),
    ("cook", "work",  "a7dd969ca07589a5b1c44f9720a60c1f.mp4", 55, 99,  30),
    ("cook", "sleep", "a7dd969ca07589a5b1c44f9720a60c1f.mp4", 99, 120, 30),
]

STEP = 2           # 每 2 帧取 1（24fps→12fps，70ms/tick 播放接近原速）
MAX_H = 360        # 帧限高（显示 180，留 2 倍余量）


def remove_bg(frame_rgb, tol):
    """漫水填充去背景：从四边种子点出发，吃掉与背景同色区域。
    返回 RGBA 数组（背景 alpha=0）。"""
    h, w = frame_rgb.shape[:2]
    img = frame_rgb.copy()
    # 背景色 = 边缘一圈的中位色
    ring = np.concatenate([
        frame_rgb[:8].reshape(-1, 3), frame_rgb[-8:].reshape(-1, 3),
        frame_rgb[:, :8].reshape(-1, 3), frame_rgb[:, -8:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    # 种子：边缘上与背景同色的点（隔4取一，省时间）
    mask = np.zeros((h + 2, w + 2), np.uint8)
    seeds = []
    for x in range(0, w, 4):
        seeds += [(x, 0), (x, h - 1)]
    for y in range(0, h, 4):
        seeds += [(0, y), (w - 1, y)]
    diff = np.abs(frame_rgb.astype(np.int16) - bg).max(axis=2)
    for sx, sy in seeds:
        if mask[sy + 1, sx + 1] == 0 and diff[sy, sx] < 45:
            cv2.floodFill(img, mask, (sx, sy), 0,
                          (tol, tol, tol), (tol, tol, tol),
                          flags=4 | (1 << 8))
    alpha = np.where(mask[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)

    # 连通域过滤：只留大块（角色本体/道具），水印碎屑丢弃
    n, labels, stats, _ = cv2.connectedComponentsWithStats(alpha, 8)
    if n > 1:
        biggest = stats[1:, cv2.CC_STAT_AREA].max()
        keep = np.zeros_like(alpha)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= max(biggest * 0.03, 300):
                keep[labels == i] = 255
        alpha = keep
    return np.dstack([frame_rgb, alpha])


def bbox_of(alpha):
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def process(role, pose, video, f0, f1, tol):
    rdr = imageio.get_reader(os.path.join(SRC, video))
    frames = []
    for idx in range(f0, f1 + 1, STEP):
        try:
            rgb = rdr.get_data(idx)
        except (IndexError, StopIteration):
            break
        frames.append(remove_bg(rgb, tol))
    rdr.close()
    if not frames:
        print(f"!! {role}/{pose} 无帧")
        return 0

    # 序列统一取景框：各帧 bbox 的并集 + 6px 边距 → 角色不跳位
    boxes = [bbox_of(f[:, :, 3]) for f in frames]
    boxes = [b for b in boxes if b]
    if not boxes:
        print(f"!! {role}/{pose} 抠完是空的")
        return 0
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    pad = 6
    H, W = frames[0].shape[:2]
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(W, x1 + pad); y1 = min(H, y1 + pad)

    outdir = os.path.join(DST, role, pose)
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    scale = MAX_H / (y1 - y0)
    for i, f in enumerate(frames):
        crop = f[y0:y1, x0:x1]
        im = Image.fromarray(crop, "RGBA")
        if scale < 1:
            im = im.resize((int(crop.shape[1] * scale), MAX_H), Image.LANCZOS)
        im.save(os.path.join(outdir, f"f{i:03d}.png"), optimize=True)
    print(f"{role}/{pose}: {len(frames)}帧  取景框 {(x1-x0)}x{(y1-y0)}")
    return len(frames)


def qa_sheet(role, pose):
    """抽 8 帧拼到深色底上预览（桌宠多半压在壁纸上，深色更接近真相）"""
    d = os.path.join(DST, role, pose)
    files = sorted(os.listdir(d))
    if not files:
        return
    picks = [files[int(i * (len(files) - 1) / 7)] for i in range(8)]
    thumbs = []
    for f in picks:
        im = Image.open(os.path.join(d, f)).convert("RGBA")
        im.thumbnail((150, 180))
        canvas = Image.new("RGBA", (160, 190), (38, 34, 30, 255))  # 深石板底
        canvas.paste(im, ((160 - im.width) // 2, 185 - im.height), im)
        thumbs.append(canvas.convert("RGB"))
    sheet = Image.new("RGB", (160 * 8, 190), (38, 34, 30))
    for i, t in enumerate(thumbs):
        sheet.paste(t, (i * 160, 0))
    sheet.save(os.path.join(QA, f"qa_{role}_{pose}.png"))


if __name__ == "__main__":
    for role, pose, video, f0, f1, tol in JOBS:
        n = process(role, pose, video, f0, f1, tol)
        if n:
            qa_sheet(role, pose)
    print("done")
