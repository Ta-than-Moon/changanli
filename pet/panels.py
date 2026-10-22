# -*- coding: utf-8 -*-
"""
panels.py —— 四座衙门的界面（长安画境版）
聊天签押房 / 长安驿站（备忘录）/ 司天监（天气穿搭）/ 尚食局（美食游玩）

视觉方案「长安画境」：
- 背景取自实拍长安风景：银杏映唐建、灞柳风雪雾桥、暮色钟楼
- 配色：宣纸米白为底，朱砂红为魂，鎏金勾边，黛墨压角
- 字体：楷体作匾额标题（书卷气），微软雅黑作正文（清爽易读）
- 主页填满：画境横幅 + 值房时钟 + 四衙门画卡 + 今日驿卷 + 轮值小吏
"""
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QTextBrowser, QTimeEdit, QDateEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QMessageBox, QStackedWidget, QFrame, QGraphicsDropShadowEffect,
    QMenu,
)
from PySide6.QtCore import Qt, QThread, Signal, QTime, QDate, QTimer, QRectF, QPointF, QByteArray
from PySide6.QtGui import (QColor, QIcon, QPixmap, QPainter, QLinearGradient, QRadialGradient, QFont,
                           QPainterPath, QPen, QBrush, QTransform, QDesktopServices)
from PySide6.QtCore import QUrl

import json
import datetime
import math
import os
import random
import re

import brain
import food_media
import ledger_store
import memo_store
import weather

# ---------- 资源路径 ----------
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_BG = lambda name: os.path.join(_ASSETS, "bg", name)
_SPRITE = lambda name: os.path.join(_ASSETS, "sprites", "male", name)


def cover_pixmap(source, width, height):
    """等比放大裁剪成 cover 效果：铺满容器且不变形（取中景）"""
    pm = QPixmap(source) if isinstance(source, str) else source
    if pm.isNull() or width <= 0 or height <= 0:
        return QPixmap()
    scaled = pm.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


# ---------- 「长安画境」样式表 ----------
CHANGAN_QSS = """
QWidget { background: #f5efe2; color: #322a20;
          font-family: "Microsoft YaHei", "微软雅黑"; font-size: 14px; }
QLabel { background: transparent; }
QLabel#title { font-family: "KaiTi","STKaiti","楷体"; font-size: 26px; font-weight: bold;
               color: #322a20; padding: 0 0 0 14px; margin: 2px 0 6px 0; }
QLabel#titleSub { color: #9a8b6d; font-size: 12px; margin-left: 16px; }
QLabel#hint { color: #9a8b6d; font-size: 12px; }
QLabel#cardTitle { font-family: "KaiTi","STKaiti","楷体"; font-size: 17px; font-weight: bold; color: #8e2f1f; }
QLineEdit, QTimeEdit, QSpinBox { background: #fffdf7; border: 1px solid #ddd0b2;
               border-radius: 8px; padding: 8px 10px; }
QLineEdit:focus, QTimeEdit:focus, QSpinBox:focus { border: 1px solid #b03a2e; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #b03a2e, stop:1 #96301f);
               color: #fdf6e9; border: 1px solid #8a2a1a; border-radius: 9px;
               padding: 9px 18px; font-weight: bold; }
QPushButton:hover { background: #c94a3a; }
QPushButton:pressed { background: #8e2f1f; }
QPushButton:disabled { background: #c9bda6; }
QPushButton#ghost { background: transparent; color: #9e2b22; border: 2px solid #b03a2e; }
QPushButton#ghost:hover { background: #f6e3d5; }
QListWidget, QTextBrowser { background: #fffdf7; border: 1px solid #e3d8bd;
               border-radius: 12px; padding: 8px; }
QSlider::groove:horizontal { height: 8px; background: #e8ddc2; border-radius: 4px; }
QSlider::sub-page:horizontal { background: #b03a2e; border-radius: 4px; }
QSlider::handle:horizontal { background: #b03a2e; width: 22px; height: 22px;
               margin: -8px 0; border-radius: 11px; border: 3px solid #fdf6e9; }
/* ---- 侧栏（画境·暮雾） ---- */
QLabel#brand { color: #f5e6c4; font-family: "KaiTi","STKaiti","楷体";
               font-size: 30px; font-weight: bold; background: transparent; }
QLabel#brandSub { color: #cbb98d; font-size: 11px; background: transparent; }
QPushButton#nav { background: rgba(253, 246, 233, 40); color: #f0e6cf; border: 1px solid transparent;
               border-radius: 10px; text-align: left; padding: 12px 16px; font-size: 15px; }
QPushButton#nav:hover { background: rgba(253, 246, 233, 80); }
QPushButton#nav:checked { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
               stop:0 #b03a2e, stop:1 #c14a36); color: #fff7e8; font-weight: bold;
               border: 1px solid #e0b95c; }
/* ---- 主页画卡（满卡铺图，文字浮于画上） ---- */
QFrame#gateCard { background: #2b241c; border: 1px solid #c9a253; border-radius: 14px; }
QFrame#cardFrame { background: rgba(255, 253, 247, 208); border: 1px solid #e3d8bd; border-radius: 14px; }
QLabel#gateName { font-family: "KaiTi","STKaiti","楷体"; font-size: 20px;
               font-weight: bold; color: #fff7e8; background: transparent; }
QLabel#gateDesc { color: #e8d9b0; font-size: 12px; background: transparent; }
QListWidget, QTextBrowser { background: rgba(255, 253, 247, 115); border: 1px solid #e3d8bd;
               border-radius: 12px; padding: 8px; }
QTextBrowser#summary { border: none; background: transparent; }
QLineEdit, QTimeEdit, QSpinBox { background: rgba(255, 253, 247, 235); }
/* ---- 徽记（加急档位小签） ---- */
QLabel#chip { color: #fff7e8; border-radius: 9px; padding: 3px 12px;
              font-size: 12px; font-weight: bold; }
/* ---- 户部账房 ---- */
QPushButton#kindBtn { background: rgba(255, 253, 247, 220); color: #8e2f1f;
              border: 1px solid #ddd0b2; border-radius: 8px; padding: 7px 18px; }
QPushButton#kindBtn:checked { background: #b03a2e; color: #fff7e8; border: 1px solid #8a2a1a; }
QComboBox, QDateEdit { background: rgba(255, 253, 247, 235); border: 1px solid #ddd0b2;
              border-radius: 8px; padding: 7px 10px; }
QComboBox QAbstractItemView { background: #fffdf7; border: 1px solid #ddd0b2;
              selection-background-color: #b03a2e; selection-color: #fff7e8; }
QLabel#moneyBig { font-family: "KaiTi","STKaiti","楷体"; font-size: 30px; font-weight: bold; }
QLabel#moneySub { color: #8b6f47; font-size: 12px; }
/* ---- 主页轮播窗 ---- */
QPushButton#arrow { background: rgba(255, 253, 247, 220); color: #8e2f1f;
              border: 1px solid #ddd0b2; border-radius: 13px; font-size: 15px; font-weight: bold; }
QPushButton#arrow:hover { background: #b03a2e; color: #fff7e8; }
QPushButton#dot { background: transparent; border: none; color: #dccfae; font-size: 13px; }
QPushButton#dot:checked { color: #b03a2e; font-size: 15px; }
/* ---- 印章 ---- */
QLabel#seal { background: #9e2b22; color: #f7e7c3; border: 2px solid #e0b95c;
              border-radius: 6px; font-family: "KaiTi","STKaiti","楷体";
              font-size: 15px; font-weight: bold; }
"""


def _shadow(widget, blur=22, dy=5):
    """给卡片加一层柔和投影——现代界面立体感的来源"""
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(60, 40, 20, 40))
    widget.setGraphicsEffect(effect)


# ---------- 弹框三兄弟：强制置顶 ----------
# 衙门悬浮窗是置顶窗（Windows 的"置顶层"），普通弹框在"普通层"——
# 层级规则压过父子关系，弹框会被压在自己的悬浮窗底下点不到，
# 而模态弹框又会卡住整个程序。所以所有弹框都必须带上置顶旗。
def box_warning(parent, title, text):
    mb = QMessageBox(QMessageBox.Warning, title, text, QMessageBox.Ok, parent)
    mb.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    mb.exec()


def box_info(parent, title, text):
    mb = QMessageBox(QMessageBox.Information, title, text, QMessageBox.Ok, parent)
    mb.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    mb.exec()


def box_question(parent, title, text):
    """Yes/No 问询（强制置顶），返回 True = 主人点了"是"""
    mb = QMessageBox(QMessageBox.Question, title, text,
                     QMessageBox.Yes | QMessageBox.No, parent)
    mb.setDefaultButton(QMessageBox.No)
    mb.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    return mb.exec() == QMessageBox.Yes


class Worker(QThread):
    """
    跑腿小厮：网络请求（AI 回复、天气查询）比较慢，
    如果直接在主界面等待，窗口会"卡死"。
    所以把慢活交给这个"小厮"在后台线程里跑，跑完用信号通知界面。
    信号用 object 类型：既能递文字，也能递图鉴那种列表数据。
    """
    done = Signal(object)

    def __init__(self, job):
        super().__init__()
        self.job = job

    def run(self):
        try:
            self.done.emit(self.job())
        except Exception as e:
            self.done.emit(f"（小厮办事不利：{e}）")


# ========== 画境底座：铺满风景照 + 渐变压暗的容器 ==========
class SceneWidget(QFrame):
    """把一张风景照做成容器背景（cover 铺满 + 从左至右压暗），文字浮在其上"""
    def __init__(self, image_path, dark=170, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.dark = dark  # 压暗强度（0~255，越大越暗、文字越清楚）
        self._pixmap = QPixmap(image_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        pm = cover_pixmap(self._pixmap, self.width(), self.height())
        if not pm.isNull():
            painter.drawPixmap(0, 0, pm)
        # 左深右浅的横向渐变，保证左侧文字可读、右侧风景透出来
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(24, 18, 12, self.dark))
        grad.setColorAt(0.55, QColor(24, 18, 12, int(self.dark * 0.55)))
        grad.setColorAt(1.0, QColor(24, 18, 12, int(self.dark * 0.25)))
        painter.fillRect(self.rect(), grad)
        # 底部鎏金细线收边
        painter.fillRect(QRectF(0, self.height() - 3, self.width(), 3), QColor("#c9a253"))


# ========== 画卡：满卡铺风景画、文字浮于画上的"衙门画匾" ==========
class GateCard(QFrame):
    clicked = Signal(str)

    def __init__(self, image_path, name, desc, kind):
        super().__init__(objectName="gateCard")
        self.kind = kind
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(230)
        self._image = QPixmap(image_path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 14)
        lay.addStretch()
        self.name_label = QLabel(name, objectName="gateName")
        self.name_label.setAlignment(Qt.AlignHCenter)
        self.desc_label = QLabel(desc, objectName="gateDesc")
        self.desc_label.setAlignment(Qt.AlignHCenter)
        lay.addWidget(self.name_label)
        lay.addWidget(self.desc_label)

    def paintEvent(self, event):
        """满卡铺图：风景照裁剪铺满整张卡，底部压暗渐变托住文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # 圆角裁剪
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        painter.setClipPath(path)
        # 铺满整卡
        pm = cover_pixmap(self._image, self.width(), self.height())
        if not pm.isNull():
            painter.drawPixmap(0, 0, pm)
        # 自上而下压暗：上部透出风景，下部托住文字
        h = self.height()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(20, 15, 10, 30))
        grad.setColorAt(0.5, QColor(20, 15, 10, 85))
        grad.setColorAt(1.0, QColor(20, 15, 10, 195))
        painter.fillRect(self.rect(), grad)
        # 鎏金细边：悬停时提亮
        painter.setClipRect(self.rect())  # 解除裁剪，画完整描边
        pen = QPen(QColor("#e0b95c") if self.underMouse() else QColor(201, 162, 83, 160),
                   2 if self.underMouse() else 1)
        painter.setPen(pen)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.kind)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()


# ========== 四位小吏的轮值表 ==========
XIAOLI = [
    {"key": "zhu",  "name": "主簿·阿卷",   "duty": "总管闲聊"},
    {"key": "yi",   "name": "驿丞·急急",   "duty": "备忘录与提醒"},
    {"key": "tian", "name": "司天·云娘",   "duty": "天气与穿搭"},
    {"key": "shi",  "name": "尚食·小尝",   "duty": "美食与游玩"},
    {"key": "hu",   "name": "户部·阿算",   "duty": "记账与理财"},
]

# 各衙门口头禅（名牌条上的提气话）
PERSONA_MOTTO = {
    "yi":   "驿卷如山，急急替你盯着",
    "tian": "云卷云舒，穿衣不踩雷",
    "shi":  "长安百味，小尝先尝",
    "hu":   "锱铢必较，账账清楚",
}

# 点一下负责人，他随手搭的一句话（各衙门口吻）
PERSONA_QUOTES = {
    "zhu":  ["主人在，卷宗在，阿卷都在。", "衙署大小事，先过阿卷的眼。",
             "主人但说无妨，小吏这就研墨。", "四位同僚各有所长，主人尽管差遣。",
             "今日衙署清净，宜闲聊，宜议事。", "笔墨已备好，主人请吩咐。"],
    "yi":   ["主人莫催，马已备好！", "今日驿道通畅，诸事顺遂。",
             "要加个急？小吏随时点火。", "八百里加急，也得一碗好茶垫底。",
             "文书在手，天下我有。", "主人且歇着，盯梢的活儿交给我。",
             "刚清点过驿卷，一件不少。", "马蹄声远，是好消息近了。",
             "今日份的加急，急急包了！", "驿站不打烊，主人随时吩咐。"],
    "tian": ["今夜云厚，记得添衣。", "小吏观星多年，这身穿搭错不了。",
             "风起了，主人的心事也散了。", "明日或有雨，伞莫离身。",
             "云娘抬头看天，主人低头看路。", "星子眨眼，是在替主人打气。",
             "天光正好，宜出行，宜见面。", "今日的风向，顺主人的意。",
             "若夜里凉，汤婆子比外套管用。", "观天测云，也观主人的气色。"],
    "shi":  ["这碗面，小尝先替你验过了。", "饿着肚子可议不了事。",
             "长安一百零八坊，好吃的都在我肚里。", "主人，该吃点好的了。",
             "遇事不决，先咥一碗。", "今日灶上炖着汤，闻着就舒坦。",
             "甜的解忧，辣的解闷，主人要哪样？", "饭后百步走，小尝陪你走。",
             "新开的铺子，小尝已去探过店了。", "人生大事，吃喝二字。"],
    "hu":   ["一钱一分，皆有去处。", "账清，心就静。",
             "主人今日破费了？让阿算瞧瞧。", "省下的，都是赚下的。",
             "算盘一响，心里亮堂。", "这笔账阿算记着，主人只管花得明白。",
             "月末一对账，方知钱花哪了。", "小账不记，大账就乱。",
             "结余见长，主人持家有方。", "要查哪笔？阿算这就翻账册。"],
}


class PersonaStage(QWidget):
    """
    人物栏的主角：一位会动、会溜达、可逗弄的小吏。

    状态机（五态，姿势之间用运动衔接，看起来连贯）：
    - idle  待机呼吸浮动
    - walk  栏内踱步：左右移动 + 脚步颠簸 + 自动转身（镜像朝向）
    - greet 作揖：点他一下 / AI 答复到达时，先蹦一下再落地
    - work  办差：AI 议事思考中埋头读公文
    - sleep 打盹：约一分钟没人理就打瞌睡，飘 Zzz，碰一下即醒

    互动：点他 = 作揖搭话；按住拖 = 跟着走；久不理 = 打盹。
    外部可调用：busy(True/False) 办差开关；react("greet", 文字) 让他表态。
    """
    # 各小吏的立绘目录：急急（骑马驿丞）、小尝（厨娘）、阿算（账房）、云娘（司天）
    # 都有专属形象了；主簿阿卷与缺的姿势自动回退 male 顶着
    SPRITE_SET = {"zhu": "male", "yi": "yi", "tian": "tian",
                  "shi": "shi", "hu": "hu"}

    def __init__(self, key, on_poke=None, h=148):
        super().__init__()
        self.key = key
        self.on_poke = on_poke
        self.sprite_h = h
        self.setCursor(Qt.PointingHandCursor)
        # 宽 = 高的 1.45 倍（给踱步留跑道）；高 = 立绘 + 气泡区 + 地面
        self.setFixedSize(max(130, int(h * 1.45)), h + 62)
        self.setToolTip("点他作揖 · 拖他溜达")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._load_sprites()

        self._state = "idle"
        self._phase = 0.0
        self._zzz_phase = 0.0
        self._x = (self.width() - self._pm["idle"]["right"].width()) / 2
        self._target_x = self._x
        self._facing = "right"
        self._greet_left = 0      # 作揖还剩多少帧
        self._bubble = ""         # 头顶搭话
        self._bubble_left = 0
        self._idle_ticks = 0      # 多久没人理他
        self._busy = False        # AI 办差中
        self._drag = None         # 拖拽时的抓取偏移
        self._moved = False       # 这次按压有没有拖动

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    # ---------- 立绘加载（多帧动画图横排，缺图就先用男吏顶着） ----------
    def _load_sprites(self):
        folder = self.SPRITE_SET.get(self.key, "male")
        manifest = {}
        mf = os.path.join(_ASSETS, "sprites", folder, "sheet.json")
        if os.path.exists(mf):
            try:
                manifest = json.load(open(mf, encoding="utf-8"))
            except Exception:
                manifest = {}
        self._pm = {}       # 当前帧（对外保持单图形状，绘制逻辑不用改）
        self._frames = {}   # 整套动画帧
        for pose in ("idle", "walk", "greet", "work", "sleep"):
            pm = QPixmap(os.path.join(_ASSETS, "sprites", folder, f"{pose}.png"))
            if pm.isNull():
                pm = QPixmap(os.path.join(_ASSETS, "sprites", "male", f"{pose}.png"))
            pm = pm.scaledToHeight(self.sprite_h, Qt.SmoothTransformation)
            n = int(manifest.get(pose, 1))
            frames = _split_sheet(pm, n)
            self._frames[pose] = {"right": frames,
                                  "left": [f.transformed(QTransform().scale(-1, 1))
                                           for f in frames]}
            self._pm[pose] = {"right": frames[0], "left": self._frames[pose]["left"][0]}
        self._fidx = 0
        self._ftick = 0

    def _advance_frame(self):
        """动画走帧：每隔几拍换一张，约 7 帧/秒"""
        self._ftick += 1
        if self._ftick % 3:
            return
        self._fidx += 1
        for pose, pair in self._frames.items():
            if len(pair["right"]) <= 1:
                continue
            i = self._fidx % len(pair["right"])
            self._pm[pose]["right"] = pair["right"][i]
            self._pm[pose]["left"] = pair["left"][i]

    # ---------- 对外 API ----------
    def busy(self, on=True, text="办差中…"):
        """AI 议事/查询时埋头办公；办完了直起身"""
        self._busy = on
        if on:
            self._wake()
            self._state = "work"
            self._bubble, self._bubble_left = text, 10 ** 9
        else:
            self._state = "idle"
            self._bubble_left = min(self._bubble_left, 25)
        self.update()

    def react(self, kind="greet", text=None):
        """让他表个态：作揖，可选一句话"""
        self._wake()
        if kind == "greet":
            self._greet_left = 26
        if text:
            self._bubble, self._bubble_left = text, 110
        self.update()

    def poke(self):
        """点他一下：作揖 + 随口搭话"""
        self._wake()
        self._greet_left = 26
        line = random.choice(PERSONA_QUOTES.get(self.key, ["主人在。"]))
        self._bubble, self._bubble_left = line, 110
        if self.on_poke:
            self.on_poke(line)
        self.update()

    def _wake(self):
        self._idle_ticks = 0
        if self._state == "sleep":
            self._state = "idle"
            self._bubble, self._bubble_left = "唔…主人回来了？", 60

    # ---------- 状态机节拍 ----------
    def _tick(self):
        self._phase = (self._phase + 0.06) % (2 * math.pi)
        self._advance_frame()
        self._idle_ticks += 1
        if self._greet_left > 0:
            self._greet_left -= 1
        if self._bubble_left > 0:
            self._bubble_left -= 1
            if self._bubble_left == 0:
                self._bubble = ""
        if self._busy:
            self._state = "work"
        elif self._state == "work":
            self._state = "idle"
        # 自由行动（办差 / 被拖 / 作揖 时打断）
        if not self._busy and self._drag is None and self._greet_left <= 0:
            if self._state == "walk":
                dx = self._target_x - self._x
                if abs(dx) <= 3.4:
                    self._state = "idle"
                else:
                    self._facing = "right" if dx > 0 else "left"
                    self._x += 3.2 if dx > 0 else -3.2
            elif self._state == "idle":
                if self._idle_ticks > 2000:          # 约一分半没人理 → 打盹
                    self._state = "sleep"
                elif random.random() < 0.0007:       # 很久才兴起一次，踱两步就回来
                    max_x = self.width() - self._pm["walk"]["right"].width() - 8
                    self._target_x = random.uniform(6, max(8.0, max_x))
                    if abs(self._target_x - self._x) > 24:
                        self._state = "walk"
        if self._state == "sleep":
            self._zzz_phase += 0.045
        self.update()

    # ---------- 鼠标互动 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._wake()
            self._drag = event.pos().x() - self._x
            self._moved = False

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            nx = event.pos().x() - self._drag
            if abs(nx - self._x) > 4:
                self._moved = True
                self._facing = "right" if nx > self._x else "left"
                self._state = "walk"
                max_x = self.width() - self._pm["walk"]["right"].width() - 6
                self._x = max(4.0, min(float(nx), float(max_x)))
                self.update()

    def mouseReleaseEvent(self, event):
        if self._drag is not None:
            if not self._moved:
                self.poke()          # 原地点击 = 作揖搭话
            else:
                self._state = "idle"
            self._drag = None

    def enterEvent(self, event):
        self._wake()
        super().enterEvent(event)

    # ---------- 画 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # 姿势优先级：作揖 > 办差/踱步/打盹 > 待机
        if self._greet_left > 0:
            pose = "greet"
        elif self._state in ("walk", "work", "sleep"):
            pose = self._state
        else:
            pose = "idle"
        pm = self._pm[pose][self._facing]
        ground = h - 8

        # 地面影子（随姿势宽度呼吸）
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 40, 20, 38))
        p.drawEllipse(QPointF(self._x + pm.width() / 2, ground + 2),
                      pm.width() * 0.36, 7)

        # 运动衔接：作揖蹦跳 / 走路颠簸 / 待机呼吸 / 打盹缓慢起伏
        if self._greet_left > 0:
            bob = -12 * math.sin((1 - self._greet_left / 26.0) * math.pi)
        elif pose == "walk":
            bob = -3.5 * abs(math.sin(self._phase * 2.2))
        elif pose == "sleep":
            bob = 1.2 * math.sin(self._phase * 0.6)
        else:
            bob = 3 * math.sin(self._phase)
        # 不同姿势宽度不同，以跑道中心为锚，左右朝向都踩在 _x 附近
        x = int(min(self._x, self.width() - pm.width() - 4))
        y = ground - pm.height() + int(bob)
        p.drawPixmap(x, y, pm)

        # 打盹的 Zzz，忽明忽暗往上飘
        if pose == "sleep":
            alpha = int(120 + 90 * math.sin(self._zzz_phase))
            p.setPen(QColor(110, 90, 60, max(40, alpha)))
            p.setFont(QFont("KaiTi", 13, QFont.Bold))
            p.drawText(int(x + pm.width() * 0.72),
                       int(y + 18 - 8 * math.sin(self._zzz_phase)), "Zzz")

        # 搭话气泡：宣纸底圆角 + 自动换行，快消散时淡出
        if self._bubble:
            f = QFont("KaiTi")
            f.setPointSize(11)
            p.setFont(f)
            max_w = self.width() - 10
            br = p.fontMetrics().boundingRect(0, 0, max_w - 20, 1000,
                                              Qt.TextWordWrap, self._bubble)
            bw = min(max_w, br.width() + 22)
            bh = br.height() + 18
            bx = max(2, (self.width() - bw) // 2)
            alpha = 255 if self._bubble_left > 20 else int(255 * self._bubble_left / 20)
            p.setOpacity(alpha / 255.0)
            p.setPen(QPen(QColor(158, 43, 34), 1.4))
            p.setBrush(QColor(255, 252, 244, 240))
            p.drawRoundedRect(QRectF(bx, 2, bw, bh), 10, 10)
            p.setPen(QColor(110, 30, 20))
            p.drawText(QRectF(bx + 8, 8, bw - 16, bh - 10),
                       Qt.AlignCenter | Qt.TextWordWrap, self._bubble)
            p.setOpacity(1.0)


def _split_sheet(pm, n):
    """横排精灵图按帧数切成逐帧图（n=1 就是老的单帧立绘）"""
    if n <= 1 or pm.isNull():
        return [pm]
    cw = pm.width() // n
    frames = []
    for i in range(n):
        f = pm.copy(i * cw, 0, cw, pm.height())
        if not f.isNull():
            frames.append(f)
    return frames or [pm]


def persona_card(key, on_poke=None, anim=None, caption=""):
    """
    草图版式右上角的「人物栏」：会动的小吏是绝对主角（待机/踱步/作揖/办差/打盹，
    可点可拖），下方依次是名讳职守、提气话、本司小动画。固定本尊，不随当班轮换。
    卡上挂 stage 属性，页面可拿去做联动（议事时办差、事成时作揖）。
    """
    x = next((x for x in XIAOLI if x["key"] == key), None)
    if x is None:
        return QFrame()
    card = QFrame(objectName="cardFrame")
    card.setFixedWidth(258)
    _shadow(card, blur=14, dy=4)
    v = QVBoxLayout(card)
    v.setContentsMargins(10, 10, 10, 10)
    v.setSpacing(4)

    # 人物栏本体：大尺寸会动的小吏
    stage = PersonaStage(key, on_poke=on_poke)
    v.addWidget(stage, 0, Qt.AlignHCenter)
    card.stage = stage  # 页面联动入口：stage.busy() / stage.react()

    name = QLabel(f"{x['name']}")
    name.setAlignment(Qt.AlignHCenter)
    name.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:20px;'
                       "font-weight:bold; color:#8e2f1f;")
    v.addWidget(name)
    duty = QLabel(f"本司当值 · {x['duty']}", objectName="hint")
    duty.setAlignment(Qt.AlignHCenter)
    v.addWidget(duty)

    motto = QLabel(f"「{PERSONA_MOTTO.get(key, '')}」")
    motto.setWordWrap(True)
    motto.setAlignment(Qt.AlignHCenter)
    motto.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:14px; color:#8b6f47;')
    v.addWidget(motto)
    hint = QLabel("点他作揖 · 拖他溜达 · 议事时他会埋头办差", objectName="hint")
    hint.setAlignment(Qt.AlignHCenter)
    v.addWidget(hint)

    if anim is not None:
        v.addSpacing(6)
        if caption:
            cap = QLabel(caption, objectName="hint")
            cap.setAlignment(Qt.AlignHCenter)
            v.addWidget(cap)
        v.addWidget(anim)
    v.addStretch()
    return card



# ========== 各衙门的小动画（栏位底部的"活物"） ==========
class PigeonWidget(QWidget):
    """驿道飞鸽：每隔一阵咕咕飞过；录入文书时也会飞一趟"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._x = -46.0
        self._phase = 0.0
        self._flying = False
        self._wait = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def fly(self):
        self._flying = True
        self._x = -46.0

    def _tick(self):
        self._phase += 0.16
        if self._flying:
            self._x += 4.4
            if self._x > self.width() + 46:
                self._flying = False
        else:
            self._wait += 1
            if self._wait > 250:   # 约十秒一趟
                self._wait = 0
                self.fly()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor(154, 139, 109, 130), 1, Qt.DashLine))
        p.drawLine(6, h - 14, w - 6, h - 14)
        if self._flying:
            y = h * 0.42 + 7 * math.sin(self._phase)
            p.setFont(QFont("Segoe UI Emoji", 18))
            p.drawText(int(self._x), int(y), "🕊")
            p.setFont(QFont("Segoe UI Emoji", 10))
            p.drawText(int(self._x) - 14, int(y) + 10, "✉")


class StarsWidget(QWidget):
    """司天监星斗：点点星光各自明灭，偶有一颗格外亮"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._stars = [(random.random(), random.uniform(0.15, 0.85),
                        random.uniform(1.2, 2.6), random.uniform(0.6, 1.6),
                        random.uniform(0, 6.28)) for _ in range(16)]
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(70)

    def _tick(self):
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        for i, (fx, fy, r, speed, offset) in enumerate(self._stars):
            tw = 0.5 + 0.5 * math.sin(self._phase * speed + offset)
            alpha = int(70 + 160 * tw * tw)
            p.setBrush(QColor(201, 162, 83, alpha))
            p.drawEllipse(QPointF(fx * w, fy * h), r, r)
            if tw > 0.94:  # 特别亮时画个小十字光
                p.setPen(QPen(QColor(201, 162, 83, alpha), 1))
                p.drawLine(QPointF(fx * w - r * 2.4, fy * h), QPointF(fx * w + r * 2.4, fy * h))
                p.drawLine(QPointF(fx * w, fy * h - r * 2.4), QPointF(fx * w, fy * h + r * 2.4))
                p.setPen(Qt.NoPen)


class SteamBowlWidget(QWidget):
    """尚食局热汤：一碗面，蒸汽袅袅上升"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._phase = (self._phase + 0.09) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, by = w / 2, h - 12
        # 碗：半圆 + 碗沿
        p.setPen(QPen(QColor(158, 43, 34, 220), 2))
        p.setBrush(QColor(255, 253, 247, 200))
        p.drawChord(QRectF(cx - 26, by - 20, 52, 36), 180 * 16, 180 * 16)
        p.drawLine(int(cx - 26), int(by - 2), int(cx + 26), int(by - 2))
        # 三缕蒸汽：摇摆着上升变淡
        for i in range(3):
            sx = cx - 14 + i * 14
            drift = 5 * math.sin(self._phase + i * 1.1)
            path = QPainterPath(QPointF(sx, by - 22))
            path.quadTo(QPointF(sx + drift, by - 32), QPointF(sx - drift, by - 42))
            path.quadTo(QPointF(sx - drift * 1.6, by - 48), QPointF(sx + drift * 0.6, by - 56))
            alpha = int(150 - i * 30 + 40 * math.sin(self._phase * 1.3 + i))
            p.setPen(QPen(QColor(154, 139, 109, max(60, alpha)), 1.8))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)


class CoinWidget(QWidget):
    """户部铜钱：外圆内方，金光缓缓流转"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy, r = w / 2, h / 2 - 2, 20
        # 小钱串影子
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(154, 139, 109, 60))
        p.drawEllipse(QPointF(cx + 2, cy + 16), r * 0.9, 4)
        # 铜钱本体：金圆
        grad = QRadialGradient(QPointF(cx - 6, cy - 6), r * 2)
        grad.setColorAt(0, QColor(240, 208, 120))
        grad.setColorAt(1, QColor(170, 128, 60))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(122, 92, 40), 1.6))
        p.drawEllipse(QPointF(cx, cy), r, r)
        # 内方孔
        p.setBrush(QColor(245, 239, 226))
        p.setPen(QPen(QColor(122, 92, 40), 1.4))
        p.drawRect(QRectF(cx - 6.5, cy - 6.5, 13, 13))
        # 流转的金光：一段扫过的高光弧
        p.setPen(QPen(QColor(255, 244, 200, 230), 3))
        start = int((self._phase * 57.3) % 360)
        p.drawArc(QRectF(cx - r + 3, cy - r + 3, (r - 3) * 2, (r - 3) * 2),
                  start * 16, 80 * 16)

# 加急档位配色（小签底色）
URGENCY_COLORS = ["#8b6f47", "#b3541e", "#c0392b", "#8e0000"]


class BasePanel(QWidget):
    """所有衙门的共同底座：标题 + 统一关窗行为；可选整页背景画"""
    def __init__(self, title_text, sub_text="", bg_image=None, bg_scrim=165, center_title=False,
                 animated=False):
        super().__init__()
        self.setWindowTitle(title_text)
        self.setStyleSheet(CHANGAN_QSS)
        self._workers = []  # 防止小厮（线程）被垃圾回收
        # 整页背景画：风景照铺满 + 一层宣纸色薄纱保证文字可读
        self._bg_pixmap = QPixmap(bg_image) if bg_image else None
        self._bg_scrim = bg_scrim
        # 动态背景：底图（街道/桥）定住不动，只在上面飘云雾
        self._animated = animated
        self._phase = 0.0
        self._base_pm = None      # 静止底图
        self._mist_layers = []    # 预渲染的雾层（模糊+提亮的照片）
        self._clouds = []         # 团雾参数
        self._anim_timer = None
        if animated:
            self._anim_timer = QTimer(self)
            self._anim_timer.timeout.connect(self._anim_tick)
            self._anim_timer.start(40)  # 25 帧/秒，够顺滑又不费电

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 18)
        outer.setSpacing(10)
        head = QVBoxLayout()
        head.setSpacing(0)
        title_label = QLabel(title_text, objectName="title")
        if center_title:
            # 匾额式居中标题（如「长安驿站」），朱砂大字
            title_label.setAlignment(Qt.AlignHCenter)
            title_label.setStyleSheet(
                'font-family:"KaiTi","STKaiti","楷体"; font-size:34px; font-weight:bold;'
                "color:#b03a2e; margin:0 0 2px 0;")
        head.addWidget(title_label)
        if sub_text:
            sub_label = QLabel(sub_text, objectName="titleSub")
            if center_title:
                sub_label.setAlignment(Qt.AlignHCenter)
            head.addWidget(sub_label)
        outer.addLayout(head)
        # 标题下的鎏金细线（居中标题时用对称渐变）
        line = QFrame()
        line.setFixedHeight(2)
        if center_title:
            line.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                               "stop:0 transparent, stop:0.5 #c9a253, stop:1 transparent);"
                               "border:none;")
        else:
            line.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                               "stop:0 #c9a253, stop:0.6 #e0b95c66, stop:1 transparent);"
                               "border:none;")
        outer.addWidget(line)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)

    def _anim_tick(self):
        """动态背景节拍：云雾相位缓缓前进，重绘一帧"""
        self._phase = (self._phase + 0.016) % (2 * math.pi)
        self.update()

    def _build_scene(self):
        """准备好"静止底图 + 两层飘动雾 + 几团白气"这套布景"""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        self._base_pm = cover_pixmap(self._bg_pixmap, w, h)

        # 雾层：把照片缩小再放大 = 廉价高斯模糊；再糊一层白，就成了云气
        # 上下浓、中间透（DestinationIn 竖向渐变遮罩），桥和街道不被糊死
        self._mist_layers = []
        recipes = (
            # 缩小倍数, 加宽比例, 泛白浓度, 不透明度, 漂移速度, 相位
            (8, 1.55, 62, 0.42, 1.0, 0.0),
            (22, 1.30, 122, 0.34, -0.65, 2.2),
        )
        for div, widen, whiten, alpha, speed, phase in recipes:
            small = self._base_pm.scaled(max(1, w // div), max(1, h // div),
                                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            mw, mh = int(w * widen), int(h * 1.06)
            mist = small.scaled(mw, mh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            p = QPainter(mist)
            p.fillRect(0, 0, mw, mh, QColor(255, 252, 242, whiten))
            veil = QLinearGradient(0, 0, 0, mh)
            veil.setColorAt(0.00, QColor(255, 255, 255, 235))
            veil.setColorAt(0.32, QColor(255, 255, 255, 70))
            veil.setColorAt(0.62, QColor(255, 255, 255, 105))
            veil.setColorAt(1.00, QColor(255, 255, 255, 245))
            p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p.fillRect(0, 0, mw, mh, QBrush(veil))
            p.end()
            self._mist_layers.append((mist, alpha, speed, phase))

        # 团雾：几坨白气在山腰慢慢横移，营造"云雾缭绕"
        self._clouds = [
            # x, y, 半径x, 半径y, 浓度, 速度, 相位
            (0.10, 0.62, 0.34, 0.13, 70, 1.0, 0.0),
            (0.55, 0.52, 0.40, 0.11, 58, -0.75, 1.7),
            (0.80, 0.72, 0.30, 0.10, 66, 0.9, 3.1),
            (0.32, 0.80, 0.42, 0.12, 52, -0.55, 4.4),
            (0.68, 0.30, 0.36, 0.10, 46, 0.7, 5.2),
        ]

    def _paint_clouds(self, painter):
        w, h = self.width(), self.height()
        painter.setPen(Qt.NoPen)
        for fx, fy, frx, fry, alpha, speed, phase in self._clouds:
            drift = 0.055 * math.sin(self._phase * speed + phase)
            cx = (fx + drift) * w
            cy = (fy + 0.012 * math.cos(self._phase * speed * 0.8 + phase)) * h
            rx = frx * w
            ry = fry * h
            grad = QRadialGradient(QPointF(0, 0), rx)
            grad.setColorAt(0.0, QColor(255, 255, 252, alpha))
            grad.setColorAt(0.55, QColor(255, 255, 250, int(alpha * 0.55)))
            grad.setColorAt(1.0, QColor(255, 255, 250, 0))
            painter.save()
            painter.translate(cx, cy)
            painter.scale(1.0, ry / rx)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(0, 0), rx, rx)
            painter.restore()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._base_pm = None   # 尺寸变了，布景作废，下次重绘时重建
        self._mist_layers = []

    def showEvent(self, event):
        super().showEvent(event)
        if self._animated and self._anim_timer:
            self._anim_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._animated and self._anim_timer:
            self._anim_timer.stop()  # 页面看不见时让画也歇口气

    def paintEvent(self, event):
        """整页背景画：静止风景 + 飘动云雾 + 宣纸薄纱，让文字内容可读"""
        if self._bg_pixmap is None or self._bg_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._animated:
            w, h = self.width(), self.height()
            if self._base_pm is None or self._base_pm.width() != w or self._base_pm.height() != h:
                self._build_scene()
            if self._base_pm is None:
                return
            # ① 底图定死：桥、街道、车马一动不动
            painter.drawPixmap(0, 0, self._base_pm)
            # ② 两层雾：一快一慢、一正一反地漫过画面
            for mist, alpha, speed, phase in self._mist_layers:
                extra_x = max(0, mist.width() - w)
                extra_y = max(0, mist.height() - h)
                dx = extra_x / 2 + extra_x * 0.44 * math.sin(self._phase * speed + phase)
                dy = extra_y / 2 + extra_y * 0.30 * math.cos(self._phase * speed * 0.7 + phase)
                painter.setOpacity(alpha)
                painter.drawPixmap(int(-dx), int(-dy), mist)
            painter.setOpacity(1.0)
            # ③ 团雾：几坨白气在山腰缓缓游走
            self._paint_clouds(painter)
        else:
            pm = cover_pixmap(self._bg_pixmap, self.width(), self.height())
            painter.drawPixmap(0, 0, pm)
        scrim = QColor(245, 239, 226, self._bg_scrim)
        painter.fillRect(self.rect(), scrim)

    def run_job(self, button, job, on_done):
        """统一的"派小厮跑腿"流程：按钮变灰 → 后台执行 → 恢复按钮 + 展示结果"""
        button.setEnabled(False)
        button.setText("小吏奔走中…")
        worker = Worker(job)
        self._workers.append(worker)

        def finish(text):
            button.setEnabled(True)
            on_done(text)

        worker.done.connect(finish)
        worker.start()


class AskDock(QWidget):
    """
    各衙门共用的「与小吏议事」对话区。

    三件事：
    1. 多轮追问——带着本页当前数据当上下文，主人可以一直追问"为什么/再详细点"
    2. 真能改——小吏可以在回复末尾写一行 [[指令]]，本页照办（改金额、删流水、改时辰…）
    3. 结果回流——排程、献策等结果也落在这块对话区里，不至于散落各处
    """
    def __init__(self, persona_key, title, placeholder, hint="",
                 context_fn=None, command_fn=None, view_height=96, speaker=""):
        super().__init__()
        self.persona_key = persona_key
        # 议事区固定由本衙门负责人回话，名讳写死，不随当班小吏轮换
        self.speaker = speaker or next((x["name"] for x in XIAOLI if x["key"] == persona_key), "小吏")
        self.context_fn = context_fn or (lambda: "")
        self.command_fn = command_fn
        self.history = []
        self._workers = []
        self._last_prompt = ""
        self.stage = None   # 页面可把人物栏挂上来：议事时小吏埋头办差，答复到作揖相迎

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        head = QHBoxLayout()
        head.addWidget(QLabel(title, objectName="cardTitle"))
        head.addStretch()
        self.hint_label = QLabel(hint, objectName="hint")
        head.addWidget(self.hint_label)
        lay.addLayout(head)

        self.view = QTextBrowser()
        self.view.setMinimumHeight(view_height)
        lay.addWidget(self.view, 1)

        # 输入栏是独立部件：默认跟在议事区下面，detach_input() 可拆到页面底部
        self.input_row = QWidget()
        row = QHBoxLayout(self.input_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.returnPressed.connect(self.send)
        self.btn = QPushButton("议事")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(self.btn)
        lay.addWidget(self.input_row)

    def detach_input(self):
        """把输入栏从议事区拆下来（草图版式：议事在中、对话输入在页底）"""
        self.layout().removeWidget(self.input_row)
        return self.input_row

    # ---------- 发问 ----------
    def send(self):
        q = self.input.text().strip()
        if not q:
            return
        self.input.clear()
        self.send_text(q)

    def send_text(self, q, echo=None):
        """以指定内容发问（外部如"到期文书献策"也走这里）——L2：带工具调用"""
        ctx = ""
        try:
            ctx = (self.context_fn() or "").strip()
        except Exception:
            ctx = ""
        # 议事须知：让对话"接得上"——有旧结果就在旧基础上改进，不要推倒重来
        tone = ("【议事须知】你正在与主人议事：回复可以展开三到六句，围绕主人的问题深入，"
                "不要客套开场白；上面若已有旧结果，请在其基础上继续改进、增补或微调，"
                "除非主人明说重来，否则不要推翻整份方案。")
        prompt = f"{ctx}\n{tone}\n\n——主人的话：{q}" if ctx else f"{tone}\n\n——主人的话：{q}"
        self._last_prompt = prompt
        self.view.append(f"<p><b style='color:#2f3a4a'>主人：</b>{echo or q}</p>")
        # L2 引擎：主人吩咐的实事，AI 自己调衙门工具去办（跨衙门也行）
        self._run(lambda: brain.chat_with_tools(self.persona_key, prompt, self.history))

    def _run(self, job):
        self.btn.setEnabled(False)
        self.btn.setText("小吏奔走中…")
        if self.stage:
            self.stage.busy(True)          # 人物栏：埋头办差
        worker = Worker(job)
        self._workers.append(worker)
        worker.done.connect(self._finish)
        worker.start()

    def _finish(self, result):
        """L2 结果：(答复文本, 工具轨迹)；旧 str 也兼容"""
        reply, trace = result if isinstance(result, tuple) else (result, [])
        self.btn.setEnabled(True)
        self.btn.setText("议事")
        if self.stage:
            self.stage.busy(False)         # 办完了，起身
            self.stage.react("greet")      # 作揖相迎
        # ⓪ 工具回执：这轮 AI 调了哪些衙门工具、各办成什么
        for title, _name, outcome in trace:
            self.view.append(f"<p style='color:#5c7a3a;'>🔧 {title} —— "
                             f"{outcome.replace(chr(10), '；')[:160]}</p>")
        # ① 摘出并执行小吏写下的指令 [[...]]
        done_msgs = []
        for raw in re.findall(r"\[\[(.*?)\]\]", reply):
            if not self.command_fn:
                break
            try:
                msg = self.command_fn(raw.strip())
            except Exception as e:
                msg = f"指令没办成（{e}）"
            if msg:
                done_msgs.append(msg)
        # ② 正文去掉指令行后展示
        clean = re.sub(r"\[\[.*?\]\]", "", reply).strip()
        if clean:
            self.view.append(f"<p><b style='color:#7a2015'>{self.speaker}：</b>{clean}</p>")
        for m in done_msgs:
            self.view.append(f"<p style='color:#5c7a3a;'>✅ 小吏已照办：{m}</p>")
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())
        # ③ 记入上下文（最多留 10 轮）
        self.history.append({"role": "user", "content": self._last_prompt})
        self.history.append({"role": "assistant", "content": reply})
        self.history = self.history[-20:]

    # ---------- 外部追加一条 ----------
    def note(self, html):
        self.view.append(html)
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())


class FeatureCarousel(QFrame):
    """
    主页右侧的「衙署轮播」：五座衙门轮流登场。
    - 左右箭头 / 下方圆点 / 鼠标左右拖动 / 滚轮 都能翻页
    - 无人操作时每 6 秒自动翻一张，鼠标悬停即暂停
    - 每页显示该衙门的实时数据摘要，点「进入」直达
    """
    SLIDES = [
        ("chat", "💬", "签押房", "主簿·阿卷 · 闲话聊天 有问必答", "ginkgo_eaves.jpg"),
        ("memo", "📮", "长安驿站", "驿丞·急急 · 备忘排程 到点提醒", "misty_bridge.jpg"),
        ("weather", "🌤", "司天监", "司天·云娘 · 观天象 指点穿搭", "ginkgo_tower.jpg"),
        ("food", "🍜", "尚食局", "尚食·小尝 · 荐美食 谋游玩", "xian_food.jpg"),
        ("ledger", "🧾", "户部·记账", "户部·阿算 · 收支入册 月末结余", "bell_tower_night.jpg"),
    ]

    def __init__(self, yamen):
        super().__init__(objectName="cardFrame")
        self.yamen = yamen
        self.index = 0
        self._drag_x = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(QLabel("衙署轮播", objectName="cardTitle"))
        head.addStretch()
        self.prev_btn = QPushButton("‹", objectName="arrow")
        self.next_btn = QPushButton("›", objectName="arrow")
        for b in (self.prev_btn, self.next_btn):
            b.setFixedSize(26, 26)
            b.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self.prev)
        self.next_btn.clicked.connect(self.next)
        head.addWidget(self.prev_btn)
        head.addWidget(self.next_btn)
        lay.addLayout(head)

        self.stack = QStackedWidget()
        self.info_labels = {}
        for kind, icon, name, desc, img in self.SLIDES:
            self.stack.addWidget(self._page(kind, icon, name, desc, img))
        lay.addWidget(self.stack, 1)

        dots = QHBoxLayout()
        dots.setSpacing(6)
        dots.addStretch()
        self.dots = []
        for kind, _i, _n, _d, _m in self.SLIDES:
            dot = QPushButton("●", objectName="dot")
            dot.setCheckable(True)
            dot.setFixedSize(18, 18)
            dot.setCursor(Qt.PointingHandCursor)
            dot.clicked.connect(lambda _=False, k=kind: self.go(self._kind_index(k)))
            dots.addWidget(dot)
            self.dots.append(dot)
        dots.addStretch()
        lay.addLayout(dots)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next)
        self.timer.start(6000)
        self.go(0)
        self.refresh()

    # ---------- 页面 ----------
    def _page(self, kind, icon, name, desc, img):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        cover = SceneWidget(_BG(img), dark=105)
        cover.setFixedHeight(92)
        cl = QVBoxLayout(cover)
        cl.setContentsMargins(14, 8, 14, 8)
        cl.setSpacing(2)
        ic = QLabel(icon)
        ic.setStyleSheet("font-size:24px; background:transparent;")
        nm = QLabel(name)
        nm.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:19px;'
                         "font-weight:bold; color:#fff7e8; background:transparent;")
        cl.addWidget(ic)
        cl.addWidget(nm)
        cl.addStretch()
        lay.addWidget(cover)

        d = QLabel(desc, objectName="hint")
        d.setWordWrap(True)
        lay.addWidget(d)

        info = QLabel("—")
        info.setWordWrap(True)
        info.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:14px;'
                           "color:#8e2f1f;")
        info.setAlignment(Qt.AlignTop)
        lay.addWidget(info, 1)
        self.info_labels[kind] = info

        enter = QPushButton("进入 →")
        enter.setCursor(Qt.PointingHandCursor)
        enter.clicked.connect(lambda _=False, k=kind: self.yamen.open(k))
        lay.addWidget(enter)
        return w

    # ---------- 翻页 ----------
    def _kind_index(self, kind):
        for i, s in enumerate(self.SLIDES):
            if s[0] == kind:
                return i
        return 0

    def go(self, i):
        self.index = i % len(self.SLIDES)
        self.stack.setCurrentIndex(self.index)
        for n, dot in enumerate(self.dots):
            dot.setChecked(n == self.index)

    def next(self):
        self.go(self.index + 1)

    def prev(self):
        self.go(self.index - 1)

    # ---------- 交互：拖动 / 滚轮 / 悬停暂停 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_x = event.pos().x()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_x is not None:
            delta = event.pos().x() - self._drag_x
            if abs(delta) > 45:
                self.prev() if delta > 0 else self.next()
            self._drag_x = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        self.prev() if event.angleDelta().y() > 0 else self.next()
        super().wheelEvent(event)

    def enterEvent(self, event):
        self.timer.stop()          # 鼠标进来就不再自动翻，免得抢戏
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.timer.start(6000)
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(6000)
        self.refresh()

    # ---------- 数据摘要 ----------
    def refresh(self):
        pet = self.yamen.pet
        try:
            self.info_labels["chat"].setText(f"当值：{pet.persona_name()}")
        except Exception:
            pass
        try:
            today = datetime.date.today().isoformat()
            pend = sorted(
                [m for m in memo_store.load()
                 if m["date"] == today and not m.get("done") and not m["reminded"]],
                key=lambda m: (-m["urgency"], m["time"]))
            if pend:
                self.info_labels["memo"].setText(
                    f"今日待办 {len(pend)} 件｜最急：{pend[0]['content']}（{pend[0]['time']}）")
            else:
                self.info_labels["memo"].setText("今日驿卷皆已办讫，主人清闲。")
        except Exception:
            pass
        for kind in ("weather", "food"):
            try:
                panel = self.yamen.panels_raw.get(kind)
                city = panel.city_edit.text().strip() if panel else "西安"
                extra = getattr(panel, "_last_summary", "")
                self.info_labels[kind].setText(
                    f"当前城郭：{city}" + (f"｜{extra}" if extra else ""))
            except Exception:
                pass
        try:
            inc, exp, bal = ledger_store.totals(ledger_store.month_records())
            self.info_labels["ledger"].setText(
                f"本月支出 ¥{exp:,.2f}｜结余 ¥{bal:,.2f}")
        except Exception:
            pass


# ========== ⓪ 总衙门：应用主窗口（画境侧栏 + 主页 + 页面跳转） ==========
class YamenWindow(QWidget):
    """
    长安吏的主窗口：
    左侧暮雾画境导航栏（常驻）+ 右侧内容区（画境横幅、画卡、驿卷）。
    """
    NAV = [
        ("home", "🏛  总衙门"),
        ("chat", "💬  签押房"),
        ("memo", "📮  长安驿站"),
        ("weather", "🌤  司天监"),
        ("food", "🍜  尚食局"),
        ("ledger", "🧾  户部·记账"),
    ]
    GATES = [
        ("💬 签押房", "主簿·阿卷 · 闲话聊天 有问必答", "chat", "ginkgo_eaves.jpg"),
        ("📮 长安驿站", "驿丞·急急 · 备忘排程 到点提醒", "memo", "misty_bridge.jpg"),
        ("🌤 司天监", "司天·云娘 · 观天象 指点穿搭", "weather", "ginkgo_tower.jpg"),
        ("🍜 尚食局", "尚食·小尝 · 荐美食 谋游玩", "food", "xian_food.jpg"),
        ("🧾 户部记账", "户部·阿算 · 收支入册 月末结余", "ledger", "bell_tower_night.jpg"),
        ("🔄 换班小吏", "五位小吏轮值，换个当差的", "switch", "misty_dawn.jpg"),
    ]
    WEEK = ["一", "二", "三", "四", "五", "六", "日"]

    def __init__(self, pet):
        super().__init__()
        self.pet = pet
        self.setWindowTitle("长安吏 · 总衙门")
        icon = os.path.join(_ASSETS, "icon.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setStyleSheet(CHANGAN_QSS)
        self.resize(1180, 760)
        self.setMinimumSize(980, 660)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 左侧：暮雾画境导航栏（风景照压暗铺满） ----
        self.sidebar = SceneWidget(_BG("misty_dawn.jpg"), dark=185)
        self.sidebar.setFixedWidth(226)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 26, 18, 16)
        side.setSpacing(6)
        brand_row = QHBoxLayout()
        brand_row.addWidget(QLabel("長安吏", objectName="brand"))
        seal = QLabel("印", objectName="seal")
        seal.setFixedSize(30, 30)
        seal.setAlignment(Qt.AlignCenter)
        brand_row.addSpacing(6)
        brand_row.addWidget(seal)
        brand_row.addStretch()
        side.addLayout(brand_row)
        side.addWidget(QLabel("桌面宠物系统 · CHANG'AN", objectName="brandSub"))
        side.addSpacing(24)

        self.stack = QStackedWidget()
        self.pages = {}
        self.nav_buttons = {}
        for kind, label in self.NAV:
            btn = QPushButton(label, objectName="nav")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=kind: self.open(k))
            side.addWidget(btn)
            self.nav_buttons[kind] = btn
        side.addStretch()
        switch = QPushButton("🔄  换班小吏", objectName="nav")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(pet.switch_xiaoli)
        side.addWidget(switch)
        side.addWidget(QLabel("长安县衙出品", objectName="brandSub"))
        root.addWidget(self.sidebar)

        # ---- 右侧：内容区（卡片堆） ----
        self.home = self._build_home()
        self.pages["home"] = self.home
        self.stack.addWidget(self.home)

        self.panels_raw = panel_map = {
            "chat": ChatPanel(pet),
            "memo": MemoPanel(pet),
            "weather": WeatherPanel(pet.default_city),
            "food": FoodPanel(pet.default_city),
            "ledger": LedgerPanel(pet),
        }
        for kind in ("chat", "memo", "weather", "food", "ledger"):
            self.pages[kind] = panel_map[kind]
            self.stack.addWidget(panel_map[kind])
        root.addWidget(self.stack, 1)

        # 行程总管的四衙门广播：travel_plan 跑完，各面板自动换城并填充结果。
        # 注意：travel_plan 在后台线程执行，广播的 Qt 操作必须转投主线程——
        # 用一个信号当"渡船"：线程里 emit，主线程槽里安全地刷界面。
        import brain as _brain
        from PySide6.QtCore import QObject

        class _Bridge(QObject):
            relay = Signal(dict)

        self._yamen_bridge = _Bridge()
        self._yamen_bridge.relay.connect(self._apply_yamen_broadcast)

        def _on_weather(payload):
            self._yamen_bridge.relay.emit({"kind": "weather", **payload})

        def _on_food(payload):
            self._yamen_bridge.relay.emit({"kind": "food", **payload})

        def _on_memo(payload):
            self._yamen_bridge.relay.emit({"kind": "memo", **payload})

        def _on_ledger(payload):
            self._yamen_bridge.relay.emit({"kind": "ledger", **payload})

        def _on_memo_refresh(_payload):
            self._yamen_bridge.relay.emit({"kind": "memo_refresh"})

        def _on_ledger_refresh(_payload):
            self._yamen_bridge.relay.emit({"kind": "ledger_refresh"})

        _brain.register_yamen_broadcast("weather", _on_weather)
        _brain.register_yamen_broadcast("food", _on_food)
        _brain.register_yamen_broadcast("memo", _on_memo)
        _brain.register_yamen_broadcast("ledger", _on_ledger)
        _brain.register_yamen_broadcast("memo_refresh", _on_memo_refresh)
        _brain.register_yamen_broadcast("ledger_refresh", _on_ledger_refresh)

        self.open("home")
        self._start_clock()

    def _apply_yamen_broadcast(self, payload):
        """主线程侧：把某座衙门的结果落到对应面板"""
        kind = payload.get("kind")
        text, city = payload.get("text", ""), payload.get("city", "")
        panel_map = self.panels_raw
        if kind == "memo_refresh":
            panel_map["memo"].refresh()           # 数据层变了：驿卷立即重画
        elif kind == "ledger_refresh":
            panel_map["ledger"].refresh()         # 账册立即重画
        elif kind == "weather":
            wp = panel_map["weather"]
            wp.city_edit.setText(city)
            wp._show("【行程总管·司天监】\n" + text)
        elif kind == "food":
            fp = panel_map["food"]
            fp.city_edit.setText(city)
            fp._show("【行程总管·尚食局荐】\n" + text)
        elif kind == "memo":
            mp = panel_map["memo"]
            mp.dock.view.append(
                f"<p><b>🏛 行程总管 · {city}之旅：</b></p>"
                f"<p>{text.replace(chr(10), '<br>')}</p><br>")
            mp.dock.view.verticalScrollBar().setValue(
                mp.dock.view.verticalScrollBar().maximum())
            mp.refresh()
        elif kind == "ledger":
            lp = panel_map["ledger"]
            lp.dock.view.append(
                f"<p><b>🏛 行程总管 · {city}之预算：</b></p>"
                f"<p>{text.replace(chr(10), '<br>')}</p><br>")
            lp.dock.view.verticalScrollBar().setValue(
                lp.dock.view.verticalScrollBar().maximum())

    # ---------- 值房时钟 ----------
    def _start_clock(self):
        """值房时钟：每秒走字"""
        clock = QTimer(self)
        clock.timeout.connect(self._tick_clock)
        clock.start(1000)
        self._tick_clock()

    # ---------- 主页搭建 ----------
    def _build_home(self):
        home = QWidget()
        layout = QVBoxLayout(home)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        # 画境横幅：银杏映唐建 + 匾额 + 值房时钟
        banner = SceneWidget(_BG("ginkgo_court.jpg"), dark=175)
        banner.setFixedHeight(196)
        _shadow(banner, blur=24, dy=6)
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(30, 22, 30, 18)
        left = QVBoxLayout()
        left.addStretch()
        t = QLabel("長安吏 · 總衙門", objectName="heroTitle")
        t.setStyleSheet('color:#f5e6c4; font-family:"KaiTi","STKaiti","楷体";'
                        "font-size:36px; font-weight:bold; background:transparent;")
        left.addWidget(t)
        s = QLabel("长安县衙 AI 衙署 ｜ 四位小吏轮值当差 ｜ 聊天 · 备忘 · 观天 · 荐味",
                   objectName="heroSub")
        s.setStyleSheet("color:#e5cfa4; font-size:13px; background:transparent;")
        left.addWidget(s)
        left.addStretch()
        bl.addLayout(left, 3)
        right = QVBoxLayout()
        right.addStretch()
        self.clock_label = QLabel("--:--")
        self.clock_label.setStyleSheet(
            'color:#f5e6c4; font-family:"KaiTi","STKaiti","楷体";'
            "font-size:44px; font-weight:bold; background:transparent;")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right.addWidget(self.clock_label)
        self.date_label = QLabel("大唐历 · 今日")
        self.date_label.setStyleSheet(
            "color:#e5cfa4; font-size:13px; background:transparent;")
        self.date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right.addWidget(self.date_label)
        right.addStretch()
        bl.addLayout(right, 2)
        layout.addWidget(banner)

        # 中段：左 3×2 画卡（五衙门 + 换班），右 五功能轮播窗
        mid = QHBoxLayout()
        mid.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.gate_cards = {}
        for i, (gate, desc, kind, img) in enumerate(self.GATES):
            card = GateCard(_BG(img), gate, desc, kind)
            card.clicked.connect(self.open)
            _shadow(card, blur=18, dy=4)
            grid.addWidget(card, i // 3, i % 3)
            self.gate_cards[kind] = card
        mid.addLayout(grid, 3)

        # 右侧：五座衙门的轮播窗（可左右滑动 / 点圆点 / 自动播放）
        self.carousel = FeatureCarousel(self)
        _shadow(self.carousel, blur=18, dy=4)
        self.carousel.setMinimumWidth(300)
        self.carousel.setMaximumWidth(360)
        mid.addWidget(self.carousel, 2)
        layout.addLayout(mid, 1)

        # 底部：左 motto，右署名
        bottom = QHBoxLayout()
        motto = QLabel("「案牍劳形，不如小吏代劳。」", objectName="hint")
        motto.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:14px; color:#8b6f47;')
        bottom.addWidget(motto)
        bottom.addStretch()
        bottom.addWidget(QLabel("—— 长安县衙 敬呈", objectName="hint"))
        layout.addLayout(bottom)
        return home

    # ---------- 时钟 ----------
    def _tick_clock(self):
        now = datetime.datetime.now()
        self.clock_label.setText(now.strftime("%H:%M"))
        week = "周" + self.WEEK[now.weekday()]
        self.date_label.setText(f"{now.year}年{now.month}月{now.day}日 · {week}")

    # ---------- 页面跳转（侧边栏 + 主页画卡共用同一入口） ----------
    def open(self, kind):
        """翻到某页，并让侧边栏对应按钮高亮"""
        if kind == "switch":                     # 画卡上的「换班小吏」
            self.pet.switch_xiaoli()
            self.refresh_summary()
            return
        if kind == "home":
            self.refresh_summary()
        # 这页若正被衙门悬浮窗借用，先召回面板（悬浮窗自动收起）
        if kind in self.panels_raw:
            recall = getattr(self.pet, "_recall_panel", None)
            if recall:
                recall(kind)
        self.stack.setCurrentWidget(self.pages[kind])
        # 驿卷/账册翻到这页时重读一遍磁盘——别处的改动（悬浮窗焚毁、小吏议事）即时可见
        page = self.pages[kind]
        if kind in ("memo", "ledger") and hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception:
                pass
        for k, b in self.nav_buttons.items():
            b.setChecked(k == kind)

    def go_home(self):
        self.open("home")

    def showEvent(self, event):
        """每次窗口被打开/唤醒，若停在主页就刷新驿卷摘要"""
        super().showEvent(event)
        if self.stack.currentWidget() == self.home:
            self.refresh_summary()

    def refresh_summary(self):
        """主页数据摘要：交给右侧「衙署轮播」窗显示"""
        if getattr(self, "carousel", None):
            self.carousel.refresh()


# ========== ① 签押房：日常聊天 ==========
# ========== 聊天气泡：小吏靠左带头像，主人靠右 ==========
class ChatBubble(QWidget):
    def __init__(self, text, mine=False, avatar=None, who=""):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(10)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.PlainText)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setMaximumWidth(560)
        if mine:  # 主人：黛墨底、米白字，靠右
            bubble.setStyleSheet(
                "background: #3a4759; color: #f5efe2; border-radius: 12px;"
                "border-top-right-radius: 4px; padding: 10px 14px;"
                'font-family:"Microsoft YaHei","微软雅黑"; font-size:14px;')
        else:     # 小吏：宣纸底、朱砂压边，靠左
            bubble.setStyleSheet(
                "background: rgba(255, 253, 247, 244); color: #322a20;"
                "border: 1px solid #d8c69a; border-left: 4px solid #9e2b22;"
                "border-radius: 12px; border-top-left-radius: 4px; padding: 10px 14px;"
                'font-family:"Microsoft YaHei","微软雅黑"; font-size:14px;')
        _shadow(bubble, blur=10, dy=2)

        # 说话人名讳：谁被请进来回话，一目了然
        who_lbl = None
        if who:
            who_lbl = QLabel(who)
            who_lbl.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:12px;'
                                  "color:#8e2f1f; background:transparent; padding:0 4px;")

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        if who_lbl is not None:
            col.addWidget(who_lbl, 0, Qt.AlignLeft if not mine else Qt.AlignRight)
        col.addWidget(bubble)

        if mine:
            row.addStretch()
            row.addLayout(col)
        else:
            if avatar is not None and not avatar.isNull():
                av = QLabel()
                av.setFixedWidth(52)
                av.setPixmap(avatar.scaledToHeight(52, Qt.SmoothTransformation))
                av.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
                av.setStyleSheet("background:transparent;")
                row.addWidget(av, 0, Qt.AlignTop)
            row.addLayout(col)
            row.addStretch()


class ChatPanel(BasePanel):
    def __init__(self, pet):
        super().__init__("✒️ 签押房 · 衙署厅堂", "主人落座，小吏研墨——闲话也好，吩咐差事也好",
                         bg_image=_BG("ginkgo_eaves.jpg"), bg_scrim=118)
        self.pet = pet
        # 签押房固定由主簿·阿卷坐堂，不随换班小吏轮换；
        # 别衙门的事他只做引见，请对应小吏进来回话
        self.get_persona_key = lambda: "zhu"
        self.history = []  # 对话记录，让 AI 记得上下文
        self._last_prompt = ""
        self._sprite_pm = QPixmap(_SPRITE("idle.png"))

        # ---- 大管家名帖：会动的人物栏 + 名讳职守 + 衙署速览 ----
        card = QFrame(objectName="cardFrame")
        _shadow(card, blur=14, dy=3)
        row = QHBoxLayout(card)
        row.setContentsMargins(18, 12, 18, 12)
        row.setSpacing(14)
        # 人物栏（签押房版，稍小一号）：点他搭话，议事时埋头办差
        self._stage = PersonaStage(
            "zhu", h=92,
            on_poke=lambda t: self._add_msg(t, mine=False, who="主簿·阿卷"))
        row.addWidget(self._stage)
        col = QVBoxLayout()
        col.setSpacing(3)
        self.persona_label = QLabel()
        self.persona_label.setStyleSheet(
            'font-family:"KaiTi","STKaiti","楷体"; font-size:21px; font-weight:bold; color:#8e2f1f;')
        col.addWidget(self.persona_label)
        self.persona_duty = QLabel(objectName="hint")
        col.addWidget(self.persona_duty)
        self.persona_hint = QLabel("县衙大管家坐堂：记账、备忘、观天、荐味都可一句话差遣，"
                                   "别衙门的事他会请负责人进来回话", objectName="hint")
        col.addWidget(self.persona_hint)
        col.addStretch()
        row.addLayout(col, 1)
        # 右：衙署速览（时辰 / 待办 / 账上 / 城郭）
        ov = QVBoxLayout()
        ov.setSpacing(3)
        self.ov_time = QLabel()
        self.ov_memo = QLabel()
        self.ov_money = QLabel()
        self.ov_city = QLabel()
        for lb in (self.ov_time, self.ov_memo, self.ov_money, self.ov_city):
            lb.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:13px; color:#6b5637;')
            lb.setAlignment(Qt.AlignRight)
            ov.addWidget(lb)
        ov.addStretch()
        row.addLayout(ov)
        self.body.addWidget(card)

        # ---- 聊斋：气泡式对话区 ----
        self.msg_list = QListWidget()
        self.msg_list.setStyleSheet(
            "QListWidget { background: rgba(255, 253, 247, 90);"
            " border: 1px solid rgba(227, 216, 189, 150); border-radius: 14px; padding: 8px; }"
            "QListWidget::item { border: none; background: transparent; }")
        self.body.addWidget(self.msg_list, 1)

        # ---- 送信栏 ----
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.returnPressed.connect(self.send)
        send_btn = QPushButton("送信")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(send_btn)
        self.body.addLayout(row)
        self.body.addWidget(QLabel(
            "阿卷是县衙总管家——闲聊中可直接吩咐：「记一笔午饭30」「下午三点提醒我开会」"
            "「今天适合穿什么」「给推荐两家面馆」，小吏即刻差人去办。",
            objectName="hint"))
        self.send_btn = send_btn
        self.refresh_persona()

    # ---------- 聊斋操作 ----------
    def _add_msg(self, text, mine=False, system=False, who=""):
        """落一条消息：小吏/主人是气泡（可标名讳），回执是居中小字"""
        if system:
            w = QWidget()
            w.setAttribute(Qt.WA_TranslucentBackground)
            rl = QHBoxLayout(w)
            rl.setContentsMargins(6, 2, 6, 2)
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #5c7a3a; font-size: 12px; background:transparent;")
            rl.addWidget(lbl)
        else:
            w = ChatBubble(text, mine=mine, avatar=self._sprite_pm, who=who)
        item = QListWidgetItem(self.msg_list)
        item.setFlags(Qt.NoItemFlags)
        w.adjustSize()
        item.setSizeHint(w.sizeHint())
        self.msg_list.setItemWidget(item, w)
        self.msg_list.scrollToBottom()

    def _greet_once(self):
        """第一次进签押房：阿卷主动打个招呼，报一报衙署现状"""
        if self.msg_list.count() > 0:
            return
        name = next((x["name"] for x in XIAOLI if x["key"] == self.get_persona_key()), "小吏")
        now = datetime.datetime.now()
        hour = now.hour
        if hour < 6:
            when = "夜已深了"
        elif hour < 9:
            when = "晨光正好"
        elif hour < 12:
            when = "日头渐高"
        elif hour < 14:
            when = "晌午时分"
        elif hour < 18:
            when = "午后清闲"
        elif hour < 22:
            when = "掌灯时分"
        else:
            when = "夜阑人静"
        pend = [m for m in memo_store.load()
                if m["date"] == now.date().isoformat() and not m.get("done") and not m["reminded"]]
        inc, exp, bal = ledger_store.totals(ledger_store.month_records())
        memo_line = (f"驿站还有 {len(pend)} 件文书待办" if pend else "今日驿卷清闲")
        greet = (f"{when}，主人万安。眼下{memo_line}，账上结余 ¥{bal:,.2f}。"
                 "闲聊、吩咐差事都使得——小吏这厢候着了。")
        self._add_msg(greet, mine=False, who=name)

    # ---------- 衙署总管家：上下文 + 指令路由 ----------
    CHAT_CMD_HINT = (
        "【衙署总管家·议事规矩】\n"
        "① 若主人的话属于其他衙门职掌，你不要代答——先一句客气引见（如「这桩事归驿丞掌管，我请他进来回话」），"
        "并在回复最后另起一行写：[[请|yi]]（备忘/排程/提醒→驿丞·急急）/ [[请|tian]]（天气/穿搭→司天·云娘）/ "
        "[[请|shi]]（美食/游玩→尚食·小尝）/ [[请|hu]]（记账/账目/省钱→户部·阿算）。被请来的小吏会亲自回话。\n"
        "② 主人吩咐的事你可直接代办的，在回复最后另起一行写指令，签押房会立刻执行：\n"
        "- 记账：[[账｜支出或收入｜科目｜金额｜备注]]；删最近一笔：[[删账｜关键词]]；改金额：[[改账｜关键词｜新金额]]\n"
        "- 备忘：[[录｜内容｜HH:MM｜加急0-3]]；办讫画销：[[销｜关键词]]；改时辰：[[改｜关键词｜新时辰]]\n"
        "- 司天监改观测城市：[[城｜城市名]]；尚食局改口味偏好：[[味｜偏好]]\n"
        "指令之外照常闲聊；无事可办就不要写指令。")

    # 被请进来的小吏回话时，可用的本衙门指令
    DOMAIN_HINTS = {
        "yi":  "可下指令：[[录｜内容｜HH:MM｜加急0-3]] 录文书 / [[销｜关键词]] 画销 / "
               "[[改｜关键词｜新时辰]] 改时辰 / [[急｜关键词｜0-3]] 改加急 / "
               "[[耗时｜关键词｜分钟]] 改耗时 / [[焚｜关键词]] 彻底焚毁 / [[排]] 重新排程",
        "tian": "可下指令：[[城｜城市名]] 改观测城郭 / [[风｜风格偏好]] 改穿搭风格",
        "shi":  "可下指令：[[味｜偏好]] 改口味偏好 / [[城｜城市名]] 改城郭",
        "hu":   "可下指令：[[账｜支出或收入｜科目｜金额｜备注]] 记一笔 / [[删账｜关键词]] 焚账 / [[改账｜关键词｜新金额]] 改金额",
    }

    def _cur_name(self):
        key = self.get_persona_key()
        return next((x["name"] for x in XIAOLI if x["key"] == key), "小吏")

    def _chat_context(self):
        """把衙门的现状摘要告诉阿卷，他才知道家里有几件事、账上还有多少钱"""
        lines = []
        try:
            today = datetime.date.today().isoformat()
            pend = [m for m in memo_store.load()
                    if m["date"] == today and not m.get("done") and not m["reminded"]]
            lines.append(f"今日驿站还有 {len(pend)} 件待办文书")
        except Exception:
            pass
        try:
            inc, exp, bal = ledger_store.totals(ledger_store.month_records())
            lines.append(f"本月户部账上：支出 ¥{exp:,.2f}，结余 ¥{bal:,.2f}")
        except Exception:
            pass
        lines.append(f"当前城郭：{self.pet.default_city}")
        return "\n".join(lines) + "\n" + self.CHAT_CMD_HINT

    def _run_cmd(self, raw):
        """把阿卷写下的指令路由给对应的衙门去办"""
        parts = [p.strip() for p in (raw.replace("｜", "|").split("|") if ("｜" in raw or "|" in raw) else raw.split())]
        parts = [p for p in parts if p]
        if not parts:
            return None
        routes = {
            "账": "ledger", "记": "ledger", "记一笔": "ledger",
            "删账": "ledger", "销账": "ledger", "改账": "ledger",
            "录": "memo", "录文": "memo", "加": "memo", "新增": "memo",
            "销": "memo", "销文": "memo", "办讫": "memo",
            "改": "memo", "改时辰": "memo",
            "城": "weather", "城市": "weather", "天": "weather", "观测": "weather",
            "味": "food", "偏好": "food",
        }
        kind = routes.get(parts[0])
        if not kind:
            return None
        yamen = getattr(self.pet, "_panels", {}).get("yamen")
        panel = yamen.panels_raw.get(kind) if yamen else None
        if panel is None:
            return "该衙门尚未开门（先打开一次总衙门）"
        return panel._run_cmd(raw)

    def refresh_persona(self):
        """刷新值班小吏名帖 + 衙署速览（换班或回页时更新）"""
        for x in XIAOLI:
            if x["key"] == self.get_persona_key():
                self.persona_label.setText(f"{x['name']} · 坐堂理事")
                self.persona_duty.setText(f"职守：{x['duty']}｜双击桌宠也可以唤出本页")
                self.input.setPlaceholderText(f"对{x['name']}说点什么…（回车发送）")
                break
        # 衙署速览：时辰 / 待办 / 账上 / 城郭
        now = datetime.datetime.now()
        self.ov_time.setText(f"🕐 {now.strftime('%H:%M')} · 周{['一','二','三','四','五','六','日'][now.weekday()]}")
        try:
            today = now.date().isoformat()
            pend = [m for m in memo_store.load()
                    if m["date"] == today and not m.get("done") and not m["reminded"]]
            self.ov_memo.setText(f"📮 今日待办 {len(pend)} 件")
        except Exception:
            self.ov_memo.setText("📮 今日待办 —")
        try:
            inc, exp, bal = ledger_store.totals(ledger_store.month_records())
            self.ov_money.setText(f"💰 本月结余 ¥{bal:,.2f}")
        except Exception:
            self.ov_money.setText("💰 本月结余 —")
        self.ov_city.setText(f"📍 城郭：{self.pet.default_city}")

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.refresh_persona()
        self.input.clear()
        self._add_msg(text, mine=True)
        key = self.get_persona_key()
        self._last_prompt = f"{self._chat_context()}\n\n——主人的话：{text}"
        self._stage.busy(True, "阿卷思索中…")
        # L2 引擎：带工具调用循环（AI 自己决定调哪件衙门工具）
        self.run_job(
            self.send_btn,
            lambda: brain.chat_with_tools(key, self._last_prompt, self.history),
            lambda result: self._show_reply_l2(text, result),
        )

    def _show_reply_l2(self, user_text, result):
        """L2 回复：答复文本 + 工具调用轨迹（每一步都给主人看回执）"""
        reply, trace = result
        self.send_btn.setText("送信")
        self._stage.busy(False)
        self._stage.react("greet")
        # ① 工具回执：AI 这轮调了哪些衙门工具、各办成什么
        for title, _name, outcome in trace:
            self._add_msg(f"🔧 {title} —— {outcome}", system=True)
        # ② 兼容旧的 [[指令]] 格式（AI 偶尔还会写，照办）
        handoff = re.search(r"\[\[请\|(\w+)\]\]", reply)
        done_msgs = []
        for raw in re.findall(r"\[\[(?!请\|)(.*?)\]\]", reply):
            try:
                msg = self._run_cmd(raw.strip())
            except Exception as e:
                msg = f"差事没办成（{e}）"
            if msg:
                done_msgs.append(msg)
        clean = re.sub(r"\[\[.*?\]\]", "", reply).strip()
        if clean:
            self._add_msg(clean, mine=False, who=self._cur_name())
        for m in done_msgs:
            self._add_msg(f"✅ 小吏已差人照办：{m}", system=True)
        self.refresh_persona()
        # 记录上下文（最多留 10 轮；只存文本，工具细节不重复进历史）
        self.history.append({"role": "user", "content": self._last_prompt})
        self.history.append({"role": "assistant", "content": reply})
        self.history = self.history[-20:]
        # ③ 引见：请对应衙门的小吏亲自进来回话
        if handoff:
            key = handoff.group(1)
            if key in self.DOMAIN_HINTS and key != self.get_persona_key():
                self._summon(key, user_text)

    def _summon(self, key, question):
        """阿卷引见后，请该衙门的小吏进来回话（带着本衙门的规矩与现状）"""
        name = next((x["name"] for x in XIAOLI if x["key"] == key), "小吏")
        prompt = (f"你刚被主簿·阿卷请进签押房回话。主人的问题：{question}\n\n"
                  f"衙署现状：\n{self._chat_context()}\n\n"
                  f"你当值本衙门，{self.DOMAIN_HINTS[key]}。"
                  "直接以你的口吻回答主人，不必重复引见；指令之外照常作答。")
        self._last_prompt = prompt
        self._stage.busy(True, "请同僚回话…")
        self.run_job(
            self.send_btn,
            lambda: brain.chat(key, prompt, self.history),
            lambda reply: self._show_summoned(key, question, reply),
        )

    def _show_summoned(self, key, user_text, reply):
        """被请进来的小吏回话：气泡上标他的名讳，他的指令照办"""
        self.send_btn.setText("送信")
        self._stage.busy(False)
        self._stage.react("greet")
        name = next((x["name"] for x in XIAOLI if x["key"] == key), "小吏")
        done_msgs = []
        for raw in re.findall(r"\[\[(?!请\|)(.*?)\]\]", reply):
            try:
                msg = self._run_cmd(raw.strip())
            except Exception as e:
                msg = f"差事没办成（{e}）"
            if msg:
                done_msgs.append(msg)
        clean = re.sub(r"\[\[.*?\]\]", "", reply).strip()
        if clean:
            self._add_msg(clean, mine=False, who=name)
        for m in done_msgs:
            self._add_msg(f"✅ 小吏已差人照办：{m}", system=True)
        self.refresh_persona()
        self.history.append({"role": "user", "content": self._last_prompt})
        self.history.append({"role": "assistant", "content": reply})
        self.history = self.history[-20:]

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_persona()
        self._greet_once()


# ========== ② 长安驿站：智能备忘录（两栏文书局格局） ==========
class MemoPanel(BasePanel):
    """
    布局仿手绘格局：
    上：居中匾额 + 待办输入框（时辰 / 耗时 / 加急一行录完）
    左栏：待办清单（点一下即算办讫）+ 飞鸽传书智能排程
    右栏：到期文书（已到时辰未焚毁）+ 问小吏（DeepSeek 讨对策）
    整页以晨雾灞桥风景画覆盖。
    """
    def __init__(self, pet):
        super().__init__("长 安 驿 站", "录一件文书，选一档加急——时辰一到，小吏飞马来报",
                         bg_image=_BG("misty_dawn.jpg"), bg_scrim=150, center_title=True)
        self.pet = pet  # 提醒时要让宠物冒气泡
        self._selected_overdue = None

        # 草图版式：上排「功能区（录入 + 到期提醒条 + 待办清单）｜人物卡」，中排满宽「议事」，下排满宽「对话输入」
        top = QHBoxLayout()
        top.setSpacing(16)
        func = QVBoxLayout()
        func.setSpacing(10)

        # ---- 待办录入框 ----
        card = QFrame(objectName="cardFrame")
        _shadow(card, blur=14, dy=3)
        form = QVBoxLayout(card)
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(8)

        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("要办何事？（例：下午和队友讨论黑客松路演）")
        self.content_edit.returnPressed.connect(self.add_memo)  # 回车也能录入
        form.addWidget(self.content_edit)

        row = QHBoxLayout()
        row.addWidget(QLabel("时辰："))
        self.time_edit = QTimeEdit(QTime.currentTime().addSecs(3600))  # 默认一小时后
        self.time_edit.setDisplayFormat("HH:mm")
        row.addWidget(self.time_edit)
        row.addSpacing(10)
        row.addWidget(QLabel("耗时："))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 600)
        self.duration_spin.setValue(30)
        self.duration_spin.setSuffix(" 分钟")
        row.addWidget(self.duration_spin)
        row.addSpacing(10)
        row.addWidget(QLabel("加急：", objectName="hint"))
        self.urgency_slider = QSlider(Qt.Horizontal)
        self.urgency_slider.setRange(0, 3)
        self.urgency_slider.setTickPosition(QSlider.TicksBelow)
        self.urgency_slider.setTickInterval(1)
        self.urgency_slider.valueChanged.connect(self._urgency_changed)
        row.addWidget(self.urgency_slider, 1)
        self.urgency_label = QLabel(self.URGENCY_DESC[0])
        self.urgency_label.setMinimumWidth(230)
        self.urgency_label.setStyleSheet(
            'font-family:"KaiTi","STKaiti","楷体"; font-size:14px; font-weight:bold;')
        row.addWidget(self.urgency_label)
        add_btn = QPushButton("录入驿卷")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_memo)
        row.addWidget(add_btn)
        form.addLayout(row)
        func.addWidget(card)

        # ---- 到期文书：横贯的提醒条（不高不挤，点选后可问对策） ----
        func.addWidget(QLabel("🔥 到期文书 · 已到时辰但还没焚毁的（点选后可问对策）", objectName="hint"))
        self.overdue_list = QListWidget()
        self.overdue_list.setMaximumHeight(88)
        self.overdue_list.itemClicked.connect(self._overdue_clicked)
        func.addWidget(self.overdue_list)

        # ---- 待办清单：驿站的主角，占住大块版面 ----
        func.addWidget(QLabel("📋 待办事项（单击选中 → 可焚毁；双击办讫/恢复；右键更多）", objectName="hint"))
        self.list_widget = QListWidget()
        # 单击 = 只选中（供「焚毁此条」取用）；双击 = 办讫/恢复 —— 两个手势分家，不再打架
        self.list_widget.itemDoubleClicked.connect(self._toggle_done)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._list_menu)
        func.addWidget(self.list_widget, 1)
        lb = QHBoxLayout()
        lb.setSpacing(12)
        self.plan_btn = QPushButton("🕊️ 飞鸽传书 · 智能排程")
        self.plan_btn.setCursor(Qt.PointingHandCursor)
        self.plan_btn.clicked.connect(self.plan)
        del_btn = QPushButton("焚毁此条", objectName="ghost")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self.delete_selected)
        lb.addWidget(self.plan_btn, 2)
        lb.addWidget(del_btn, 1)
        func.addLayout(lb)
        top.addLayout(func, 1)

        # 右上：人物栏（急急 + 驿道飞鸽）
        self._anim = PigeonWidget()
        self._pcard = persona_card("yi", on_poke=lambda t: getattr(self, "dock", None) and self.dock.note(f"<p><b style='color:#7a2015'>{self.dock.speaker}：</b>{t} <span style='color:#9a8b6d'>（随手搭话）</span></p>"),
                                   anim=self._anim, caption="🕊 驿道飞鸽")
        top.addWidget(self._pcard)
        self.body.addLayout(top, 3)

        # ---- 中排：议事（满宽；排程/献策结果也落这里） ----
        self.dock = AskDock(
            "yi", "驿丞排程 · 可与急急议事",
            "追问某件文书、要更细的排程，或直接说「加一条…」「销掉…」「把××改成八百里加急」（回车发送）",
            hint="可下指令：录 / 销 / 改时辰 / 改加急 / 改耗时 / 焚 / 重排",
            context_fn=self._ask_context, command_fn=self._run_cmd,
            view_height=140)
        self.dock.stage = self._pcard.stage   # 议事联动：奔走时急急埋头办差，答复到作揖相迎
        self.plan_view = self.dock.view
        self.body.addWidget(self.dock, 3)

        # ---- 下排：对话输入（满宽） ----
        self.body.addWidget(self.dock.detach_input())
        self.refresh()
        self._urgency_changed(0)

    # 滑杆拖动时，文案跟着变——四档加急各有驿站风解说
    URGENCY_DESC = [
        "🐎 普快 —— 寻常公文，徐徐图之",
        "🏇 三百里加急 —— 驿站换马，星夜兼程",
        "🔥 五百里加急 —— 马蹄踏碎，不敢稍歇",
        "⚡ 八百里加急 —— 金牌在手，人命关天！",
    ]

    def _urgency_changed(self, idx):
        self.urgency_label.setText(self.URGENCY_DESC[idx])
        self.urgency_label.setStyleSheet(
            f"color:{URGENCY_COLORS[idx]}; font-weight:bold;"
            'font-family:"KaiTi","STKaiti","楷体"; font-size:14px;')

    def add_memo(self):
        content = self.content_edit.text().strip()
        if not content:
            box_warning(self, "驿站规矩", "主人，文书上总得写点什么事吧？")
            return
        memo_store.add(
            content=content,
            time_str=self.time_edit.time().toString("HH:mm"),
            urgency_idx=self.urgency_slider.value(),
            duration=self.duration_spin.value(),
        )
        self.content_edit.clear()
        self.refresh()
        if getattr(self, "_anim", None):
            self._anim.fly()  # 飞鸽传书去也
        self._pcard.stage.react("greet", "文书已录，妥了！")
        self.pet.say(f"已录入驿卷！{memo_store.URGENCY[self.urgency_slider.value()]}，急急记下了！")

    def delete_selected(self):
        """焚毁此条：彻底删除记录，从驿卷里消失（办讫才是画销留档）"""
        item = self.list_widget.currentItem()
        if not item:
            box_info(self, "驿站规矩", "主人，先在待办清单里点选一条文书，再焚毁。")
            return
        memo_id = item.data(Qt.UserRole)
        target = next((m for m in memo_store.load() if m["id"] == memo_id), None)
        if not target:
            # 清单是陈影：这条文书已被别处（另一扇窗/小吏议事）焚毁——
            # 不再静默装死，明说缘由并换上最新驿卷
            box_info(self, "驿站快报",
                     "这条文书已不在驿卷中（许是刚在别处焚毁了），\n已为你换上最新清单。")
            self.refresh()
            return
        # 二次确认：焚毁不可恢复
        if not box_question(
            self, "驿站问询",
            f"「{target['content']}」\n\n焚毁即灰飞烟灭，不可恢复——主人确定？",
        ):
            return
        memo_store.remove(memo_id)
        self._pcard.stage.react("greet", "已焚毁，灰飞烟灭！")
        self.pet.say(f"「{target['content']}」已焚毁，灰飞烟灭！")
        self.refresh()

    def _toggle_done(self, item):
        """双击待办 = 办讫画销（斜线+变浅）；再双击 = 恢复待办"""
        memo_id = item.data(Qt.UserRole)
        memos = memo_store.load()
        for m in memos:
            if m["id"] == memo_id:
                m["done"] = not m.get("done", False)
                if m["done"]:
                    self.pet.say(f"「{m['content']}」办讫！小吏给你记一功～")
                break
        memo_store.save(memos)
        self.refresh()

    def _list_menu(self, pos):
        """右键菜单：办讫/恢复、焚毁画销——和双击、按钮三路畅通"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        self.list_widget.setCurrentItem(item)   # 右键的同时选中，按钮也能接续
        memo_id = item.data(Qt.UserRole)
        target = next((m for m in memo_store.load() if m["id"] == memo_id), None)
        if not target:
            self.refresh()                      # 陈影条目：右键即自愈刷新
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            'QMenu { background:#fffdf7; border:1px solid #ddd0b2; font-size:14px; }'
            "QMenu::item { padding:8px 26px; }"
            "QMenu::item:selected { background:#b03a2e; color:#fdf6e9; }")
        done = target.get("done", False)
        act_done = menu.addAction("✅ 办讫画销" if not done else "↩ 恢复待办")
        act_burn = menu.addAction("🔥 焚毁此条（灰飞烟灭，不可恢复）")
        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen == act_done:
            self._toggle_done(item)
        elif chosen == act_burn:
            self.delete_selected()

    # ---------- 议事：上下文与指令 ----------
    CMD_HINT = ("【指令】若要改动文书，在回复最后另起一行写："
                "[[录｜内容｜HH:MM｜加急0-3]] 新增一件；"
                "[[销｜关键词]] 把匹配的文书画销办讫；"
                "[[改｜关键词｜新时辰]] 改时辰；"
                "[[急｜关键词｜加急0-3]] 改加急档位；"
                "[[耗时｜关键词｜分钟]] 改耗时；"
                "[[焚｜关键词]] 彻底焚毁（不可恢复）；"
                "[[排]] 重新智能排程。指令之外照常回答主人。")

    def _ask_context(self):
        today = datetime.date.today().isoformat()
        memos = [m for m in memo_store.load() if m["date"] == today]
        lines = [f"今日驿卷（{today}）："]
        pend = sorted([m for m in memos if not m.get("done")],
                      key=lambda m: (-m["urgency"], m["time"]))
        for m in pend[:8]:
            lines.append(f"- {m['time']} 【{m['urgency_name']}】{m['content']}"
                         f"（{m['duration']}分钟）")
        if not pend:
            lines.append("- 今日无待办")
        if getattr(self, "_selected_overdue", None):
            m = self._selected_overdue
            lines.append(f"主人刚选中的到期文书：{m['content']}"
                         f"（时辰 {m['time']}，{m['urgency_name']}）")
        lines.append(self.CMD_HINT)
        return "\n".join(lines)

    def _run_cmd(self, raw):
        """执行小吏写下的 [[指令]]：新增 / 画销 / 改时辰"""
        sep = "|" if ("｜" in raw or "|" in raw) else None
        parts = [p.strip() for p in (raw.replace("｜", "|").split("|") if sep else raw.split())]
        parts = [p for p in parts if p]
        if not parts:
            return None
        op = parts[0]
        if op in ("录", "录文", "加", "新增") and len(parts) >= 2:
            content = parts[1]
            t = parts[2] if len(parts) > 2 else \
                datetime.datetime.now().strftime("%H:%M")
            try:
                urg = max(0, min(3, int(parts[3]))) if len(parts) > 3 else 1
            except ValueError:
                urg = 1
            memo_store.add(content, t, urg, 30)
            self.refresh()
            return f"已录入「{content}」（{t}，{memo_store.URGENCY[urg]}）"
        if op in ("销", "销文", "办讫", "删") and len(parts) >= 2:
            kw = parts[1]
            memos = memo_store.load()
            hit = [m for m in memos if kw in m["content"] and not m.get("done")]
            if not hit:
                return f"没找到含「{kw}」的未办文书"
            hit[0]["done"] = True
            memo_store.save(memos)
            self.refresh()
            return f"已画销办讫：{hit[0]['content']}"
        if op in ("改", "改时辰") and len(parts) >= 3:
            kw, nt = parts[1], parts[2]
            memos = memo_store.load()
            hit = [m for m in memos if kw in m["content"]]
            if not hit:
                return f"没找到含「{kw}」的文书"
            hit[0]["time"] = nt
            memo_store.save(memos)
            self.refresh()
            return f"已把「{hit[0]['content']}」的时辰改到 {nt}"
        if op in ("急", "加急", "改急") and len(parts) >= 3:
            kw = parts[1]
            try:
                urg = max(0, min(3, int(parts[2])))
            except ValueError:
                return None
            memos = memo_store.load()
            hit = [m for m in memos if kw in m["content"] and not m.get("done")]
            if not hit:
                return f"没找到含「{kw}」的未办文书"
            hit[0]["urgency"] = urg
            hit[0]["urgency_name"] = memo_store.URGENCY[urg]
            memo_store.save(memos)
            self.refresh()
            return f"已把「{hit[0]['content']}」改作{memo_store.URGENCY[urg]}"
        if op in ("耗时", "工时") and len(parts) >= 3:
            kw = parts[1]
            try:
                dur = max(5, min(600, int(parts[2])))
            except ValueError:
                return None
            memos = memo_store.load()
            hit = [m for m in memos if kw in m["content"] and not m.get("done")]
            if not hit:
                return f"没找到含「{kw}」的未办文书"
            hit[0]["duration"] = dur
            memo_store.save(memos)
            self.refresh()
            return f"已把「{hit[0]['content']}」的耗时改为 {dur} 分钟"
        if op in ("焚", "焚毁", "销毁") and len(parts) >= 2:
            kw = parts[1]
            memos = memo_store.load()
            hit = [m for m in memos if kw in m["content"]]
            if not hit:
                return f"没找到含「{kw}」的文书"
            memo_store.remove(hit[0]["id"])
            self.refresh()
            return f"已彻底焚毁：{hit[0]['content']}（不可恢复）"
        if op in ("排", "重排", "排程"):
            self.plan()
            return "已为主人重新排程"
        return None

    def _overdue_clicked(self, item):
        """点到期的文书：弹窗问主人办讫了没——是则画销，否则让驿丞献策"""
        memo_id = item.data(Qt.UserRole)
        target = None
        for m in memo_store.load():
            if m["id"] == memo_id:
                target = m
                break
        if not target:
            self.refresh()                      # 到期栏的陈影：点一下就刷新掉
            return
        self._selected_overdue = target
        if box_question(
            self, "驿站问询",
            f"「{target['content']}」\n（时辰 {target['time']}，{target['urgency_name']}）\n\n"
            "时辰已到——主人，这件事办讫了吗？",
        ):
            memos = memo_store.load()
            for m in memos:
                if m["id"] == memo_id:
                    m["done"] = True
                    break
            memo_store.save(memos)
            self.refresh()
            self.pet.say("办讫！小吏给你记一功～")
        else:
            # 未完成：让驿丞带着上下文出一套可执行的补救步骤（结果落在议事区）
            self.dock.send_text(
                f"「{target['content']}」（时辰 {target['time']}，{target['urgency_name']}，"
                f"预计耗时 {target['duration']} 分钟）已超时未办，"
                "请给一套立即可执行的补救步骤，编号列出，简短实用。",
                echo=f"【到期文书】{target['content']}（{target['time']}）——请小吏献策",
            )

    @staticmethod
    def _day_label(date_str):
        """日期转『今天/明天/后天/周X/M月D日』，多日行程分组一目了然"""
        try:
            d = datetime.date.fromisoformat(date_str)
        except Exception:
            return date_str
        delta = (d - datetime.date.today()).days
        if delta == 0:
            return "今天"
        if delta == 1:
            return "明天"
        if delta == 2:
            return "后天"
        week = "一二三四五六日"[d.weekday()]
        return f"{d.month}月{d.day}日 · 周{week}"

    def refresh(self):
        """刷新两栏列表：左=驿卷按日分组（组内综合紧迫分排序），右=到期未办"""
        self.list_widget.clear()
        self.overdue_list.clear()
        memos = memo_store.smart_sorted(memo_store.load())
        last_date = None
        for m in memos:
            # ---- 日期分隔头：换天就插一行「── 明天 ──」----
            if m["date"] != last_date:
                last_date = m["date"]
                header = QListWidgetItem(f"── {self._day_label(m['date'])} ──")
                header.setFlags(Qt.NoItemFlags)
                header.setForeground(QColor("#9a8b6d"))
                hf = header.font()
                hf.setPointSize(9)
                hf.setBold(True)
                header.setFont(hf)
                self.list_widget.addItem(header)
            done = m.get("done", False)
            tag = "🗑" if done else ("✅" if m["reminded"] else "⏰")
            item = QListWidgetItem(
                f"  {tag} {m['time']} ｜ 【{m['urgency_name']}】{m['content']}（{m['duration']}分钟）"
            )
            item.setData(Qt.UserRole, m["id"])  # 把编号藏在条目里
            font = item.font()
            font.setStrikeOut(done)          # 焚毁 = 划一条斜线
            item.setFont(font)
            if done:
                item.setForeground(QColor("#b3a78e"))  # 颜色变浅
            else:
                # 按加急档位着色：越急越红，一眼可辨
                item.setForeground(QColor(URGENCY_COLORS[m["urgency"]]))
            self.list_widget.addItem(item)
            if m["reminded"] and not done and m["date"] == datetime.date.today().isoformat():
                od = QListWidgetItem(
                    f"🔥 {m['time']} ｜ 【{m['urgency_name']}】{m['content']}"
                )
                od.setData(Qt.UserRole, m["id"])
                self.overdue_list.addItem(od)

    def plan(self):
        today = [m for m in memo_store.load()
                 if not m["reminded"] and not m.get("done", False)]
        if not today:
            box_info(self, "驿站清闲", "今日驿卷空空如也，主人先录入几件事吧！")
            return
        self._pcard.stage.busy(True, "排程中…")
        self.run_job(
            self.plan_btn,
            lambda: brain.arrange_schedule(today),
            self._show_plan,
        )

    def _show_plan(self, text):
        self.plan_btn.setText("🕊️ 飞鸽传书 · 智能排程")
        self._pcard.stage.busy(False)
        if text.startswith("（"):  # AI 掉线 → 本地算法兜底，排程照样带理由
            pending = [m for m in memo_store.load()
                       if not m["reminded"] and not m.get("done", False)]
            text = memo_store.local_plan(pending)
            self._pcard.stage.react("greet", "飞鸽未归，小吏已就地急排！")
        else:
            self._pcard.stage.react("greet", "排程完毕，主人过目！")
        self.plan_view.append(f"<p><b>驿丞排程：</b></p><p>{text.replace(chr(10), '<br>')}</p><br>")
        self.plan_view.verticalScrollBar().setValue(
            self.plan_view.verticalScrollBar().maximum())
        self.pet.say("排程完毕！主人请看驿丞的安排～")


# ========== ③ 司天监：天气 + 穿搭 ==========
class WeatherPanel(BasePanel):
    def __init__(self, default_city):
        super().__init__("🌤 司天监 · 观天台", "夜观天象，日察云纹——顺带告诉主人今日该怎么穿",
                         bg_image=_BG("misty_bridge.jpg"), bg_scrim=72, animated=True)

        # 草图版式：上排「功能区｜人物卡」，中排「议事」，下排「对话输入」
        top = QHBoxLayout()
        top.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(8)
        card = QFrame(objectName="cardFrame")
        _shadow(card, blur=14, dy=3)
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 10, 14, 10)
        form.setSpacing(8)
        row = QHBoxLayout()
        self.city_edit = QLineEdit(default_city)
        self.city_edit.setPlaceholderText("何方地界？（城市名）")
        self.city_edit.returnPressed.connect(self.query)
        btn = QPushButton("观测天象")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.query)
        row.addWidget(QLabel("城郭："))
        row.addWidget(self.city_edit, 1)
        row.addWidget(btn)
        form.addLayout(row)
        # 风格偏好：让主人点菜（例：喜欢新中式 / 要通勤得体 / 学生党休闲）
        row2 = QHBoxLayout()
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("风格偏好？（例：新中式 / 通勤得体 / 户外风——留空则云娘自便）")
        self.style_edit.returnPressed.connect(self.query)
        row2.addWidget(QLabel("风格："))
        row2.addWidget(self.style_edit, 1)
        form.addLayout(row2)
        left.addWidget(card)
        left.addWidget(QLabel("天象实录 · 云娘着装策（风格推荐 + 整套搭配单）：", objectName="hint"))
        self.result_view = QTextBrowser()
        left.addWidget(self.result_view, 1)
        top.addLayout(left, 1)
        self._anim = StarsWidget()
        self._pcard = persona_card("tian", on_poke=lambda t: getattr(self, "dock", None) and self.dock.note(f"<p><b style='color:#7a2015'>{self.dock.speaker}：</b>{t} <span style='color:#9a8b6d'>（随手搭话）</span></p>"),
                                   anim=self._anim, caption="✨ 今夜星斗")
        top.addWidget(self._pcard)
        self.body.addLayout(top, 3)

        # 议事区（中排，满宽）
        self._last_summary = ""
        self.dock = AskDock(
            "tian", "与司天·云娘议事",
            "换个风格 / 加一条围巾 / 这套下雨天能穿吗…（回车发送）",
            hint="可下指令：城 / 风",
            context_fn=self._ask_context, command_fn=self._run_cmd,
            view_height=120)
        self.dock.stage = self._pcard.stage   # 议事联动：云娘观天时埋头，测完作揖
        self.body.addWidget(self.dock, 2)
        self.body.addWidget(self.dock.detach_input())   # 对话输入（下排，满宽）

        self.body.addWidget(QLabel(
            "内置「大唐舆地图」：省份、省会、热门旅游城市离线秒查；小众地名走双接口兜底。",
            objectName="hint"))
        self.btn = btn

    def _ask_context(self):
        city = self.city_edit.text().strip() or "西安"
        style = self.style_edit.text().strip() if hasattr(self, "style_edit") else ""
        res = self.result_view.toPlainText().strip()
        ctx = f"当前城郭：{city}\n"
        if style:
            ctx += f"主人填写的风格偏好：{style}\n"
        if res:
            ctx += "刚才测到的天象与着装策：\n" + res[:900] + "\n"
        ctx += ("【指令】若要改动，在回复最后另起一行写：[[城｜城市名]] 改城市；"
                "[[风｜风格偏好]] 改风格——都只改设定、不重新观测，请在已有的天象基础上继续议。"
                "指令之外照常回答主人。")
        return ctx

    def _run_cmd(self, raw):
        parts = [p.strip() for p in (raw.replace("｜", "|").split("|") if ("｜" in raw or "|" in raw) else raw.split())]
        parts = [p for p in parts if p]
        if not parts:
            return None
        op = parts[0]
        if op in ("城", "城市", "天", "观测") and len(parts) >= 2:
            self.city_edit.setText(parts[1])
            return f"已把城郭记为「{parts[1]}」（原有观测不推翻，照此续议）"
        if op in ("风", "风格", "偏好") and len(parts) >= 2:
            pref = " ".join(parts[1:])
            self.style_edit.setText(pref)
            return f"已把风格偏好记为「{pref}」，下次观测与议事照此办理"
        return None

    def query(self):
        city = self.city_edit.text().strip() or "西安"
        style = self.style_edit.text().strip() if hasattr(self, "style_edit") else ""

        def job():
            desc = weather.get_weather(city)                    # 第一步：拿真实天气
            advice = brain.outfit_advice(desc, style_pref=style)  # 第二步：AI 出整套着装策
            return f"【天象实录】\n{desc}\n\n{advice}"

        self._pcard.stage.busy(True, "观天裁衣中…")
        self.run_job(self.btn, job, self._show)

    def _show(self, text):
        self.btn.setText("观测天象")
        self._pcard.stage.busy(False)
        self._pcard.stage.react("greet", "着装策已拟好，主人过目！")
        self.result_view.setPlainText(text)
        self._last_summary = next((l.strip() for l in text.splitlines() if l.strip()), "")[:22]
        if getattr(self, "dock", None) and self._last_summary:
            self.dock.hint_label.setText(f"当前：{self._last_summary}")


# ========== ④ 尚食局：美食 + 游玩推荐 ==========
class FoodPanel(BasePanel):
    def __init__(self, default_city):
        super().__init__("🍜 尚食局 · 荐味司", "百味尝遍，长安吃透——主人今天想吃点什么？",
                         bg_image=_BG("xian_food.jpg"), bg_scrim=145)

        # 草图版式：上排「功能区｜人物卡」，中排「议事」，下排「对话输入」
        top = QHBoxLayout()
        top.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(8)
        card = QFrame(objectName="cardFrame")
        _shadow(card, blur=14, dy=3)
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 10, 14, 10)
        form.setSpacing(8)
        row = QHBoxLayout()
        self.city_edit = QLineEdit(default_city)
        self.city_edit.setPlaceholderText("何方地界？")
        row.addWidget(QLabel("城郭："))
        row.addWidget(self.city_edit, 1)
        form.addLayout(row)
        self.pref_edit = QLineEdit()
        self.pref_edit.setPlaceholderText("偏好？（例：想吃面食 / 想逛古迹 / 预算 50 元）")
        self.pref_edit.returnPressed.connect(self.query)
        form.addWidget(self.pref_edit)
        btn = QPushButton("小尝献宝")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.query)
        form.addWidget(btn, 0, Qt.AlignRight)
        left.addWidget(card)
        left.addWidget(QLabel("小尝荐单：", objectName="hint"))
        self.result_view = QTextBrowser()
        left.addWidget(self.result_view, 1)
        # 探店图鉴：荐单下方一排「真图 + 地图」卡片（搜索完自动填充）
        self.gallery_label = QLabel("📷 探店图鉴 · 献宝后自动寻真图（点击📍可去高德地图看位置）", objectName="hint")
        left.addWidget(self.gallery_label)
        self.gallery = QWidget()
        self.gallery.setAttribute(Qt.WA_TranslucentBackground)
        self.gallery_row = QHBoxLayout(self.gallery)
        self.gallery_row.setContentsMargins(0, 0, 0, 0)
        self.gallery_row.setSpacing(8)
        self.gallery_row.addStretch()
        left.addWidget(self.gallery)
        top.addLayout(left, 1)
        self._anim = SteamBowlWidget()
        self._pcard = persona_card("shi", on_poke=lambda t: getattr(self, "dock", None) and self.dock.note(f"<p><b style='color:#7a2015'>{self.dock.speaker}：</b>{t} <span style='color:#9a8b6d'>（随手搭话）</span></p>"),
                                   anim=self._anim, caption="🍜 灶上正热")
        top.addWidget(self._pcard)
        self.body.addLayout(top, 3)

        # 议事区（中排，满宽）
        self._last_summary = ""
        self.dock = AskDock(
            "shi", "与尚食·小尝议事",
            "追问店家细节 / 换个价位口味 / 顺手排个路线…（回车发送）",
            hint="可下指令：城 / 味",
            context_fn=self._ask_context, command_fn=self._run_cmd,
            view_height=120)
        self.dock.stage = self._pcard.stage   # 议事联动：小尝尝味时埋头，献宝时作揖
        self.body.addWidget(self.dock, 2)
        self.body.addWidget(self.dock.detach_input())   # 对话输入（下排，满宽）
        self.btn = btn

    def _ask_context(self):
        city = self.city_edit.text().strip() or "西安"
        prefs = self.pref_edit.text().strip()
        res = self.result_view.toPlainText().strip()
        ctx = f"当前城郭：{city}；主人偏好：{prefs or '（未填）'}\n"
        if res:
            ctx += "刚才给出的荐单：\n" + res[:900] + "\n"
        ctx += ("【指令】若要改动，在回复最后另起一行写：[[城｜城市名]] 改城市；"
                "[[味｜偏好]] 记下新口味/预算——两者都只改设定、不重新荐单，"
                "请在原有荐单上继续改进。指令之外照常回答主人。")
        return ctx

    def _run_cmd(self, raw):
        parts = [p.strip() for p in (raw.replace("｜", "|").split("|") if ("｜" in raw or "|" in raw) else raw.split())]
        parts = [p for p in parts if p]
        if not parts:
            return None
        op = parts[0]
        if op in ("城", "城市") and len(parts) >= 2:
            self.city_edit.setText(parts[1])
            return f"已把城郭记为「{parts[1]}」（原有荐单不推翻，照此续议）"
        if op in ("味", "偏好") and len(parts) >= 2:
            pref = " ".join(parts[1:])
            self.pref_edit.setText(pref)
            return f"已记下偏好「{pref}」，荐单在此基础上继续改进"
        return None

    def query(self):
        city = self.city_edit.text().strip() or "西安"
        prefs = self.pref_edit.text().strip()
        self._pcard.stage.busy(True, "尝味中…")
        self.run_job(self.btn, lambda: brain.recommend(city, prefs), self._show)

    # ---------- 探店图鉴 ----------
    def _clear_gallery(self):
        """清空图鉴行（保留结尾的 stretch）"""
        while self.gallery_row.count() > 1:
            item = self.gallery_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _gallery_card(self, name, dish=""):
        """一张探店卡：真实照片（搜招牌菜）+ 店名与招牌 + 📍地图按钮（跳高德官方页面）"""
        card = QFrame(objectName="cardFrame")
        card.setFixedWidth(152)
        v = QVBoxLayout(card)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)
        pic = QLabel("寻图中…")
        pic.setFixedSize(140, 96)
        pic.setAlignment(Qt.AlignCenter)
        pic.setStyleSheet("background:#efe6d2; color:#9a8b6d; border-radius:8px; font-size:12px;")
        pic.setToolTip(f"按招牌「{dish or name}」寻图" if dish else "寻图中")
        v.addWidget(pic)
        nm = QLabel(name)
        nm.setWordWrap(True)
        nm.setAlignment(Qt.AlignHCenter)
        nm.setStyleSheet('font-family:"KaiTi","STKaiti","楷体"; font-size:13px;'
                         "font-weight:bold; color:#8e2f1f;")
        nm.setMaximumHeight(34)
        v.addWidget(nm)
        if dish and dish != name:
            dsh = QLabel(f"招牌 · {dish}")
            dsh.setAlignment(Qt.AlignHCenter)
            dsh.setStyleSheet("color:#8b6f47; font-size:11px;")
            v.addWidget(dsh)
        city = self.city_edit.text().strip() or "西安"
        map_btn = QPushButton("📍 地图")
        map_btn.setCursor(Qt.PointingHandCursor)
        map_btn.setStyleSheet("padding:3px 8px; font-size:12px;")
        map_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(food_media.amap_link(name, city))))
        v.addWidget(map_btn)
        card._pic = pic
        return card

    def _fetch_gallery(self, items):
        """
        后台线程：为每个「店名+招牌」搜真图并填进卡片。
        图片搜招牌菜名（小众店名没图，菜名才有海量真图）；地图跳店名。
        """
        cards = []
        city = self.city_edit.text().strip() or "西安"   # 主线程先取好，不跨线程碰控件
        for name, dish in items:
            card = self._gallery_card(name, dish)
            self.gallery_row.insertWidget(self.gallery_row.count() - 1, card)
            cards.append((name, dish, card))

        def job():
            out = []
            for name, dish, _card in cards:
                core = dish or name
                # 严格双查询链：先"城市+菜名"，标题命中才用；0 命中换裸菜名；
                # 整页都不相关就放弃——宁可"图未寻得"也不给错图
                queries = [f"{city}{core}", core] if city not in core else [core, city + core]
                data = None
                for q in queries:
                    urls = food_media.search_images(q, count=4, keyword=core, strict=True)
                    for u in urls:
                        data = food_media.fetch_thumb(u)
                        if data:
                            break
                    if data:
                        break
                out.append((name, data))
            return out

        worker = Worker(job)
        self._workers.append(worker)

        def fill(result):
            by_name = dict(result)
            for name, _dish, card in cards:
                pic = card._pic
                data = by_name.get(name)
                if data:
                    pm = QPixmap()
                    if pm.loadFromData(QByteArray(data)):
                        # 等比缩放裁进 140×96 的框（cover 效果）
                        scaled = pm.scaled(140, 96, Qt.KeepAspectRatioByExpanding,
                                           Qt.SmoothTransformation)
                        x = max(0, (scaled.width() - 140) // 2)
                        y = max(0, (scaled.height() - 96) // 2)
                        pic.setPixmap(scaled.copy(x, y, 140, 96))
                        pic.setText("")
                else:
                    pic.setText("图未寻得")
                    pic.setStyleSheet("background:#efe6d2; color:#b3a78e;"
                                      "border-radius:8px; font-size:12px;")

        worker.done.connect(fill)
        worker.start()

    def _show(self, text):
        self.btn.setText("小尝献宝")
        self._pcard.stage.busy(False)
        self._pcard.stage.react("greet", "献宝喽，主人慢用！")
        self.result_view.setPlainText(text)
        self._last_summary = next((l.strip() for l in text.splitlines() if l.strip()), "")[:22]
        # 按行解析「店名」与【招牌：菜名】——图搜招牌菜，地图跳店名
        self._clear_gallery()
        items = []
        for line in text.splitlines():
            m_store = re.search(r"「(.+?)」", line)
            if not m_store:
                continue
            store = m_store.group(1)
            m_dish = re.search(r"【招牌[：:](.+?)】", line)
            # 店名里的"·"后段往往是菜品（老米家·泡馍）——招牌缺省时作图搜词
            dish = m_dish.group(1).strip() if m_dish else ""
            if not dish:
                dish = store.split("·")[-1].strip() if "·" in store else store
            items.append((store, dish))
        items = items[:4]
        if items:
            self._fetch_gallery(items)
        else:
            # 荐单里没解析到店名（AI 没守格式）——不显示空图鉴
            self._clear_gallery()


# ========== ⑤ 户部·记账房：收支流水 ==========
class BarChart(QWidget):
    """近七日支出小柱图：手绘，不引额外图表库"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(112)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.data = []

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if not self.data or w <= 10:
            return
        pad_b, pad_t = 20, 18
        n = len(self.data)
        maxv = max([v for _, v in self.data] + [1.0])
        slot = w / n
        bw = min(24.0, slot * 0.46)
        f = QFont("Microsoft YaHei")
        f.setPointSize(8)
        p.setFont(f)
        for i, (label, val) in enumerate(self.data):
            bh = (h - pad_b - pad_t) * (val / maxv) if maxv else 0
            x = slot * i + (slot - bw) / 2
            if bh < 2:
                bh = 2
                p.setBrush(QColor(206, 192, 164, 130))
                p.setPen(Qt.NoPen)
            else:
                y0 = h - pad_b - bh
                grad = QLinearGradient(x, y0, x, h - pad_b)
                grad.setColorAt(0, QColor(201, 122, 78, 240))
                grad.setColorAt(1, QColor(148, 48, 31, 210))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(grad))
            y = h - pad_b - bh
            p.drawRoundedRect(QRectF(x, y, bw, bh), 4, 4)
            if val >= 1:
                p.setPen(QColor(122, 92, 52))
                p.drawText(QRectF(x - 14, y - 16, bw + 28, 14), Qt.AlignCenter, f"{val:.0f}")
            p.setPen(QColor(154, 139, 109))
            p.drawText(QRectF(slot * i, h - pad_b + 2, slot, 16), Qt.AlignCenter, label)


class LedgerPanel(BasePanel):
    """户部账房：一收一支皆入册，顺手算清这个月钱都去哪了"""

    def __init__(self, pet):
        super().__init__("🧾 户部 · 记账房", "一收一支皆入册，月末方知钱去哪——主人只管记，账小吏来算")
        self.pet = pet
        self._kind = "out"

        # 草图版式：上排「功能区（录入 + 流水/月账）｜人物卡」，中排满宽「议事」，下排满宽「对话输入」
        top = QHBoxLayout()
        top.setSpacing(14)
        func = QVBoxLayout()
        func.setSpacing(10)

        # ---- 录入卡片 ----
        card = QFrame(objectName="cardFrame")
        _shadow(card, blur=14, dy=3)
        form = QVBoxLayout(card)
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(10)

        r1 = QHBoxLayout()
        r1.setSpacing(10)
        self.btn_out = QPushButton("支出", objectName="kindBtn")
        self.btn_in = QPushButton("收入", objectName="kindBtn")
        for b, k in ((self.btn_out, "out"), (self.btn_in, "in")):
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, kk=k: self._set_kind(kk))
            r1.addWidget(b)
        self.btn_out.setChecked(True)
        r1.addSpacing(12)
        r1.addWidget(QLabel("金额："))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(1)
        self.amount_spin.setPrefix("¥ ")
        self.amount_spin.setFixedWidth(120)
        r1.addWidget(self.amount_spin)
        r1.addWidget(QLabel("科目："))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(ledger_store.CATS_OUT)
        self.cat_combo.setFixedWidth(110)
        r1.addWidget(self.cat_combo)
        r1.addWidget(QLabel("日期："))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("MM-dd")
        self.date_edit.setFixedWidth(96)
        r1.addWidget(self.date_edit)
        r1.addStretch()
        form.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(10)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("备注？（例：食堂午饭 / 买教材）")
        self.note_edit.returnPressed.connect(self.add_record)
        r2.addWidget(self.note_edit, 1)
        add_btn = QPushButton("记一笔")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_record)
        r2.addWidget(add_btn)
        form.addLayout(r2)
        func.addWidget(card)

        # ---- 流水 + 月账：并肩排开，谁也不挤谁 ----
        mid = QHBoxLayout()
        mid.setSpacing(14)

        left_card = QFrame(objectName="cardFrame")
        _shadow(left_card, blur=14, dy=3)
        lv = QVBoxLayout(left_card)
        lv.setContentsMargins(16, 12, 16, 12)
        lv.setSpacing(8)
        lv.addWidget(QLabel("流水账册", objectName="cardTitle"))
        self.list_widget = QListWidget()
        lv.addWidget(self.list_widget, 1)
        foot = QHBoxLayout()
        foot.addWidget(QLabel("点选一条，可焚账销号", objectName="hint"))
        foot.addStretch()
        self._ana_btn = QPushButton("📜 翻账 · 今日账评")
        self._ana_btn.setCursor(Qt.PointingHandCursor)
        self._ana_btn.clicked.connect(self.analyze)
        foot.addWidget(self._ana_btn)
        del_btn = QPushButton("焚账", objectName="ghost")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self.delete_selected)
        foot.addWidget(del_btn)
        lv.addLayout(foot)
        mid.addWidget(left_card, 3)

        right_card = QFrame(objectName="cardFrame")
        right_card.setFixedWidth(280)
        _shadow(right_card, blur=14, dy=3)
        rv = QVBoxLayout(right_card)
        rv.setContentsMargins(18, 12, 18, 12)
        rv.setSpacing(6)
        rv.addWidget(QLabel("本月结余", objectName="cardTitle"))
        self.balance_label = QLabel("¥0.00", objectName="moneyBig")
        rv.addWidget(self.balance_label)
        self.month_sub = QLabel("收入 ¥0.00　支出 ¥0.00", objectName="moneySub")
        rv.addWidget(self.month_sub)
        rv.addSpacing(4)
        rv.addWidget(QLabel("近七日支出", objectName="hint"))
        self.bar = BarChart()
        rv.addWidget(self.bar)
        rv.addWidget(QLabel("支出去向", objectName="hint"))
        self.cat_view = QTextBrowser(objectName="summary")
        self.cat_view.setMinimumHeight(80)
        rv.addWidget(self.cat_view, 1)
        mid.addWidget(right_card, 2)
        func.addLayout(mid, 1)
        top.addLayout(func, 1)

        # 右上：人物栏（阿算 + 账房铜钱）
        self._anim = CoinWidget()
        self._pcard = persona_card("hu", on_poke=lambda t: getattr(self, "dock", None) and self.dock.note(f"<p><b style='color:#7a2015'>{self.dock.speaker}：</b>{t} <span style='color:#9a8b6d'>（随手搭话）</span></p>"),
                                   anim=self._anim, caption="💰 账房铜钱")
        top.addWidget(self._pcard)
        self.body.addLayout(top, 3)

        # ---- 中排：议事（带着本月账目追问，或直接让阿算改账） ----
        self.dock = AskDock(
            "hu", "与户部·阿算议事",
            "问「这个月钱花哪了」「怎么省」或直接说「记一笔…」「删掉…」（回车发送）",
            hint="可下指令：账 / 删账 / 改账",
            context_fn=self._ask_context, command_fn=self._run_cmd,
            view_height=120)
        self.dock.stage = self._pcard.stage   # 议事联动：阿算对账时埋头，账讫作揖
        self.body.addWidget(self.dock, 2)

        # ---- 下排：对话输入（满宽） ----
        self.body.addWidget(self.dock.detach_input())
        self.refresh()

    # ---------- 议事：上下文与指令 ----------
    def _ask_context(self):
        recs = ledger_store.load()
        month = ledger_store.month_records(recs)
        inc, exp, bal = ledger_store.totals(month)
        lines = [f"本月账目：收入 ¥{inc:,.2f}，支出 ¥{exp:,.2f}，结余 ¥{bal:,.2f}"]
        cats = ledger_store.by_category(month, "out")[:6]
        if cats:
            lines.append("支出构成：" + "，".join(f"{n} ¥{v:,.2f}" for n, v in cats))
        recent = sorted(recs, key=lambda r: (r["date"], r["time"]), reverse=True)[:12]
        if recent:
            lines.append("最近流水：")
            for r in recent:
                kind = "支出" if r["kind"] == "out" else "收入"
                lines.append(f"- {r['date']} {r['time']} {kind} {r['category']} "
                             f"{r.get('note') or ''} ¥{r['amount']:,.2f}")
        lines.append("【指令】可写：[[账｜支出或收入｜科目｜金额｜备注]] 记一笔；"
                     "[[删账｜关键词]] 删最近一条匹配的流水；"
                     "[[改账｜关键词｜新金额]] 改金额。指令之外照常回答主人。")
        return "\n".join(lines)

    def _run_cmd(self, raw):
        parts = [p.strip() for p in (raw.replace("｜", "|").split("|") if ("｜" in raw or "|" in raw) else raw.split())]
        parts = [p for p in parts if p]
        if not parts:
            return None
        op = parts[0]
        if op in ("账", "记", "记一笔") and len(parts) >= 4:
            kind = "in" if parts[1].startswith("收") else "out"
            cat = parts[2]
            try:
                amt = round(float(parts[3]), 2)
            except ValueError:
                return None
            note = " ".join(parts[4:])
            ledger_store.add(kind, cat, amt, note)
            self.refresh()
            return f"记一笔{'收入' if kind == 'in' else '支出'}：{cat} ¥{amt:,.2f} {note}"
        if op in ("删账", "销账", "删") and len(parts) >= 2:
            kw = parts[1]
            hit = [r for r in ledger_store.load()
                   if kw in r.get("note", "") or kw in r["category"]]
            if not hit:
                return f"没找到含「{kw}」的流水"
            r = sorted(hit, key=lambda x: (x["date"], x["time"]))[-1]
            ledger_store.remove(r["id"])
            self.refresh()
            return f"已焚账：{r['category']}·{r.get('note') or '—'} ¥{r['amount']:,.2f}"
        if op in ("改账", "改") and len(parts) >= 3:
            kw = parts[1]
            try:
                newv = round(float(parts[2]), 2)
            except ValueError:
                return None
            recs = ledger_store.load()
            hit = [r for r in recs if kw in r.get("note", "") or kw in r["category"]]
            if not hit:
                return f"没找到含「{kw}」的流水"
            r = sorted(hit, key=lambda x: (x["date"], x["time"]))[-1]
            old = r["amount"]
            r["amount"] = newv
            ledger_store.save(recs)
            self.refresh()
            return f"已把「{r['category']}·{r.get('note') or '—'}」从 ¥{old:,.2f} 改为 ¥{newv:,.2f}"
        return None

    # ---------- 翻账 · 今日账评 ----------
    def analyze(self):
        """本地算对比数据 → AI 出账评；掉线时本地结论兜底"""
        facts, verdict, stats = ledger_store.compare_report()

        def job():
            reply = brain.ledger_analysis(facts, verdict, stats)
            if reply.startswith("（"):    # AI 掉线 → 师爷就地口述本地结论
                return (f"【今日对账】\n{facts}\n\n【本地核对】\n{verdict}\n\n"
                        "（飞鸽未归，师爷就地核对——数字皆实，建议改日再议。）")
            return reply

        self._pcard.stage.busy(True, "翻账核对中…")
        self.run_job(self._ana_btn, job, self._show_analysis)

    def _show_analysis(self, text):
        self._ana_btn.setText("📜 翻账 · 今日账评")
        self._pcard.stage.busy(False)
        self._pcard.stage.react("greet", "账评出炉，主人过目！")
        self.dock.view.append(f"<p><b>📜 今日账评：</b></p><p>{text.replace(chr(10), '<br>')}</p><br>")
        self.dock.view.verticalScrollBar().setValue(
            self.dock.view.verticalScrollBar().maximum())
        self.pet.say("今日账评已出——变化如何，且听阿算道来。")

    # ---------- 收 / 支切换 ----------
    def _set_kind(self, kind):
        self._kind = kind
        self.btn_out.setChecked(kind == "out")
        self.btn_in.setChecked(kind == "in")
        self.cat_combo.clear()
        self.cat_combo.addItems(ledger_store.CATS_OUT if kind == "out" else ledger_store.CATS_IN)

    # ---------- 记一笔 ----------
    def add_record(self):
        amount = self.amount_spin.value()
        if amount <= 0:
            box_warning(self, "账房规矩", "主人，金额得大于零才记得上账。")
            return
        category = self.cat_combo.currentText()
        note = self.note_edit.text().strip()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        ledger_store.add(self._kind, category, amount, note, date_str)
        self.amount_spin.setValue(0)
        self.note_edit.clear()
        self.refresh()
        word = "支出" if self._kind == "out" else "入账"
        self._pcard.stage.react("greet", "入账，妥！")
        self.pet.say(f"{word} {amount:.2f} 元（{category}），已录入户部账册。")

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item or item.data(Qt.UserRole) is None:
            box_info(self, "账房规矩", "先点选一条流水，再焚账销号。")
            return
        ledger_store.remove(item.data(Qt.UserRole))
        self.refresh()
        self.pet.say("这条流水已焚账销号。")

    # ---------- 刷新 ----------
    def refresh(self):
        records = sorted(ledger_store.load(), key=lambda r: (r["date"], r["time"]), reverse=True)
        self.list_widget.clear()
        last_date = None
        for r in records:
            if r["date"] != last_date:
                last_date = r["date"]
                try:
                    d = datetime.date.fromisoformat(r["date"])
                    day_text = f"{d.month}月{d.day}日"
                except Exception:
                    day_text = r["date"]
                header = QListWidgetItem(f"──  {day_text}  ──")
                header.setFlags(Qt.NoItemFlags)
                header.setForeground(QColor("#9a8b6d"))
                hf = header.font()
                hf.setPointSize(9)
                header.setFont(hf)
                self.list_widget.addItem(header)
            sign = "－" if r["kind"] == "out" else "＋"
            note = r.get("note") or "—"
            item = QListWidgetItem(
                f"  {r['time']}   {r['category']} · {note}        {sign}¥{r['amount']:,.2f}")
            item.setData(Qt.UserRole, r["id"])
            item.setForeground(QColor("#9e2b22" if r["kind"] == "out" else "#3f6b3a"))
            self.list_widget.addItem(item)

        month = ledger_store.month_records(records)
        income, expense, balance = ledger_store.totals(month)
        self.balance_label.setText(f"¥{balance:,.2f}")
        self.balance_label.setStyleSheet(
            'font-family:"KaiTi","STKaiti","楷体"; font-size:30px; font-weight:bold;'
            f"color:{'#8e2f1f' if balance < 0 else '#3f6b3a'};")
        self.month_sub.setText(f"本月收入 ¥{income:,.2f}　支出 ¥{expense:,.2f}")
        self.bar.set_data(ledger_store.last_days(records, 7))

        cats = ledger_store.by_category(month, "out")
        total = expense or 1.0
        if not cats:
            self.cat_view.setHtml("<p style='color:#9a8b6d;'>本月尚无支出记录。</p>")
        else:
            rows = ["<table width='100%' cellspacing='0' cellpadding='3'>"]
            for name, val in cats[:6]:
                pct = val / total * 100
                rows.append(
                    f"<tr><td>{name}</td>"
                    f"<td align='right'><b>¥{val:,.2f}</b></td>"
                    f"<td align='right' width='46'><span style='color:#9a8b6d;'>{pct:.0f}%</span></td></tr>")
            rows.append("</table>")
            self.cat_view.setHtml("".join(rows))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
