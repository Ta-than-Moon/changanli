import sys, time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, Qt

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
import main


def wait(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents(); time.sleep(0.02)


class FakePress:
    def button(self): return Qt.LeftButton
    def buttons(self): return Qt.LeftButton
    def globalPosition(self):
        class P:
            def toPoint(self): return QPoint(100, 100)
        return P()


pet = main.PetWindow()
pet.show()
pet.open_panel("yamen")
yamen = pet._panels["yamen"]

pet.contextMenuEvent(FakePress())
wait(700)
deck = pet._deck
deck._dispatch("memo")
wait(400)

fw = pet._floats.get("memo")
panel = yamen.pages["memo"]
print("fw visible:", fw.isVisible())
print("panel parent is host:", panel.parentWidget() is fw.host)
print("panel isHidden:", panel.isHidden())
print("host isHidden:", fw.host.isHidden())
print("shell isHidden:", fw.shell.isHidden())
print("fw isHidden:", fw.isHidden())
