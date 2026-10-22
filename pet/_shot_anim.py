# -*- coding: utf-8 -*-
"""验证：四位小吏是否真的逐帧动起来了（连续推进帧，比较画面差异）"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import panels


def sig(stage, pose="idle"):
    img = stage._pm[pose]["right"].toImage().convertToFormat(QImage.Format_ARGB32)
    return img.constBits()[:img.sizeInBytes()]


for key in ("hu", "yi", "tian", "shi", "zhu"):
    st = panels.PersonaStage(key)
    sigs = []
    for _ in range(4):
        for _ in range(3):          # 每 3 拍走一帧
            st._advance_frame()
        sigs.append(bytes(sig(st)))
    uniq = len({hash(s) for s in sigs})
    n = len(st._frames["idle"]["right"])
    print(f"{key}: 帧数={n}  四拍后不同画面数={uniq}  {'动起来了' if uniq > 1 else '仍是静态'}")

# 顺手存一张动画帧拼图，肉眼看看动作连不连贯
st = panels.PersonaStage("yi")
tiles = []
for i in range(5):
    pm = st._frames["walk"]["right"][i]
    img = QImage(pm.size(), QImage.Format_ARGB32)
    img.fill(QColor("#efe6d0"))
    from PySide6.QtGui import QPainter
    p = QPainter(img)
    p.drawPixmap(0, 0, pm)
    p.end()
    tiles.append(img)
w = sum(t.width() for t in tiles)
h = max(t.height() for t in tiles)
out = QImage(w, h, QImage.Format_ARGB32)
out.fill(QColor("#efe6d0"))
from PySide6.QtGui import QPainter
p = QPainter(out)
x = 0
for t in tiles:
    p.drawImage(x, 0, t)
    x += t.width()
p.end()
out.save("_anim_strip_yi.png")
print("strip ok")
