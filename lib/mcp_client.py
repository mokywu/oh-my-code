"""MCP 客户端 - 基于官方 Python MCP SDK (mcp 包)。

使用 asyncio 后台线程管理异步 MCP 连接，对外提供同步接口。
"""

import asyncio
import json
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """管理单个 MCP Server 连接。"""

    def __init__(self, name: str, command: str, args: list = None, env: dict = None):
        self.name = name
        self.tools = []
        self._command = command
        self._args = args or []
        self._env = env
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def connect(self):
        """异步连接到 MCP Server。"""
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )

        self._exit_stack = AsyncExitStack()
        transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = transport

        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self._session.initialize()

        # 获取工具列表
        tools_result = await self._session.list_tools()
        self.tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "inputSchema": t.inputSchema if t.inputSchema else {"type": "object", "properties": {}},
            }
            for t in tools_result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict = None) -> str:
        """异步调用 MCP 工具。"""
        if not self._session:
            return "error: MCP session 未连接"

        result = await self._session.call_tool(tool_name, arguments or {})

        parts = []
        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
        return "\n".join(parts) if parts else json.dumps({"status": "ok"})

    async def close(self):
        """关闭连接。"""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None


class MCPManager:
    """MCP 全局管理器 - 通过后台 asyncio 线程管理所有连接。"""

    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def _ensure_loop(self):
        """确保后台事件循环在运行。"""
        if self._loop and self._loop.is_running():
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """后台线程运行事件循环。"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro, timeout=30):
        """在后台事件循环中执行协程，同步等待结果。"""
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def start(self, name: str, command: str, args: list = None, env: dict = None) -> bool:
        """启动 MCP Server。"""
        try:
            client = MCPClient(name, command, args, env)
            self._run_async(client.connect(), timeout=30)
            self.clients[name] = client
            return True
        except Exception as e:
            print(f"启动 MCP Server '{name}' 失败: {e}")
            return False

    def call(self, server: str, tool: str, args: dict = None) -> str:
        """调用 MCP 工具。"""
        if server not in self.clients:
            return f"error: MCP Server '{server}' 不存在"

        try:
            return self._run_async(self.clients[server].call_tool(tool, args), timeout=30)
        except Exception as e:
            return f"error: {e}"

    def get_tools(self) -> list:
        """获取所有 MCP 工具（供智能体调用）。"""
        tools = []
        self._tool_map = {}
        for server, client in self.clients.items():
            for tool in client.tools:
                key = f"mcp__{server}__{tool['name']}"
                self._tool_map[key] = (server, tool["name"])
                tools.append({
                    "name": key,
                    "description": f"[MCP:{server}] {tool.get('description', '')}",
                    "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
                })
        return tools

    def resolve_tool(self, name: str):
        """解析 MCP 工具名为 (server, tool) 元组，失败返回 None。"""
        if not hasattr(self, "_tool_map"):
            self.get_tools()
        return self._tool_map.get(name)

    def shutdown(self):
        """关闭所有 Server。"""
        for client in self.clients.values():
            try:
                self._run_async(client.close(), timeout=5)
            except:
                pass
        self.clients.clear()

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
            self._loop = None


_manager = MCPManager()


def get_mcp_manager() -> MCPManager:
    return _manager


def init_mcp():
    """从配置初始化 MCP。"""
    try:
        from .config import MCP_SERVERS
        if MCP_SERVERS:
            print("初始化 MCP Server...")
            for name, cfg in MCP_SERVERS.items():
                if _manager.start(name, cfg["command"], cfg.get("args"), cfg.get("env")):
                    count = len(_manager.clients[name].tools)
                    print(f"  [OK] {name}: {count} tools")
    except Exception as e:
        print(f"MCP 初始化异常: {e}")
