# -*- coding: utf-8 -*-
"""v5.4 视觉验证：五位小吏桌宠换装全家福 + 急急云娘人物栏"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main
import panels


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
wait(300)

for idx, tag in ((0, "zhu"), (1, "yi"), (2, "tian"), (3, "shi"), (4, "hu")):
    pet.current = idx
    pet.refresh_appearance()
    pet._place("idle", 40)
    app.processEvents()
    wait(120)
    snap(pet, f"_stage_v54_pet_{tag}.png")
    print("pet", tag, "ok")

for key in ("yi", "tian"):
    st = panels.PersonaStage(key)
    st.show()
    app.processEvents()
    wait(300)
    snap(st, f"_stage_v54_stage_{key}.png")
    print("stage", key, "ok")
print("done")
