#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WordLens 核心逻辑的离线单元测试。

用法：
    python tests/test_core.py           # 只跑离线用例
    python tests/test_core.py --live    # 额外跑真实网络请求
"""

import sys
from pathlib import Path

# Windows 控制台默认 GBK，音标里的 IPA 字符会打印失败
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 让 `python tests/test_core.py` 也能 import 到仓库根目录的 core.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import is_word, parse_youdao, fetch_word, fetch_translate  # noqa: E402

failures = 0


def check(name, got, exp):
    global failures
    ok = got == exp
    if not ok:
        failures += 1
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got!r} exp={exp!r}")


def test_is_word():
    print("\n== is_word ==")
    check("single word", is_word("serendipity"), True)
    check("short word", is_word("AI"), True)
    check("contraction", is_word("don't"), True)
    check("abbrev w/ dot", is_word("U.S."), True)
    check("phrase", is_word("hello world"), False)
    check("sentence", is_word("The rapid development of AI"), False)
    check("digits", is_word("123"), False)
    check("empty", is_word(""), False)
    check("none", is_word(None), False)
    check("too long", is_word("a" * 31), False)


def test_parse():
    print("\n== parse_youdao ==")
    sample = {
        "ec": {
            "word": [{"return-phrase": "hello", "ukphone": "həˈləʊ", "usphone": "həˈloʊ"}],
            "trs": [
                {"pos": "int.", "tr": [{"tran": "喂；哈罗，你好"}]},
                {"pos": "n.", "tr": [{"tran": "引人瞩目的事物"}]},
            ],
        },
        "web_trans": [{"trans": {"tran": "你好"}}],
    }
    r = parse_youdao(sample, "hello")
    check("uk phone", r["uk"], "həˈləʊ")
    check("us phone", r["us"], "həˈloʊ")
    check("entry0", r["entries"][0], ("int.", "喂；哈罗，你好"))
    check("entry1", r["entries"][1], ("n.", "引人瞩目的事物"))

    empty = parse_youdao({"foo": 1}, "xyz")
    check("no entry -> None", empty, None)


def test_live():
    print("\n== live network ==")
    w = fetch_word("serendipity")
    if w:
        print(f"fetch_word OK: uk={w['uk']} us={w['us']} entries={len(w['entries'])}")
        print("  sample:", w["entries"][0])
    else:
        print("fetch_word: None (no result)")
    t = fetch_translate("The cat sat on the mat.")
    print("fetch_translate:", t)


if __name__ == "__main__":
    test_is_word()
    test_parse()
    if "--live" in sys.argv:
        test_live()

    print(f"\n{'ALL TESTS PASSED' if failures == 0 else str(failures) + ' FAILURES'}")
    sys.exit(1 if failures else 0)
