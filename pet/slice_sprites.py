# -*- coding: utf-8 -*-
"""
动作表切图 + 抠图脚本
原理（讲给新手听）：
1. 按列扫描：背景是纯色米色，哪一列"几乎全是背景色"就是动作之间的缝隙，以此把整张大图切成一个个动作
2. 去文字：每个动作下方有标签文字，找到角色与文字之间的"空白带"，从那里斩断
3. 抠图：从图片四边开始"漫水"——凡是与背景色相近且与边缘相连的像素都变透明。
   角色内部的浅色（如白纸、浅色衣）因为不与边缘相连，得以保留
"""
import os
from collections import deque
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))

# 每张表的配置：文件名、动作数、输出目录、动作映射（列序号 -> 统一动作名）
SHEETS = [
    {
        "src": os.path.join(BASE, "assets", "src", "male_sheet.jpg"),
        "out": os.path.join(BASE, "assets", "sprites", "male"),
        # 男吏五态：待机/走路/作揖/读公文/打盹（顺序即列顺序）
        "poses": ["idle", "walk", "greet", "work", "sleep"],
    },
    {
        "src": os.path.join(BASE, "assets", "src", "female_sheet.jpg"),
        "out": os.path.join(BASE, "assets", "sprites", "female"),
        # 女吏九态：待机/走路/开心/惊讶/害羞/困倦/读书/叉腰/小憩
        # 映射到统一五态：开心->greet，读书->work，小憩->sleep
        "poses": ["idle", "walk", "greet", "surprise", "shy", "drowsy", "work", "akimbo", "sleep"],
    },
]

BG_TOL = 42        # 与背景色的容差（越大抠得越狠）
GAP_MIN = 12       # 至少这么宽的空白列才算动作缝隙


def bg_color(img):
    """取四角像素的中位数作为背景色"""
    w, h = img.size
    px = img.load()
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    rs = sorted(c[0] for c in corners)
    gs = sorted(c[1] for c in corners)
    bs = sorted(c[2] for c in corners)
    return (rs[1] + rs[2]) // 2, (gs[1] + gs[2]) // 2, (bs[1] + bs[2]) // 2


def diff(c, bg):
    return abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])


def column_segments(img, bg, n_poses):
    """按列投影找出 n_poses 个内容区段 [(x0, x1), ...]"""
    w, h = img.size
    px = img.load()
    col_has = []
    for x in range(w):
        found = False
        for y in range(0, h, 3):  # 隔行采样提速
            if diff(px[x, y], bg) > BG_TOL:
                found = True
                break
        col_has.append(found)

    # 找出所有内容段，合并间距小于 GAP_MIN 的段
    segs = []
    x = 0
    while x < w:
        if col_has[x]:
            x0 = x
            while x < w and (col_has[x] or (x + 1 < w and any(col_has[x + 1:x + 1 + GAP_MIN]))):
                x += 1
            segs.append((x0, x))
        else:
            x += 1

    # 段数若多于动作数（文字标签造成碎段），按宽度保留最宽的 n_poses 段，并按 x 排序
    if len(segs) > n_poses:
        segs = sorted(segs, key=lambda s: s[1] - s[0], reverse=True)[:n_poses]
        segs.sort()
    return segs


def cut_label(seg_img, bg):
    """在下半部分找最宽的空白横带，斩断文字标签"""
    w, h = seg_img.size
    px = seg_img.load()
    row_has = []
    for y in range(h):
        found = False
        for x in range(0, w, 3):
            if diff(px[x, y], bg) > BG_TOL:
                found = True
                break
        row_has.append(found)
    # 从 40% 高度往下找第一个"连续 >=10 行无内容"的空白带
    best_cut = h
    y = int(h * 0.4)
    while y < h:
        if not row_has[y]:
            y0 = y
            while y < h and not row_has[y]:
                y += 1
            if y - y0 >= 10:
                best_cut = y0
                break
        else:
            y += 1
    return seg_img.crop((0, 0, w, best_cut))


def flood_matte(img, bg):
    """从边缘漫水抠图：与边缘相连的背景色变透明"""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    visited = bytearray(w * h)
    stack = deque()
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        idx = y * w + x
        if visited[idx]:
            continue
        visited[idx] = 1
        r, g, b, _ = px[x, y]
        if diff((r, g, b), bg) <= BG_TOL:
            px[x, y] = (r, g, b, 0)
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))
    return img


def autocrop(img):
    """裁掉四周全透明的边"""
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def process(sheet):
    img = Image.open(sheet["src"])
    bg = bg_color(img)
    print(f"{os.path.basename(sheet['src'])} 背景色 {bg} 尺寸 {img.size}")
    segs = column_segments(img, bg, len(sheet["poses"]))
    print(f"  切出 {len(segs)} 段：{segs}")
    if len(segs) != len(sheet["poses"]):
        print("  ⚠️ 段数与动作数不符，请检查！")
        return False
    os.makedirs(sheet["out"], exist_ok=True)
    for (x0, x1), pose in zip(segs, sheet["poses"]):
        seg = img.crop((x0, 0, x1, img.size[1]))
        seg = cut_label(seg, bg)
        seg = flood_matte(seg, bg)
        seg = autocrop(seg)
        # 统一缩放到高度 260 以内，避免窗口过大
        if seg.size[1] > 260:
            ratio = 260 / seg.size[1]
            seg = seg.resize((int(seg.size[0] * ratio), 260), Image.LANCZOS)
        path = os.path.join(sheet["out"], f"{pose}.png")
        seg.save(path)
        print(f"  ✓ {pose}.png {seg.size}")
    return True


if __name__ == "__main__":
    ok = all(process(s) for s in SHEETS)
    print("全部完成" if ok else "有问题需要人工检查")
