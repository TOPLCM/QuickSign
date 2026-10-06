#!/bin/bash
# TRAE 积分余额查询（只读，不签到）
# 用法: ./run_monitor.sh
set -e
cd "$(dirname "$0")"
source device_identity.env
export TRAE_ACCOUNTS="$(cat trae_sms_accounts.json)"
export TRAE_TOKEN_CACHE="$(pwd)/token_cache.json"
python3 trae_credit_monitor.py "$@" 2>&1 | tee -a monitor.log
