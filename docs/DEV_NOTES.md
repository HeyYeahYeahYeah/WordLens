# 开发笔记

## 起源

2026-10-22 用 WorkBuddy 做的第一个"划词速查"小工具。需求原话：

> Windows 桌面悬浮窗，复制/选中英文即查；单个单词 → 有道词典释义（音标 + 词性 + 核心释义），句子/短语 → MyMemory 整句翻译；右下角固定、不抢焦点、不存历史、无发音。

## 设计取舍

- **为什么用剪贴板轮询，而不是全局钩子？** 全局键盘钩子要装驱动级 hook，容易被安全软件拦；剪贴板轮询 0.3s 足够快，且"复制"这个动作本身是用户主动的，误触发少。
- **为什么单词和句子分流？** 有道词典接口返回的是结构化释义（音标/词性/多条），整句翻译接口给不出这些；MyMemory 反过来只适合整句。二者组合才既准又稳。
- **为什么免 key 接口？** 目标用户（自己/同事）不想申请 API key，装完即用。代价是接口可能限流或变动。
- **为什么不抢焦点？** 查词场景下用户往往在看网页/写文档，弹出窗口把焦点抢走会打断输入。所以 `show()` 里先记下 `GetForegroundWindow()`，弹窗后再 `SetForegroundWindow()` 还原。

## 踩过的坑

- **托管 Python 3.13 是精简构建，不带 tkinter/Tcl-Tk**：PyInstaller 打包时报 `No module named 'tkinter'`。解决：改用系统 Anaconda（3.9，自带 tkinter 8.6）建干净 venv 再打包。
- **该 anaconda-tk venv 缺 sqlite3.dll**：如果这个工具要存历史/配置，别用 sqlite3，PyInstaller 打包后会崩；用 JSON 文件更稳。
- **`pyperclip.paste()` 在剪贴板被其他程序占用时会抛异常**：已 `try/except` 吞掉，下一轮继续轮询，不要让它把线程搞死。

## 高分屏 DPI（2026-11-01 补）

- **症状**：在 150% 缩放的屏幕上，悬浮窗跑到屏幕右下角外面，几乎看不见。
- **根因**：进程没开 DPI 感知，Windows 会把 `winfo_screenwidth()` 等接口的返回值按缩放比例放大（实测 2560 的屏返回 3414），按这个坐标算出来的位置就在真实屏幕之外。
- **修复**：`enable_dpi_awareness()` 在 `tk.Tk()` 之前调 `SetProcessDpiAwareness(2)`（失败退回 `SetProcessDPIAware()`）；`position()` 再把坐标夹回屏幕内。
- **连带问题**：字体用「点」会随 DPI 放大，但 `wraplength` 是像素值，于是字变大、换行宽度不变，文字被挤成很窄的一列。改为按 `winfo_fpixels("1i")/96` 得到的缩放比换算 `wraplength`。

## 演示模式

`python main.py --demo`：跳过托盘和剪贴板监听，直接弹一张示例卡片。用于截图、预览界面，也方便改样式时快速看效果（不用真的去复制东西）。

## 已知限制 / 可以继续做的方向

- 只做英译中；中译英、日/韩等可以照 `langpair` 扩展
- 无发音（可以接有道 TTS 或系统 SAPI）
- 无本地词库缓存（离线就查不了）
- 只支持 Windows（`ctypes.windll` + pystray 托盘）
- 想升级成"框选屏幕区域 → OCR → 翻译"，可以复用 `core.py` 的翻译层，把捕获方式从剪贴板换成截图 OCR（如 Windows.Media.Ocr / Tesseract）
