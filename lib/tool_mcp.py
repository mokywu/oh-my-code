"""极简 MCP 工具。"""

from .mcp_client import get_mcp_manager


def tool_mcp(args):
    """MCP 工具管理。"""
    m = get_mcp_manager()
    
    # 列出 Server
    if not args or args.get("action") == "list":
        if not m.clients:
            return "没有运行的 MCP Server"
        
        lines = ["MCP Server 状态:"]
        for name, client in m.clients.items():
            lines.append(f"  {name}: {len(client.tools)} 个工具")
        return "\n".join(lines)
    
    # 调用工具
    if "tool" in args:
        server = args.get("server", "")
        tool = args.get("tool", "")
        return m.call(server, tool, args.get("arguments"))
    
    return "用法: {action: list} 或 {server, tool, arguments}"
