# 长安吏 · AI 桌面小吏

一只住在桌面上的唐朝小吏，替你记事、记账、看天、荐味、陪聊。
点他作揖、拖他溜达、右键可差遣五衙门办事；平时安静待机，偶尔自己踱两步。

---

## 一、目录结构

```
changanli/
├── pet/                    # 程序主体（源码都在这里）
│   ├── main.py             # 桌面小吏窗口：动画状态机、托盘菜单、语音入口
│   ├── panels.py           # 五衙门面板：聊天 / 备忘 / 天气 / 美食 / 账本
│   ├── brain.py            # 接 DeepSeek 的"大脑"：意图识别与工具调用
│   ├── memo_store.py       # 备忘录存储
│   ├── ledger_store.py     # 账本存储
│   ├── weather.py          # 天气查询（需 city 配置）
│   ├── food_media.py       # 美食配图
│   ├── voice.py            # 语音输入（faster-whisper 本地转写）
│   ├── fireworks.py        # 节庆烟花彩蛋
│   ├── paths.py            # 路径统一处理（源码/打包后都能找到资源）
│   ├── 长安吏.spec         # PyInstaller 打包配置
│   └── assets/             # 素材：角色精灵图、背景图、图标
│       └── sprites/        # 角色动画：每个角色一个目录
│           ├── male/       # 通用小吏（主簿阿卷暂用）
│           ├── yi/         # 驿丞·急急（骑马）
│           ├── tian/       # 司天·云娘
│           ├── shi/        # 尚食·小尝（厨娘）
│           ├── hu/         # 户部·阿算（账房先生）
│           └── */sheet.json  # 该角色每个姿势的动画帧数
├── config.example.json     # 配置模板（复制成 config.json 用）
├── .gitignore
└── README.md
```

> 仓库里**不含** exe、语音模型、私人数据（备忘录/账本）和含密钥的 `config.json`，这些都不会上传。

---

## 二、环境要求

- Windows 10 / 11（桌面宠物依赖 Windows 窗口特性）
- Python **3.13**（3.10 亦可，开发用 3.13）
- 约 500MB 磁盘空间（含语音模型缓存）

---

## 三、安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install PySide6 requests pillow numpy sounddevice faster-whisper
```

可选依赖（做素材用，跑程序不需要）：

```bash
pip install opencv-python-headless rembg onnxruntime
```

| 依赖 | 用途 |
|---|---|
| PySide6 | 界面与动画 |
| requests | 天气 / 大模型接口 |
| pillow / numpy | 图像处理 |
| sounddevice | 录音 |
| faster-whisper | 本地语音转文字（首次运行会自动下载模型到 `voice_models/`） |

---

## 四、配置

把模板复制成正式配置：

```bash
copy config.example.json config.json
```

然后编辑 `config.json`：

```json
{
  "deepseek_api_key": "sk-你的DeepSeek密钥",
  "city": "西安"
}
```

- `deepseek_api_key`：在 [DeepSeek 开放平台](https://platform.deepseek.com/) 申请
- `city`：天气默认城市，改成你所在的城市即可

> `config.json` 已被 `.gitignore` 排除，**不会**提交到仓库，密钥安全。

---

## 五、从源码运行

```bash
cd pet
python main.py
```

桌面右下角就会出现小吏。右键点他会展开一幅卷轴菜单：

- **四位头像** = 四个常用衙门：云娘（司天监·天气）、急急（驿站·备忘）、阿算（户部·账本）、小尝（尚食局·美食），点头像弹对应悬浮窗
- **顶部横栏** = 对话框，吩咐一句回车即送签押房议事
- **右上角城楼** = 回总衙门主页面（五衙门面板）
- **右下角朱印圆钮** = 换班（五位小吏轮流当值）
- **左下角小字** = 放小吏下班（退出程序）

调试期想在无窗口环境跑冒烟测试：

```bash
QT_QPA_PLATFORM=offscreen python _test_deck.py
```

---

## 六、打包成 exe

用的是 **PyInstaller**，配置已经写在 `pet/长安吏.spec` 里（单文件模式，会带上 Qt、faster-whisper、语音相关二进制）。

### 步骤

```bash
pip install pyinstaller
cd pet
python -m PyInstaller 长安吏.spec --noconfirm --distpath dist --workpath build
```

打包约 1.5～3 分钟，产物在：

```
pet/dist/长安吏.exe      # 约 158 MB，单文件，可独立运行
```

### spec 里做了什么

- `datas = [('assets', 'assets')]`：把整个素材目录打进包（新增角色目录无需改配置）
- `collect_all(...)`：自动收 `ctranslate2 / av / sounddevice / faster_whisper / tokenizers` 的动态库和数据
- `excludes`：裁掉 QtWebEngine、QtPdf、Qt3D 等用不到的模块，给 exe 瘦身
- 图标：`assets/icon.ico`

### 打包后的注意点

- exe 是单文件模式，**每次启动会往 `%TEMP%` 解压约 340MB**；C 盘空间不足会打不开
- 用任务管理器强杀进程，解压目录来不及自清，会留垃圾。正常退出（右键 → 放小吏下班）会自动清理
- 分发时 exe 同级目录会自动生成 `config.json`（首次运行提示填写）、`memos.json`、`ledger.json`

---

## 七、角色形象是怎么来的（可选阅读）

想给小吏换形象时，流程是：拿到角色视频/立绘 → 抠图 → 切帧 → 做成横排精灵图 → 放进 `assets/sprites/<角色>/`。

相关脚本（都在 `pet/` 下）：

| 脚本 | 作用 |
|---|---|
| `_cutout_ai.py` | AI 抠图（rembg / u2net），黑底白底都能抠 |
| `_build_sheets2.py` | 把视频切成 10 帧横排精灵图 |
| `_reassign.py` | 角色与目录的对应调整 |

约定：

- 每个姿势一个 PNG，**横排 N 帧**，帧数写在该目录的 `sheet.json`
- 五姿势固定：`idle`（待机）、`walk`（巡街）、`greet`（作揖）、`work`（办差）、`sleep`（打盹）
- 缺哪个姿势就往 `male/` 回退，不会崩
- 新人设接入只需改两张"人事表"：`panels.py` 的 `PersonaStage.SPRITE_SET` 和 `main.py` 的 `PET_SPRITE_SET`

---

## 八、常见问题

**Q：双击 exe 没反应？**
先看 C 盘剩余空间（单文件启动要解压 340MB 到临时目录）。再检查 `%TEMP%` 里有没有堆积的 `_MEI*` 目录，删掉即可。

**Q：提示缺 API Key？**
exe 同级目录需要 `config.json`，参照 `config.example.json` 填好密钥和城市。

**Q：语音用不了？**
首次使用会下载 faster-whisper 模型到 `voice_models/`（约 460MB，不入库），保持联网即可。

---

MIT License。素材为 AI 生成，仅供学习交流。
