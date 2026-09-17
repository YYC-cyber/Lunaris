"""
聊天相关纯函数单元测试 —— 记忆解析 / 情绪提取 / 亲密度阶段 / 有效对话判定 / SOUL.md 加载。

均不依赖数据库，可离线运行。
"""
from common.helpers import extract_emotion, intimacy_stage
from core.memory import parse_json
from services.v1_0.chat_service import _is_meaningful
from services.v1_0.context_service import SoulPromptLoader


# ---------------- 记忆 JSON 解析 ----------------
def test_parse_memory_json_valid():
    raw = '[{"type":"user_profile","content":"用户叫小明，喜欢喝奶茶"}]'
    items = parse_json(raw)
    assert len(items) == 1
    assert items[0]["type"] == "user_profile"
    assert items[0]["content"] == "用户叫小明，喜欢喝奶茶"


def test_parse_memory_json_with_fence():
    raw = '```json\n[{"type":"long_term","content":"下周要搬家"}]\n```'
    items = parse_json(raw)
    assert len(items) == 1
    assert items[0]["content"] == "下周要搬家"


def test_parse_memory_json_invalid():
    assert parse_json("") == []
    assert parse_json("这不是JSON") == []
    assert parse_json('{"not":"a list"}') == []


def test_parse_memory_json_filters_bad_type():
    raw = '[{"type":"wrong_type","content":"x"},{"type":"user_profile","content":"ok"}]'
    items = parse_json(raw)
    assert [i["type"] for i in items] == ["user_profile"]


# ---------------- 情绪提取 ----------------
def test_extract_emotion_happy():
    assert extract_emotion("今天好开心啊哈哈") == "happy"


def test_extract_emotion_sad():
    assert extract_emotion("我好难过，最近压力好大") == "sad"


def test_extract_emotion_neutral():
    assert extract_emotion("随便聊聊") == "neutral"
    assert extract_emotion("") == "neutral"


# ---------------- 亲密度阶段 ----------------
def test_intimacy_stage():
    assert intimacy_stage(0) == "初识"
    assert intimacy_stage(30) == "熟悉"
    assert intimacy_stage(60) == "亲密"
    assert intimacy_stage(90) == "挚爱"


# ---------------- 有效对话判定 ----------------
def test_is_meaningful():
    assert _is_meaningful("今天想聊聊工作") is True
    assert _is_meaningful("嗯") is False
    assert _is_meaningful("哦哦") is False
    assert _is_meaningful("") is False


# ---------------- SOUL.md 加载 ----------------
class _Soul:
    def __init__(self, display_name, personality):
        self.display_name = display_name
        self.personality = personality


def test_soul_prompt_loader_real_file():
    text = SoulPromptLoader.load(_Soul("艾登", "data/souls/aiden/SOUL.md"))
    assert text.strip()


def test_soul_prompt_loader_fallback_when_missing():
    text = SoulPromptLoader.load(_Soul("测试角色", "data/souls/不存在的角色/SOUL.md"))
    assert "测试角色" in text
