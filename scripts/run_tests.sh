#!/bin/bash
# Lunaris 快速测试启动脚本

set -e

echo "🧪 Lunaris 测试启动助手"
echo "=========================="
echo ""

# 配置
BACKEND_DIR="/Users/yyc/PycharmProjects/Lunaris/backend"
REPO_ROOT="/Users/yyc/PycharmProjects/Lunaris"

# 1. 检查后端是否运行
echo "1️⃣ 检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端已在运行 (http://localhost:8000)"
else
    echo "❌ 后端未运行，需要启动"
    echo ""
    echo "请在新的终端运行："
    echo "  cd $BACKEND_DIR"
    echo "  python -m uvicorn main:app --reload"
    echo ""
    exit 1
fi

# 2. 检查前端是否运行
echo ""
echo "2️⃣ 检查前端服务..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ 前端已在运行 (http://localhost:5173)"
else
    echo "⚠️  前端未运行，不影响 API 测试，但无法进行前端测试"
fi

# 3. 检查日志系统
echo ""
echo "3️⃣ 检查日志系统..."
if [ -d "$BACKEND_DIR/logs" ]; then
    log_count=$(find "$BACKEND_DIR/logs" -name "*.log" | wc -l)
    if [ $log_count -gt 0 ]; then
        echo "✅ 日志文件存在（找到 $log_count 个日志文件）"
        latest_log=$(find "$BACKEND_DIR/logs" -name "*.log" -type f | head -1)
        echo "   最新日志文件：$latest_log"
        echo "   日志内容预览："
        tail -n 3 "$latest_log" | sed 's/^/   /'
    else
        echo "❌ logs 目录存在但为空"
    fi
else
    echo "❌ logs 目录不存在"
fi

# 4. 检查数据库
echo ""
echo "4️⃣ 检查数据库..."
if psql -U lunaris -d lunaris_db -h localhost -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ 数据库连接成功"

    # 统计表情包
    sticker_count=$(psql -U lunaris -d lunaris_db -h localhost -t -c "SELECT COUNT(*) FROM stickers;" 2>/dev/null || echo "0")
    echo "   表情包数量：$sticker_count 个"

    # 统计用户
    user_count=$(psql -U lunaris -d lunaris_db -h localhost -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    echo "   用户数量：$user_count 个"
else
    echo "❌ 数据库连接失败"
    echo "   请确保 PostgreSQL 正在运行："
    echo "   brew services start postgresql"
fi

# 5. 运行自动化测试
echo ""
echo "5️⃣ 运行自动化 API 测试..."
echo ""
cd "$REPO_ROOT"
python scripts/test_suite.py

# 6. 显示测试报告位置
echo ""
echo "📊 测试报告已生成："
if [ -f "$REPO_ROOT/.docs/TEST_REPORT.md" ]; then
    echo "   ✅ $REPO_ROOT/.docs/TEST_REPORT.md"
    echo ""
    echo "   查看报告："
    echo "   cat $REPO_ROOT/.docs/TEST_REPORT.md"
fi

echo ""
echo "================================"
echo "✅ 测试检查完成！"
echo "================================"
echo ""
echo "📝 下一步："
echo "1. 检查 API 测试结果是否都通过"
echo "2. 手动测试前端功能（见 TESTING_GUIDE.md）"
echo "3. 查看完整测试报告"
echo ""
