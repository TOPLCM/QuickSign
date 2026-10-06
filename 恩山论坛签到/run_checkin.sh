#!/bin/bash
# 恩山无线论坛每日签到运行入口
# 流程：直连优先 → 失败则浏览器兜底
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  恩山无线论坛 每日签到"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 直连签到
echo ">>> 直连签到..."
python3 signin_direct.py
DIRECT_EXIT=$?

echo ""
if [ $DIRECT_EXIT -eq 0 ]; then
    echo "✅ 直连签到成功"
    echo "RESULT|直连签到成功"
else
    echo "❌ 直连签到失败(exit=$DIRECT_EXIT)，切换浏览器兜底..."
    echo "RESULT|NEED_BROWSER_FALLBACK"
fi

echo ""
echo "=========================================="
echo "  签到流程结束"
echo "=========================================="
