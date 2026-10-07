#!/bin/bash
# MiniMax Agent 每日签到运行入口
# 流程：直连优先 → 失败则 Playwright 无头浏览器兜底
# 用法: ./run_checkin.sh
cd "$(dirname "$0")"

echo "=========================================="
echo "  MiniMax Agent 每日签到"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 第 1 步：直连签到（status 查询 + claim 领取）
echo ">>> [1/2] 直连签到..."
python3 signin_direct.py
DIRECT_EXIT=$?

echo ""
if [ $DIRECT_EXIT -eq 0 ]; then
    echo "✅ 直连签到成功"
    echo "RESULT|直连签到成功"
    echo ""
    echo "=========================================="
    echo "  签到流程结束"
    echo "=========================================="
    exit 0
fi

# 直连失败，进入第 2 步
echo ">>> 直连失败(exit=$DIRECT_EXIT)，切换 Playwright 浏览器兜底..."
echo ""

# 第 2 步：Playwright 无头浏览器签到
echo ">>> [2/2] Playwright 浏览器签到..."
python3 signin_playwright.py
PW_EXIT=$?

echo ""
if [ $PW_EXIT -eq 0 ]; then
    echo "✅ Playwright 浏览器签到成功"
    echo "RESULT|浏览器兜底签到成功"
else
    echo "❌ Playwright 浏览器签到失败(exit=$PW_EXIT)"
    echo "RESULT|签到失败"
fi

echo ""
echo "=========================================="
echo "  签到流程结束"
echo "=========================================="
exit $PW_EXIT
