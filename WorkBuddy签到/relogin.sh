#!/bin/bash
# WorkBuddy 凭证过期后重新授权登录
# 用法: ./relogin.sh
# 会打印 OAuth 登录链接，浏览器打开完成登录后自动刷新凭据
set -e
cd "$(dirname "$0")"
export WORKBUDDY_AUTH_FILE="$(pwd)/workbuddy-desktop.info"
echo "=========================================="
echo "  WorkBuddy 重新授权登录"
echo "  凭据文件: $WORKBUDDY_AUTH_FILE"
echo "=========================================="
echo ""
python3 signin.py login
echo ""
echo "✅ 授权完成，新凭证已保存。"
echo "   可运行 ./run_checkin.sh 验证签到。"
