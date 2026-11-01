#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WordLens - 划词速查。

复制英文单词或句子，右下角自动弹出释义 / 翻译。
- 单个英文单词 -> 有道词典（音标 + 词性 + 中文释义）
- 句子 / 短语   -> MyMemory 翻译（整句中译）
全局监听剪贴板（Ctrl+C / 右键复制），系统托盘常驻，Esc 或点击关闭。
"""

import ctypes
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

import pyperclip
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as Item

from core import is_word, fetch_word, fetch_translate

# ----------------------------- 配置 -----------------------------
PAD = 20
AUTO_HIDE_MS = 12000


def enable_dpi_awareness():
    """开启 DPI 感知。

    不开启的话，系统会把 Tk 报告的屏幕尺寸按缩放比例放大（如 200% 下 1707px 变成
    3414），悬浮窗按错误坐标定位就会跑到屏幕外。必须在 tk.Tk() 之前调用。
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass



# ----------------------------- 悬浮窗 -----------------------------
class WordLens:
    def __init__(self, demo=False):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.attributes("-topmost", True)
        # 每逻辑英寸像素数 / 96 = 系统缩放比例（100% -> 1.0，150% -> 1.5）
        try:
            self.scale = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        except Exception:
            self.scale = 1.0
        self.win = None
        self.last_shown = ""
        self.auto_hide_id = None
        if demo:
            # 演示模式：不监听剪贴板、不建托盘，直接展示一个示例卡片（用于截图/预览）
            self.root.after(800, self.render_demo)
        else:
            self.build_tray()
            threading.Thread(target=self.clip_loop, daemon=True).start()
        self.root.mainloop()

    # ---- 演示模式 ----
    def render_demo(self):
        self.render_word({
            "word": "serendipity",
            "uk": "ˌserənˈdɪpəti",
            "us": "ˌserənˈdɪpəti",
            "entries": [
                ("n.", "意外发现美好事物的运气"),
                ("n.", "机缘巧合；意外发现珍宝的运气"),
            ],
        })


    # ---- 系统托盘 ----
    def build_tray(self):
        img = Image.new("RGB", (64, 64), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=(53, 74, 183))
        d.text((26, 20), "W", fill=(255, 255, 255))
        menu = pystray.Menu(
            Item("关于 WordLens", self.on_about),
            Item("退出", self.on_quit),
        )
        self.icon = pystray.Icon("WordLens", img, "WordLens 划词速查", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    # ---- 剪贴板监听 ----
    def clip_loop(self):
        last = ""
        while True:
            time.sleep(0.3)
            try:
                text = pyperclip.paste()
            except Exception:
                continue
            if not text:
                continue
            text = text.strip()
            if not text or text == last or text == self.last_shown:
                last = text
                continue
            last = text
            self.handle(text)

    def handle(self, text):
        if is_word(text):
            res = fetch_word(text)
            if res:
                self.root.after(0, self.render_word, res)
            else:
                self.root.after(0, self.render_msg, f"未找到「{text}」的释义")
        else:
            tr = fetch_translate(text)
            if tr:
                self.root.after(0, self.render_sentence, text, tr)
            else:
                self.root.after(0, self.render_msg, "翻译失败，请检查网络")

    # ---- 窗口骨架 ----
    def ensure_win(self):
        if self.win is None:
            self.win = tk.Toplevel(self.root)
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            self.win.configure(bg="white")
            self.win.bind("<Escape>", lambda e: self.hide())
            self.win.bind("<Button-1>", lambda e: self.hide())
            self.frame = tk.Frame(self.win, bg="white",
                                  highlightbackground="#d0d0d0", highlightthickness=1)
            self.frame.pack(fill="both", expand=True)
        for w in self.frame.winfo_children():
            w.destroy()

    def position(self):
        self.win.update_idletasks()
        w = max(self.win.winfo_width(), self.win.winfo_reqwidth())
        h = max(self.win.winfo_height(), self.win.winfo_reqheight())
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        # 夹到屏幕内，避免坐标算出界导致窗口跑到屏幕外
        x = max(0, min(sw - w - PAD, sw - w))
        y = max(0, min(sh - h - PAD, sh - h))
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def show(self):
        fg = ctypes.windll.user32.GetForegroundWindow()
        self.win.deiconify()
        self.position()
        # 还原焦点，避免抢走用户当前窗口
        try:
            ctypes.windll.user32.SetForegroundWindow(fg)
        except Exception:
            pass
        if self.auto_hide_id:
            self.win.after_cancel(self.auto_hide_id)
        self.auto_hide_id = self.win.after(AUTO_HIDE_MS, self.hide)

    def hide(self):
        if self.win:
            self.win.withdraw()

    # ---- 渲染：单词 ----
    def render_word(self, res):
        self.ensure_win()
        self.last_shown = res["word"]
        f_title = tkfont.Font(size=15, weight="bold")
        f_phon = tkfont.Font(size=12)
        f_body = tkfont.Font(size=12)

        head = tk.Frame(self.frame, bg="white")
        head.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(head, text=res["word"], font=f_title, bg="white",
                 fg="#1a1a1a", anchor="w").pack(side="left")
        phon = []
        if res["uk"]:
            phon.append(f"英 [{res['uk']}]")
        if res["us"]:
            phon.append(f"美 [{res['us']}]")
        if phon:
            tk.Label(head, text="  ".join(phon), font=f_phon, bg="white",
                     fg="#666").pack(side="left", padx=(6, 0))

        for pos, tran in res["entries"]:
            row = tk.Frame(self.frame, bg="white")
            row.pack(fill="x", padx=12, pady=1)
            if pos:
                tk.Label(row, text=pos, font=f_body, bg="white", fg="#3c3489",
                         width=6, anchor="w").pack(side="left")
            tk.Label(row, text=tran, font=f_body, bg="white", fg="#1a1a1a",
                     anchor="w", wraplength=int(240 * self.scale), justify="left"
                     ).pack(side="left", fill="x", expand=True)
        self.build_footer()
        self.show()

    # ---- 渲染：句子 ----
    def render_sentence(self, src, dst):
        self.ensure_win()
        self.last_shown = src
        f_src = tkfont.Font(size=11)
        f_dst = tkfont.Font(size=13)
        tk.Label(self.frame, text=src, font=f_src, bg="white", fg="#666",
                 wraplength=int(260 * self.scale), justify="left", anchor="w"
                 ).pack(padx=12, pady=(10, 4))
        tk.Label(self.frame, text=dst, font=f_dst, bg="white", fg="#1a1a1a",
                 wraplength=int(260 * self.scale), justify="left", anchor="w"
                 ).pack(padx=12, pady=(2, 4))
        self.build_footer()
        self.show()

    # ---- 渲染：提示 ----
    def render_msg(self, msg):
        self.ensure_win()
        self.last_shown = msg
        tk.Label(self.frame, text=msg, font=tkfont.Font(size=12), bg="white",
                 fg="#a32d2d", wraplength=int(260 * self.scale), justify="left"
                 ).pack(padx=12, pady=14)
        self.build_footer()
        self.show()

    def build_footer(self):
        foot = tk.Frame(self.frame, bg="white")
        foot.pack(fill="x", padx=12, pady=(6, 8))
        tk.Label(foot, text="Esc / 点击关闭", font=tkfont.Font(size=9),
                 bg="white", fg="#aaa", anchor="e").pack(side="right")

    # ---- 托盘回调 ----
    def on_about(self):
        self.root.after(0, self.render_msg, "WordLens · 复制英文即可查词/翻译")

    def on_quit(self):
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.after(0, self.root.quit)


if __name__ == "__main__":
    enable_dpi_awareness()
    WordLens(demo="--demo" in sys.argv)
