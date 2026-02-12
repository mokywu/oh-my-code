"""内置工具实现与注册。聚合各工具模块。"""

from .tool_file import tool_edit, tool_glob, tool_grep, tool_read, tool_write
from .tool_shell import tool_bash
from .tool_web import tool_browse, tool_search
from .tool_fs import get_platform, tool_fs
from .tool_mcp import tool_mcp



# 每个工具：(描述, 参数 schema 简写, 实现函数)
# 参数类型后缀 "?" 表示可选
TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        tool_read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        tool_write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        tool_edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        tool_glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        tool_grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        tool_bash,
    ),
    "search": (
        "Search the web using search engines (duckduckgo/searx)",
        {"query": "string", "engine": "string?", "limit": "number?"},
        tool_search,
    ),
    "browse": (
        "Browse a specific webpage and extract its text content",
        {"url": "string"},
        tool_browse,
    ),
    "fs": (
        "File system operations (cross-platform). action: list|copy|move|delete|mkdir. "
        "list: path?, recursive? | copy: src, dst, overwrite? | move: src, dst | delete: path | mkdir: path, exist_ok?",
        {
            "action": "string",
            "path": "string?",
            "src": "string?",
            "dst": "string?",
            "recursive": "boolean?",
            "overwrite": "boolean?",
            "exist_ok": "boolean?",
        },
        tool_fs,
    ),
    "mcp": (
        "MCP tool management",
        {"action": "string?", "server": "string?", "tool": "string?", "arguments": "object?"},
        tool_mcp,
    ),
}



def run_tool(name, args):
    """执行指定工具，捕获异常返回错误信息。"""
    # 内置工具
    if name in TOOLS:
        try:
            return TOOLS[name][2](args)
        except Exception as err:
            return f"error: {err}"
    
    # MCP 工具 (格式: mcp__server__tool)
    if name.startswith("mcp__"):
        try:
            from .mcp_client import get_mcp_manager
            m = get_mcp_manager()
            resolved = m.resolve_tool(name)
            if resolved:
                server, tool = resolved
                return m.call(server, tool, args)
            return f"error: unknown MCP tool: {name}"
        except Exception as err:
            return f"error: {err}"
    
    return f"error: 未知工具 '{name}'"



def make_schema():
    """将工具注册表转换为 Anthropic API tools schema 格式。"""
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
        result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    
    # 添加 MCP 工具
    try:
        from .mcp_client import get_mcp_manager
        result.extend(get_mcp_manager().get_tools())
    except:
        pass
    
    return result

