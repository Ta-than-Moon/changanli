import sys, time
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
import main

def wait(ms):
    end = time.time() + ms/1000
    while time.time() < end:
        app.processEvents(); time.sleep(0.02)

pet = main.PetWindow(); pet.show()
fw = pet.open_float('memo')
app.processEvents(); wait(300)
fw._panel.grab().save('_diag_panel.png')
fw.shell.grab().save('_diag_shell.png')
print('done')
