# backend/middleware/rate_limit.py
"""限流中间件 —— 内存滑动窗口，防滥用/防攻击（不限制正常用户）。

- 按「路径前缀」匹配规则：登录/注册按 IP，聊天/上传按用户
- 正常用户远低于阈值，无感知；拦的是脚本刷接口/暴力破解
"""
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# (路径前缀, 每分钟次数, 范围: ip=按IP / user=按用户)
RULES = [
    ("/api/auth/login", 10, "ip"),
    ("/api/auth/register", 5, "ip"),
    ("/v1/chat/completions", 60, "user"),
    ("/api/voice/transcribe", 30, "user"),
    ("/api/voice/synthesize", 30, "user"),
]

_WINDOW = 60  # 窗口秒数
_buckets: dict = defaultdict(list)  # key → [最近请求时间戳]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":  # CORS 预检放行
            return await call_next(request)

        path = request.url.path
        for prefix, limit, scope in RULES:
            if not path.startswith(prefix):
                continue

            if scope == "user":
                uid = getattr(request.state, "user_id", None)
                key = f"user:{uid}" if uid else f"ip:{request.client.host}"
            else:
                key = f"ip:{request.client.host}"

            now = time.time()
            # 滑动窗口：只保留最近 60s
            recent = [t for t in _buckets[key] if now - t < _WINDOW]
            if len(recent) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": "请求过于频繁，请稍后再试",
                        "data": None,
                        "timestamp": int(now),
                    },
                )
            recent.append(now)
            _buckets[key] = recent
            break

        return await call_next(request)
