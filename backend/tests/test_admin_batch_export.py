"""
后台管理 - 批量操作和导出 API 单元测试（P2-08, P2-09）

测试项：
- 批量删除用户
- 批量暂停用户账户
- 批量删除消息
- 导出用户数据（CSV/JSON）
- 导出消息数据（按日期范围，CSV/JSON）
- 导出举报记录（按状态筛选，CSV/JSON）
"""
import uuid
import pytest
from datetime import datetime, timedelta

# 注：这些是语法检查测试，实际集成测试需要测试数据库和 FastAPI TestClient


def test_batch_delete_request_model():
    """测试 BatchDeleteRequest 模型"""
    from controllers.admin_batch_controller import BatchDeleteRequest

    user_ids = [uuid.uuid4(), uuid.uuid4()]
    request = BatchDeleteRequest(user_ids=user_ids)
    assert len(request.user_ids) == 2
    assert request.user_ids[0] == user_ids[0]


def test_batch_suspend_request_model():
    """测试 BatchSuspendRequest 模型"""
    from controllers.admin_batch_controller import BatchSuspendRequest

    user_ids = [uuid.uuid4(), uuid.uuid4()]
    request = BatchSuspendRequest(user_ids=user_ids, duration_days=7)
    assert len(request.user_ids) == 2
    assert request.duration_days == 7


def test_batch_message_delete_request_model():
    """测试 BatchMessageDeleteRequest 模型"""
    from controllers.admin_batch_controller import BatchMessageDeleteRequest

    message_ids = [1, 2, 3]
    request = BatchMessageDeleteRequest(message_ids=message_ids)
    assert len(request.message_ids) == 3


def test_batch_operation_response_model():
    """测试 BatchOperationResponse 模型"""
    from controllers.admin_batch_controller import BatchOperationResponse

    response = BatchOperationResponse(deleted_count=5)
    assert response.deleted_count == 5

    response2 = BatchOperationResponse(suspended_count=3)
    assert response2.suspended_count == 3


def test_export_request_model():
    """测试 ExportRequest 模型"""
    from controllers.admin_export_controller import ExportRequest

    request = ExportRequest(format="csv", limit=5000)
    assert request.format == "csv"
    assert request.limit == 5000


def test_controller_imports():
    """测试控制器模块导入"""
    from controllers import admin_batch_controller, admin_export_controller

    assert hasattr(admin_batch_controller, 'router')
    assert hasattr(admin_export_controller, 'router')
    assert hasattr(admin_batch_controller, 'batch_delete_users')
    assert hasattr(admin_batch_controller, 'batch_suspend_users')
    assert hasattr(admin_batch_controller, 'batch_delete_messages')
    assert hasattr(admin_export_controller, 'export_users')
    assert hasattr(admin_export_controller, 'export_messages')
    assert hasattr(admin_export_controller, 'export_reports')


def test_user_model_suspended_until_field():
    """测试 User 模型是否包含 suspended_until 字段"""
    from models.user import User

    # 检查列定义
    assert hasattr(User, 'suspended_until')

    # 检查列属性
    from sqlalchemy import inspect
    mapper = inspect(User)
    column_names = [c.name for c in mapper.columns]
    assert 'suspended_until' in column_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
