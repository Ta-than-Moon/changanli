# -*- coding: utf-8 -*-
"""卷轴令牌架 + 衙门悬浮窗 冒烟测试"""
import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint


class _Pos:
    """模拟 event.globalPosition() 返回的 QPointF（有 toPoint）"""

    def __init__(self, pt):
        self._pt = pt

    def toPoint(self):
        return self._pt


class FakePress:
    """模拟鼠标按下（左键）"""

    def button(self):
        return Qt.LeftButton

    def buttons(self):
        return Qt.LeftButton

    def globalPosition(self):
        return _Pos(QPoint(100, 100))


class FakeMove(FakePress):
    """模拟鼠标拖动（左键按住，走到指定点）"""

    def __init__(self, pt):
        self._pt = _Pos(pt)

    def globalPosition(self):
        return self._pt


def wait(ms):
    """转着事件循环等动画跑完"""
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

import main

pet = main.PetWindow()
pet.show()
pet.open_panel("yamen")
yamen = pet._panels["yamen"]

# ---------- ① 卷轴弹出 + 展开动画 ----------
pet.contextMenuEvent(FakePress())
app.processEvents()
deck = pet._deck
assert isinstance(deck, main.ScrollDeck)
assert len(deck.TOKENS) == 6 and len(deck.DEEDS) == 4
assert deck.isVisible()
assert deck._unroll == 0.0          # 刚弹出时是卷着的
wait(700)                                # 等展开动画收尾
assert deck._unroll >= 0.99, deck._unroll
print("① 卷轴弹出并展开 OK（进度 %.2f）" % deck._unroll)

# ---------- ② 衙门条目差遣：卷起并消失 → 弹悬浮窗，面板借出 ----------
deck._dispatch("memo")
wait(400)                                # 等收卷动画 + open_float
assert not deck.isVisible(), "收卷后卷轴未消失（只卷了纸，窗框还在）"
fw = pet._floats.get("memo")
assert fw is not None and fw.isVisible(), "驿站悬浮窗未弹出"
assert yamen.pages["memo"].parentWidget() is fw.host, "面板没有借进悬浮窗"
assert yamen.pages["memo"].isVisible(), "面板在悬浮窗里不可见（隐藏标记未清除）"
print("② 驿站悬浮窗弹出，真身面板已借出且可见 OK")

# 借出后再开总衙门同一页：面板应被召回
yamen.open("memo")
app.processEvents()
assert yamen.pages["memo"].parentWidget() is yamen.stack, "总衙门没把面板召回"
assert not fw.isVisible(), "召回后悬浮窗应收起"
print("③ 总衙门召回面板（悬浮窗自动收起）OK")

# ---------- ③ 关闭悬浮窗 = 面板归还书架 ----------
fw2 = pet.open_float("memo")
app.processEvents()
assert fw2 is fw and fw.isVisible()
fw.close()
app.processEvents()
assert yamen.pages["memo"].parentWidget() is yamen.stack, "关窗后面板没归还"
print("④ 关闭悬浮窗，面板归还总衙门 OK")

# ---------- ④ 五衙门全部能开悬浮窗（只验嵌入，不点真网络） ----------
for kind in ("chat", "weather", "food", "ledger"):
    f = pet.open_float(kind)
    app.processEvents()
    assert f.isVisible() and f._panel.parentWidget() is f.host, kind
    f.close()
    app.processEvents()
    assert f._panel.parentWidget() is yamen.stack, kind
print("⑤ 五衙门悬浮窗：借出/归还 全链路 OK")

# ---------- ⑤ 即时差遣与总衙门入口 ----------
deck._dispatch("yamen")
wait(400)
app.processEvents()
assert yamen.isVisible(), "总衙门未打开"
print("⑥ 总衙门条目进主页面 OK")

deck._dispatch("stroll")
wait(400)
assert pet.state == main.PetWindow.WALK, "巡街令未生效"
print("⑦ 即时差遣（巡街）OK")

# 语音令牌：没有麦克风也应安全（不崩）
deck._dispatch("voice")
wait(400)
print("⑧ 语音令牌安全 OK")

# ---------- ⑥ 卷轴拖动带动小吏 ----------
pet._deck.show()
wait(700)
old_pos = pet.pos()
deck._drag = QPoint(old_pos.x() + 5, old_pos.y() + 5)
deck.mouseMoveEvent(FakeMove(QPoint(old_pos.x() - 60, old_pos.y() - 20)))
assert pet.pos() != old_pos, "拖卷轴没带动小吏"
print("⑨ 拖卷轴带动小吏 OK")

# ---------- ⑦ 弹框强制置顶（置顶悬浮窗里不能被压住） ----------
import panels
from PySide6.QtWidgets import QMessageBox

_seen = {}
_orig_exec = QMessageBox.exec


def _fake_exec(self):
    _seen["topmost"] = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
    return QMessageBox.Yes


QMessageBox.exec = _fake_exec
try:
    assert panels.box_question(None, "驿站问询", "测试？") is True
    assert _seen["topmost"], "问询弹框没带置顶旗"
    panels.box_warning(None, "t", "t")
    assert _seen["topmost"], "警告弹框没带置顶旗"
    panels.box_info(None, "t", "t")
    assert _seen["topmost"], "提示弹框没带置顶旗"
finally:
    QMessageBox.exec = _orig_exec
print("⑩ 弹框三兄弟强制置顶 OK")

# ---------- ⑧ 陈影自愈：别窗已焚毁的文书，本窗删除不装死 ----------
yamen = pet._panels["yamen"]
memo_panel = yamen.panels_raw["memo"]
memo_store = main.memo_store
memo_store.add("陈影自愈测试文书", "23:59", 1, 30)
memo_panel.refresh()
ghost_item = None
for i in range(memo_panel.list_widget.count()):
    it = memo_panel.list_widget.item(i)
    if it.data(Qt.UserRole) and "陈影自愈测试文书" in it.text():
        ghost_item = it
        break
assert ghost_item is not None
memo_panel.list_widget.setCurrentItem(ghost_item)
ghost_id = ghost_item.data(Qt.UserRole)
memo_store.remove(ghost_id)              # 模拟"另一扇窗"先把它焚毁了

_info_seen = []
_orig_info = panels.box_info
panels.box_info = lambda *a, **k: _info_seen.append(a)
try:
    memo_panel.delete_selected()         # 对着陈影点焚毁：不许静默装死
finally:
    panels.box_info = _orig_info
assert _info_seen, "陈影删除没有给用户任何交代"
assert all("陈影自愈测试文书" not in (memo_panel.list_widget.item(i).text() or "")
           for i in range(memo_panel.list_widget.count())), "陈影没被刷新掉"
print("⑪ 陈影自愈（别窗焚毁→本窗明说+刷新）OK")

print("全部通过")
