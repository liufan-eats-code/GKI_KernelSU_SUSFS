#!/usr/bin/env python3
"""关闭 SukiSU (builtin 分支) 的安全模式。

背景:
    builtin 分支的 vol_detector_event() 用 static 变量累计音量键次数
    (vol_up_cnt / vol_down_cnt)，整个开机周期都不清零，也没有任何时间
    窗口限制。官方文档说的是"开机第一屏后快速按三次"，但实现上只要累计
    满 3 次就会置 safe_mode_flag，导致正常调节音量也误触发安全模式，
    所有模块被禁用。

做法:
    把 ksu_is_safe_mode() 整个函数体替换成 return false，这样无论音量键
    被按多少次，用户态都认为没有进入安全模式。

定位方式:
    不依赖固定行号，也不拼接原始函数体文本（上游随时会改注释），而是找到
    函数签名后，再找它后面第一个行首的 `}` 作为函数结束，整体替换。
    这样对上游改动更鲁棒。

用法:
    python3 disable-sukisu-safe-mode.py <path-to-ksud.c>
"""

import pathlib
import sys

SIGNATURE = "bool ksu_is_safe_mode(void)"
MARKER = "PATCHED: safe mode disabled"

REPLACEMENT = (
    SIGNATURE
    + "\n{\n"
    "    /* PATCHED: safe mode disabled.\n"
    "     * builtin branch used static, never-reset volume counters with no\n"
    "     * time window, so normal volume changes falsely triggered safe mode\n"
    "     * and disabled all modules. Always report not-in-safe-mode. */\n"
    "    return false;\n"
    "}\n"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: disable-sukisu-safe-mode.py <path-to-ksud.c>")
        return 2

    path = pathlib.Path(sys.argv[1])
    if not path.is_file():
        print(f"::error::file not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8")

    # 幂等：重复执行不再改写
    if MARKER in text:
        print("safe-mode patch already applied, skipping")
        return 0

    start = text.find(SIGNATURE)
    if start < 0:
        print(f"::error::{SIGNATURE} not found; upstream changed")
        return 1

    # 函数体收尾：签名之后第一个行首的 "}\n"
    end = text.find("\n}\n", start)
    if end < 0:
        print("::error::closing brace of ksu_is_safe_mode not found")
        return 1

    patched = text[:start] + REPLACEMENT + text[end + 3 :]

    if patched == text:
        print("::error::replacement produced no change")
        return 1

    path.write_text(patched, encoding="utf-8")
    print("safe mode disabled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
