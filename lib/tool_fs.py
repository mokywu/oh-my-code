"""文件系统操作工具（合并：list/copy/move/delete/mkdir）。"""

import os
import shutil
import sys


def get_platform():
    """检测当前操作系统，返回 'windows' | 'darwin' | 'linux'。"""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _norm_path(p):
    return os.path.normpath(p)


def tool_fs(args):
    """
    文件系统操作（跨平台）。action: list|copy|move|delete|mkdir
    - list: path, recursive?
    - copy: src, dst, overwrite?
    - move: src, dst
    - delete: path
    - mkdir: path, exist_ok?
    """
    action = args.get("action", "list").lower()
    platform = get_platform()

    if action == "list":
        path = _norm_path(args.get("path", "."))
        recursive = args.get("recursive", False)
        if not os.path.exists(path):
            return f"error: path not found: {path}"
        if not os.path.isdir(path):
            return f"error: not a directory: {path}"
        lines = [f"Platform: {platform} | Path: {path}", ""]

        def _list(dir_path, prefix=""):
            try:
                entries = sorted(
                    os.listdir(dir_path),
                    key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()),
                )
            except PermissionError:
                return [f"{prefix}[Permission denied]"]
            out = []
            for name in entries:
                full = os.path.join(dir_path, name)
                rel = os.path.join(prefix, name) if prefix else name
                try:
                    if os.path.isdir(full):
                        out.append(f"{rel}/  [dir]")
                        if recursive:
                            out.extend(_list(full, rel))
                    else:
                        size = os.path.getsize(full)
                        out.append(f"{rel}  {size} bytes")
                except (PermissionError, OSError):
                    out.append(f"{rel}  [unreadable]")
            return out

        lines.extend(_list(path))
        return "\n".join(lines) if lines else "empty"

    elif action == "copy":
        src = _norm_path(args["src"])
        dst = _norm_path(args["dst"])
        if not os.path.exists(src):
            return f"error: source not found: {src}"
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=args.get("overwrite", False))
            else:
                dst_dir = os.path.dirname(dst)
                if dst_dir and not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                if os.path.isdir(dst):
                    dst = os.path.join(dst, os.path.basename(src))
                shutil.copy2(src, dst)
            return f"ok: copied {src} -> {dst} (platform: {platform})"
        except shutil.Error as e:
            return f"error: {e}"
        except FileExistsError:
            return "error: destination exists (use overwrite=true for directories)"

    elif action == "move":
        src = _norm_path(args["src"])
        dst = _norm_path(args["dst"])
        if not os.path.exists(src):
            return f"error: source not found: {src}"
        try:
            shutil.move(src, dst)
            return f"ok: moved {src} -> {dst} (platform: {platform})"
        except Exception as e:
            return f"error: {e}"

    elif action == "delete":
        path = _norm_path(args["path"])
        if not os.path.exists(path):
            return f"error: path not found: {path}"
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                return f"ok: removed directory {path} (platform: {platform})"
            os.remove(path)
            return f"ok: removed file {path} (platform: {platform})"
        except Exception as e:
            return f"error: {e}"

    elif action == "mkdir":
        path = _norm_path(args["path"])
        try:
            os.makedirs(path, exist_ok=args.get("exist_ok", True))
            return f"ok: created {path} (platform: {platform})"
        except Exception as e:
            return f"error: {e}"

    else:
        return f"error: unknown action '{action}'. Use: list|copy|move|delete|mkdir"
