#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咸鱼单机（https://www.xianyudanji.gg）每日自动签到 —— 直连方案（主路径）

原理（已逆向并实测验证）：
  1. 访问首页，从页面内联脚本 rscConfig 中取滑块验证码的 nonce（每次加载都会变化）
  2. POST admin-ajax.php action=rsc_get_token 获取验证 token
  3. 生成拟人化拖动轨迹，POST action=rsc_verify 通过滑块验证（服务器会话记录验证通过）
  4. POST action=user_login 登录，拿到 WordPress 认证 Cookie（wordpress_logged_in_*，有效期 14 天）
  5. 访问 /user 用户中心，从"每日签到"按钮提取 data-nonce
  6. POST action=user_qiandao 完成签到；若已签到则返回"今日已签到"，视为成功（幂等）

长期可用性设计：
  - Cookie 持久化到 cookies.json，14 天有效期内直接复用，过期自动重新登录
  - 滑块验证码最多重试 max_captcha_retries 次，每次轨迹随机化
  - 所有步骤带重试与清晰日志；退出码 0=成功，1=失败（供定时任务判断是否走浏览器兜底）

用法：
  python3 signin_direct.py [--username xxx --password xxx]
  凭据默认从同目录 config.json 读取，也可用命令行参数覆盖。
"""
import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from http.cookiejar import Cookie

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UA_DEFAULT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg, log_path):
    line = f"[{now_str()}] {msg}"
    print(line, flush=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_config():
    cfg_path = os.path.join(BASE_DIR, "config.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("cookie_file", "cookies.json")
    cfg.setdefault("log_file", "signin.log")
    cfg.setdefault("max_captcha_retries", 6)
    cfg.setdefault("user_agent", UA_DEFAULT)
    cfg["cookie_path"] = os.path.join(BASE_DIR, cfg["cookie_file"])
    cfg["log_path"] = os.path.join(BASE_DIR, cfg["log_file"])
    return cfg


def new_session(cfg):
    s = requests.Session()
    s.headers.update({
        "User-Agent": cfg["user_agent"],
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": cfg["site"] + "/",
    })
    return s


def parse_nonce(text):
    """从页面 HTML 提取 rscConfig.nonce"""
    m = re.search(r"var\s+rscConfig\s*=\s*(\{.*?\});", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1)).get("nonce")
    except json.JSONDecodeError:
        return None


def gen_track(max_x=250, duration=None):
    """生成拟人化拖动轨迹：快速起步 + 缓速收尾 + 微抖动 + 偶发回退，时间戳递增"""
    duration = duration or random.randint(700, 1400)
    track = [{"x": 0, "y": 0, "t": 0}]
    t = 0
    x = 0.0
    while t < duration:
        step = random.randint(12, 28)
        t = min(t + step, duration)
        progress = t / duration
        target = max_x * (1 - (1 - progress) ** 2.2)
        x = max(x, target - random.uniform(0, 6))
        if random.random() < 0.05:
            x -= random.uniform(0, 3)
        track.append({
            "x": round(max(0.0, min(max_x, x)), 2),
            "y": round(random.uniform(-2.5, 2.5), 2),
            "t": t,
        })
    track.append({"x": float(max_x), "y": 0.0, "t": duration})
    return track


def do_verify(session, cfg, nonce, fp, retries):
    """获取 token 并提交轨迹验证，通过后服务器在会话内标记验证成功；返回是否通过"""
    for attempt in range(1, retries + 1):
        try:
            r = session.post(cfg["ajax_url"], data={
                "action": "rsc_get_token",
                "nonce": nonce,
                "fingerprint": fp,
            }, timeout=30)
            token = r.json().get("token")
            if not token:
                log(f"  [验证码] 获取 token 失败(第{attempt}次): {r.text[:150]}", cfg["log_path"])
                time.sleep(2)
                continue

            track = gen_track()
            r2 = session.post(cfg["ajax_url"], data={
                "action": "rsc_verify",
                "token": token,
                "duration": track[-1]["t"],
                "raw_track": json.dumps(track),
                "fingerprint": fp,
                "nonce": nonce,
            }, timeout=30)
            j = r2.json()
            if j.get("success"):
                return True
            msg = j.get("message", "")
            if j.get("locked"):
                wait = j.get("remaining", 60)
                log(f"  [验证码] 触发限流锁定，等待{wait}s后重试(第{attempt}次)", cfg["log_path"])
                time.sleep(min(wait + 2, 120))
            else:
                log(f"  [验证码] 验证未通过(第{attempt}次): {msg}", cfg["log_path"])
                time.sleep(1.5 + random.random() * 2)
        except (requests.RequestException, ValueError) as e:
            log(f"  [验证码] 网络/解析异常(第{attempt}次): {e}", cfg["log_path"])
            time.sleep(2)
    return False


def login(session, cfg, username, password):
    """完整登录流程；成功返回 True"""
    try:
        r = session.get(cfg["site"] + "/", timeout=30)
        nonce = parse_nonce(r.text)
        if not nonce:
            log("  [登录] 无法从首页解析 rscConfig nonce", cfg["log_path"])
            return False
    except requests.RequestException as e:
        log(f"  [登录] 首页请求失败: {e}", cfg["log_path"])
        return False

    fp = "".join(random.choice("0123456789abcdef") for _ in range(16))
    if not do_verify(session, cfg, nonce, fp, cfg["max_captcha_retries"]):
        log("  [登录] 滑块验证码最终失败，放弃本次登录", cfg["log_path"])
        return False

    try:
        r2 = session.post(cfg["ajax_url"], data={
            "action": "user_login",
            "username": username,
            "password": password,
            "rememberme": 1,
        }, timeout=30)
        j = r2.json()
        if str(j.get("status")) == "1":
            log("  [登录] 登录成功", cfg["log_path"])
            return True
        log(f"  [登录] 登录被拒绝: {j.get('msg','')}", cfg["log_path"])
        return False
    except (requests.RequestException, ValueError) as e:
        log(f"  [登录] 登录请求异常: {e}", cfg["log_path"])
        return False


def save_cookies(session, cfg):
    """持久化会话 Cookie（含 path/domain/expires），供后续复用"""
    data = []
    for c in session.cookies:
        data.append({
            "name": c.name, "value": c.value,
            "domain": c.domain, "path": c.path,
            "expires": c.expires, "secure": c.secure,
        })
    tmp = cfg["cookie_path"] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"saved_at": now_str(), "cookies": data}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, cfg["cookie_path"])
    log(f"  [Cookie] 已保存 {len(data)} 个 Cookie", cfg["log_path"])


def load_cookies(session, cfg):
    """载入持久化 Cookie；返回是否载入成功"""
    if not os.path.exists(cfg["cookie_path"]):
        return False
    try:
        with open(cfg["cookie_path"], encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("cookies", []):
            c = Cookie(
                version=0, name=item["name"], value=item["value"],
                port=None, port_specified=False,
                domain=item["domain"], domain_specified=bool(item["domain"]),
                domain_initial_dot=item["domain"].startswith("."),
                path=item["path"], path_specified=True,
                secure=item.get("secure", False), expires=item.get("expires"),
                discard=item.get("expires") is None, comment=None, comment_url=None,
                rest={}, rfc2109=False,
            )
            session.cookies.set_cookie(c)
        return True
    except (OSError, ValueError) as e:
        log(f"  [Cookie] 读取失败({e})，将重新登录", cfg["log_path"])
        return False


def is_logged_in(session, cfg):
    """GET /user，若页面是用户中心(有每日签到按钮)则已登录；若出现登录弹窗则未登录"""
    try:
        r = session.get(cfg["site"] + "/user", timeout=30)
    except requests.RequestException as e:
        log(f"  [状态] /user 请求失败: {e}", cfg["log_path"])
        return False, None
    text = r.text
    logged = ("go-user-qiandao" in text) and ("登录您的账户" not in text)
    return logged, r


def get_sign_nonce(user_html):
    """从用户中心 HTML 提取「每日签到」按钮的 data-nonce"""
    m = re.search(r'go-user-qiandao[^>]*data-nonce="([a-f0-9]+)"', user_html)
    return m.group(1) if m else None


def sign_in(session, cfg):
    """执行签到；返回 (exit_code, summary)"""
    logged, r = is_logged_in(session, cfg)
    if not logged:
        return 1, "未登录"
    nonce = get_sign_nonce(r.text)
    if not nonce:
        return 1, "未能在用户中心找到签到按钮 nonce（页面结构可能变化）"
    try:
        rr = session.post(cfg["ajax_url"], data={
            "action": cfg["sign_action"],
            "nonce": nonce,
        }, timeout=30)
        j = rr.json()
        status = str(j.get("status"))
        msg = j.get("msg", "")
        if status == "1":
            return 0, f"签到成功：{msg}"
        if status == "0" and ("已签到" in msg or "明日" in msg):
            return 0, f"今日已签到（无需重复）：{msg}"
        return 1, f"签到接口返回异常：status={status} msg={msg}"
    except (requests.RequestException, ValueError) as e:
        return 1, f"签到请求异常：{e}"


def main():
    parser = argparse.ArgumentParser(description="咸鱼单机每日自动签到（直连）")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    cfg = load_config()
    username = args.username or cfg["username"]
    password = args.password or cfg["password"]
    if not username or not password:
        log("缺少账号或密码（config.json 或 --username/--password）", cfg["log_path"])
        sys.exit(1)

    log("===== 咸鱼单机 每日自动签到（直连）开始 =====", cfg["log_path"])
    session = new_session(cfg)

    # 1) 尝试复用已保存 Cookie；有效则直接进入签到
    logged = False
    if load_cookies(session, cfg):
        logged, _ = is_logged_in(session, cfg)
        if logged:
            log("  [登录] 复用本地 Cookie，登录态有效", cfg["log_path"])
        else:
            log("  [登录] 本地 Cookie 已失效，重新登录", cfg["log_path"])

    # 2) 未登录则走完整登录流程（含滑块验证）
    if not logged:
        if not login(session, cfg, username, password):
            log("===== 直连签到失败（登录环节）=====", cfg["log_path"])
            sys.exit(1)
        save_cookies(session, cfg)

    # 3) 签到
    code, summary = sign_in(session, cfg)
    log(f"===== 结果: {summary} =====", cfg["log_path"])
    print(f"RESULT|{summary}")
    sys.exit(code)


if __name__ == "__main__":
    main()
