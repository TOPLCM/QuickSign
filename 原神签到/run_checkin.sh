#!/bin/bash
# 米游社原神每日签到运行入口
# 基于 MiyoQian (米游签) 开源项目，CLI 模式执行
# 用法: ./run_checkin.sh
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  米游社原神每日签到 (MiyoQian)"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo ">>> 虚拟环境不存在，正在安装依赖..."
    uv sync
    echo ""
fi

# 执行原神签到（只执行游戏社区签到，跳过云游戏和米游币任务）
echo ">>> 执行原神签到..."
uv run python main.py run --game genshin 2>&1
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 签到执行完成"
    echo "RESULT|原神签到成功"
else
    echo "❌ 签到执行失败(exit=$EXIT_CODE)"
    echo "RESULT|原神签到失败"
fi

echo ""
echo "=========================================="
echo "  签到流程结束"
echo "=========================================="

# 保留项目自身的日志，不额外写 signin.log
# 日志位置: logs/miyouqian.log
exit $EXIT_CODE
