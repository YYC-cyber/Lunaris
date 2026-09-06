# scripts/setup_whisper.py
"""安装本地 whisper.cpp（免 key）到 backend/data/whisper/。

【多平台策略】
- Windows x64：下载 release 预编译 whisper-bin-x64.zip（自包含，可打包进项目）
- Linux x64：下载 release 预编译 whisper-bin-ubuntu-x64.tar.gz
- macOS：用 Homebrew 安装（brew install whisper-cpp），客户端通过 PATH 找到
  —— brew 的 whisper-cli 是动态链接的，不要复制进项目（会缺 libwhisper），
     打包分发时需改用静态编译的二进制
- 模型：优先 hf-mirror.com（国内可达），回退 huggingface.co / ggml.ggerganov.com

【用法】python scripts/setup_whisper.py
"""
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# backend/data/whisper
BACKEND_DATA = Path(__file__).resolve().parent.parent / "backend" / "data" / "whisper"

GITHUB_API = "https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest"
MODEL_NAME = "ggml-base.bin"
MODEL_SOURCES = [
    "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
]


def _arch():
    return "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"


def _platform_key():
    return f"{sys.platform}-{_arch()}"


def _curl(url, dest: Path):
    print(f"⬇️  {url}")
    subprocess.run(["curl", "-sSL", "-o", str(dest), url], check=True)
    print(f"   → {dest.name} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def _latest_assets() -> dict:
    result = subprocess.run(["curl", "-sSL", GITHUB_API], capture_output=True, text=True)
    data = json.loads(result.stdout)
    print(f"📦 whisper.cpp release: {data.get('tag_name')}")
    return {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}


def _install_binary():
    if sys.platform == "darwin":
        # macOS：用 Homebrew（客户端通过 which 找到；动态链接不能复制进项目）
        print("🍎 macOS：用 Homebrew 安装 whisper-cpp")
        if not shutil.which("whisper-cli"):
            subprocess.run(["brew", "install", "whisper-cpp"], check=True)
        print(f"✅ whisper-cli: {shutil.which('whisper-cli')}")
        return

    bin_dir = BACKEND_DATA / "bin" / _platform_key()
    bin_dir.mkdir(parents=True, exist_ok=True)
    bin_name = "whisper-cli.exe" if sys.platform.startswith("win") else "whisper-cli"
    bin_path = bin_dir / bin_name
    if bin_path.exists():
        print(f"✅ 二进制已存在: {bin_path}")
        return

    assets = _latest_assets()
    if sys.platform.startswith("win"):
        zip_name = "whisper-bin-x64.zip"
        if zip_name not in assets:
            print("❌ 没找到 Windows 预编译包")
            sys.exit(1)
        zp = BACKEND_DATA / zip_name
        _curl(assets[zip_name], zp)
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(bin_dir)
        zp.unlink()
        _move_to(bin_dir, bin_name)
    elif sys.platform.startswith("linux"):
        tar_name = "whisper-bin-ubuntu-x64.tar.gz"
        if tar_name not in assets:
            print("❌ 没找到 Linux 预编译包")
            sys.exit(1)
        tp = BACKEND_DATA / tar_name
        _curl(assets[tar_name], tp)
        with tarfile.open(tp, "r:gz") as tf:
            tf.extractall(bin_dir)
        tp.unlink()
        _move_to(bin_dir, bin_name)
    else:
        print(f"❌ 暂不支持平台: {sys.platform} {_arch()}")
        sys.exit(1)
    print(f"✅ 二进制: {bin_path}")


def _move_to(bin_dir: Path, bin_name: str):
    target = bin_dir / bin_name
    for f in bin_dir.rglob(bin_name):
        if f != target:
            f.replace(target)
    target.chmod(0o755)


def _install_model():
    models_dir = BACKEND_DATA / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / MODEL_NAME
    if model_path.exists():
        print(f"✅ 模型已存在: {model_path}")
        return
    for url in MODEL_SOURCES:
        try:
            _curl(url, model_path)
            if model_path.stat().st_size > 10_000_000:  # 至少 10MB 才算成功
                print(f"✅ 模型: {model_path}")
                return
            model_path.unlink()
        except Exception as e:
            print(f"⚠️ 下载失败，换源: {e}")
            model_path.unlink(missing_ok=True)
    print("❌ 所有源都失败，请手动下载模型放入 backend/data/whisper/models/")


def main():
    _install_binary()
    _install_model()
    print("\n🎉 就绪！验证：")
    print("  python -c \"from clients.whisper_client import WhisperClient; print(WhisperClient().check_ready())\"")


if __name__ == "__main__":
    main()
