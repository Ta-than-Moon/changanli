# -*- coding: utf-8 -*-
"""v5.3 视觉验证：桌宠换装（小尝/阿算）+ 人物栏新形象"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main
import panels


def wait(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def snap(widget, name, w=None, h=None):
    w = w or widget.width()
    h = h or widget.height()
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor("#efe6d0"))          # 宣纸色底便于看透明边缘
    widget.render(img)
    img.save(name)


pet = main.PetWindow()
pet.show()
wait(300)

# 桌宠：换班到小尝（idx3）和阿算（idx4）
for idx, tag in ((3, "shi"), (4, "hu"), (1, "yi")):
    pet.current = idx
    pet.refresh_appearance()
    pet._place("idle", 40)
    app.processEvents()
    wait(120)
    snap(pet, f"_stage_pet_{tag}.png")
    print("pet", tag, pet.width(), pet.height())

# 人物栏：小尝 / 阿算
for key in ("shi", "hu"):
    st = panels.PersonaStage(key)
    st.show()
    app.processEvents()
    wait(300)
    snap(st, f"_stage_stage_{key}.png")
    print("stage", key, st.width(), st.height())

print("done")
