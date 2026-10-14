#!/usr/bin/env python3
"""
广西职业院校学生岗位实习管理系统 - 每日自动签到（直连方案）

功能：
  1. 账号密码登录（POST /api/studentapp/Login）
  2. 获取签到设置（POST /api/studentapp/Settings），含公司坐标和签到范围
  3. 检查今日签到状态（POST /api/studentapp/Info，SignToday字段）
  4. 未签到时，使用配置的坐标调用签到接口（POST /api/studentapp/Sign，参数Lat/Lng）
  5. 验证签到结果

接口说明：
  - 登录: POST {api_base}/api/studentapp/Login
    参数: {"UserName": "...", "Password": "..."}
    返回: {"Data": {"access_token": "...", "refresh_token": "..."}, "Code": 0}
  - 学生信息: POST {api_base}/api/studentapp/Info（需Bearer token）
    返回: {"Data": {"SignToday": false, "TotalSignCount": 6, ...}, "Code": 0}
  - 签到设置: POST {api_base}/api/studentapp/Settings（需Bearer token）
    返回: {"Data": {"CompanyLat": 22.8, "CompanyLng": 108.3, "SignRange": 400000, ...}, "Code": 0}
  - 签到: POST {api_base}/api/studentapp/Sign（需Bearer token）
    参数: {"Lat": 22.8, "Lng": 108.3}
    返回: {"Code": 0, "Msg": "成功"} 或 {"Code": 1, "Msg": "当前位置不在可签到范围"}
  - 签到日志: POST {api_base}/api/studentapp/SignLog（需Bearer token）
"""

import json
import sys
import os
from datetime import datetime

import requests

# 工作目录
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(WORK_DIR, "config.json")
LOG_PATH = os.path.join(WORK_DIR, "signin.log")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
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


def login(session: requests.Session, api_base: str, username: str, password: str) -> str:
    """
    账号密码登录，返回 access_token。

    登录成功返回 JWT token，有效期 24 小时。
    """
    url = f"{api_base}/api/studentapp/Login"
    try:
        r = session.post(
            url,
            json={"UserName": username, "Password": password},
            headers={**HEADERS, "Referer": "https://gxzjsxs.gxibvc.net/"},
            timeout=15,
        )
        data = r.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"登录请求失败: {e}")
        return ""

    if data.get("Code") == 0 and data.get("Data", {}).get("access_token"):
        token = data["Data"]["access_token"]
        log(f"登录成功（账号: {username}）")
        return token

    log(f"登录失败: {data.get('Msg', '未知错误')}")
    return ""


def get_student_info(session: requests.Session, api_base: str, token: str) -> dict:
    """获取学生信息，含今日签到状态。"""
    url = f"{api_base}/api/studentapp/Info"
    try:
        r = session.post(
            url,
            json={},
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return r.json().get("Data", {})
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"获取学生信息失败: {e}")
        return {}


def get_sign_settings(session: requests.Session, api_base: str, token: str) -> dict:
    """获取签到设置，含公司坐标和签到范围。"""
    url = f"{api_base}/api/studentapp/Settings"
    try:
        r = session.post(
            url,
            json={},
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return r.json().get("Data", {})
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"获取签到设置失败: {e}")
        return {}


def do_sign(session: requests.Session, api_base: str, token: str, lat: float, lng: float) -> dict:
    """
    执行签到。

    参数 Lat/Lng 为签到定位坐标。签到范围通常为 400 公里，
    使用公司坐标或实习城市坐标均可。
    """
    url = f"{api_base}/api/studentapp/Sign"
    try:
        r = session.post(
            url,
            json={"Lat": lat, "Lng": lng},
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return r.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        log(f"签到请求失败: {e}")
        return {"Code": -1, "Msg": str(e)}


def main() -> int:
    """主流程：登录 → 检查状态 → 签到 → 验证。"""
    log("=== 广西职业院校学生岗位实习签到开始（直连） ===")

    # 读取配置
    try:
        config = load_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"配置文件读取失败: {e}")
        print("RESULT|配置文件读取失败")
        return 1

    api_base = config.get("api_base", "https://gxzjsx.gxibvc.net")
    username = config.get("username", "")
    password = config.get("password", "")
    sign_lat = config.get("sign_lat", 22.79798846)
    sign_lng = config.get("sign_lng", 108.32937565)

    if not username or not password:
        log("配置文件缺少 username 或 password")
        print("RESULT|配置不完整")
        return 1

    session = requests.Session()

    # 1. 登录
    token = login(session, api_base, username, password)
    if not token:
        print("RESULT|登录失败")
        return 1

    # 2. 获取签到设置
    settings = get_sign_settings(session, api_base, token)
    if settings:
        company_name = settings.get("CompanyName", "")
        company_addr = settings.get("CompanyAddress", "")
        sign_range = settings.get("SignRange", 0)
        log(f"实习单位: {company_name}（{company_addr}），签到范围: {sign_range/1000:.0f}公里")

    # 3. 检查今日签到状态
    info = get_student_info(session, api_base, token)
    sign_today = info.get("SignToday", False)
    total_sign = info.get("TotalSignCount", 0)

    if sign_today:
        log(f"今日已签到（累计签到 {total_sign} 次）")
        print(f"RESULT|今日已签到（累计{total_sign}次）")
        return 0

    # 4. 未签到，执行签到
    log(f"今日未签到，开始签到（定位: {sign_lat}, {sign_lng}）...")
    result = do_sign(session, api_base, token, sign_lat, sign_lng)

    code = result.get("Code", -1)
    msg = result.get("Msg", "")

    if code == 0:
        # 5. 验证签到结果
        info2 = get_student_info(session, api_base, token)
        if info2.get("SignToday"):
            total2 = info2.get("TotalSignCount", total_sign)
            log(f"签到成功（累计签到 {total2} 次）")
            print(f"RESULT|签到成功（累计{total2}次）")
            return 0
        else:
            log("签到接口返回成功但状态未变更")
            print("RESULT|签到可能成功但验证失败")
            return 1
    else:
        log(f"签到失败: {msg}")
        print(f"RESULT|签到失败: {msg}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
