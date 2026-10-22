# -*- coding: utf-8 -*-
"""真机冒烟 v2：右键展开卷轴 → 点驿站 → 卷轴必须消失，悬浮窗弹出"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QTimer

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main


class FakePress:
    def button(self): return Qt.LeftButton
    def buttons(self): return Qt.LeftButton
    def globalPosition(self):
        class P:
            def toPoint(self): return QPoint(100, 100)
        return P()


pet = main.PetWindow()
pet.show()

QTimer.singleShot(800, lambda: pet.contextMenuEvent(FakePress()))
QTimer.singleShot(1800, lambda: pet._deck._dispatch("memo"))


def check():
    deck_gone = not pet._deck.isVisible()
    fw = pet._floats.get("memo")
    fw_up = fw is not None and fw.isVisible()
    print("卷轴已消失:", deck_gone, "| 悬浮窗已弹出:", fw_up)
    app.exit(0 if (deck_gone and fw_up) else 1)


QTimer.singleShot(3200, check)
sys.exit(app.exec())
