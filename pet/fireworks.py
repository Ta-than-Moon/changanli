# -*- coding: utf-8 -*-
"""
fireworks.py —— 桌面烟花
用于「文书截止前十分钟」的提醒：屏幕上层炸开几朵金色烟火，
中间压一条烫金横幅写清是哪件事、几点截止。

窗口是透明、无边框、置顶且鼠标穿透的——它只是"在桌面上放一场烟花"，
不会挡住主人手头的活。
"""
import math
import random

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QRadialGradient, QFont, QGuiApplication,
                           QCursor, QPen)
from PySide6.QtWidgets import QWidget

# 长安夜空的配色：鎏金为主，掺朱砂与月白
PALETTE = [
    (255, 216, 130), (255, 238, 190), (255, 168, 88),
    (255, 110, 86), (208, 230, 255), (255, 196, 92),
]


class _Spark:
    """一颗火星"""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "r", "color", "twinkle")

    def __init__(self, x, y, vx, vy, life, radius, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.r = radius
        self.color = color
        self.twinkle = random.uniform(0, 6.28)


class FireworkOverlay(QWidget):
    """整屏烟花层：一次提醒 = 一场约 4.5 秒的烟火"""

    _alive = []          # 持有的窗口引用，防止被垃圾回收
    FRAME_MS = 16
    TOTAL_FRAMES = 285   # ≈ 4.6 秒

    def __init__(self, text, when=""):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.NoFocus)

        self.text = text
        self.when = when
        self.frame = 0
        self.sparks = []
        self.bursts_done = []
        # 烟花在屏幕上半部炸开，错开时间，形成一串"噼里啪啦"
        self.plan = [0, 16, 34, 56, 82, 112]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(self.FRAME_MS)

    # ---------- 对外入口 ----------
    @classmethod
    def pop(cls, text, when=""):
        """在鼠标所在的屏幕上放一场烟花"""
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo = screen.geometry()
        win = cls(text, when)
        win.setGeometry(geo)
        win.show()
        win.raise_()
        cls._alive.append(win)
        return win

    # ---------- 每帧推进 ----------
    def _tick(self):
        self.frame += 1
        w, h = self.width(), self.height()

        for i, f in enumerate(self.plan):
            if self.frame == f and i not in self.bursts_done:
                self.bursts_done.append(i)
                cx = random.uniform(w * 0.18, w * 0.82)
                cy = random.uniform(h * 0.14, h * 0.46)
                self._burst(cx, cy, random.choice([72, 86, 100]))

        alive = []
        for s in self.sparks:
            s.vy += 0.075          # 重力：火星先上后落
            s.vx *= 0.982
            s.vy *= 0.982
            s.x += s.vx
            s.y += s.vy
            s.life -= 1
            if s.life > 0:
                alive.append(s)
        self.sparks = alive

        self.update()
        if self.frame >= self.TOTAL_FRAMES and not self.sparks:
            self.close()

    def _burst(self, cx, cy, count):
        """炸开一朵：环形抛射 + 少量"垂柳"长尾"""
        base_color = random.choice(PALETTE)
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.2, 7.6) * (1.0 if random.random() > 0.12 else 1.55)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            color = base_color if random.random() > 0.25 else random.choice(PALETTE)
            self.sparks.append(_Spark(
                cx, cy, vx, vy,
                life=random.randint(46, 96),
                radius=random.uniform(1.3, 2.7),
                color=color,
            ))
        # 中心的爆闪
        for _ in range(16):
            ang = random.uniform(0, 2 * math.pi)
            self.sparks.append(_Spark(
                cx, cy, math.cos(ang) * 0.8, math.sin(ang) * 0.8,
                life=random.randint(12, 22), radius=2.6,
                color=(255, 250, 220),
            ))

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Plus)

        for s in self.sparks:
            t = s.life / s.max_life
            alpha = int(255 * (t ** 1.6))
            if alpha <= 3:
                continue
            flicker = 0.72 + 0.28 * math.sin(self.frame * 0.7 + s.twinkle)
            r, g, b = s.color
            col = QColor(r, g, b, int(alpha * flicker))
            # 尾迹：从上一帧位置画一条细线，暗一点
            tail = QPointF(s.x - s.vx * 2.2, s.y - s.vy * 2.2)
            p.setPen(QPen(QColor(r, g, b, int(alpha * 0.32 * flicker)), max(0.8, s.r * 0.7)))
            p.drawLine(tail, QPointF(s.x, s.y))
            # 外晕 + 内芯：两层圆叠出光感
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(r, g, b, int(alpha * 0.18)))
            p.drawEllipse(QPointF(s.x, s.y), s.r * 2.6, s.r * 2.6)
            p.setBrush(col)
            p.drawEllipse(QPointF(s.x, s.y), s.r, s.r)

        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self._draw_banner(p)

    def _draw_banner(self, p):
        if not self.text:
            return
        fade = min(1.0, self.frame / 14.0) * min(1.0, max(0.0, (self.TOTAL_FRAMES - self.frame) / 40.0))
        p.setOpacity(fade)
        w, h = self.width(), self.height()
        bw = min(680, int(w * 0.6))
        bh = 108
        x = (w - bw) / 2
        y = h * 0.62
        rect = QRectF(x, y, bw, bh)

        # 底：夜墨半透 + 鎏金细边
        p.setPen(QPen(QColor(201, 162, 83, 220), 1.6))
        p.setBrush(QColor(28, 22, 16, 205))
        p.drawRoundedRect(rect, 16, 16)

        # 朱砂小签
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(176, 58, 46, 240))
        p.drawRoundedRect(QRectF(x + 18, y + 18, 8, bh - 36), 4, 4)

        f = QFont("KaiTi")
        f.setPointSize(17)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(255, 233, 186))
        text = self.text if len(self.text) <= 22 else self.text[:21] + "…"
        p.drawText(QRectF(x + 40, y + 18, bw - 60, 40), Qt.AlignLeft | Qt.AlignVCenter, f"「{text}」")

        f2 = QFont("Microsoft YaHei")
        f2.setPointSize(10)
        p.setFont(f2)
        p.setPen(QColor(226, 197, 140))
        sub = f"距截止还有 10 分钟" + (f"　·　截止 {self.when}" if self.when else "")
        p.drawText(QRectF(x + 40, y + 58, bw - 60, 32), Qt.AlignLeft | Qt.AlignVCenter, sub)
        p.setOpacity(1.0)
