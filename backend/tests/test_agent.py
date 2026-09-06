"""
agent 层单元测试 —— LRU 缓存 / 工具 schema / 无工具循环。

不依赖数据库（无工具分支不落库）。
"""
import asyncio
import uuid

from core.agent import MEMORY_TOOL_SCHEMA, HermesAgent, get_agent


def test_agent_lru_cache():
    uid = uuid.uuid4()
    a = get_agent(uid, 1)
    b = get_agent(uid, 1)
    assert a is b  # 同 (user, soul) 复用实例
    c = get_agent(uid, 2)
    assert c is not a


def test_memory_tool_schema():
    fn = MEMORY_TOOL_SCHEMA["function"]
    assert fn["name"] == "memory_tool"
    props = fn["parameters"]["properties"]
    assert set(props) == {"operation", "memory_type", "content", "old_content"}
    assert props["operation"]["enum"] == ["add", "replace", "remove"]


def test_agent_loop_no_tools():
    class _MockLLM:
        async def chat_completion_messages(self, messages, tools=None, **kwargs):
            # 断言 tools 被传入
            assert tools is not None
            return {"content": "你好", "tool_calls": []}

    agent = HermesAgent(uuid.uuid4(), 1)
    result = asyncio.run(
        agent._agent_loop(_MockLLM(), [{"role": "user", "content": "hi"}], 0.8, 100)
    )
    assert result == "你好"
