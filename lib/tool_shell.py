"""Shell 命令工具。"""

import subprocess

from .colors import DIM, RESET
from .config import BASH_TIMEOUT


def tool_bash(args):
    """执行 shell 命令并实时输出。"""
    proc = subprocess.Popen(
        args["cmd"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines = []
    try:
        if proc.stdout is not None:
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    print(f"    {DIM}┊ {line.rstrip()}{RESET}", flush=True)
                    output_lines.append(line)
        proc.wait(timeout=BASH_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append(f"\n(timed out after {BASH_TIMEOUT}s)")
    return "".join(output_lines).strip() or "(empty)"
