"""
朋友圈工作流单元测试 —— 发布 / 删除 / 隐私控制（P0 + P2-04）。

覆盖：发布验证、可见性计算、分组隐私过滤、删除权限。
"""
import uuid
from datetime import datetime

import pytest


# ============================================================
# 隐私可见性规则（纯逻辑，模拟 DAO 过滤逻辑）
# ============================================================

def _compute_visible(
    moment_visibility: str,
    visible_groups: list,
    hidden_user_ids: list,
    viewer_id,
    author_id,
    is_friend: bool = False,
    viewer_groups: list = None,
):
    """模拟 moment_dao.list_timeline_visible() 的过滤逻辑。"""
    viewer_groups = viewer_groups or []

    # 作者本人始终可见
    if viewer_id == author_id:
        return True

    # 黑名单：被隐藏的用户不可见（作者除外）
    if viewer_id in hidden_user_ids:
        return False

    if moment_visibility == 'private':
        return False

    # 分组可见优先
    if visible_groups:
        return bool(set(viewer_groups) & set(visible_groups))

    if moment_visibility == 'friends':
        return is_friend

    # public
    return True


def test_public_visible_to_everyone():
    assert _compute_visible('public', [], [], "userA", "userB") is True


def test_private_only_author():
    assert _compute_visible('private', [], [], "userA", "userB") is False
    assert _compute_visible('private', [], [], "userB", "userB") is True


def test_friends_requires_friendship():
    assert _compute_visible('friends', [], [], "userA", "userB", is_friend=True) is True
    assert _compute_visible('friends', [], [], "userA", "userB", is_friend=False) is False


def test_hidden_user_blocked_even_if_friend():
    assert _compute_visible('public', [], ["userA"], "userA", "userB") is False


def test_visible_groups_filtering():
    # viewer 在"家人"组，moment 只对"家人"可见 → 可见
    assert _compute_visible('public', ["family"], [], "userA", "userB",
                            viewer_groups=["family"]) is True
    # viewer 在"工作"组，moment 只对"家人"可见 → 不可见
    assert _compute_visible('public', ["family"], [], "userA", "userB",
                            viewer_groups=["work"]) is False


def test_empty_content_rejected():
    """模拟发布时内容校验：空内容或超长应拒绝。"""
    def validate_content(content):
        if not content or not content.strip():
            return False, "内容不能为空"
        if len(content) > 2000:
            return False, "内容超出 2000 字限制"
        return True, None

    ok, _ = validate_content("   ")
    assert not ok
    ok, _ = validate_content("今天天气不错")
    assert ok
    ok, _ = validate_content("x" * 2001)
    assert not ok


def test_delete_ownership_check():
    """模拟删除权限：非所有者返回 404。"""
    def delete_moment(moment_owner_id, requester_id):
        if moment_owner_id != requester_id:
            return None, 404
        return {"deleted": True}, 200

    _, code = delete_moment("owner", "other")
    assert code == 404
    _, code = delete_moment("owner", "owner")
    assert code == 200
