"""
内容安全 —— 三层防御 + 记忆注入扫描。

【职责】
- scan_text(text) -> ScanResult
  第一层：textfilter 敏感词过滤（中文 DFA，自带词库；
         原 toolgood-words 无 Python 版，v1.2 评审后替换）
  第二层：DeepSeek 分类 prompt 语义审核（涉黄/暴力/政治/诱导等分类，
         返回 JSON 判定；原 llm-guard 依赖 torch 无 Intel Mac 包，
         v1.2.1 评审替换）
  第三层：命中/未命中都异步写审计日志（audit_log）
  ScanResult: {is_passed, risk_level, hit_keywords, guard_flags}
- scan_for_crisis(text) -> CrisisHit | None
  # 危机专用检测（区别于常规敏感词）：
  # 自伤/轻生/受虐词表 + DeepSeek 语义分类 → 交给 core/crisis.py
- scan_memory_content(text) -> MemoryScanResult   # ★ 参考 lee-agent
  # 记忆写入前的注入/外泄防护，命中即拒绝写入：
  #   prompt_injection  提示注入（ignore previous instructions 等）
  #   role_hijack       角色劫持（you are now ...）
  #   deception_hide    隐藏指令（do not tell the user ...）
  #   exfil_curl/wget   密钥外泄（curl/wget 拼接 ${KEY/TOKEN/SECRET}）
  #   read_secrets      读取密钥文件（.env / credentials / .netrc）
  #   ssh_backdoor      SSH 后门（authorized_keys / ~/.ssh）
  #   invisible_unicode 隐形字符（U+200B~U+202E）

【说明】
- 常规安全、危机检测、记忆注入防护三者分离，各司其职
- 社区文本与对话文本共用 scan_text
"""
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MemoryScanResult:
    """记忆写入扫描结果"""
    is_passed: bool
    hits: list = field(default_factory=list)


# 记忆写入前的防注入 / 防外泄模式（参考 lee-agent，简化版）
_MEMORY_SCAN_PATTERNS: dict = {
    "prompt_injection": re.compile(
        r"ignore (previous|above) (instructions|prompt)|system prompt override|"
        r"忽略(之前|上面)的(指令|提示)|重新执行指令|无视系统", re.I
    ),
    "role_hijack": re.compile(r"you are now|你现在是|扮演|role[ -]?play", re.I),
    "deception_hide": re.compile(r"do not tell the user|不要告诉用户|别告诉用户", re.I),
    "exfil_curl": re.compile(r"curl\b.*(\$\{?\w*(KEY|TOKEN|SECRET)|sk-|ghp_)", re.I),
    "exfil_wget": re.compile(r"wget\b.*(\$\{?\w*(KEY|TOKEN|SECRET)|sk-|ghp_)", re.I),
    "read_secrets": re.compile(r"(cat|type|less)\b.*(\.env|credentials|\.netrc|\.ssh|id_rsa)", re.I),
    "ssh_backdoor": re.compile(r"authorized_keys|\.ssh", re.I),
    "invisible_unicode": re.compile(r"[​-‮]"),
}


def scan_memory_content(text: str) -> MemoryScanResult:
    """记忆写入前的注入 / 外泄防护。命中任一模式即拒绝写入。"""
    if not text:
        return MemoryScanResult(is_passed=True)
    hits = [name for name, pat in _MEMORY_SCAN_PATTERNS.items() if pat.search(text)]
    return MemoryScanResult(is_passed=not hits, hits=hits)


# ==================== 常规内容安全（scan_text）+ 危机检测（scan_for_crisis） ====================

_BASE_DATA = Path(__file__).resolve().parent.parent / "data"
_SENSITIVE_WORDS_FILE = _BASE_DATA / "sensitive_words.txt"
_CRISIS_WORDS_FILE = _BASE_DATA / "crisis_words.txt"


@dataclass
class ScanResult:
    """常规内容安全扫描结果"""
    is_passed: bool
    hit_keywords: list = field(default_factory=list)
    risk_level: str = "normal"   # normal / warning / high
    filtered_text: str = ""


@dataclass
class CrisisHit:
    """危机检测命中结果"""
    risk_level: str          # warning / high / critical
    hit_channel: str         # keywords / llm / both
    hit_keywords: list = field(default_factory=list)


def _load_word_file(path: Path) -> list:
    """读取词库文件：跳过注释(#)和空行，统一转小写。"""
    if not path.exists():
        return []
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        words.append(line.lower())
    return words


_sensitive_words: list = None


def _get_sensitive_words() -> list:
    global _sensitive_words
    if _sensitive_words is None:
        _sensitive_words = _load_word_file(_SENSITIVE_WORDS_FILE)
    return _sensitive_words


_crisis_words: list = None


def _get_crisis_words() -> list:
    global _crisis_words
    if _crisis_words is None:
        _crisis_words = _load_word_file(_CRISIS_WORDS_FILE)
    return _crisis_words


_text_filter = None


def _get_text_filter():
    """延迟初始化 textfilter（DFA 敏感词）。"""
    global _text_filter
    if _text_filter is None:
        from textfilter.textfilter import TextFilter
        _text_filter = TextFilter(file=str(_SENSITIVE_WORDS_FILE))
    return _text_filter


async def scan_text(text: str, db=None) -> ScanResult:
    """三层防御的第一层：字面敏感词（textfilter DFA）。

    优先使用数据库驱动的敏感词；如果 db 为 None，则使用文件词库。
    第二层（DeepSeek 语义审核）与第三层（审计日志）为 TODO，
    接入后在此扩展。当前命中即 risk_level=warning。
    """
    if not text:
        return ScanResult(is_passed=True)

    # 获取敏感词列表（优先数据库，降级文件）
    if db is not None:
        try:
            from services.sensitive_word_service import SensitiveWordService
            db_words = await SensitiveWordService.load_active_words(db)
            # 如果数据库返回了单词，使用数据库词；否则降级到文件
            words_to_check = db_words if db_words else _get_sensitive_words()
        except Exception:
            words_to_check = _get_sensitive_words()
    else:
        words_to_check = _get_sensitive_words()

    lower = text.lower()
    filtered = _get_text_filter().filter(lower)
    if filtered == lower:
        return ScanResult(is_passed=True)

    hit_keywords = [w for w in words_to_check if w and w in lower]
    return ScanResult(
        is_passed=False,
        hit_keywords=hit_keywords,
        risk_level="warning",
        filtered_text=filtered,
    )


def scan_for_crisis(text: str) -> CrisisHit | None:
    """危机专用检测（关键词通道）。

    命中 crisis_words.txt 高危词 → 返回 CrisisHit（risk_level=high）；
    未命中返回 None。DeepSeek 语义通道为第二通道（后续接入）。
    """
    if not text:
        return None

    lower = text.lower()
    hit = [w for w in _get_crisis_words() if w and w in lower]
    if not hit:
        return None
    return CrisisHit(risk_level="high", hit_channel="keywords", hit_keywords=hit)


async def scan_semantic(text: str) -> dict:
    """语义审核层（第二层）：DeepSeek 分类涉黄/暴力/诱导。

    返回 {"is_passed", "risk_level", "categories"}。
    无平台 key 或调用失败 → fail-open（放行）。
    """
    if not text or not text.strip():
        return {"is_passed": True, "risk_level": "normal", "categories": []}

    from config.settings import get_settings
    s = get_settings()
    if not s.DEEPSEEK_API_KEY:
        return {"is_passed": True, "risk_level": "normal", "categories": []}

    from clients.llm_client import LLMClient
    llm = LLMClient()  # 用平台 key 做内容审核（不依赖用户 BYOK）
    prompt = (
        "你是内容安全审核员。判断文本是否含违规内容（涉黄/暴力/政治敏感/诱导诈骗/人身攻击）。\n"
        "只输出 JSON，不要其它文字，格式：{\"passed\": true或false, \"categories\": [违规类别列表]}。\n"
        f"文本：{text[:500]}"
    )
    try:
        import json
        import re
        result = await llm.chat_completion(
            system_prompt="你是内容安全审核员，只输出 JSON。",
            history=[], user_message=prompt, temperature=0.1, max_tokens=80,
        )
        m = re.search(r"\{.*\}", result, re.S)
        data = json.loads(m.group(0)) if m else {}
        passed = bool(data.get("passed", True))
        return {
            "is_passed": passed,
            "risk_level": "high" if not passed else "normal",
            "categories": data.get("categories", []),
        }
    except Exception as e:
        print(f"⚠️ 语义审核失败: {e}")
        return {"is_passed": True, "risk_level": "normal", "categories": []}
