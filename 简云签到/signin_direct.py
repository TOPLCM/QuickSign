#!/usr/bin/env python3
"""
简云 - 每日自动签到（直连方案）

功能：
  1. 邮箱密码登录（POST /login?action=email，含CSRF token）
  2. 访问签到页，从内联JS的 initialSummary 提取签到状态
  3. 未签到时调用签到接口（POST /addons?_plugin=90&_controller=index&_action=checkin）
  4. 验证签到结果

接口说明：
  - 登录页: GET /login（获取CSRF token）
  - 登录: POST /login?action=email（email, password, token）
  - 签到页: GET /addons?_plugin=90&_controller=index&_action=signin
  - 签到: POST /addons?_plugin=90&_controller=index&_action=checkin
"""

import json
import re
import sys
import os
from datetime import datetime
from urllib.parse import quote

import requests

# 工作目录
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(WORK_DIR, "config.json")
LOG_PATH = os.path.join(WORK_DIR, "signin.log")

# 常量
BASE_URL = "https://www.jianidc.com"
LOGIN_URL = f"{BASE_URL}/login"
SIGNIN_PAGE_URL = f"{BASE_URL}/addons?_plugin=90&_controller=index&_action=signin"
CHECKIN_API_URL = f"{BASE_URL}/addons?_plugin=90&_controller=index&_action=checkin"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def log(msg: str) -> None:
    """写入日志并打印到标准输出。"""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config() -> dict:
    """读取配置文件。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_csrf_token(session: requests.Session) -> str:
    """从登录页获取CSRF token。"""
    r = session.get(LOGIN_URL, headers={**HEADERS, "Referer": BASE_URL}, timeout=15)
    tokens = re.findall(r'name="token"\s+value="([^"]+)"', r.text)
    if not tokens:
        raise RuntimeError("未找到CSRF token")
    return tokens[0]


def login(session: requests.Session, email: str, password: str) -> bool:
    """
    邮箱密码登录。

    登录成功后服务端返回302重定向到/clientarea，并设置JWT cookie。
    密码含特殊字符需URL编码。
    """
    token = get_csrf_token(session)
    data = f"email={quote(email)}&password={quote(password)}&token={token}"

    try:
        r = session.post(
            f"{LOGIN_URL}?action=email",
            data=data.encode("utf-8"),
            headers={
                **HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": LOGIN_URL,
            },
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException as e:
        log(f"登录请求失败: {e}")
        return False

    # 302重定向到/clientarea表示登录成功
    if r.status_code == 302 and "/clientarea" in r.headers.get("Location", ""):
        log(f"登录成功（邮箱: {email}）")
        return True

    log(f"登录失败（HTTP {r.status_code}）")
    return False


def get_sign_summary(session: requests.Session) -> dict:
    """
    从签到页提取 initialSummary 数据。

    返回包含 signed_today, month_count, days 等字段的字典。
    """
    r = session.get(SIGNIN_PAGE_URL, headers={**HEADERS, "Referer": f"{BASE_URL}/clientarea"}, timeout=15)

    # 从内联JS中提取 initialSummary JSON
    m = re.search(r"initialSummary\s*=\s*(\{.*?\});", r.text, re.S)
    if not m:
        raise RuntimeError("未找到签到状态数据")

    # 处理Unicode转义（\u0026 -> &）
    raw = m.group(1).encode().decode("unicode_escape")
    return json.loads(raw)


def do_checkin(session: requests.Session) -> dict:
    """
    调用签到接口。

    签到接口为POST空body，返回JSON结果。
    """
    try:
        r = session.post(
            CHECKIN_API_URL,
            json={},
            headers={
                **HEADERS,
                "Referer": SIGNIN_PAGE_URL,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15,
        )
        return r.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"签到请求失败: {e}")
        return {"error": str(e)}


def main() -> int:
    """主流程：登录 → 检查状态 → 签到 → 验证。"""
    log("=== 简云签到开始（直连） ===")

    # 读取配置
    try:
        config = load_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"配置文件读取失败: {e}")
        print("RESULT|配置文件读取失败")
        return 1

    email = config.get("email", "")
    password = config.get("password", "")

    if not email or not password:
        log("配置文件缺少 email 或 password")
        print("RESULT|配置不完整")
        return 1

    # 创建会话
    session = requests.Session()

    # 1. 登录
    if not login(session, email, password):
        print("RESULT|登录失败")
        return 1

    # 2. 检查签到状态
    try:
        summary = get_sign_summary(session)
    except RuntimeError as e:
        log(f"获取签到状态失败: {e}")
        print("RESULT|获取签到状态失败")
        return 1

    signed_today = summary.get("signed_today", False)
    month_count = summary.get("month_count", 0)
    streak = summary.get("streak", 0)

    if signed_today:
        log(f"今日已签到（本月累计 {month_count} 天，连续 {streak} 天）")
        print(f"RESULT|今日已签到（本月累计{month_count}天，连续{streak}天）")
        return 0

    # 3. 未签到，执行签到
    log(f"今日未签到，开始签到（本月已签 {month_count} 天）...")
    result = do_checkin(session)

    # 4. 验证结果
    if result.get("error"):
        log(f"签到失败: {result['error']}")
        print(f"RESULT|签到失败: {result['error']}")
        return 1

    # 重新获取状态验证
    try:
        summary2 = get_sign_summary(session)
        if summary2.get("signed_today"):
            month_count2 = summary2.get("month_count", month_count)
            streak2 = summary2.get("streak", streak)
            log(f"签到成功（本月累计 {month_count2} 天，连续 {streak2} 天）")
            print(f"RESULT|签到成功（本月累计{month_count2}天，连续{streak2}天）")
            return 0
        else:
            log(f"签到后状态未变更，接口返回: {json.dumps(result, ensure_ascii=False)[:200]}")
            print("RESULT|签到失败: 状态未变更")
            return 1
    except RuntimeError as e:
        log(f"签到后验证失败: {e}")
        print(f"RESULT|签到可能成功但验证失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
