# -*- coding: utf-8 -*-
"""
voice.py —— 驿卒耳力（语音输入）
双击唤醒桌宠 → 麦克风收音（自动断句：静音 1.4 秒即收）→ 本地 Whisper 转文字
→ 送进签押房走 L2 引擎议事。

技术选型（讲给新手听）：
- 收音：sounddevice（PortAudio），16kHz 单声道——语音识别的标准采样率
- 转写：faster-whisper（CTranslate2 加速的 Whisper，纯 CPU 就够快）；
  模型放在 exe 旁边，不联网也能转写——演示日断网照样听懂主人
- 断句：按音量能量判断——先听 0.5 秒环境底噪，音量超过底噪 3 倍算开口，
  连续 1.4 秒没声算说完；再点一下小吏可提前收音
"""
import os
import sys
import time

import numpy as np

FS = 16000  # 采样率：语音识别的标准


# ---------- 模型住址：exe 旁边优先（打包后），开发目录兜底 ----------
def _model_base_dirs():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        return [base, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    return [os.path.dirname(os.path.abspath(__file__))]


def find_model(name="whisper-small"):
    """找本地模型目录；找不到返回 None（首次会自动下载）"""
    for d in _model_base_dirs():
        p = os.path.join(d, "voice_models", name)
        if os.path.exists(os.path.join(p, "model.bin")):
            return p
    return None


_ENGINE = None
_ENGINE_ERR = None


def get_engine():
    """加载 Whisper 引擎（单例）。首次调用会下载模型（约480MB，需要网络）。"""
    global _ENGINE, _ENGINE_ERR
    if _ENGINE is not None:
        return _ENGINE
    if _ENGINE_ERR is not None:
        raise RuntimeError(_ENGINE_ERR)
    try:
        from faster_whisper import WhisperModel
        local = find_model()
        if local:
            _ENGINE = WhisperModel(local, device="cpu", compute_type="int8")
        else:
            root = os.path.join(_model_base_dirs()[0], "voice_models")
            os.makedirs(root, exist_ok=True)
            _ENGINE = WhisperModel("small", device="cpu", compute_type="int8",
                                   download_root=root)
        return _ENGINE
    except Exception as e:
        _ENGINE_ERR = str(e)
        raise


_PROMPT = "以下是普通话口述句子，请使用简体字并添加标点。"


def transcribe(audio_f32, language="zh"):
    """
    把一段 16kHz 单声道 float32 音频转成文字。
    initial_prompt 是给 Whisper 的"定场诗"：提示它说普通话、好好加标点。
    注意：Whisper 在静音时会把定场诗自己念出来——必须过滤掉，
    不然没人说话时会把提示词当成主人的话发出去（实测踩坑）。
    """
    eng = get_engine()
    segments, info = eng.transcribe(
        audio_f32, language=language, beam_size=1,
        condition_on_previous_text=False,
        initial_prompt=_PROMPT)
    text = "".join(s.text.strip() for s in segments).strip()
    # 过滤"回声"：输出若只是定场诗的复述（整段含于提示词），视为没听清
    if text and text in _PROMPT:
        return ""
    return text


# ---------- 收音：能量断句 ----------
class Recorder:
    """麦克风采音器：等主人开口，静音 1.4 秒即自动收音"""

    def __init__(self, fs=FS):
        self.fs = fs

    def record(self, stop_flag=None, max_s=25.0, silence_s=1.4, min_rms=0.015):
        """
        录一段话。stop_flag 是个函数，返回 True 就提前收（再点一下小吏）。
        返回 float32 数组；没等到人声返回 None。
        """
        import sounddevice as sd
        block = int(self.fs * 0.1)  # 每次读 100 毫秒
        frames = []
        floor_blocks = []           # 前 5 块用来估环境底噪
        floor = None
        started = False             # 主人开口了没有
        silent_rounds = 0           # 连续静音了多少个 100ms
        waited_s = 0.0              # 等主人开口等了多久

        with sd.InputStream(samplerate=self.fs, channels=1,
                            dtype="int16", blocksize=block) as stream:
            t0 = time.time()
            while time.time() - t0 < max_s:
                if stop_flag is not None and stop_flag():
                    break
                data, _overflowed = stream.read(block)
                if data.size == 0:
                    time.sleep(0.05)
                    continue
                mono = data[:, 0].astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(mono ** 2)))
                frames.append(mono)

                # ① 前 0.5 秒：只估底噪，不算话
                if floor is None:
                    floor_blocks.append(rms)
                    if len(floor_blocks) >= 5:
                        floor = max(0.004, float(np.mean(sorted(floor_blocks)[1:4])))
                        thresh = max(floor * 3.0, min_rms)
                    continue

                # ② 说话检测
                if rms >= thresh:
                    started = True
                    silent_rounds = 0
                elif started:
                    silent_rounds += 1
                    if silent_rounds * 0.1 >= silence_s:
                        break          # 说完了，收音
                else:
                    waited_s += 0.1
                    if waited_s >= 10.0:
                        return None    # 等了十秒没人说话，撤

        if not frames:
            return None
        return np.concatenate(frames)


def mic_available():
    """有没有可用的麦克风（提前探一下，别等主人说完才发现没麦）"""
    try:
        import sounddevice as sd
        return len(sd.query_devices()) > 0 and any(
            d["max_input_channels"] > 0 for d in sd.query_devices())
    except Exception:
        return False
