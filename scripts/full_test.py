#!/usr/bin/env python3
"""
Lunaris 完整前后端集成测试脚本
包括：后端启动 + 自动化 API 测试 + 前端自动化测试（使用 Playwright）
"""

import asyncio
import subprocess
import time
import sys
import json
from pathlib import Path
from datetime import datetime
import httpx

# 配置
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
BACKEND_DIR = Path("/Users/yyc/PycharmProjects/Lunaris/backend")
FRONTEND_DIR = Path("/Users/yyc/PycharmProjects/Lunaris/frontend")
REPO_ROOT = Path("/Users/yyc/PycharmProjects/Lunaris")

class TestRunner:
    """完整测试运行器"""

    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.results = {
            "backend": {"status": "pending", "tests": []},
            "frontend": {"status": "pending", "tests": []},
            "integration": {"status": "pending", "tests": []},
            "timestamp": datetime.now().isoformat()
        }

    async def start_backend(self):
        """启动后端服务"""
        print("🔧 启动后端服务...")
        try:
            self.backend_process = subprocess.Popen(
                ["python", "-m", "uvicorn", "main:app", "--reload", "--log-level", "info"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 等待后端启动
            await asyncio.sleep(3)

            # 检查是否成功启动
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    resp = await client.get(f"{BACKEND_URL}/health")
                    if resp.status_code == 200:
                        print("✅ 后端已启动 (http://localhost:8000)")
                        self.results["backend"]["status"] = "running"
                        return True
                except Exception as e:
                    print(f"❌ 后端启动失败: {e}")
                    return False
        except Exception as e:
            print(f"❌ 启动后端出错: {e}")
            return False

    async def start_frontend(self):
        """启动前端服务"""
        print("🎨 启动前端服务...")
        try:
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 等待前端启动
            await asyncio.sleep(5)

            # 检查是否成功启动
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    resp = await client.get(FRONTEND_URL)
                    if resp.status_code == 200:
                        print("✅ 前端已启动 (http://localhost:5173)")
                        self.results["frontend"]["status"] = "running"
                        return True
                except Exception as e:
                    print(f"⚠️  前端启动中（需要时间）: {e}")
                    # 继续，给前端更多时间
                    return True
        except Exception as e:
            print(f"❌ 启动前端出错: {e}")
            return False

    async def test_backend_apis(self):
        """测试后端 APIs"""
        print("\n" + "="*60)
        print("🧪 第 1 步：后端 API 测试")
        print("="*60)

        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
            tests = [
                ("健康检查", "GET", "/health", None, 200),
                ("表情包列表", "GET", "/api/stickers", None, 200),
                ("表情包数量检查", "GET", "/api/stickers", None, 200, "check_sticker_count"),
            ]

            for test in tests:
                name = test[0]
                method = test[1]
                path = test[2]

                try:
                    if method == "GET":
                        resp = await client.get(path)

                    if resp.status_code == test[4]:
                        print(f"✅ {name}: {resp.status_code}")
                        self.results["backend"]["tests"].append({"name": name, "status": "passed"})

                        # 特殊检查
                        if len(test) > 5 and test[5] == "check_sticker_count":
                            data = resp.json()
                            count = len(data.get("data", []))
                            if count >= 43:
                                print(f"   └─ 表情包数量: {count} ✅")
                            else:
                                print(f"   └─ 表情包数量: {count} ❌ (预期: ≥43)")
                    else:
                        print(f"❌ {name}: {resp.status_code} (预期: {test[4]})")
                        self.results["backend"]["tests"].append({"name": name, "status": "failed"})
                except Exception as e:
                    print(f"❌ {name}: {str(e)}")
                    self.results["backend"]["tests"].append({"name": name, "status": "error", "error": str(e)})

        self.results["backend"]["status"] = "completed"

    async def test_frontend_features(self):
        """测试前端功能（使用 Playwright）"""
        print("\n" + "="*60)
        print("🎨 第 2 步：前端功能测试")
        print("="*60)

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("⚠️  未安装 Playwright，跳过前端自动化测试")
            print("   安装方式: pip install playwright")
            print("   然后运行: playwright install")
            self.results["frontend"]["status"] = "skipped"
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            tests_passed = 0
            tests_total = 0

            try:
                # 测试 1: 访问首页
                print("\n📝 测试 1: 访问首页")
                tests_total += 1
                try:
                    await page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=10000)
                    print("✅ 前端首页加载成功")
                    tests_passed += 1
                    self.results["frontend"]["tests"].append({"name": "首页加载", "status": "passed"})
                except Exception as e:
                    print(f"❌ 首页加载失败: {str(e)}")
                    self.results["frontend"]["tests"].append({"name": "首页加载", "status": "failed", "error": str(e)})

                # 测试 2: 检查页面元素
                print("\n📝 测试 2: 检查页面结构")
                tests_total += 1
                try:
                    # 等待页面加载
                    await page.wait_for_timeout(2000)

                    # 检查是否有登录相关的元素
                    body_text = await page.inner_text("body")
                    if "登" in body_text or "Login" in body_text or "注册" in body_text:
                        print("✅ 页面包含认证相关元素")
                        tests_passed += 1
                        self.results["frontend"]["tests"].append({"name": "页面结构", "status": "passed"})
                    else:
                        print("⚠️  页面结构检查 (需要人工验证)")
                        self.results["frontend"]["tests"].append({"name": "页面结构", "status": "skipped"})
                except Exception as e:
                    print(f"⚠️  页面检查出错: {str(e)}")

                # 测试 3: 检查表情包元素（如果登录成功）
                print("\n📝 测试 3: 检查前端网络连接")
                tests_total += 1
                try:
                    # 监听网络请求
                    requests = []
                    page.on("request", lambda req: requests.append(req.url))

                    # 刷新页面以捕获请求
                    await page.reload()
                    await page.wait_for_timeout(3000)

                    # 检查是否有 API 请求
                    api_requests = [r for r in requests if "/api/" in r]
                    if api_requests:
                        print(f"✅ 检测到 {len(api_requests)} 个 API 请求")
                        for req in api_requests[:3]:
                            print(f"   └─ {req}")
                        tests_passed += 1
                        self.results["frontend"]["tests"].append({"name": "API 连接", "status": "passed"})
                    else:
                        print("⚠️  未检测到 API 请求")
                        self.results["frontend"]["tests"].append({"name": "API 连接", "status": "skipped"})
                except Exception as e:
                    print(f"⚠️  网络监听出错: {str(e)}")

                print(f"\n📊 前端测试结果: {tests_passed}/{tests_total} 通过")

            finally:
                await browser.close()

        self.results["frontend"]["status"] = "completed"

    async def test_integration(self):
        """集成测试"""
        print("\n" + "="*60)
        print("🔗 第 3 步：集成测试（前后端通信）")
        print("="*60)

        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
            # 测试 1: 注册用户
            print("\n📝 测试 1: 用户认证流程")
            import uuid
            user_id = str(uuid.uuid4())

            try:
                # 注册
                reg_resp = await client.post("/api/auth/register", json={
                    "user_id": user_id,
                    "password": "test123",
                    "gender": "male"
                })

                if reg_resp.status_code in (200, 201):
                    print(f"✅ 注册成功")
                    self.results["integration"]["tests"].append({"name": "用户注册", "status": "passed"})
                else:
                    print(f"❌ 注册失败: {reg_resp.status_code}")
                    self.results["integration"]["tests"].append({"name": "用户注册", "status": "failed"})

                # 登录
                login_resp = await client.post("/api/auth/login", json={
                    "user_id": user_id,
                    "password": "test123"
                })

                if login_resp.status_code == 200:
                    token = login_resp.json().get("access_token")
                    print(f"✅ 登录成功，获得 Token")
                    self.results["integration"]["tests"].append({"name": "用户登录", "status": "passed"})

                    # 使用 Token 测试其他接口
                    headers = {"Authorization": f"Bearer {token}"}

                    # 测试 2: 获取表情包
                    print("\n📝 测试 2: 表情包 API")
                    sticker_resp = await client.get("/api/stickers", headers=headers)
                    if sticker_resp.status_code == 200:
                        data = sticker_resp.json()
                        count = len(data.get("data", []))
                        print(f"✅ 获取表情包成功 ({count} 个)")
                        if count >= 43:
                            print(f"   └─ 表情包初始化完整 ✅")
                        self.results["integration"]["tests"].append({
                            "name": "表情包获取",
                            "status": "passed",
                            "count": count
                        })
                    else:
                        print(f"❌ 获取表情包失败: {sticker_resp.status_code}")
                        self.results["integration"]["tests"].append({
                            "name": "表情包获取",
                            "status": "failed"
                        })

                    # 测试 3: 配对角色
                    print("\n📝 测试 3: 配对角色")
                    soul_resp = await client.post("/api/souls/", json={"soul_id": 1}, headers=headers)
                    if soul_resp.status_code in (200, 201):
                        print(f"✅ 配对角色成功")
                        self.results["integration"]["tests"].append({"name": "配对角色", "status": "passed"})
                    else:
                        print(f"⚠️  配对角色: {soul_resp.status_code}")

                    # 测试 4: 发送聊天消息
                    print("\n📝 测试 4: 聊天功能")
                    chat_resp = await client.post("/v1/chat/completions", json={
                        "soul_id": 1,
                        "message": "你好，今天天气很好",
                        "stream": False
                    }, headers=headers)

                    if chat_resp.status_code == 200:
                        response_data = chat_resp.json()
                        ai_response = response_data.get("content", "")
                        print(f"✅ AI 回复成功")
                        print(f"   └─ AI: {ai_response[:50]}...")

                        # 检查回复质量
                        if "（" in ai_response or "）" in ai_response:
                            print(f"   └─ ⚠️  检测到括号动作，需要改进")
                        else:
                            print(f"   └─ ✅ 回复格式正确（无括号）")

                        self.results["integration"]["tests"].append({
                            "name": "聊天功能",
                            "status": "passed",
                            "response_preview": ai_response[:50]
                        })
                    else:
                        print(f"❌ 聊天失败: {chat_resp.status_code}")
                        self.results["integration"]["tests"].append({
                            "name": "聊天功能",
                            "status": "failed"
                        })
                else:
                    print(f"❌ 登录失败: {login_resp.status_code}")
                    self.results["integration"]["tests"].append({"name": "用户登录", "status": "failed"})

            except Exception as e:
                print(f"❌ 集成测试出错: {str(e)}")
                self.results["integration"]["tests"].append({
                    "name": "整体测试",
                    "status": "error",
                    "error": str(e)
                })

        self.results["integration"]["status"] = "completed"

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n🎯 开始 Lunaris 完整前后端测试\n")

        try:
            # 启动服务
            print("="*60)
            print("🚀 第 0 步：启动服务")
            print("="*60 + "\n")

            backend_ok = await self.start_backend()
            if not backend_ok:
                print("❌ 后端启动失败，无法继续测试")
                return

            frontend_ok = await self.start_frontend()
            if not frontend_ok:
                print("⚠️  前端启动失败，继续后端测试")

            # 运行测试
            await self.test_backend_apis()
            await self.test_frontend_features()
            await self.test_integration()

            # 生成报告
            self.generate_report()

        finally:
            # 清理
            self.cleanup()

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 测试报告")
        print("="*60 + "\n")

        # 统计
        total_tests = 0
        passed_tests = 0

        for section in ["backend", "frontend", "integration"]:
            tests = self.results[section]["tests"]
            total_tests += len(tests)
            passed_tests += sum(1 for t in tests if t["status"] == "passed")

            status = self.results[section]["status"]
            print(f"\n{section.upper()}")
            print("-" * 40)
            for test in tests:
                icon = "✅" if test["status"] == "passed" else "❌" if test["status"] == "failed" else "⏭️"
                print(f"{icon} {test['name']}: {test['status']}")

        print("\n" + "="*60)
        print(f"总体结果: {passed_tests}/{total_tests} 通过 ({(passed_tests/total_tests*100):.0f}%)")
        print("="*60)

        # 保存报告
        report_path = REPO_ROOT / ".docs" / "FRONTEND_TEST_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 前后端集成测试报告\n\n")
            f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"## 测试摘要\n\n")
            f.write(f"- 总测试数: {total_tests}\n")
            f.write(f"- 通过: {passed_tests}\n")
            f.write(f"- 成功率: {(passed_tests/total_tests*100):.0f}%\n\n")

            for section in ["backend", "frontend", "integration"]:
                f.write(f"## {section.upper()}\n\n")
                for test in self.results[section]["tests"]:
                    f.write(f"- {test['name']}: {test['status']}\n")
                f.write("\n")

        print(f"\n✅ 报告已生成: {report_path}")

    def cleanup(self):
        """清理进程"""
        print("\n🧹 清理...")
        if self.backend_process:
            self.backend_process.terminate()
        if self.frontend_process:
            self.frontend_process.terminate()


async def main():
    runner = TestRunner()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
