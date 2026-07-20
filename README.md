<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows_10%2B-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/Language-Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<h1 align="center">⚔️ GBFR AutoReBattle</h1>

<p align="center">
  <b>Granblue Fantasy: Relink</b> 全自动刷图脚本<br>
  OCR 识别 · 一键循环 · 解放双手
</p>

<p align="center">
  <img src="https://img.shields.io/badge/OCR-RapidOCR-blueviolet?style=flat-square" alt="OCR Engine">
  <img src="https://img.shields.io/badge/Input-pynput-orange?style=flat-square" alt="Input">
  <img src="https://img.shields.io/badge/Screen-ImageGrab-lightgrey?style=flat-square" alt="Screen">
</p>

---

## ✦ 目录

- [📖 简介](#-简介)
- [✨ 特性](#-特性)
- [🎯 工作原理](#-工作原理)
- [📦 使用方式（EXE）](#-使用方式exe)
- [⌨️ 热键说明](#️-热键说明)
- [⚙️ 注意事项](#️-注意事项)
- [🐛 常见问题](#-常见问题)
- [📂 项目结构](#-项目结构)
- [🙏 致谢](#-致谢)

---

## 📖 简介

**GBFR AutoReBattle** 是一个基于 OCR 图像识别的《碧蓝幻想：Relink》全自动刷图工具。

> 🔍 通过实时截取游戏画面，识别 **跳跃** / **再次挑战** / **继续** 等 UI 文字，自动模拟键盘鼠标操作，完成 **战斗 → 结算 → 再战** 的完整循环。

告别机械重复，专注享受游戏。

---

## ✨ 特性

| 🏷️ 模块 | ✨ 说明 |
|:--|:--|
| 🔎 **OCR 文字识别** | 基于 rapidocr-onnxruntime-lite识别游戏 UI 文字 |
| 🖥️ **窗口无关截图** | 截取屏幕像素而非窗口，游戏在后台也能正常运行 |
| ⌨️ **pynput 键盘模拟** | 底层键盘事件注入，绕过大部分反作弊检测 |
| 🔥 **一键启停** | F1 开始循环 / F2 立即停止，随时掌控 |
| 📊 **彩色控制台** | ANSI 彩色日志，运行状态一目了然 |
| 📝 **完整日志文件** | 每次运行自动生成 `logs/gbfr.log`，方便回溯排查 |
| 🧩 **无边框窗口感知** | 自动适配 DPI 缩放，精准坐标映射 |
| 🔒 **管理员运行** | 自动提权，确保按键注入生效 |

---


脚本循环执行以下阶段：

1. **战斗阶段** —— 检测到 `跳跃` 后，锁定视角并自动跑图
2. **结算阶段** —— 等待 `继续` 按钮出现，连点跳过结算动画
3. **再战阶段** —— 识别 `再次挑战` / `挑战` 按钮，自动确认并进入下一轮

---

## 📦 使用方式（EXE）

### 🔽 第一步：下载

从 [Releases](../../releases) 页面下载最新版本的 `GBFR_AutoReBattle.exe`。

### 📁 第二步：放置

将 `GBFR_AutoReBattle.exe` 放到任意目录（**建议放在独立的英文路径文件夹中**）。

### 🚀 第三步：启动游戏

启动 **Granblue Fantasy: Relink**，确保：

- ✅ 分辨率 **1920 × 1080 或更高**
- ✅ 显示模式为 **无边框窗口** 或 **窗口化**
- ✅ 进入关卡后，画面中出现 **「跳跃」** 两个字

### 🟢 第四步：启动脚本

1. **双击运行** `GBFR_AutoReBattle.exe`（自动以管理员身份运行）
2. 看到彩色日志界面后，移动到游戏画面
3. 按下 **`F1`** 开始自动循环

```
  ┌─────────────────────────────────────────────┐
  │  ⚔️  GBFR 自动重战 启动                      │
  │  Admin: 是                                  │
  │  按 F1 开始战斗循环, F2 停止                  │
  └─────────────────────────────────────────────┘
```

### ⏹️ 第五步：停止

- 按 **`F2`** 停止战斗循环
- 再次按 `F1` 可重新开始
- 直接关闭控制台窗口退出程序

---

## ⌨️ 热键说明

| 按键 | 功能 | 说明 |
|:--:|:--|:--|
| **`F1`** | 🟢 开始 | 启动自动战斗循环 |
| **`F2`** | 🔴 停止 | 立即停止当前循环，结算中按下会等本次完成 |

> ⚠️ **F1 / F2 是全局热键**，即使你的焦点不在控制台窗口也能响应。

---

## ⚙️ 注意事项

### 🔴 必须满足

| 编号 | 要求 | 原因 |
|:--:|:--|:--|
| ① | **分辨率 ≥ 1920 × 1080** | OCR 区域坐标基于此分辨率换算，低分辨率会导致识别准度下降 |
| ② | **无边框窗口 / 窗口化** | 独占全屏模式下截图会黑屏，无法 OCR 识别 |

### 🟡 建议事项

| 编号 | 建议 | 说明 |
|:--:|:--|:--|
| ④ | 🔒 **以管理员身份运行** | 程序会自动提权，确保 `pynput` 按键注入对游戏生效 |
| ⑤ | 🖥️ **不要遮挡游戏窗口** | 脚本截取的是屏幕像素，窗口被遮挡会导致识别失败 |
| ⑥ | 🎮 **游戏音效可保留** | 脚本不使用图像匹配，不会与游戏画面冲突 |
| ⑦ | 🚫 **关闭杀毒软件误报** | `pynput` 模拟按键可能被部分杀软误判，添加信任即可 |
| ⑧ | ⏸️ **结算阶段不要手动操作** | 脚本会连点跳过结算，手动操作可能打断流程 |
| ⑩ | 🔤 **游戏语言为简中** | OCR 识别的是中文文字，其他语言界面无法识别 |

---

## 🐛 常见问题

<details>
<summary><b>❓ 启动后没有反应？</b></summary>

1. 确认游戏是 无边框窗口 / 窗口化 模式
2. 查看 `logs/gbfr.log` 日志文件排查具体错误
</details>

<details>
<summary><b>❓ 能识别文字但不按键？</b></summary>

1. 确保以**管理员身份**运行（程序会自动提权，但某些系统可能需手动右键 → 以管理员身份运行）
2. 将游戏切换为**无边框窗口**模式（窗口化模式下鼠标点击可能不准）
</details>



---

## 📂 项目结构

```
GBFR_AutoReBattle/
├── GBFR_AutoReBattle.exe     ← 打包后的可执行文件
├── main.py                   ← 主程序入口
├── module/
│   ├── controller.py         ← 核心控制器（截图 / OCR / 按键 / 热键）
│   ├── log.py                ← 彩色日志系统
│   └── rapidocr_onnxruntime/ ← RapidOCR CPU 专版（轻量 OCR 引擎）
│       ├── *.onnx            ← ONNX 推理模型
│       └── *.yaml            ← 模型配置
├── logs/                     ← 运行日志（每次启动自动清空）
│   └── gbfr.log
└── screenshot/               ← 调试截图（save=True 时启用）
```

---

## 🙏 致谢

本项目的核心 OCR 能力源自以下优秀开源项目：

<table>
<tr>
<td align="center" width="50%">
  <b>🔍 RapidOCR</b><br>
  <sub>超轻量级多平台 OCR 引擎</sub><br><br>
  <a href="https://github.com/RapidAI/RapidOCR">
    <img src="https://img.shields.io/badge/GitHub-RapidAI%2FRapidOCR-181717?style=for-the-badge&logo=github" alt="RapidOCR">
  </a>
</td>
<td align="center" width="50%">
  <b>📦 rapidocr-onnxruntime-lite</b><br>
  <sub>专门优化的 CPU 压缩专版</sub><br><br>
  <a href="https://github.com/R4Ajeti/rapidocr-onnxruntime-lite">
    <img src="https://img.shields.io/badge/GitHub-R4Ajeti%2Frapidocr--lite-181717?style=for-the-badge&logo=github" alt="rapidocr-onnxruntime-lite">
  </a>
</td>
</tr>
</table>

<!-- 分割线 -->

<br>

> 💡 **特别感谢** [R4Ajeti](https://github.com/R4Ajeti) 提供的 `rapidocr-onnxruntime-lite` CPU 压缩专版，大幅减小了模型体积和内存占用，使得 EXE 打包更加轻量。

<br>

<p align="center">
  <sub>Made with ❤️ for GBF Relink players</sub>
</p>
