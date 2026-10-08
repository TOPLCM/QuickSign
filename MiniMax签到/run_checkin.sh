#!/bin/bash
# MiniMax Agent 每日签到运行入口
# 方案：Playwright 无头浏览器（直连因签名算法未破解已移除）
# 用法: ./run_checkin.sh
cd "$(dirname "$0")"

echo "=========================================="
echo "  MiniMax Agent 每日签到"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

echo ">>> Playwright 无头浏览器签到..."
python3 signin_playwright.py
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 签到成功"
    echo "RESULT|签到成功"
else
    echo "❌ 签到失败(exit=$EXIT_CODE)"
    echo "RESULT|签到失败"
fi

echo ""
echo "=========================================="
echo "  签到流程结束"
echo "=========================================="
exit $EXIT_CODE
