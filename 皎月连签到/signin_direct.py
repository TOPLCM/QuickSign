#!/usr/bin/env python3
"""
皎月连内网穿透 - 每日自动签到（直连方案）

功能：
  1. 使用账号密码登录，建立 PHPSESSID 会话
  2. 访问签到页面，提取"下次可签到时间"判断今日是否已签到
  3. 未签到时调用 qiandao_bf 预检查接口
  4. 若需要验证码（网易易盾），直连无法完成，返回失败码由浏览器兜底

接口说明：
  - 登录: POST /pc/login/login.html (username, password)
  - 签到页: GET /pc/sign/index.html
  - 签到预检查: POST /pc/sign/qiandao_bf.html
  - 实际签到: POST /pc/sign/qiandao.html（需验证码，直连不调用）

注意：登录接口虽返回 500，但 PHPSESSID 已建立，登录态有效。
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
BASE_URL = "https://www.natpierce.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/pc/login/login.html",
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


def login(session: requests.Session, username: str, password: str) -> bool:
    """
    登录皎月连，建立 PHPSESSID 会话。

    登录接口返回 500 属正常现象（服务端响应异常），
    只要 PHPSESSID cookie 生成且首页显示用户名即视为登录成功。
    """
    # 密码含 & 等特殊字符，需手动 URL 编码
    data = f"username={quote(username)}&password={quote(password)}"
    try:
        r = session.post(
            f"{BASE_URL}/pc/login/login.html",
            data=data.encode("utf-8"),
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
    except requests.RequestException as e:
        log(f"登录请求失败: {e}")
        return False

    # 验证登录态：访问首页检查用户名
    try:
        r2 = session.get(f"{BASE_URL}/pc/index/index.html", timeout=15)
        if username in r2.text:
            log(f"登录成功（用户: {username}）")
            return True
    except requests.RequestException:
        pass

    log(f"登录失败（HTTP {r.status_code}，登录态验证未通过）")
    return False


def check_sign_status(session: requests.Session) -> tuple[bool, str]:
    """
    检查签到状态。

    返回: (今日是否已签到, 下次可签到时间或状态信息)
    """
    try:
        r = session.get(f"{BASE_URL}/pc/sign/index.html", timeout=15)
    except requests.RequestException as e:
        log(f"签到页访问失败: {e}")
        return False, "签到页访问失败"

    # 提取"下次可签到时间"
    m = re.search(r"下次可签到时间[：:]\s*([^<\s]+)", r.text)
    next_sign = m.group(1) if m else "未知"

    # 提取服务到期时间
    m2 = re.search(r"服务到期时间[：:]\s*([^<\s]+)", r.text)
    expire = m2.group(1) if m2 else "未知"

    today = datetime.now().strftime("%Y-%m-%d")

    # 判断：如果下次可签到时间晚于今天，说明今天已签到
    if next_sign != "未知" and next_sign > today:
        return True, f"今日已签到（下次可签到: {next_sign}，服务到期: {expire}）"

    return False, f"今日未签到（下次可签到: {next_sign}，服务到期: {expire}）"


def pre_check(session: requests.Session) -> tuple[bool, str]:
    """
    签到预检查（qiandao_bf）。

    返回: (是否可以直接签到, 消息)
    - code=200: 可以签到，但需要验证码（直连无法完成）
    - code=400: 服务尚未到期，无需签到（视为已签到成功）
    - 其他: 异常
    """
    try:
        r = session.post(
            f"{BASE_URL}/pc/sign/qiandao_bf.html",
            headers={
                **HEADERS,
                "Referer": f"{BASE_URL}/pc/sign/index.html",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15,
        )
        data = r.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"签到预检查失败: {e}")
        return False, "预检查请求失败"

    code = data.get("code")
    message = data.get("message", "")

    if code == 200:
        # 需要验证码，直连无法完成
        return False, "需要验证码（网易易盾），直连无法完成，请使用浏览器兜底"
    elif code == 400:
        # 服务尚未到期，无需签到（通常意味着今天已签到或服务期内）
        return True, f"无需签到（{message}）"
    else:
        return False, f"预检查异常: code={code}, message={message}"


def main() -> int:
    """主流程：登录 → 检查状态 → 预检查 → 输出结果。"""
    log("=== 皎月连签到开始（直连） ===")

    # 读取配置
    try:
        config = load_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"配置文件读取失败: {e}")
        print("RESULT|配置文件读取失败")
        return 1

    username = config.get("username", "")
    password = config.get("password", "")

    if not username or not password:
        log("配置文件缺少 username 或 password")
        print("RESULT|配置不完整")
        return 1

    # 创建会话
    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. 登录
    if not login(session, username, password):
        print("RESULT|登录失败")
        return 1

    # 2. 检查签到状态
    signed, status_msg = check_sign_status(session)
    log(f"签到状态: {status_msg}")

    if signed:
        log(f"=== 皎月连签到完成: {status_msg} ===")
        print(f"RESULT|{status_msg}")
        return 0

    # 3. 未签到，执行预检查
    can_sign, pre_msg = pre_check(session)
    log(f"预检查: {pre_msg}")

    if can_sign:
        # code=400 "服务尚未到期，无需签到" 视为成功
        log(f"=== 皎月连签到完成: {pre_msg} ===")
        print(f"RESULT|签到成功（{pre_msg}）")
        return 0
    else:
        # 需要验证码，直连失败，返回 2 触发浏览器兜底
        log(f"=== 皎月连直连失败: {pre_msg} ===")
        print(f"RESULT|直连失败（{pre_msg}）")
        return 2


if __name__ == "__main__":
    sys.exit(main())
