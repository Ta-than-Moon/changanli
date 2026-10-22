# -*- coding: utf-8 -*-
"""
角色抠图管线：
- 账房先生：黑底视频帧 → 泛洪去底（避开黑袍）
- 厨娘：白底Q版立绘 → 泛洪去底（避开白围裙）
统一：角落水印遮盖 → 泛洪背景 → 最大连通域 → 边缘羽化 → 紧凑裁剪
"""
import cv2
import numpy as np
import os

SRC = r"D:\用完就删\云吞面"
OUT = r"E:\changan\pet\_vidprobe"


def imread_cn(path):
    """中文路径读图"""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_cn(path, img):
    """中文/任意路径写图"""
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def grab_frame(video, idx):
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    cap.release()
    assert ok, f"取帧失败 {video} #{idx}"
    return fr


def flood_bg_mask(img, seeds_tol):
    """从四边种子点泛洪，返回背景掩码（255=背景）。fixed range 模式只吞与种子相近的连通色块。"""
    h, w = img.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    work = img.copy()
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8) | cv2.FLOODFILL_FIXED_RANGE
    step = 6
    for x in range(0, w, step):
        for y in (0, h - 1):
            if mask[y + 1, x + 1] == 0:
                cv2.floodFill(work, mask, (x, y), 0, seeds_tol, seeds_tol, flags)
    for y in range(0, h, step):
        for x in (0, w - 1):
            if mask[y + 1, x + 1] == 0:
                cv2.floodFill(work, mask, (x, y), 0, seeds_tol, seeds_tol, flags)
    return mask[1:-1, 1:-1]


def largest_fg(alpha):
    """只保留最大的前景连通域（浮空碎屑、水印孤岛一并丢弃）"""
    n, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 10).astype(np.uint8), 8)
    if n <= 1:
        return alpha
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = (labels == biggest).astype(np.uint8) * 255
    return cv2.bitwise_and(alpha, keep)


def tight_crop(img, alpha, margin=8):
    ys, xs = np.where(alpha > 8)
    if len(ys) == 0:
        return img, alpha
    y0, y1 = max(0, ys.min() - margin), min(img.shape[0], ys.max() + margin + 1)
    x0, x1 = max(0, xs.min() - margin), min(img.shape[1], xs.max() + margin + 1)
    return img[y0:y1, x0:x1], alpha[y0:y1, x0:x1]


def cutout(img, tol, corner_patch=None, feather=3, open_k=3, erode=1):
    """
    完整抠图：corner_patch=(x_ratio, y_ratio) 把右下角涂成背景色遮水印
    返回 BGRA 图
    """
    work = img.copy()
    if corner_patch:
        h, w = work.shape[:2]
        bg = [int(c) for c in work[2, 2]]  # 左上角当背景色
        cv2.rectangle(work, (int(w * corner_patch[0]), int(h * corner_patch[1])),
                      (w, h), tuple(bg), -1)
    bg_mask = flood_bg_mask(work, tol)
    alpha = 255 - bg_mask
    if open_k:
        k = np.ones((open_k, open_k), np.uint8)
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, k)     # 去碎点
    alpha = largest_fg(alpha)
    if erode:
        k = np.ones((3, 3), np.uint8)
        alpha = cv2.erode(alpha, k, iterations=erode)          # 收掉背景色描边
    if feather:
        alpha = cv2.GaussianBlur(alpha, (feather * 2 + 1, feather * 2 + 1), 0)
    work, alpha = tight_crop(work, alpha)
    return work, alpha


def make_bgra(work, alpha):
    b, g, r = cv2.split(work)
    return cv2.merge([b, g, r, alpha])


# ---------- 账房先生（黑底，三姿势） ----------
HU = {
    "idle":  ("0e36816ead8c43c3e462896c08abd745.mp4", 38),
    "greet": ("68ce54df3f97b6c1fac74e8d9827f038.mp4", 96),
    "work":  ("7bf75c06bae06a609aaee40f20832d5d.mp4", 57),
}
os.makedirs(os.path.join(OUT, "hu"), exist_ok=True)
for pose, (vid, idx) in HU.items():
    fr = grab_frame(os.path.join(SRC, vid), idx)
    work, alpha = cutout(fr, tol=28, corner_patch=(0.78, 0.86), feather=2, erode=1)
    imwrite_cn(os.path.join(OUT, "hu", f"{pose}.png"), make_bgra(work, alpha))
    print(f"hu/{pose}.png  {work.shape[1]}x{work.shape[0]}")

# ---------- 厨娘（白底 Q 版立绘，五姿势共用） ----------
img = imread_cn(os.path.join(SRC, "微信图片_20261022031024_303_1535.jpg"))
work, alpha = cutout(img, tol=26, corner_patch=None, feather=2, erode=1)
os.makedirs(os.path.join(OUT, "shi"), exist_ok=True)
imwrite_cn(os.path.join(OUT, "shi", "idle.png"), make_bgra(work, alpha))
print(f"shi/idle.png  {work.shape[1]}x{work.shape[0]}")
print("done")
