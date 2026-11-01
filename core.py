#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WordLens 核心查询逻辑（无 GUI 依赖，便于测试与复用）。"""

import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 6
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\-\.]*$")


def is_word(text):
    """判断是否为单个英文单词（无空格、纯字母/连字符/撇号/缩写点）。"""
    t = text.strip() if text else ""
    if not t or len(t) > 30:
        return False
    return bool(WORD_RE.match(t))


def fetch_word(word):
    """有道词典免 key 接口，返回 {word, uk, us, entries:[(pos, tran)]} 或 None。"""
    url = "https://dict.youdao.com/jsonapi"
    try:
        r = requests.get(url, params={"q": word}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return parse_youdao(r.json(), word)
    except Exception:
        return None


def parse_youdao(data, word):
    """从有道 jsonapi 响应里抽取音标与释义。"""
    res = {"word": word, "uk": "", "us": "", "entries": []}
    ec = data.get("ec")
    if ec:
        for w in ec.get("word", []):
            res["uk"] = w.get("ukphone", "") or res["uk"]
            res["us"] = w.get("usphone", "") or res["us"]
            if res["uk"] and res["us"]:
                break
        for tr in ec.get("trs", [])[:4]:
            pos = tr.get("pos", "")
            tran = ""
            for t in tr.get("tr", []):
                tran = t.get("tran", "") or tran
            if tran:
                res["entries"].append((pos, tran.strip()))
    if not res["entries"]:
        for wt in data.get("web_trans", [])[:4]:
            tran = wt.get("trans", {}).get("tran", "")
            if tran:
                res["entries"].append(("", tran.strip()))
    return res if res["entries"] else None


def fetch_translate(text):
    """MyMemory 免 key 翻译，返回中文或 None。"""
    url = "https://api.mymemory.translated.net/get"
    try:
        r = requests.get(url, params={"q": text, "langpair": "en|zh-CN"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        d = r.json()
        if d.get("responseStatus") == 200:
            tr = d.get("responseData", {}).get("translatedText", "")
            return tr if tr else None
    except Exception:
        return None
    return None
