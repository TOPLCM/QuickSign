#!/bin/bash
# TRAE 每日签到运行脚本
# 用法: ./run_checkin.sh
# 环境变量全部从工作区读取，确保过 12 点重置后不丢失
set -e
cd "$(dirname "$0")"

# 1. 加载设备身份（ECDSA 密钥 / device_id / machine_id）
source device_identity.env

# 2. 加载账号凭证（TRAE_ACCOUNTS JSON 数组）
export TRAE_ACCOUNTS="$(cat trae_sms_accounts.json)"

# 3. token 缓存文件固定在工作区（refreshToken 轮换链回写，防止丢失）
export TRAE_TOKEN_CACHE="$(pwd)/token_cache.json"

# 4. 运行签到，日志追加到 checkin.log
python3 trae_checkin.py "$@" 2>&1 | tee -a checkin.log
