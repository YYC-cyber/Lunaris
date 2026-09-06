"""
CORS 中间件 —— 框架占位，按注释实现。

【内容】
- CORSMiddleware(app, allow_origins=settings.CORS_ORIGINS.split(","),
                allow_methods=["*"], allow_headers=["*"],
                allow_credentials=True)
- 来源：Electron file://（生产）与 Vite dev 端口（开发）
  如 http://localhost:5173

【说明】WebSocket 不受 CORS 限制，但 REST 接口必须配置
"""
