# backend/clients/whisper_client.py
"""Whisper 语音转文字 —— 本地 whisper.cpp（免 API key）。

【原理】
- 调用打包的 whisper.cpp 二进制（subprocess），CPU 本地转写
- 无需任何 API key（BYOK 差异化：语音开箱即用）
- 多平台/多版本兼容：按系统+架构选二进制；兼容新版 whisper-cli / 旧版 main

【目录结构】（由 scripts/setup_whisper.py 下载生成）
backend/data/whisper/
├── bin/
│   ├── darwin-arm64/whisper-cli
│   ├── darwin-x86_64/whisper-cli
│   ├── win32-x86_64/whisper-cli.exe
│   └── linux-x86_64/whisper-cli
└── models/ggml-base.bin

【用法】
    client = WhisperClient()
    text = await client.transcribe(audio_bytes)   # 音频需为 whisper.cpp 可识别格式（wav/mp3/flac）
"""
import asyncio
import mimetypes
import platform
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

from config.settings import get_settings

settings = get_settings()

# whisper.cpp 数据目录（backend/data/whisper）
_WHISPER_DIR = Path(__file__).resolve().parent.parent / "data" / "whisper"

# 平台 → 目录名映射
_ARCH_MAP = {
    "x86_64": "x86_64", "amd64": "x86_64", "i386": "x86_64",
    "arm64": "arm64", "aarch64": "arm64",
}


def _platform_key() -> str:
    """返回平台键：darwin-arm64 / darwin-x86_64 / win32-x86_64 / linux-x86_64。"""
    machine = _ARCH_MAP.get(platform.machine().lower(), "x86_64")
    return f"{sys.platform}-{machine}"


def _binary_path() -> Optional[Path]:
    """定位 whisper.cpp 二进制。

    顺序：
    1. 项目内置（backend/data/whisper/bin/<平台>/whisper-cli）——打包分发用
    2. PATH 上的 whisper-cli（brew 等）——开发环境用
    兼容旧版 main / 新版 whisper-cli。
    """
    bin_dir = _WHISPER_DIR / "bin" / _platform_key()
    exe = "whisper-cli.exe" if sys.platform.startswith("win") else "whisper-cli"
    for name in (exe, "main", "main.exe"):
        p = bin_dir / name
        if p.exists():
            return p
    found = shutil.which(exe) or shutil.which("whisper-cli")
    return Path(found) if found else None


def _clean_output(raw: str) -> str:
    """清理输出：去时间戳和 Whisper 常见的停顿幻觉。"""
    lines = []
    for line in raw.splitlines():
        # 形如 [00:00:00.000 --> 00:00:01.500] 文本
        line = re.sub(r"\[[\d:.]+(?:\s+-->\s+[\d:.]+)?\]\s*", "", line).strip()
        line = re.sub(
            r"\b(?:break|wait)\s+time\s+is\s+(?:about\s+)?[\d.]+\s+"
            r"(?:ms|s|sec|secs|second|seconds)\b[.!?]?",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        line = re.sub(
            r"(?<![A-Za-z])(?:wait(?:time)?|break(?:time)?|time)\s*[:=]\s*[\d.]+\s*"
            r"(?:ms|s|sec|secs|second|seconds)?(?![A-Za-z])",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            lines.append(line)
    return "\n".join(dict.fromkeys(lines))


class WhisperClient:
    """本地 whisper.cpp 转写客户端。"""

    def __init__(self, model_path: Optional[str] = None, timeout: Optional[int] = None):
        self.model_path = model_path or settings.WHISPER_MODEL_PATH or str(
            _WHISPER_DIR / "models" / "ggml-base.bin"
        )
        self.timeout = timeout or settings.WHISPER_TIMEOUT

    def _build_command(self, audio_path: Path) -> list:
        binary = _binary_path()
        if binary is None:
            raise RuntimeError("未找到本地 whisper.cpp 二进制，请先运行 scripts/setup_whisper.py")
        if not Path(self.model_path).exists():
            raise RuntimeError(
                f"未找到 whisper 模型：{self.model_path}，请先运行 scripts/setup_whisper.py"
            )
        # 固定中文识别，关闭回退和非语音 token，降低英文/停顿幻觉。
        return [
            str(binary), "-m", self.model_path, "-f", str(audio_path),
            "-l", "zh", "-nt", "-nf", "-sns", "-tp", "0",
            "--prompt", "这是一段中文普通话语音，请使用简体中文转写：",
        ]

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """转写音频字节（本地 CPU，免 key）。"""
        # 写临时音频文件
        tmp_dir = _WHISPER_DIR / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename or "").suffix.lower()
        if not suffix:
            suffix = mimetypes.guess_extension(content_type or "") or ".wav"
        if suffix == ".oga":
            suffix = ".ogg"
        if suffix not in {".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a"}:
            raise RuntimeError(
                f"不支持的音频格式（{content_type or suffix}）。请使用 OGG、WAV、MP3 或 FLAC。"
            )
        audio_path = tmp_dir / f"voice_{uuid.uuid4().hex[:8]}{suffix}"
        audio_path.write_bytes(audio_bytes)

        cmd = self._build_command(audio_path)
        try:
            # CPU 转写是阻塞的，放到线程池避免卡事件循环
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=self.timeout
            )
        finally:
            audio_path.unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(f"whisper.cpp 转写失败: {result.stderr[:300]}")

        text = _clean_output(result.stdout)
        if not text:
            raise RuntimeError("whisper.cpp 未识别到内容")
        return text

    def check_ready(self) -> tuple:
        """返回 (二进制是否就绪, 模型是否就绪)，供接口诊断。"""
        return _binary_path() is not None, Path(self.model_path).exists()
