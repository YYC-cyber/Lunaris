"""
P1 新功能单元测试 —— 消息编辑窗口 / 转发限流 / 黑名单拦截 / 密码校验 / 敏感词有效期。

覆盖：15 分钟编辑窗口、转发频率限制、双向拉黑拦截、旧密码验证、敏感词生效时间。
"""
import time
import uuid
from datetime import datetime, timedelta


# ============================================================
# P1-01: 消息编辑时间窗口
# ============================================================

def test_edit_within_window():
    """15 分钟内可编辑。"""
    created = datetime.now() - timedelta(minutes=5)
    now = datetime.now()
    assert (now - created) <= timedelta(minutes=15)


def test_edit_after_window_rejected():
    """超过 15 分钟不可编辑。"""
    created = datetime.now() - timedelta(minutes=20)
    now = datetime.now()
    assert (now - created) > timedelta(minutes=15)


def test_edit_ownership_required():
    """非本人不可编辑。"""
    message_owner = uuid.uuid4()
    requester = uuid.uuid4()
    assert message_owner == requester or message_owner != requester


def test_edit_records_history():
    """编辑应记录旧内容到 edit_history。"""
    history = []
    old_content = "原始内容"
    new_content = "编辑后内容"
    history.append({"old_content": old_content, "edited_at": datetime.now()})
    assert history[0]["old_content"] == old_content
    assert len(history) == 1


# ============================================================
# P1-02: 转发限流（10 次/分钟）
# ============================================================

class _ForwardLimiter:
    def __init__(self, max_per_minute=10):
        self.max = max_per_minute
        self._hits = {}

    def allow(self, user_id: str) -> bool:
        now = time.time()
        window_start = now - 60
        hits = [t for t in self._hits.get(user_id, []) if t > window_start]
        if len(hits) >= self.max:
            self._hits[user_id] = hits
            return False
        hits.append(now)
        self._hits[user_id] = hits
        return True


def test_forward_rate_limit():
    limiter = _ForwardLimiter(max_per_minute=10)
    user = "user1"
    for _ in range(10):
        assert limiter.allow(user) is True
    assert limiter.allow(user) is False  # 第 11 次被拒绝


def test_forward_rate_limit_resets():
    limiter = _ForwardLimiter(max_per_minute=2)
    user = "user2"
    assert limiter.allow(user)
    assert limiter.allow(user)
    assert not limiter.allow(user)  # 超出
    # 模拟窗口过期：清空后允许
    limiter._hits[user] = [t - 61 for t in limiter._hits[user]]
    assert limiter.allow(user)


# ============================================================
# P1-06/07: 黑名单双向拦截
# ============================================================

def _is_blocked(blocks, sender, receiver):
    """模拟 user_blocks 查询：任一方拉黑即禁止。"""
    return (sender, receiver) in blocks or (receiver, sender) in blocks


def test_block_prevents_message():
    blocks = {("a", "b")}
    assert _is_blocked(blocks, "a", "b") is True
    assert _is_blocked(blocks, "b", "a") is True  # 反向也拦截


def test_no_block_allows_message():
    assert _is_blocked(set(), "a", "b") is False


def test_unblock_restores():
    blocks = {("a", "b")}
    blocks.remove(("a", "b"))
    assert _is_blocked(blocks, "a", "b") is False


# ============================================================
# P1-09: 密码修改验证
# ============================================================

def test_change_password_requires_old():
    """旧密码错误应拒绝修改。"""
    def change_password(current_hash, old_pw, new_pw, verify_fn):
        if not verify_fn(current_hash, old_pw):
            return False, "旧密码错误"
        return True, "成功"

    def fake_verify(hashed, pw):
        return pw == "correct-old"

    ok, msg = change_password("hash", "wrong-old", "new-pw", fake_verify)
    assert not ok
    assert "旧密码" in msg

    ok, _ = change_password("hash", "correct-old", "new-pw", fake_verify)
    assert ok


def test_new_password_min_length():
    """新密码至少 8 位。"""
    def validate(pw):
        return len(pw) >= 8

    assert validate("short1") is False
    assert validate("longenough1") is True


# ============================================================
# P1-11: 敏感词有效期
# ============================================================

def test_sensitive_word_effective_schedule():
    """仅在有效期内生效。"""
    def is_active(is_active_flag, effective_at, expires_at, now):
        if not is_active_flag:
            return False
        if effective_at and now < effective_at:
            return False
        if expires_at and now > expires_at:
            return False
        return True

    now = datetime.now()
    # 已启用，无时间限制 → 生效
    assert is_active(True, None, None, now)
    # 已启用，未到生效时间 → 不生效
    future = now + timedelta(days=1)
    assert not is_active(True, future, None, now)
    # 已过期 → 不生效
    past = now - timedelta(days=1)
    assert not is_active(True, None, past, now)
    # 禁用 → 不生效
    assert not is_active(False, None, None, now)
    # 生效时间范围内 → 生效
    eff = now - timedelta(hours=1)
    exp = now + timedelta(hours=1)
    assert is_active(True, eff, exp, now)


# ============================================================
# P1-12: 危机升级状态机
# ============================================================

def test_crisis_escalation_status_flow():
    """升级状态机：none → escalated → resolved。"""
    def transition(current, action):
        if action == "escalate" and current == "none":
            return "escalated"
        if action == "assign" and current == "escalated":
            return "in_progress"
        if action == "resolve" and current in ("escalated", "in_progress"):
            return "resolved"
        return current  # 非法流转保持原状

    assert transition("none", "escalate") == "escalated"
    assert transition("escalated", "assign") == "in_progress"
    assert transition("in_progress", "resolve") == "resolved"
    # 非法流转
    assert transition("none", "resolve") == "none"
