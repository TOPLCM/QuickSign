#!/bin/bash
# WorkBuddy 每日签到运行脚本（签到 + 成长中心）
# 用法: ./run_checkin.sh
set -e
cd "$(dirname "$0")"

# 凭据文件固定在工作区（过 12 点重置不丢失）
export WORKBUDDY_AUTH_FILE="$(pwd)/workbuddy-desktop.info"

# 运行签到（auto = 签到 + 成长中心），日志追加到 signin.log
python3 signin.py auto 2>&1 | tee -a signin.log
