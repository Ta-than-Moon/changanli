# -*- coding: utf-8 -*-
"""验证新卷轴：展开渲染 + 区域边框标注 + 输入框注入测试"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor, QPainter, QPen

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main


def wait(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


pet = main.PetWindow()
pet.show()
wait(200)

deck = main.ScrollDeck(pet)
deck.show()
deck._unroll = 1.0
deck._apply_mask()
app.processEvents()
wait(150)

# 标注可点区域（按窗口真实 DPR 截图，避免坐标系偏差）
dpr = deck.devicePixelRatioF()
print("DPR =", dpr)
pm = deck.grab()                     # grab 按设备像素出图
img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
img.save("_shot_deck_v2_raw.png")
p = QPainter(img)
p.setPen(QPen(QColor(255, 60, 40), 3))
s = deck._s * dpr                    # 图上坐标 = 原图 × _s × dpr
for rect, act, _ in deck.AVATARS:
    x0, y0, x1, y1 = rect
    p.drawRect(int(x0*s), int(y0*s), int((x1-x0)*s), int((y1-y0)*s))
for r in (deck.BAR_RECT, deck.TOWER_RECT, deck.QUIT_RECT):
    x0, y0, x1, y1 = r
    p.drawRect(int(x0*s), int(y0*s), int((x1-x0)*s), int((y1-y0)*s))
cx, cy = deck.SWITCH_CENTER
p.drawEllipse(int((cx-30)*s), int((cy-30)*s), int(60*s), int(60*s))
p.end()
img.save("_shot_deck_v2.png")
print("deck render ok", deck.width(), deck.height())

# 输入框注入 → 回车 → 签押房悬浮窗收到话
deck.bar.setText("帮我记一下明天下午三点开会")
deck._submit_bar()
wait(600)
fw = pet._floats.get("chat")
print("chat float:", "已开" if (fw and fw.isVisible()) else "未开")
print("done")
