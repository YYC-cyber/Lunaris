"""
日志配置模块 —— 统一的日志管理（包括文件、控制台、结构化日志）

【特性】
- 文件日志：backend/logs/{日期}.log（按天滚动）
- 控制台日志：彩色输出便于调试
- 结构化日志：JSON 格式便于日志系统解析
- 请求追踪：每个请求配置 request_id
- 性能监控：记录响应耗时
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import json
import sys

from config.settings import get_settings

settings = get_settings()

# 创建 logs 目录
LOG_DIR = settings.BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件路径
LOG_FILE = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
ERROR_LOG_FILE = LOG_DIR / f"error-{datetime.now().strftime('%Y-%m-%d')}.log"
ACCESS_LOG_FILE = LOG_DIR / f"access-{datetime.now().strftime('%Y-%m-%d')}.log"


class JSONFormatter(logging.Formatter):
    """将日志转换为 JSON 格式（便于日志系统解析）"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台输出"""

    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.name = f"{color}{record.name}{self.RESET}"
        return super().format(record)


def setup_logging():
    """初始化日志系统"""

    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 移除已有的处理器（避免重复）
    root_logger.handlers.clear()

    # ============ 1. 控制台处理器（彩色输出） ============
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ============ 2. 文件处理器 - 通用日志（按天滚动） ============
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=7,  # 保留 7 天的日志
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # ============ 3. 文件处理器 - 错误日志 ============
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = JSONFormatter()
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)

    # ============ 4. 针对特定模块的日志 ============
    # 数据库日志（降噪）
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # HTTP 日志（降噪）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    # uvicorn 访问日志
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.setLevel(logging.INFO)
    access_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "access.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    access_formatter = JSONFormatter()
    access_handler.setFormatter(access_formatter)
    uvicorn_logger.addHandler(access_handler)

    # 应用日志
    app_logger = logging.getLogger("lunaris")
    app_logger.setLevel(logging.DEBUG)

    root_logger.info(f"✅ 日志系统初始化成功，日志文件位置: {LOG_DIR}")
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(f"lunaris.{name}")
