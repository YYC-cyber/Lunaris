# ws 包：实时通信层
#
# 【职责】
# - connection_manager.py  连接注册表 + 推送 + 心跳 + 离线补发
# - streamer.py            流式聊天逐块转发
#
# 【说明】被 services/notify_service 调用；
#         也保存核心单例 ConnectionManager（main.py 生命周期初始化）

# backend/ws/__init__.py
from .connection_manager import ConnectionManager, get_connection_manager
from .streamer import Streamer

__all__ = ["ConnectionManager", "get_connection_manager", "Streamer"]