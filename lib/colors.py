"""ANSI 转义序列和终端工具函数。"""

import os

# 文本样式
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# 前景色
BLUE = "\033[34m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"

# 背景色
BG_GRAY = "\033[48;5;236m"


def get_width():
    """获取终端宽度，最大 80 列。"""
    try:
        return min(os.get_terminal_size().columns, 80)
    except OSError:
        return 80
