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
  <img src="https://img.shields.io/badge/Input-ctypes_SendInput-blue?style=flat-square" alt="Input">
  <img src="https://img.shields.io/badge/Screen-ImageGrab-lightgrey?style=flat-square" alt="Screen">
  <img src="https://img.shields.io/badge/Pack-Nuitka-2E8B57?style=flat-square" alt="Pack">
</p>

---

## ✦ 目录

- [📖 简介](#-简介)
- [✨ 特性](#-特性)
- [🎯 工作原理](#-工作原理)
- [📦 使用方式](#-使用方式exe)
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

| 🏷️ 亮点 | ✨ 说明 |
|:--|:--|
| 🎮 **主控角色全自动参战** | 脚本操控角色 **移动、攻击、确认再战**，完全替代手动刷图 |
| 🔎 **OCR 智能文字识别** | 基于 rapidocr-onnxruntime-lite，实时识别 `跳跃`/`继续`/`再次挑战` 等 UI 文字 |
| ⌨️ **裸 Win32 SendInput** | ctypes 直接调用系统 API 模拟键鼠，**零第三方依赖**，pynput / pyautogui 统统不需要 |
| 🔥 **全局热键一键启停** | F1 开始 / F2 停止，**即使焦点不在 GUI 窗口也能响应** |
| 📊 **战斗次数统计** | 运行状态卡片实时显示已战斗次数，一目了然 |
| 📝 **日志文件回溯** | 每次运行生成 `logs/gbfr.log` |
| 🧩 **多屏 DPI 自适应** | Per-Monitor DPI 感知 + 负坐标多屏回退，4K / 异形分辨率全覆盖 |
| 🗜️ **Nuitka 原生编译** | anti-bloat + 排除 20+ stdlib + zstd 压缩，嵌入 15MB 模型后仍极致小巧 |

---


## 📦 使用方式

### 🔽 第一步：下载

从 [Releases](../../releases) 页面下载最新版本的 `GBFR_AutoReBattle.exe`。

### 📁 第二步：放置

将 `GBFR_AutoReBattle.exe` 放到任意目录（**建议放在独立的英文路径文件夹中**）。

### 🚀 第三步：启动游戏

启动 **Granblue Fantasy: Relink**，确保：

- ✅ **以管理员身份运行脚本**（程序会自动提权，否则按键注入和后台截图无效）
- ✅ 分辨率 **1920 × 1080 或更高**
- ✅ 显示模式为 **无边框窗口** 或 **窗口化**
- ❌ **不要最小化游戏窗口**（可切到后台，但最小化后画面不渲染会截图失败）

### 🟢 第四步：启动脚本

1. **右键 → 以管理员身份运行** `GBFR_AutoReBattle.exe`

2. 按下 **`F1`** 开始自动循环





## ⌨️ 热键说明

| 按键 | 功能 | 说明 |
|:--:|:--|:--|
| **`F1`** | 🟢 开始 | 启动自动战斗循环（或点击 ▶ 启动战斗 按钮） |
| **`F2`** | 🔴 停止 | 立即停止当前循环（或点击 ⏸ 暂停 按钮） |

> ⚠️ **F1 / F2 是全局热键**，即使焦点不在 GUI 窗口也能响应。

---

## ⚙️ 注意事项

### 🔴 必须满足

| 编号 | 要求 | 原因 |
|:--:|:--|:--|
| ① | **以管理员身份运行** | 按键模拟（SendInput）和后台截图均需要管理员权限，否则操作无法生效 |
| ② | **分辨率 ≥ 1920 × 1080** | OCR 区域坐标基于此分辨率换算，低分辨率会导致识别准度下降 |
| ③ | **无边框窗口 / 窗口化** | 独占全屏模式下截图会黑屏，无法 OCR 识别 |



### 🟡 建议事项

| 编号 | 建议 | 说明 |
|:--:|:--|:--|
| ⑤ | ⏸️ **结算阶段不要手动操作** | 脚本会连点跳过结算，手动操作可能打断流程 |
| ⑥ | 🔤 **游戏语言为简中** | OCR 识别的是中文文字，其他语言界面无法识别 |
| ⑦ | 🔳 **不要遮挡 OCR 关键区域** | `跳跃`/`继续`/`再次挑战` 等 UI 文字被遮挡会导致识别失败 |

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
├── GBFR_AutoReBattle.exe     ← 打包后的可执行文件（Nuitka 原生编译）
├── main.py                   ← 主程序入口（GUI + 战斗循环 + 状态同步）
├── build_exe.py              ← Nuitka 打包脚本（无控制台 + 全面瘦身）
├── module/
│   ├── controller.py         ← 核心控制器（截图 / OCR / 按键 / 热键）
│   ├── log.py                ← 日志系统
│   ├── utils.py              ← 工具函数
│   ├── screenshot/           ← 截图模块（ImageGrab / DXCam / Win32）
│   └── rapidocr_onnxruntime/ ← RapidOCR CPU 专版（轻量 OCR 引擎）
│       ├── *.onnx            ← ONNX 推理模型
│       └── *.yaml            ← 模型配置
├── logs/                     ← 运行日志
│   └── gbfr.log
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
