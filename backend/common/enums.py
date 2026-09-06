# backend/common/enums.py
"""枚举类型（规划中，暂缓全量替换；当前业务用字符串常量，见 constants.py）。

【计划内容】
- Gender(str, Enum):       MALE = "male", FEMALE = "female"
- SenderType(str, Enum):   USER = "user", AI = "ai"
- MemoryType(str, Enum):   USER_PROFILE / LONG_TERM / EMOTIONAL_STATE
- RiskLevel(str, Enum):    NORMAL / WARNING / HIGH
- WSEventType(str, Enum):  MESSAGE / MOMENT / NOTIFICATION / STREAM_CHUNK / STREAM_END

【说明】等需要强类型约束时再启用；当前为占位。
"""
