# -*- coding: utf-8 -*-
"""
长安吏 · 桌面宠物系统 —— 主程序（画境版）
运行方式：python main.py
右键宠物 = 衙门菜单；双击宠物 = 作揖问候 + 闲聊；左键拖动 = 提起来挪位置

桌宠演出系统（小吏的一日）：
- 待机：原地呼吸浮动，偶尔翻翻公文
- 巡街：在桌面上散步，会掉头、迈步带弹跳
- 作揖：双击时蹦一下作揖问安
- 打盹：太久没人理会就坐下打盹（点他一下就醒）
- 提醒：备忘到点，头顶冒出加急气泡
"""
import os
import json
import sys
import math
import random

from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QMenu, QPushButton,
                               QGridLayout, QVBoxLayout, QHBoxLayout, QFrame,
                               QGraphicsDropShadowEffect, QMessageBox, QLineEdit)
from PySide6.QtCore import (Qt, QPoint, QTimer, QThread, Signal, QRectF,
                           QVariantAnimation, QEasingCurve, QEvent, QLockFile)
from PySide6.QtGui import (QPixmap, QAction, QTransform, QPainter, QColor, QPen,
                           QPainterPath, QRegion, QLinearGradient, QBrush, QFont)

import brain
import memo_store
import fireworks
import voice
from panels import YamenWindow, XIAOLI


# ---------- 资源路径：开发环境和打包成 exe 后都能找到 ----------
def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


SPRITE_DIR = os.path.join("assets", "sprites", "male")

# 桌宠换班时的形象目录（与 panels.PersonaStage.SPRITE_SET 同一张人事表）：
# 急急=骑马驿丞、云娘=司天、小尝=厨娘、阿算=账房；主簿阿卷仍用通用 male
PET_SPRITE_SET = {"zhu": "male", "yi": "yi", "tian": "tian",
                  "shi": "shi", "hu": "hu"}


def split_sheet(pm, n):
    """横排精灵图按帧数切成逐帧图（n=1 就是原来的单帧立绘）"""
    if n <= 1 or pm.isNull():
        return [pm]
    cw = pm.width() // n
    frames = []
    for i in range(n):
        f = pm.copy(i * cw, 0, cw, pm.height())
        if not f.isNull():
            frames.append(f)
    return frames or [pm]

# ---------- 气泡样式（寻常 / 加急）：宣纸底、朱砂边、楷体字 ----------
BUBBLE_QSS = """
QLabel { background: #fbf6ea; color: #322a20; border: 1px solid #d8c69a;
         border-left: 5px solid #9e2b22; border-radius: 12px; padding: 12px 16px;
         font-family: "KaiTi","STKaiti","楷体"; font-size: 15px; }
"""
BUBBLE_URGENT_QSS = """
QLabel { background: #fdecea; color: #8e1f14; border: 1px solid #e5b3ac;
         border-left: 5px solid #9e2b22; border-radius: 12px; padding: 12px 16px;
         font-weight: bold; font-family: "KaiTi","STKaiti","楷体"; font-size: 15px; }
"""


class Bubble(QWidget):
    """宠物头上的气泡：无边框小窗口，显示一段时间后自动消失"""
    def __init__(self, text, urgent=False):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(300)
        self.label.setStyleSheet(BUBBLE_URGENT_QSS if urgent else BUBBLE_QSS)
        self.resize(self.label.sizeHint())
        # 普通气泡 8 秒消失，加急气泡 12 秒
        QTimer.singleShot(12000 if urgent else 8000, self.close)


class EventLike:
    """一个能跨线程 set 的开关（给语音线程发"提前收音"信号）"""
    def __init__(self):
        self._flag = False

    def set(self):
        self._flag = True

    def __call__(self):
        return self._flag


class VoiceWorker(QThread):
    """驿卒耳力：后台收音 → 本地 Whisper 转写，完了发信号回主界面"""
    done = Signal(str)
    fail = Signal(str)

    def __init__(self, cut):
        super().__init__()
        self.cut = cut

    def run(self):
        try:
            rec = voice.Recorder()
            audio = rec.record(stop_flag=self.cut)
            if audio is None or len(audio) < voice.FS // 4:   # 不到 0.25 秒
                self.done.emit("")
                return
            text = voice.transcribe(audio)
            self.done.emit(text)
        except Exception as e:
            self.fail.emit(str(e))


# ========== 差遣卷轴：右键展开的新版卷轴（用户设计稿 juanzhou.png） ==========
class ScrollDeck(QWidget):
    """
    悬浮卷轴 v2：右键桌宠，一幅卷轴从左轴向右滚开。
    - 皮相：用户设计的卷轴图（assets/ui/juanzhou.png），展开时纸面从左轴后抽出
    - 四个头像 = 四大衙门（云娘·天气 / 急急·备忘 / 阿算·账本 / 小尝·美食）
    - 右上角城楼 = 总衙门（主页面 home）
    - 顶部横栏 = 差遣输入框：打字回车，直接送进签押房议事
    - 右下角朱印小圆钮 = 换班；左下角小字 = 放小吏下班
    - 点外部自动收卷（Qt.Popup）；按住空白纸面拖动 = 挪动小吏
    """
    VIEW_W = 780                      # 显示宽度（原图 1023，等比缩）
    ROLLER_X = 118                    # 左轴右缘（原图坐标，收卷时遮到这里）

    # 原图坐标系里的可点区域（在裁剪后的 juanzhou.png 上量取）
    BAR_RECT   = (180, 150, 865, 250)          # 顶部差遣横栏
    TOWER_RECT = (830, 100, 890, 165)          # 城楼 = 总衙门
    AVATARS = [                                # 四头像 = 四衙门
        ((130, 285, 300, 435), "weather", "司天监 · 云娘 —— 天气穿搭"),
        ((325, 285, 490, 435), "memo",    "长安驿站 · 急急 —— 备忘提醒"),
        ((510, 285, 675, 435), "ledger",  "户部记账 · 阿算 —— 收支流水"),
        ((700, 285, 865, 435), "food",    "尚食局 · 小尝 —— 美食探店"),
    ]
    SWITCH_CENTER = (814, 509)                  # 换班朱印圆钮
    QUIT_RECT = (130, 440, 300, 478)            # 左下角"放小吏下班"小字

    BTN_QSS = """
        QPushButton { background: transparent; border: none; border-radius: 16px; }
        QPushButton:hover { background: rgba(201,162,83,0.28);
                            border: 2px solid rgba(176,58,46,0.75); }
        QPushButton:pressed { background: rgba(158,43,34,0.30); }
    """

    def __init__(self, pet):
        super().__init__()
        self.pet = pet
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)

        pm = QPixmap(resource_path(os.path.join("assets", "ui", "juanzhou.png")))
        pm.setDevicePixelRatio(1.0)                    # 杜绝 DPR 把图拉偏
        self._img = pm.scaledToWidth(self.VIEW_W, Qt.SmoothTransformation)
        self._img.setDevicePixelRatio(1.0)
        self._s = self.VIEW_W / 1023.0                 # 显示坐标 = 原图坐标 × _s
        self.setFixedSize(self.VIEW_W, self._img.height())

        self._unroll = 0.0
        self._anim = None
        self._drag = None

        # ---- 顶部横栏：差遣输入框 ----
        self.bar = QLineEdit(self)
        self.bar.setGeometry(*self._rect(self.BAR_RECT))
        self.bar.setPlaceholderText("差遣小吏：吩咐一句，回车即办")
        self.bar.setAlignment(Qt.AlignCenter)
        self.bar.setCursor(Qt.IBeamCursor)
        self.bar.setStyleSheet(
            'QLineEdit { background: rgba(255,252,244,120); border: none; color: #322a20;'
            ' font-family: "KaiTi","STKaiti","楷体"; font-size: 17px; padding: 0 18px; }'
            'QLineEdit:focus { background: rgba(255,252,244,190); }'
        )
        self.bar.returnPressed.connect(self._submit_bar)

        # ---- 四头像 ----
        for rect, act, tip in self.AVATARS:
            b = QPushButton("", self)
            b.setGeometry(*self._rect(rect))
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.setStyleSheet(self.BTN_QSS)
            b.clicked.connect(lambda _=False, a=act: self._dispatch(a))

        # ---- 城楼：回总衙门 ----
        t = QPushButton("", self)
        t.setGeometry(*self._rect(self.TOWER_RECT))
        t.setCursor(Qt.PointingHandCursor)
        t.setToolTip("总衙门 —— 进主页面")
        t.setStyleSheet(self.BTN_QSS)
        t.clicked.connect(lambda: self._dispatch("yamen"))

        # ---- 右下角朱印：换班 ----
        cx, cy = self.SWITCH_CENTER
        r = int(30 * self._s) + 4
        sw = QPushButton("换班", self)
        sw.setGeometry(int((cx - 30) * self._s), int((cy - 30) * self._s), r * 2, r * 2)
        sw.setCursor(Qt.PointingHandCursor)
        sw.setToolTip("换一位小吏当值")
        sw.setStyleSheet(
            'QPushButton { background: qradialgradient(cx:0.4,cy:0.35,radius:0.9,'
            '  stop:0 #c0392b, stop:1 #8e1f14); color: #f7e7c3;'
            '  border: 2px solid #e0b95c; border-radius: %dpx;'
            '  font-family: "KaiTi","STKaiti","楷体"; font-size: 13px; font-weight: bold; }'
            'QPushButton:hover { background: #c0392b; }'
            'QPushButton:pressed { background: #7a1a10; }' % r
        )
        sw.clicked.connect(lambda: self._dispatch("switch"))

        # ---- 左下角小字：放小吏下班 ----
        q = QPushButton("· 放小吏下班 ·", self)
        q.setGeometry(*self._rect(self.QUIT_RECT))
        q.setCursor(Qt.PointingHandCursor)
        q.setStyleSheet(
            'QPushButton { background: transparent; border: none; color: #a8976f;'
            ' font-size: 12px; font-family: "Microsoft YaHei","微软雅黑"; }'
            'QPushButton:hover { color: #8e1f14; }'
        )
        q.clicked.connect(lambda: self._dispatch("quit"))

    def _rect(self, r):
        """原图坐标 → 显示坐标"""
        x0, y0, x1, y1 = r
        return (int(x0 * self._s), int(y0 * self._s),
                int((x1 - x0) * self._s), int((y1 - y0) * self._s))

    # ---------- 差遣：收卷 → 办事 ----------
    def _submit_bar(self):
        text = self.bar.text().strip()
        if not text:
            return
        self.bar.clear()

        def go():
            fw = self.pet.open_float("chat")       # 送进签押房，走正经议事流程
            chat = fw._panel
            chat.input.setText(text)
            chat.send()
        self._roll_close(then=go)

    def _dispatch(self, act):
        def go():
            p = self.pet
            if act == "switch":
                p.switch_xiaoli()
            elif act == "quit":
                QApplication.quit()
            elif act == "yamen":
                p.open_panel("yamen")
            else:
                p.open_float(act)                   # 四衙门：弹悬浮窗
        self._roll_close(then=go)

    # ---------- 展开 / 收卷：纸面从左轴后向右抽出 ----------
    def _apply_mask(self):
        w = max(int(self.ROLLER_X * self._s), int(self._unroll * self.width()))
        self.setMask(QRegion(0, 0, w, self.height()))

    def _on_unroll(self, v):
        self._unroll = float(v)
        self._apply_mask()
        self.update()

    def showEvent(self, event):
        """右键唤出：卷轴从左轴向右展开"""
        super().showEvent(event)
        if self._anim is not None:
            # 收卷中途又唤出：作废旧动画（stop 会同步发 finished，先置空防误关窗）
            old = self._anim
            self._anim = None
            old.stop()
        self._unroll = 0.0
        self._apply_mask()
        anim = QVariantAnimation(self)
        anim.setDuration(480)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(self._on_unroll)
        anim.start()
        self._anim = anim

    def _roll_close(self, then=None):
        """收卷：纸卷回左轴，卷完才真正关窗，然后办事"""
        anim = QVariantAnimation(self)
        anim.setDuration(240)
        anim.setStartValue(self._unroll)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.valueChanged.connect(self._on_unroll)

        def _done():
            if self._anim is anim:
                self._anim = None
                self.close()
                if then:
                    then()

        anim.finished.connect(_done)
        anim.start()
        self._anim = anim

    # ---------- 拖动卷轴 = 拖着小吏一起走（按住空白纸面） ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.pet.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag is not None and (event.buttons() & Qt.LeftButton):
            self.pet.move(event.globalPosition().toPoint() - self._drag)
            self.pet._reposition_bubbles()
            self.pet._place_deck()

    def mouseReleaseEvent(self, event):
        self._drag = None

    # ---------- 皮相：就是用户那幅卷轴 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._img)           # 强制铺满窗口，不吃 DPR 亏


# ========== 衙门悬浮窗：把总衙门的真身面板"借"出来悬浮当差 ==========
# (衙门名, 当值小吏, 窗宽, 窗高)
FLOAT_META = {
    "chat":    ("签押房",   "主簿·阿卷", 560, 680),
    "memo":    ("长安驿站", "驿丞·急急", 660, 760),
    "weather": ("司天监",   "司天·云娘", 620, 740),
    "food":    ("尚食局",   "尚食·小尝", 680, 780),
    "ledger":  ("户部记账", "户部·阿算", 660, 760),
}


class FloatPanelWindow(QWidget):
    """
    衙门悬浮窗：点击卷轴上的衙门条目弹出。
    - 无边框 + 置顶（可点标题栏的 📌 取消置顶）、拖标题栏挪窗、纸色圆角 + 投影
    - 里面嵌的是总衙门里的真身面板（不是复制品）：聊天记录、驿卷、账册与总衙门同一份
    - 关窗 = 面板归还总衙门书架；总衙门要用这页时会把面板召回（悬浮窗自动收起）
    """
    M = 16      # 四周给投影留的呼吸边

    def __init__(self, pet, kind):
        super().__init__()
        self.pet = pet
        self.kind = kind
        self.name, self.clerk, w, h = FLOAT_META[kind]
        self.yamen = pet._panels.get("yamen")
        self._panel = self.yamen.panels_raw[kind]      # 真身面板（借来嵌入）
        self._pinned = True

        self.setWindowTitle(f"长安吏 · {self.name}")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(w + self.M * 2, h + self.M * 2)

        root = QVBoxLayout(self)
        root.setContentsMargins(self.M, self.M, self.M, self.M)
        root.setSpacing(0)

        # ---- 纸壳：圆角宣纸底 + 鎏金边 + 投影 ----
        self.shell = QFrame()
        self.shell.setObjectName("floatShell")
        self.shell.setStyleSheet("""
            QFrame#floatShell { background: #f5efe2;
                border: 2px solid #c9a253; border-radius: 14px; }""")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(30, 20, 10, 90))
        self.shell.setGraphicsEffect(shadow)
        root.addWidget(self.shell)     # 纸壳才是窗的全部内容，必须挂进根布局

        shell_lay = QVBoxLayout(self.shell)
        shell_lay.setContentsMargins(0, 0, 0, 0)
        shell_lay.setSpacing(0)

        # ---- 标题栏：衙门名 + 当值小吏 + 置顶钉 + 关窗 ----
        bar = QFrame()
        bar.setFixedHeight(46)
        bar.setStyleSheet("background: transparent; border-bottom: 1px solid #e3d8bd;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 4, 8, 4)
        bl.setSpacing(8)
        icon_lbl = QLabel("🏮")
        icon_lbl.setStyleSheet("background:transparent; font-size:16px;")
        title = QLabel(self.name)
        title.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:17px;'
                            "font-weight:bold; color:#322a20; background:transparent;")
        clerk = QLabel(f"{self.clerk} 当值")
        clerk.setStyleSheet("color:#9a8b6d; font-size:12px; background:transparent;")
        bl.addWidget(icon_lbl)
        bl.addWidget(title)
        bl.addWidget(clerk)
        bl.addStretch()
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(34, 32)
        self.pin_btn.setToolTip("已置顶：点击可取消置顶")
        self.pin_btn.setStyleSheet("""
            QPushButton { background: rgba(255,253,247,200); border: 1px solid #ddd0b2;
                border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background: #f6e3d5; border: 1px solid #b03a2e; }""")
        self.pin_btn.clicked.connect(self._toggle_pin)
        bl.addWidget(self.pin_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(34, 32)
        close_btn.setToolTip("收起（面板归还总衙门）")
        close_btn.setStyleSheet("""
            QPushButton { background: rgba(255,253,247,200); border: 1px solid #ddd0b2;
                border-radius: 8px; color: #8e2f1f; font-size: 14px; }
            QPushButton:hover { background: #b03a2e; color: #fff7e8; border: 1px solid #8a2a1a; }""")
        close_btn.clicked.connect(self.close)
        bl.addWidget(close_btn)
        shell_lay.addWidget(bar)

        # ---- 面板借宿处 ----
        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_lay.setContentsMargins(0, 0, 0, 0)
        shell_lay.addWidget(self.host, 1)

        # ---- 拖动状态：按住标题栏即可挪窗 ----
        self._bar = bar
        self._drag = None
        bar.installEventFilter(self)

    # ---------- 面板借出 / 归还 ----------
    def _embed(self):
        """把真身面板从总衙门书架上取来，嵌进这扇悬浮窗"""
        if self._panel is not None and self._panel.parentWidget() is not self.host:
            self.host_lay.addWidget(self._panel)     # addWidget 自动换爸爸
            # 面板在总衙门书架里若不是当前页，带着"显式隐藏"标记，
            # 换了爸爸标记还在——必须重新点亮，否则悬浮窗里是空的
            self._panel.show()

    def _return_panel(self):
        """面板归还总衙门书架（QStackedWidget）"""
        if self._panel is not None and self._panel.parentWidget() is self.host:
            self.yamen.stack.addWidget(self._panel)

    def closeEvent(self, event):
        self._return_panel()
        super().closeEvent(event)

    # ---------- 置顶 / 拖动 ----------
    def _toggle_pin(self):
        self._pinned = not self._pinned
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._pinned)
        self.show()
        self.pin_btn.setToolTip("已置顶：点击可取消置顶" if self._pinned
                                else "未置顶：点击恢复置顶")

    def eventFilter(self, obj, event):
        """标题栏：按下记偏移，拖动挪窗，松手放下"""
        if obj is self._bar:
            t = event.type()
            if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif t == QEvent.MouseMove and self._drag is not None \
                    and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag)
            elif t == QEvent.MouseButtonRelease:
                self._drag = None
        return super().eventFilter(obj, event)

    def _place_near_pet(self):
        """出生落点：小吏身边，贴屏换边、上下不越界"""
        p = self.pet
        screen = QApplication.primaryScreen().availableGeometry()
        x = p.x() - self.width() - 26
        if x < 8:
            x = min(p.x() + p.width() + 26, screen.right() - self.width())
        y = max(8, min(p.y() - 30, screen.bottom() - self.height()))
        self.move(x, y)


def _preload_voice_model():
    """后台预热：把 Whisper 模型先搬进内存（首次会自动下载约480MB）"""
    import threading

    def _load():
        try:
            voice.get_engine()
        except Exception:
            pass

    threading.Thread(target=_load, daemon=True).start()


class PetWindow(QWidget):
    """桌宠窗口：状态机驱动的一套流畅小动作"""

    # 状态常量
    IDLE, WALK, GREET, WORK, SLEEP = "idle", "walk", "greet", "work", "sleep"

    def __init__(self):
        super().__init__()

        # 窗口三件套：无边框 + 透明 + 置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(190, 252)

        # ---- 精灵图加载：五个动作正反两个朝向，按当值小吏分目录 ----
        self.sprites = {}
        self._load_sprites()
        self.facing = "right"  # 朝向

        # ---- 名牌 + 形象 ----
        self.badge = QLabel(self)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet(
            "background: rgba(43,42,38,225); color:#f0d998; border:1px solid #c9a253;"
            "border-radius:10px; padding:3px 12px;"
            'font-family:"KaiTi","STKaiti","楷体"; font-size:13px; font-weight:bold;'
        )
        self.badge.adjustSize()
        self.badge.setFixedWidth(148)
        self.badge.move((self.width() - self.badge.width()) // 2, 2)

        self.label = QLabel(self)
        self.label.resize(190, 190)

        # 当前值班小吏（默认驿丞，贴合主打功能）
        self.current = 1
        self.refresh_appearance()

        # 初始位置：屏幕右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 240, screen.height() - 330)

        # ---- 动画状态机 ----
        self.state = self.IDLE
        self.phase = 0          # 动画帧计数
        self.state_until = 0    # 当前状态持续到第几帧
        self.walk_dir = 1       # 巡街方向：1 向右，-1 向左
        self.dragging = False

        # 动作帧时钟：每 70 毫秒走一帧，所有动作都在这里"演"
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._tick)
        self.frame_timer.start(70)

        # 小吏的行为闹钟：待机一阵后自己决定干点什么（散步/翻公文/作揖）
        self._schedule_next_behavior()

        # 打盹计时：太久没人理会就睡着（毫秒）
        self.idle_ms = 0
        self.nap_timer = QTimer(self)
        self.nap_timer.timeout.connect(self._count_idle)
        self.nap_timer.start(1000)

        # 驿卷巡查：每 20 秒检查一次有没有到点的备忘
        self.remind_timer = QTimer(self)
        self.remind_timer.timeout.connect(self._check_reminders)
        self.remind_timer.start(20 * 1000)

        # 面板缓存（避免重复创建窗口）
        self._panels = {}
        self._floats = {}      # 衙门悬浮窗缓存 {kind: FloatPanelWindow}
        self._bubbles = []

        cfg = brain.load_config()
        self.default_city = cfg.get("city", "西安")

        # 出场问候：作揖 + 一句话
        QTimer.singleShot(800, self._entrance)

    # ---------- 外观 ----------
    def _load_sprites(self):
        """按当值小吏的目录装立绘（横排多帧动画图）；某姿势缺图时回退男吏通用图"""
        folder = PET_SPRITE_SET.get(self.persona_key() if hasattr(self, "current") else "zhu",
                                    "male")
        manifest = {}
        mf = resource_path(os.path.join("assets", "sprites", folder, "sheet.json"))
        if os.path.exists(mf):
            try:
                manifest = json.load(open(mf, encoding="utf-8"))
            except Exception:
                manifest = {}
        self.sprites = {}       # 当前帧
        self._frames = {}       # 整套动画帧
        for pose in ("idle", "walk", "greet", "work", "sleep"):
            pm = QPixmap(resource_path(os.path.join("assets", "sprites", folder, f"{pose}.png")))
            if pm.isNull():      # 这位小吏还没画这个姿势 → 借男吏的
                pm = QPixmap(resource_path(os.path.join(SPRITE_DIR, f"{pose}.png")))
            pm = pm.scaledToHeight(180, Qt.SmoothTransformation)
            frames = split_sheet(pm, int(manifest.get(pose, 1)))
            self._frames[pose] = {"right": frames,
                                  "left": [f.transformed(QTransform().scale(-1, 1))
                                           for f in frames]}
            self.sprites[pose] = {"right": frames[0], "left": self._frames[pose]["left"][0]}
        self._fidx = 0
        self._ftick = 0

    def _advance_frame(self):
        """动画走帧：约 7 帧/秒"""
        self._ftick += 1
        if self._ftick % 2:
            return
        self._fidx += 1
        for pose, pair in self._frames.items():
            if len(pair["right"]) <= 1:
                continue
            i = self._fidx % len(pair["right"])
            self.sprites[pose]["right"] = pair["right"][i]
            self.sprites[pose]["left"] = pair["left"][i]

    def refresh_appearance(self):
        """换班：刷新名牌 + 换成这位小吏自己的形象"""
        self._load_sprites()
        x = XIAOLI[self.current]
        self.badge.setText(f"{x['name']} · 当值")
        self.badge.adjustSize()
        self.badge.setFixedWidth(148)
        self.badge.move((self.width() - self.badge.width()) // 2, 2)

    # ---------- 当前值班小吏 ----------
    def persona_key(self):
        return XIAOLI[self.current]["key"]

    def persona_name(self):
        return XIAOLI[self.current]["name"]

    def switch_xiaoli(self):
        """换班：四位小吏轮流上岗"""
        self.current = (self.current + 1) % len(XIAOLI)
        self.refresh_appearance()
        x = XIAOLI[self.current]
        self._set_state(self.GREET, 26)  # 新小吏作揖亮相
        self.say(f"{x['name']}前来当值！分管「{x['duty']}」，主人尽管吩咐～")

    # ---------- 状态机 ----------
    def _set_state(self, state, frames):
        """切换状态并声明持续帧数（70ms/帧）"""
        self.state = state
        self.phase = 0
        self.state_until = frames

    def _tick(self):
        """动作帧时钟：让当前状态"演"起来"""
        if self.dragging:
            return
        self.phase += 1
        self._advance_frame()

        if self.state == self.IDLE:
            # 呼吸浮动：正弦起伏 3px
            y = 40 + round(3 * math.sin(self.phase * 0.09))
            self._place(self.IDLE, y)
        elif self.state == self.WALK:
            # 巡街：横向移动 + 迈步弹跳 + 自动掉头
            screen = QApplication.primaryScreen().availableGeometry()
            x = self.x() + self.walk_dir * 2
            if x <= screen.left() + 4:
                self.walk_dir = 1
            elif x + self.width() >= screen.right() - 4:
                self.walk_dir = -1
            self.facing = "right" if self.walk_dir > 0 else "left"
            bounce = abs(math.sin(self.phase * 0.35)) * 5
            self._place(self.WALK, 40 - round(bounce))
            self.move(x, self.y())
        elif self.state == self.GREET:
            # 作揖：蹦起来又落地，还带一点点前倾的感觉
            hop = abs(math.sin(self.phase * 0.45)) * 12
            self._place(self.GREET, 40 - round(hop))
        elif self.state == self.WORK:
            # 翻公文：轻微点头节奏
            y = 40 + round(2 * math.sin(self.phase * 0.2))
            self._place(self.WORK, y)
        elif self.state == self.SLEEP:
            # 打盹：慢而深的呼吸
            y = 44 + round(3 * math.sin(self.phase * 0.05))
            self._place(self.SLEEP, y)

        # 状态期满：回到待机
        if self.phase >= self.state_until:
            self._set_state(self.IDLE, 10 ** 9)

    def _place(self, pose, y):
        """摆姿势：按朝向取图并挪到指定高度"""
        pm = self.sprites[pose][self.facing]
        self.label.setPixmap(pm)
        self.label.move((self.width() - pm.width()) // 2, y)

    def _schedule_next_behavior(self):
        """行为闹钟：隔上一阵子（25~50 秒）才琢磨下一件事，平时安生待着"""
        delay = random.randint(25_000, 50_000)
        QTimer.singleShot(delay, self._do_behavior)

    def _do_behavior(self):
        if self.dragging or self.state == self.SLEEP:
            self._schedule_next_behavior()
            return
        # 只有待机中的小吏会"找事做"
        if self.state == self.IDLE:
            roll = random.random()
            if roll < 0.28:
                # 巡街：随机方向走一两秒就歇
                self.walk_dir = random.choice([-1, 1])
                self.facing = "right" if self.walk_dir > 0 else "left"
                self._set_state(self.WALK, random.randint(20, 38))
            elif roll < 0.44:
                # 停下来翻一会儿公文
                self._set_state(self.WORK, random.randint(22, 40))
            elif roll < 0.52:
                # 兴致来了作个揖
                self._set_state(self.GREET, 22)
            # 其余近一半概率：继续发呆待机
        self._schedule_next_behavior()

    def _count_idle(self):
        """太久没人理会 → 小吏坐下打盹；被打扰即醒"""
        if self.dragging:
            self.idle_ms = 0
            return
        self.idle_ms += 1000
        if self.idle_ms >= 90_000 and self.state != self.SLEEP:
            self._set_state(self.SLEEP, 10 ** 9)
            self.say("（小吏打了个哈欠，倚着卷宗睡着了…… zZZ）")

    def _wake(self):
        """任何互动都会叫醒小吏"""
        self.idle_ms = 0
        if self.state == self.SLEEP:
            self._set_state(self.GREET, 22)
            self.say("小吏失礼了！这就打起精神当值！")

    def _entrance(self):
        self._set_state(self.GREET, 26)
        self.say("主人好！小吏们已就位，右键点我可以差遣各位小吏～")

    # ---------- 气泡 ----------
    def say(self, text, urgent=False):
        """让宠物说话：在头顶冒出一个气泡（多个气泡自动向上叠罗汉）"""
        bubble = Bubble(text, urgent)
        bubble.show()
        self._bubbles.append(bubble)
        self._reposition_bubbles()

    def _reposition_bubbles(self):
        """把所有气泡"拎"到宠物头顶：最新的贴着宠物，旧的往上叠"""
        self._bubbles = [b for b in self._bubbles if b.isVisible()]
        x = self.x() + self.width() - 60
        y = self.y() - 6
        for bubble in reversed(self._bubbles):
            y -= bubble.height()
            bubble.move(x, y)
            y -= 6

    # ---------- 鼠标交互 ----------
    def mousePressEvent(self, event):
        self._wake()
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    # ---------- 牌架定位：永远落在小吏身边 ----------
    def _place_deck(self):
        """令牌架贴着小吏摆：左侧优先，贴屏换右，上下不越界"""
        deck = getattr(self, "_deck", None)
        if deck is None or not deck.isVisible():
            return
        deck_w, deck_h = deck.width(), deck.height()
        screen = QApplication.primaryScreen().availableGeometry()
        x = self.x() - deck_w - 14
        if x < 8:
            x = min(self.x() + self.width() + 14, screen.right() - deck_w)
        y = max(8, min(self.y() - 30, screen.bottom() - deck_h))
        deck.move(x, y)

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            self._reposition_bubbles()
            self._place_deck()      # 小吏挪窝，牌架跟着搬家

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self._set_state(self.IDLE, 10 ** 9)  # 放下后站稳喘口气

    def voice_tap(self):
        """语音唤醒入口（双击/令牌架共用）：正在听=提前收音；否则开始听"""
        self._wake()
        if getattr(self, "_voice_running", False):
            self._voice_cut.set()
            return
        if not voice.mic_available():
            self.say("小吏没找到麦克风——主人检查一下设备？")
            return
        self._set_state(self.GREET, 26)
        self._start_voice()

    def mouseDoubleClickEvent(self, event):
        """双击 = 唤醒耳力，语音输入（正在听时再点一下 = 提前收音）"""
        self.voice_tap()

    # ---------- 语音输入：唤醒 → 收音 → 转写 → 送签押房 ----------
    def _start_voice(self):
        """唤醒耳力：小吏侧耳倾听，主人说话，静音 1.4 秒自动收"""
        self._voice_running = True
        self._voice_cut = EventLike()
        self.say("🎤 小吏听着呢，主人请讲——（再点一下小吏可提前收音）")
        self._set_state(self.WORK, 10 ** 9)   # 侧耳倾听的姿势
        self._voice_worker = VoiceWorker(self._voice_cut)
        self._voice_worker.done.connect(self._voice_done)
        self._voice_worker.fail.connect(self._voice_fail)
        self._voice_worker.start()

    def _voice_done(self, text):
        self._voice_running = False
        self._set_state(self.GREET, 26)
        text = (text or "").strip()
        if not text:
            self.say("没听清主人的话……再双击一次，小吏重新听！")
            return
        self.say(f"主人说：{text[:26]}{'…' if len(text) > 26 else ''} —— 这就去办！")
        # 送进签押房悬浮窗，走 L2 引擎（该调工具调工具）
        fw = self.open_float("chat")
        chat = fw._panel
        chat.input.setText(text)
        chat.send()

    def _voice_fail(self, err):
        self._voice_running = False
        self._set_state(self.IDLE, 10 ** 9)
        self.say(f"耳力不济：{err[:36]}")

    def contextMenuEvent(self, event):
        """右键 = 展开卷轴差遣（点外部自动收卷）"""
        self._wake()
        if getattr(self, "_deck", None) is None:
            self._deck = ScrollDeck(self)
        self._deck.show()
        self._place_deck()
        self._deck.raise_()

    def _stroll_now(self):
        """奉旨巡街：立刻在桌面上走一圈"""
        self.walk_dir = random.choice([-1, 1])
        self.facing = "right" if self.walk_dir > 0 else "left"
        self._set_state(self.WALK, 45)
        self.say("小吏这就在街上转一圈，替主人踩踩点～")

    # ---------- 面板管理 ----------
    def _ensure_yamen(self):
        """确保总衙门已开张（面板都住在里面，悬浮窗也要从这里借）"""
        yamen = self._panels.get("yamen")
        if yamen is None:
            yamen = YamenWindow(self)
            self._panels["yamen"] = yamen
        return yamen

    def open_panel(self, kind):
        """
        打开总衙门主窗口。kind 为 "yamen" 时停在主页；
        为 "chat"/"memo"/"weather"/"food" 时直接翻到对应功能页。
        """
        yamen = self._ensure_yamen()
        if kind != "yamen":
            yamen.open(kind)
        yamen.showMaximized()
        yamen.raise_()
        yamen.activateWindow()

    # ---------- 衙门悬浮窗（卷轴条目点开的那扇窗） ----------
    def open_float(self, kind):
        """
        弹出某座衙门的悬浮窗：真身面板从总衙门"借"出来嵌进窗里。
        聊天记录、驿卷、账册与总衙门是同一份——关窗即归还，不丢状态。
        """
        self._wake()
        self._ensure_yamen()
        fw = self._floats.get(kind)
        if fw is None:
            fw = FloatPanelWindow(self, kind)
            self._floats[kind] = fw
        fw._embed()
        panel = fw._panel
        if hasattr(panel, "refresh"):        # 驿卷/账册开窗时重读一遍数据
            try:
                panel.refresh()
            except Exception:
                pass
        if not fw.isVisible():
            fw._place_near_pet()
        fw.show()
        fw.raise_()
        fw.activateWindow()
        return fw

    def _recall_panel(self, kind):
        """总衙门要用这一页了：把面板从悬浮窗召回（悬浮窗自动收起）"""
        fw = self._floats.get(kind)
        if fw is not None and fw.isVisible():
            fw._return_panel()
            fw.hide()

    # ---------- 到点提醒 ----------
    def _check_reminders(self):
        # ① 提前十分钟：桌面炸一场烟花，先把主人从沉浸里"叫"出来
        for m in memo_store.due_soon(10):
            fireworks.FireworkOverlay.pop(m["content"], m["time"])
            self._wake()
            self._set_state(self.GREET, 26)
            self.say(
                f"主人！「{m['content']}」还有一刻钟就到期（{m['time']}），"
                f"小吏先替你放个烟花壮壮声势！",
                urgent=m["urgency"] >= 2,
            )

        # ② 到点：气泡正式催办
        for m in memo_store.due_reminders():
            urgent = m["urgency"] >= 2  # 五百里以上用红色气泡
            self.say(
                f"【{m['urgency_name']}】主人！时辰已到，该办「{m['content']}」了！",
                urgent=urgent,
            )
            # 提醒过的事项，顺便刷新驿站面板列表（如果总衙门开着）
            yamen = self._panels.get("yamen")
            if yamen and yamen.isVisible():
                memo = yamen.panels_raw.get("memo")
                if memo:
                    memo.refresh()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 关键开关：默认情况下 Qt 认为"最后一个窗口关了 = 程序该退了"，
    # 这会导致关掉一个功能面板就把整个宠物带走。废掉这个规矩——
    # 只有从菜单点"放小吏们下班"才真的退出。
    app.setQuitOnLastWindowClosed(False)

    # 单实例锁：长安吏只需一位当值。
    # 双开的两个实例各拿一份驿卷/账册的"旧快照"，互相看不见对方的改动——
    # 在 A 窗焚毁的文书，B 窗里还挂着陈影，怎么点都删不掉，正是此患。
    from paths import roaming_dir
    _lock = QLockFile(os.path.join(roaming_dir(), "on_duty.lock"))
    if not _lock.tryLock(100):
        box = QMessageBox(None)
        box.setWindowTitle("长安吏")
        box.setIcon(QMessageBox.Information)
        box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
        box.setText("已有小吏在当值！\n\n长安吏只需一位——请直接差遣桌面上那位即可。\n（此窗 3 秒后自行关闭）")
        QTimer.singleShot(3000, box.accept)   # 无人理会也能自行退下
        box.exec()
        sys.exit(0)

    pet = PetWindow()
    pet.show()
    _preload_voice_model()   # 后台把耳力模型先备好（首次自动下载）
    sys.exit(app.exec())
