"""
危机识别（SAFE）单元测试 —— 纯函数，无需数据库。

覆盖：scan_for_crisis 关键词通道命中 / 未命中 / 空输入。
"""
from core.security import CrisisHit, scan_for_crisis


def test_crisis_word_hit():
    hit = scan_for_crisis("我想自杀，活着没意思了")
    assert isinstance(hit, CrisisHit)
    assert hit.risk_level == "high"
    assert hit.hit_channel == "keywords"


def test_crisis_multiple_words():
    hit = scan_for_crisis("最近压力太大，真想死")
    assert hit is not None
    assert hit.risk_level == "high"


def test_normal_text_no_hit():
    assert scan_for_crisis("今天天气不错，想出去走走") is None


def test_empty_and_none():
    assert scan_for_crisis("") is None
    assert scan_for_crisis(None) is None
