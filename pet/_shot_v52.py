# -*- coding: utf-8 -*-
"""卷轴 + 悬浮窗 视觉截图（offscreen 环境中文字体缺失会显示方框，看布局即可）"""
import sys
import time

from PySide6.QtWidgets import QApplication

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
pet.open_panel("yamen")
yamen = pet._panels["yamen"]

# 卷轴：展开中途 + 完全展开
deck = main.ScrollDeck(pet)
deck.show()
wait(150)
deck.grab().save("_stage_scroll_half.png")
wait(700)
deck.grab().save("_stage_scroll_full.png")

# 衙门悬浮窗（嵌着真身面板）——透明窗在 offscreen 下 grab() 会黑屏，
# 改用 render() 画到带透明通道的 QImage
from PySide6.QtGui import QImage


def shoot(widget, path):
    img = QImage(widget.size(), QImage.Format_ARGB32)
    img.fill(0)
    widget.render(img)
    img.save(path)


fw = pet.open_float("memo")
app.processEvents()
wait(200)
shoot(fw, "_stage_float_memo.png")

fw2 = pet.open_float("weather")
app.processEvents()
wait(200)
shoot(fw2, "_stage_float_weather.png")
fw2.close()
app.processEvents()

# 卷轴 + 小吏同框
deck.hide()
app.processEvents()
pet.move(600, 400)
pet.contextMenuEvent(type("E", (), {
    "globalPos": staticmethod(lambda: None)})())
wait(700)
img = pet.grab()  # 只截小吏本体
img.save("_stage_pet.png")
print("截图完成")
