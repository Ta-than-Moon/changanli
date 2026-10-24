# -*- coding: utf-8 -*-
"""v5.9 视觉验证：总衙门主页新背景（横幅+六画卡）+ 五衙门整页背景"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main


def wait(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def snap(widget, name):
    img = QImage(widget.width(), widget.height(), QImage.Format_ARGB32)
    img.fill(QColor("#efe6d0"))
    widget.render(img)
    img.save(name)


pet = main.PetWindow()
pet.show()
pet.open_panel("yamen")
yamen = pet._panels["yamen"]
yamen.show()
yamen.resize(1180, 760)
wait(600)

snap(yamen, "_stage_v59_home.png")
print("home ok")

for kind in ("chat", "memo", "weather", "food", "ledger"):
    yamen.open(kind)
    wait(400)
    snap(yamen, f"_stage_v59_{kind}.png")
    print(kind, "ok")
print("done")
