#!/usr/bin/env python3
"""
恩山无线论坛 (right.com.cn) 每日签到 - 直连脚本
基于 Discuz! X3.5 + erling_qd 签到插件 (v1.0)

签到流程：
  1. 访问登录页获取 formhash
  2. POST 登录获取 auth cookie (rHEX_2132_auth)
  3. 访问签到页面 plugin.php?id=erling_qd:sign_in 获取 FORMHASH
  4. 检查签到状态（按钮 disabled=已签到）
  5. 未签到则 POST plugin.php?id=erling_qd:action&action=sign (formhash=FORMHASH)
  6. 解析 JSON 响应 {success, message}
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime

# 配置与日志路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "signin.log")

# 站点常量
BASE_URL = "https://www.right.com.cn/forum"
LOGIN_PAGE = f"{BASE_URL}/member.php?mod=logging&action=login"
LOGIN_SUBMIT = f"{BASE_URL}/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes"
SIGNIN_PAGE = f"{BASE_URL}/plugin.php?id=erling_qd:sign_in"
SIGNIN_ACTION = f"{BASE_URL}/plugin.php?id=erling_qd:action&action=sign"
HOME_PAGE = f"{BASE_URL}/forum.php"

# 通用请求头
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def load_config():
    """加载配置文件，返回字典"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    """追加写入日志并打印"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def make_opener():
    """创建带 Cookie 管理的 URL opener，opener.cookiejar 可访问 Cookie"""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = list(COMMON_HEADERS.items())
    opener.cookiejar = cj  # 附加引用，便于后续检查 auth cookie
    return opener, cj


def http_get(opener, url, referer=None):
    """发送 GET 请求，返回 (status, html)"""
    req = urllib.request.Request(url)
    if referer:
        req.add_header("Referer", referer)
    with opener.open(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def http_post(opener, url, data, referer=None, content_type="application/x-www-form-urlencoded"):
    """发送 POST 请求，返回 (status, body_text)"""
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", content_type)
    if referer:
        req.add_header("Referer", referer)
    with opener.open(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def extract_formhash(html):
    """从 HTML 中提取 formhash（8位十六进制）"""
    m = re.search(r'name="formhash"[^>]*value="([a-f0-9]{8})"', html)
    if m:
        return m.group(1)
    m = re.search(r'var FORMHASH\s*=\s*[\'"]([a-f0-9]{8})[\'"]', html)
    if m:
        return m.group(1)
    return None


def do_login(opener, username, password):
    """
    执行 Discuz! 登录
    返回 (success: bool, message: str)
    """
    # 1. 获取登录页 formhash
    _, html = http_get(opener, LOGIN_PAGE)
    fh = extract_formhash(html)
    if not fh:
        return False, "登录页 formhash 提取失败"

    # 2. 提交登录
    login_data = {
        "formhash": fh,
        "referer": HOME_PAGE,
        "username": username,
        "password": password,
        "cookietime": "2592000",
        "loginsubmit": "true",
    }
    try:
        status, body = http_post(opener, LOGIN_SUBMIT, login_data, referer=LOGIN_PAGE)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        status = e.code

    # 3. 检查是否登录成功（auth cookie）
    auth_cookie = None
    for cookie in opener.cookiejar:
        if "auth" in cookie.name.lower():
            auth_cookie = cookie.value
            break

    if auth_cookie:
        return True, "登录成功"
    else:
        # 尝试从响应中提取错误信息
        error_match = re.search(r'(错误[^<]{0,50}|失败[^<]{0,50}|密码[^<]{0,30})', body)
        msg = error_match.group(1) if error_match else "登录失败，未获得 auth cookie"
        return False, msg


def check_signin_status(opener):
    """
    访问签到页面，检查今日签到状态
    返回 (already_signed: bool, formhash: str|None, stats: dict)
    """
    _, html = http_get(opener, SIGNIN_PAGE, referer=HOME_PAGE)

    # 提取 FORMHASH
    formhash = extract_formhash(html)

    # 检查签到按钮状态：disabled 且文本含"已签到"
    btn_match = re.search(
        r'<button[^>]*id="signin-btn"[^>]*>([^<]*)</button>',
        html,
    )
    btn_text = btn_match.group(1).strip() if btn_match else ""
    already_signed = "已签到" in btn_text or "disabled" in (btn_match.group(0) if btn_match else "")

    # 提取统计数据
    stats = {}
    cont = re.search(r'连续签到[^<]*<span[^>]*>(\d+)</span>', html)
    if cont:
        stats["continuous_days"] = int(cont.group(1))
    total = re.search(r'总签到天数[^<]*<span[^>]*>(\d+)</span>', html)
    if total:
        stats["total_days"] = int(total.group(1))
    point = re.search(r'今日积分[^<]*<span[^>]*>(\d+)</span>', html)
    if point:
        stats["today_points"] = int(point.group(1))

    return already_signed, formhash, stats


def do_signin(opener, formhash):
    """
    执行签到（POST 到签到接口）
    返回 (success: bool, message: str)
    """
    post_data = {"formhash": formhash}
    try:
        status, body = http_post(
            opener, SIGNIN_ACTION, post_data,
            referer=SIGNIN_PAGE,
            content_type="application/x-www-form-urlencoded",
        )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        status = e.code

    # 尝试解析 JSON 响应
    try:
        resp = json.loads(body)
        success = resp.get("success", False)
        message = resp.get("message", "无消息")
        return success, message
    except json.JSONDecodeError:
        # 非 JSON 响应，检查是否包含成功关键词
        if "成功" in body or "已签到" in body:
            return True, "签到成功（非JSON响应）"
        elif "错误" in body or "失败" in body:
            return False, f"签到失败: {body[:100]}"
        else:
            return False, f"未知响应(status={status}): {body[:100]}"


def main():
    """主流程：登录 → 查状态 → 未签则签到"""
    log("=== 恩山论坛签到开始（直连） ===")

    # 加载配置
    try:
        config = load_config()
    except Exception as e:
        log(f"CONFIG_ERROR 配置文件读取失败: {e}")
        print("RESULT|配置文件读取失败")
        return 1

    username = config.get("username", "")
    password = config.get("password", "")
    if not username or not password:
        log("CONFIG_ERROR 配置中缺少 username 或 password")
        print("RESULT|配置不完整")
        return 1

    # 创建 opener
    opener, cj = make_opener()

    # 1. 登录
    log(f"正在登录账号: {username}")
    login_ok, login_msg = do_login(opener, username, password)
    if not login_ok:
        log(f"LOGIN_FAIL {login_msg}")
        print(f"RESULT|登录失败: {login_msg}")
        return 1
    log("登录成功")

    # 2. 检查签到状态
    already, formhash, stats = check_signin_status(opener)
    stats_str = f"连续{stats.get('continuous_days', '?')}天, 总{stats.get('total_days', '?')}天, 今日积分{stats.get('today_points', '?')}"
    log(f"签到状态: 已签={already}, formhash={'有' if formhash else '无'}, {stats_str}")

    if already:
        log(f"今日已签到，跳过领取（{stats_str}）")
        print(f"RESULT|今日已签到（{stats_str}）")
        log("=== 恩山论坛签到完成（直连） ===")
        return 0

    # 3. 未签到，执行签到
    if not formhash:
        log("SIGNIN_FAIL 未获取到 formhash，无法签到")
        print("RESULT|签到失败: 未获取到 formhash")
        return 1

    log("正在执行签到...")
    sign_ok, sign_msg = do_signin(opener, formhash)
    if sign_ok:
        log(f"签到成功: {sign_msg}")
        # 重新查询状态确认
        time.sleep(1)
        already2, _, stats2 = check_signin_status(opener)
        stats_str2 = f"连续{stats2.get('continuous_days', '?')}天, 总{stats2.get('total_days', '?')}天"
        log(f"签到后状态确认: 已签={already2}, {stats_str2}")
        print(f"RESULT|签到成功（{stats_str2}）")
        log("=== 恩山论坛签到完成（直连） ===")
        return 0
    else:
        log(f"SIGNIN_FAIL 签到失败: {sign_msg}")
        print(f"RESULT|签到失败: {sign_msg}")
        log("=== 恩山论坛签到失败（直连） ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())
