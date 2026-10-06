#!/bin/bash
# MiniMax Agent 每日签到运行入口
# 流程：直连优先 → 失败则浏览器兜底
# 用法: ./run_checkin.sh
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  MiniMax Agent 每日签到"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 直连签到（status 查询 + claim 领取）
echo ">>> 直连签到..."
python3 signin_direct.py
DIRECT_EXIT=$?

echo ""
if [ $DIRECT_EXIT -eq 0 ]; then
    echo "✅ 直连签到成功"
    echo "RESULT|直连签到成功"
elif [ $DIRECT_EXIT -eq 2 ]; then
    # 退出码 2 = signature_pending，需要浏览器兜底
    echo "⚠️  直连 claim 签名待补全，切换浏览器兜底..."
    echo "RESULT|NEED_BROWSER_FALLBACK"
else
    echo "❌ 直连签到失败(exit=$DIRECT_EXIT)，切换浏览器兜底..."
    echo "RESULT|NEED_BROWSER_FALLBACK"
fi

echo ""
echo "=========================================="
echo "  签到流程结束"
echo "=========================================="
