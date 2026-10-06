#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云原神每日自动签到 —— 浏览器兜底方案

原理
----
云原神网页加载时，登录态有效则自动完成「每日登录 → 赠时 15 分钟」，
无需任何额外点击。本脚本用云端浏览器打开 https://ys.mihoyo.com/cloud/，
确认登录态与当日赠时状态；若登录态丢失，则停留在登录界面并提示用户接管
（滑块 / 图标点击 / 短信验证码），登录成功后自动重新导出 Cookie。

运行方式
--------
在 browser-use 环境（computer_use_tool, plane="bu", 内嵌 seed_browser_use）中执行：

    python3 browser_fallback.py

典型时序
--------
1. 打开云原神页面，等待 12~15 秒让登录链（webVerifyForGame → webLogin →
   gamer/api/login）自动完成；
2. 读取页面文本：
   - 出现「免费时长 / AID」→ 已登录，今日赠时已记录，成功；
   - 出现「登录 / 短信登录 / 密码登录」→ 登录态丢失，进入人工接管流程；
3. 人工接管完成后，通过 CDP Network.getAllCookies 导出最新 Cookie，
   覆盖工作区 cookies.json，供直连脚本（signin_direct.py）继续使用。
"""
import json
import os
import time

import seed_browser_use as bu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL = "https://ys.mihoyo.com/cloud/"
COOKIE_PATH = os.path.join(BASE_DIR, "cookies.json")  # 固定写入脚本所在目录
SUCCESS_KEY = ["免费时长", "AID", "进入游戏"]   # 已登录主界面特征
LOGIN_KEY = ["短信登录", "密码登录", "请输入短信验证码"]  # 登录界面特征


def export_cookies(session_id=None) -> dict:
    """
    通过 CDP 导出 mihoyo 域全部 Cookie（含 HttpOnly 的 ltoken/ltuid 等），
    写回 cookies.json，供直连脚本复用。
    cdp 签名：bu.cdp(method, session_id=None, **params)
    """
    res = bu.cdp("Network.getAllCookies", session_id)
    keep = {}
    for c in res.get("cookies", []):
        if "mihoyo.com" in c.get("domain", ""):
            keep[c["name"]] = {
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
            }
    with open(COOKIE_PATH, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=2)
    return keep


def main() -> int:
    """兜底主流程：打开页面 → 判定登录态 → 导出 Cookie / 提示接管。"""
    print("[fallback] 打开云原神页面")
    try:
        bu.resync()
    except Exception:
        pass
    bu.navigate(URL)
    time.sleep(14)  # 等待登录链自动执行完成

    txt = bu.get_page_text()
    print("[fallback] 页面文本片段:", txt[:200].replace("\n", " | "))

    if any(k in txt for k in SUCCESS_KEY):
        print("[fallback] ✓ 已登录（页面自动完成每日赠时）")
        cookies = export_cookies()
        print(f"[fallback] ✓ Cookie 已导出 {len(cookies)} 条 → {COOKIE_PATH}")
        return 0

    if any(k in txt for k in LOGIN_KEY) or "验证码" in txt or "拖动滑块" in txt:
        print("[fallback] ✗ 登录态丢失，需人工接管完成登录（滑块 / 图标 / 短信验证码）")
        print("[fallback] 接管完成后将自动导出 Cookie 并结束。")
        # 保持页面停留在登录面板，等待用户接管（由外部 interaction.request_action 触发）
        time.sleep(30)
        txt2 = bu.get_page_text()
        if any(k in txt2 for k in SUCCESS_KEY):
            cookies = export_cookies()
            print(f"[fallback] ✓ 接管后登录成功，Cookie 已导出 {len(cookies)} 条")
            return 0
        print("[fallback] ✗ 等待超时仍未登录，请在下次运行时重新接管。")
        return 2

    print("[fallback] ⚠ 页面状态未知，请人工检查浏览器当前页面。")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
