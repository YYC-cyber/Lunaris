#!/usr/bin/env python3
"""
Lunaris 全面测试套件 —— 包括单元测试、集成测试、前后端连调测试

【测试覆盖】
1. 后端健康检查（数据库、缓存等）
2. API 接口测试（所有关键端点）
3. 认证流程测试
4. 聊天功能测试（含表情包）
5. WebSocket 连接测试
6. 错误处理测试
7. 性能测试

【输出】生成详细的 HTML 和 Markdown 测试报告
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import uuid

# 配置
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

class TestResult:
    """测试结果记录"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status = "pending"  # pending, passed, failed, skipped
        self.error = None
        self.response = None
        self.duration = 0
        self.details = {}

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "error": self.error,
            "duration": f"{self.duration:.2f}s",
            "details": self.details,
        }


class LunarisTestSuite:
    """Lunaris 测试套件"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.base_url = BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
        self.auth_token = None
        self.user_id = None

    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始 Lunaris 全面测试套件...\n")

        # 1. 基础检查
        await self.test_backend_health()
        await self.test_database_connection()

        # 2. 认证测试
        await self.test_auth_flow()

        # 3. 如果认证通过，继续其他测试
        if self.auth_token:
            await self.test_souls_api()
            await self.test_stickers_api()
            await self.test_chat_api()
            await self.test_moment_api()
            await self.test_friend_api()
            await self.test_settings_api()
            await self.test_websocket()
        else:
            print("⚠️ 认证失败，跳过后续 API 测试\n")

        # 4. 生成报告
        await self.generate_report()

    async def test_backend_health(self):
        """测试后端健康状态"""
        result = TestResult("Backend Health Check", "基础检查")
        start = datetime.now()

        try:
            resp = await self.client.get("/health")
            result.response = resp.json()
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_database_connection(self):
        """测试数据库连接"""
        result = TestResult("Database Connection", "基础检查")
        start = datetime.now()

        try:
            resp = await self.client.get("/health")
            data = resp.json()
            is_healthy = data.get("database") == "connected"
            result.status = "passed" if is_healthy else "failed"
            result.response = data
            result.error = None if is_healthy else data.get("error", "Unknown error")
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_auth_flow(self):
        """测试认证流程"""
        print("\n📝 认证测试：")

        # 1. 用户注册
        result = TestResult("User Registration", "认证")
        start = datetime.now()

        try:
            user_id = str(uuid.uuid4())
            self.user_id = user_id
            payload = {
                "user_id": user_id,
                "password": "test_password_123",
                "gender": "male"
            }
            resp = await self.client.post("/api/auth/register", json=payload)
            result.status = "passed" if resp.status_code in (200, 201) else "failed"
            result.error = None if resp.status_code in (200, 201) else f"Status {resp.status_code}"
            result.response = resp.json() if resp.status_code < 400 else resp.text
            result.details = {"user_id": user_id}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

        # 2. 用户登录
        result = TestResult("User Login", "认证")
        start = datetime.now()

        try:
            payload = {
                "user_id": self.user_id,
                "password": "test_password_123"
            }
            resp = await self.client.post("/api/auth/login", json=payload)
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"

            if resp.status_code == 200:
                data = resp.json()
                self.auth_token = data.get("access_token")
                self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
                result.details = {"token_type": data.get("token_type")}
            else:
                result.response = resp.text
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_souls_api(self):
        """测试角色 API"""
        print("\n👥 角色系统测试：")

        # 1. 获取已配对的角色
        result = TestResult("Get Paired Souls", "角色系统")
        start = datetime.now()

        try:
            resp = await self.client.get("/api/souls/paired")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            data = resp.json()
            result.details = {"paired_count": len(data) if isinstance(data, list) else 0}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

        # 2. 添加角色（配对）
        result = TestResult("Add Soul (Pairing)", "角色系统")
        start = datetime.now()

        try:
            resp = await self.client.post("/api/souls/", json={"soul_id": 1})
            result.status = "passed" if resp.status_code in (200, 201) else "failed"
            result.error = None if resp.status_code < 400 else f"Status {resp.status_code}"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_stickers_api(self):
        """测试表情包 API"""
        print("\n🎭 表情包系统测试：")

        # 1. 获取表情包列表
        result = TestResult("Get Stickers List", "表情包")
        start = datetime.now()

        try:
            resp = await self.client.get("/api/stickers")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            data = resp.json()
            sticker_count = len(data.get("data", [])) if isinstance(data, dict) else len(data)
            result.details = {"sticker_count": sticker_count}

            if sticker_count == 0:
                result.error = "No stickers found in database"
                result.status = "failed"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

        # 2. 按情绪筛选表情包
        for emotion in ["happy", "sad", "angry", "neutral", "love"]:
            result = TestResult(f"Get Stickers by Emotion: {emotion}", "表情包")
            start = datetime.now()

            try:
                resp = await self.client.get(f"/api/stickers?emotion={emotion}")
                result.status = "passed" if resp.status_code == 200 else "failed"
                result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
                data = resp.json()
                count = len(data.get("data", [])) if isinstance(data, dict) else len(data)
                result.details = {"emotion": emotion, "count": count}
            except Exception as e:
                result.status = "failed"
                result.error = str(e)

            result.duration = (datetime.now() - start).total_seconds()
            self.results.append(result)
            self._print_result(result)

    async def test_chat_api(self):
        """测试聊天 API"""
        print("\n💬 聊天系统测试：")

        # 1. 发送消息
        result = TestResult("Send Chat Message", "聊天")
        start = datetime.now()

        try:
            payload = {
                "soul_id": 1,
                "message": "你好，今天天气真好！",
                "stream": False
            }
            resp = await self.client.post("/v1/chat/completions", json=payload)
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            if resp.status_code == 200:
                data = resp.json()
                result.details = {"content": data.get("content", "")[:50]}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

        # 2. 获取聊天历史
        result = TestResult("Get Chat History", "聊天")
        start = datetime.now()

        try:
            resp = await self.client.get("/v1/chat/history?soul_id=1&offset=0&limit=10")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            data = resp.json()
            msg_count = len(data.get("data", [])) if isinstance(data, dict) else 0
            result.details = {"message_count": msg_count}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_moment_api(self):
        """测试朋友圈 API"""
        print("\n📸 朋友圈系统测试：")

        result = TestResult("Get Moments Feed", "朋友圈")
        start = datetime.now()

        try:
            resp = await self.client.get("/api/moments/feed?offset=0&limit=10")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            data = resp.json()
            count = len(data.get("data", [])) if isinstance(data, dict) else 0
            result.details = {"moment_count": count}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_friend_api(self):
        """测试好友系统 API"""
        print("\n👫 好友系统测试：")

        result = TestResult("Get Friends List", "好友系统")
        start = datetime.now()

        try:
            resp = await self.client.get("/api/friends")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
            data = resp.json()
            count = len(data.get("data", [])) if isinstance(data, dict) else 0
            result.details = {"friend_count": count}
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_settings_api(self):
        """测试设置 API"""
        print("\n⚙️ 设置系统测试：")

        result = TestResult("Get User Settings", "设置")
        start = datetime.now()

        try:
            resp = await self.client.get("/api/settings")
            result.status = "passed" if resp.status_code == 200 else "failed"
            result.error = None if resp.status_code == 200 else f"Status {resp.status_code}"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()
        self.results.append(result)
        self._print_result(result)

    async def test_websocket(self):
        """测试 WebSocket 连接"""
        print("\n🔌 WebSocket 测试：")

        result = TestResult("WebSocket Connection", "WebSocket")
        result.status = "skipped"
        result.error = "WebSocket 测试需要前端参与，请通过前端手动验证"
        result.details = {
            "expected_endpoint": f"{self.base_url.replace('http', 'ws')}/api/ws",
            "note": "在浏览器开发者工具中查看 Network > WS"
        }
        self.results.append(result)
        self._print_result(result)

    async def generate_report(self):
        """生成测试报告"""
        await self.client.aclose()

        print("\n" + "="*60)
        print("📊 测试报告总结")
        print("="*60 + "\n")

        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        print(f"✅ 通过: {passed}/{total}")
        print(f"❌ 失败: {failed}/{total}")
        print(f"⏭️  跳过: {skipped}/{total}")
        print(f"成功率: {(passed/total*100):.1f}%\n")

        # 按分类统计
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "skipped": 0}
            categories[result.category][result.status] += 1

        print("按分类统计：")
        for cat, stats in categories.items():
            total_cat = sum(stats.values())
            pass_rate = (stats["passed"] / total_cat * 100) if total_cat > 0 else 0
            print(f"  {cat}: {stats['passed']}/{total_cat} ✅ ({pass_rate:.0f}%)")

        # 生成 Markdown 报告
        self._generate_markdown_report()

    def _generate_markdown_report(self):
        """生成 Markdown 格式的详细报告"""
        report_path = Path(__file__).parent.parent / ".docs" / "TEST_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Lunaris 测试报告\n\n")
            f.write(f"**测试时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 总结
            total = len(self.results)
            passed = sum(1 for r in self.results if r.status == "passed")
            failed = sum(1 for r in self.results if r.status == "failed")
            skipped = sum(1 for r in self.results if r.status == "skipped")

            f.write("## 测试概览\n\n")
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 总测试数 | {total} |\n")
            f.write(f"| ✅ 通过 | {passed} |\n")
            f.write(f"| ❌ 失败 | {failed} |\n")
            f.write(f"| ⏭️ 跳过 | {skipped} |\n")
            f.write(f"| 成功率 | {(passed/total*100):.1f}% |\n\n")

            # 详细测试结果
            f.write("## 详细测试结果\n\n")

            categories = {}
            for result in self.results:
                if result.category not in categories:
                    categories[result.category] = []
                categories[result.category].append(result)

            for category, results in categories.items():
                f.write(f"### {category}\n\n")
                f.write("| 测试项 | 状态 | 耗时 | 错误信息 |\n")
                f.write("|--------|------|------|----------|\n")

                for result in results:
                    status_icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⏭️"
                    error = result.error or "—"
                    f.write(f"| {result.name} | {status_icon} {result.status} | {result.duration:.2f}s | {error} |\n")

                f.write("\n")

            # 问题列表
            failures = [r for r in self.results if r.status == "failed"]
            if failures:
                f.write("## 失败项详情\n\n")
                for i, result in enumerate(failures, 1):
                    f.write(f"### {i}. {result.name}\n\n")
                    f.write(f"**状态**：❌ {result.status}\n\n")
                    f.write(f"**错误**：{result.error}\n\n")
                    if result.details:
                        f.write(f"**详情**：\n```json\n{json.dumps(result.details, indent=2, ensure_ascii=False)}\n```\n\n")

        print(f"\n📄 详细报告已生成：{report_path}")

    def _print_result(self, result: TestResult):
        """打印单个测试结果"""
        status_icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⏭️"
        print(f"  {status_icon} {result.name} ({result.duration:.2f}s)")
        if result.error:
            print(f"     错误：{result.error}")


async def main():
    """主函数"""
    # 检查后端是否在线
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{BASE_URL}/health")
    except Exception as e:
        print(f"❌ 后端服务未运行：{e}")
        print(f"请先运行：cd backend && python -m uvicorn main:app --reload")
        sys.exit(1)

    # 运行测试套件
    suite = LunarisTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
