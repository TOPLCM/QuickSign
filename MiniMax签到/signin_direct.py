#!/usr/bin/env python3
"""
MiniMax Agent 每日签到 - 直连脚本
基于接口分析：
  GET  /minimax-cloud/api/v1/signin/status  — 查询签到状态（无需签名）
  POST /minimax-cloud/api/v1/signin/claim   — 领取签到积分（需要签名，当前返回 invalid signature）

登录态：Cookie _token (JWT, 约40天有效)
TODO: 补全 POST /claim 的签名算法（需拦截真实页面请求分析）
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signin.log")


def load_config():
    """加载配置文件"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    """写日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def api_request(config, path, method="GET", body=None, extra_headers=None):
    """通用 API 请求"""
    url = config["base_url"] + path
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"_token={config['token']}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 MiniMaxSignin/1.0",
    }
    if extra_headers:
        headers.update(extra_headers)

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(resp_body)
        except json.JSONDecodeError:
            return e.code, {"raw": resp_body}
    except Exception as e:
        return -1, {"error": str(e)}


def check_status(config):
    """查询签到状态"""
    params = "device_platform=web&biz_id=3&app_id=3001&version_code=22201"
    path = f"{config['api_base']}/status?{params}"
    status, body = api_request(config, path, "GET")

    if status != 200:
        log(f"STATUS_FAIL http={status} body={json.dumps(body, ensure_ascii=False)[:200]}")
        return None

    data = body.get("data", {})
    days = data.get("days", [])
    today = next((d for d in days if d.get("is_today")), None)
    streak = sum(1 for d in days if d.get("status") == 3)
    total_points = sum(d.get("points", 0) + d.get("bonus_points", 0) for d in days if d.get("status") == 3)

    result = {
        "today_checked": today.get("status") == 3 if today else False,
        "today_day_no": today.get("day_no") if today else None,
        "today_points": today.get("points") if today else 0,
        "today_bonus": today.get("bonus_points") if today else 0,
        "streak_days": streak,
        "total_points_this_round": total_points,
        "scene": data.get("scene"),
    }
    return result


def do_claim(config):
    """
    领取签到积分
    TODO: 需要补全签名算法，当前返回 invalid signature
    签名可能在请求头中，需拦截真实页面请求分析
    """
    params = "device_platform=web&biz_id=3&app_id=3001&version_code=22201"
    path = f"{config['api_base']}/claim?{params}"
    status, body = api_request(config, path, "POST", body={})

    if status == 200:
        log(f"CLAIM_SUCCESS body={json.dumps(body, ensure_ascii=False)[:300]}")
        return True
    elif status == 400 and "invalid signature" in str(body):
        log("CLAIM_SIGNATURE_PENDING 签名算法待补全，需浏览器兜底")
        return "signature_pending"
    elif status == 400 and ("已签到" in str(body) or "already" in str(body).lower()):
        log("CLAIM_ALREADY 今日已签到")
        return "already"
    else:
        log(f"CLAIM_FAIL http={status} body={json.dumps(body, ensure_ascii=False)[:200]}")
        return False


def main():
    """主流程：查状态 → 未签则领取"""
    log("=== MiniMax 签到开始（直连） ===")

    try:
        config = load_config()
    except Exception as e:
        log(f"CONFIG_ERROR {e}")
        print("RESULT|配置文件读取失败")
        return 1

    # 检查 token 是否过期
    token_expires = config.get("token_expires_at", "")
    if token_expires:
        try:
            exp_dt = datetime.fromisoformat(token_expires.replace("Z", "+00:00"))
            if datetime.now(exp_dt.tzinfo) > exp_dt:
                log("TOKEN_EXPIRED token已过期，需重新登录")
                print("RESULT|token已过期，请重新登录")
                return 1
        except Exception:
            pass

    # 查询签到状态
    status = check_status(config)
    if status is None:
        print("RESULT|签到状态查询失败")
        return 1

    log(f"STATUS 今日已签={status['today_checked']} 第{status['today_day_no']}天 "
        f"连续{status['streak_days']}天 本轮累计{status['total_points_this_round']}积分")

    if status["today_checked"]:
        log("今日已签到，跳过领取")
        print(f"RESULT|今日已签到（第{status['today_day_no']}天，连续{status['streak_days']}天，本轮累计{status['total_points_this_round']}积分）")
        log("=== MiniMax 签到完成（直连） ===")
        return 0

    # 未签到，尝试领取
    result = do_claim(config)

    if result is True:
        print("RESULT|签到成功")
        log("=== MiniMax 签到完成（直连） ===")
        return 0
    elif result == "signature_pending":
        # 签名待补全，返回特殊退出码让外层知道需要浏览器兜底
        print("RESULT|签名待补全，需浏览器兜底")
        log("=== MiniMax 签到需浏览器兜底 ===")
        return 2
    elif result == "already":
        print("RESULT|今日已签到")
        log("=== MiniMax 签到完成（直连） ===")
        return 0
    else:
        print("RESULT|签到失败")
        log("=== MiniMax 签到失败（直连） ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())
