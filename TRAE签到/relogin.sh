#!/bin/bash
# TRAE 凭证过期后重新授权登录（一键刷新 refreshToken）
# 用法: ./relogin.sh
# 会打印授权 URL，用浏览器打开后完成登录，回调自动刷新 trae_sms_accounts.json
set -e
cd "$(dirname "$0")"
source device_identity.env
echo "=========================================="
echo "  TRAE 重新授权登录"
echo "  设备ID: $TRAE_DEVICE_ID"
echo "=========================================="
echo ""
echo "即将启动 OAuth 登录脚本，它会打印授权 URL。"
echo "请用浏览器打开该 URL，完成手机号+验证码登录，"
echo "登录成功后会自动回调并刷新 trae_sms_accounts.json。"
echo ""
python3 trae_sms_login.py --no-open --timeout 600
echo ""
echo "✅ 授权完成，新凭证已保存到 trae_sms_accounts.json"
echo "   可运行 ./run_checkin.sh 验证签到。"
