#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云原神每日自动签到 —— 直连方案（HTTP API 直连）

原理
----
云原神「每日登录网页即自动签到，发放 15 分钟云游戏时长」。
网页加载时浏览器会依次调用以下接口，直连脚本用缓存的登录态 Cookie 原样重放：

    1. webVerifyForGame     会话校验（可选，用于提前发现 Cookie 失效）
    2. combo/granter/login/webLogin
                            换取 combo_token（登录态来自 Cookie 中的 ltoken_v2/ltuid_v2）
    3. gamer/api/login      云游戏登录（服务器记录「今日登录」并发放当日赠时）
    4. wallet/wallet/get    读取钱包/免费时长，用于确认结果与留档

幂等性
-------
服务端按「每日首次登录」发放赠时，重复调用 gamer/api/login 返回 retcode=0，
不会重复发放。因此脚本可安全地每日多次运行，日志中 free_time 即为当前余额。

失败处理
--------
- retcode -100「登录已失效」：Cookie 过期，直连不可用，需用浏览器兜底方案重新登录
  （见 browser_fallback.py 与 README.md），登录后重新导出 Cookie 到 cookies.json。
- si 失效（-100 且 Cookie 仍有效）：需在浏览器中打开一次云原神页面，
  从网络请求 x-rpc-combo_token 中提取新的 si 字段更新 config.json。

文件
----
- config.json   站点/账号/设备常量/si 缓存
- cookies.json  登录态 Cookie（HttpOnly，来自浏览器 CDP 导出）
- signin.log    运行日志（追加）
"""
import json
import sys
import datetime
import os

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg: str) -> None:
    """追加一行带时间戳的日志，同时打印到标准输出。"""
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(os.path.join(BASE_DIR, "signin.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(name: str) -> dict:
    """读取子文件夹内的 JSON 配置文件。"""
    with open(os.path.join(BASE_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def build_headers(cfg: dict, **extra) -> dict:
    """组装云游戏 API 请求头：基础 UA + 业务头 + 额外头。"""
    dev = cfg["device"]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://ys.mihoyo.com",
        "Referer": "https://ys.mihoyo.com/cloud/#/",
        "x-rpc-device_id": dev["device_id"],
        "x-rpc-device_fp": dev["device_fp"],
        "x-rpc-device_name": dev["device_name"],
        "x-rpc-device_model": dev["device_model"],
        "x-rpc-device_os": dev["device_os"],
        "x-rpc-language": "zh-cn",
        "x-rpc-app_version": cfg["app_version"],
    }
    headers.update(extra)
    return headers


def get_cookie_jar() -> dict:
    """从 cookies.json 组装 requests 的 Cookie 字典。"""
    data = load_json("cookies.json")
    return {k: v["value"] for k, v in data.items()}


def verify_session(sess: requests.Session, cfg: dict) -> bool:
    """
    第 1 步：webVerifyForGame 会话校验。
    成功返回 True；Cookie 失效返回 False（调用方决定是否继续走 webLogin）。
    """
    dev = cfg["device"]
    lifecycle = sess.cookies.get("MIHOYO_LOGIN_PLATFORM_LIFECYCLE_ID", dev["lifecycle_id"])
    headers = build_headers(cfg, **{
        "x-rpc-lifecycle_id": lifecycle,
        "x-rpc-app_id": "c76ync6mutq8",
        "x-rpc-app_version": "",
        "x-rpc-game_biz": "hk4e_cn",
        "x-rpc-sdk_version": cfg["sdk_version"],
        "x-rpc-client_type": dev["client_type_sdk"],
        "x-rpc-mi_referrer": "https://ys.mihoyo.com/cloud/#/",
    })
    try:
        r = sess.post("https://passport-api.mihoyo.com/account/ma-cn-session/web/webVerifyForGame",
                      headers=headers, data="", timeout=15)
        data = r.json()
        return data.get("retcode") == 0
    except Exception as e:  # 网络异常按「会话未知」处理，不阻断后续
        log(f"webVerifyForGame 异常（继续尝试 webLogin）: {e}")
        return True


def web_login(sess: requests.Session, cfg: dict) -> dict:
    """
    第 2 步：combo webLogin，换取 combo_token。
    返回 {"open_id": str, "combo_token": str}；失败返回 None。
    """
    dev = cfg["device"]
    headers = build_headers(cfg, **{
        "Content-Type": "application/json",
        "x-rpc-client_type": dev["client_type_sdk"],
        "x-rpc-game_biz": "hk4e_cn",
        "x-rpc-mdk_version": cfg["mdk_version"],
        "x-rpc-channel_id": "1",
    })
    r = sess.post("https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/granter/login/webLogin",
                  headers=headers, json={"app_id": 4, "channel_id": 1}, timeout=15)
    data = r.json()
    if data.get("retcode") != 0:
        return None
    inner = data.get("data") or {}
    return {"open_id": str(inner.get("open_id", "")), "combo_token": inner.get("combo_token", "")}


def cg_login(sess: requests.Session, cfg: dict, open_id: str, combo_token: str) -> dict:
    """
    第 3 步：云游戏登录 gamer/api/login（触发「今日登录」赠时）。
    返回完整 JSON 响应。
    """
    dev = cfg["device"]
    combo = f"ai=4;ci=1;oi={open_id};ct={combo_token};si={cfg['si']};bi=hk4e_cn"
    headers = build_headers(cfg, **{
        "x-rpc-client_type": dev["client_type_cg"],
        "x-rpc-sys_version": "Linux undefined",
        "x-rpc-channel": "mihoyo",
        "x-rpc-vendor_id": "2",
        "x-rpc-cg_game_biz": "hk4e_cn",
        "x-rpc-op_biz": "clgm_cn",
        "x-rpc-cps": "keyboard_mihoyo",
        "x-rpc-combo_token": combo,
        "x-rpc-app_id": "4",
    })
    r = sess.post("https://api-cloudgame.mihoyo.com/hk4e_cg_cn/gamer/api/login",
                  headers=headers, data="", timeout=15)
    return r.json()


def get_wallet(sess: requests.Session, cfg: dict, open_id: str, combo_token: str) -> dict:
    """第 4 步：读取钱包/免费时长，用于确认与留档。"""
    dev = cfg["device"]
    combo = f"ai=4;ci=1;oi={open_id};ct={combo_token};si={cfg['si']};bi=hk4e_cn"
    headers = build_headers(cfg, **{
        "x-rpc-client_type": dev["client_type_cg"],
        "x-rpc-sys_version": "Linux undefined",
        "x-rpc-channel": "mihoyo",
        "x-rpc-vendor_id": "2",
        "x-rpc-cg_game_biz": "hk4e_cn",
        "x-rpc-op_biz": "clgm_cn",
        "x-rpc-cps": "keyboard_mihoyo",
        "x-rpc-combo_token": combo,
        "x-rpc-app_id": "4",
    })
    r = sess.get("https://api-cloudgame.mihoyo.com/hk4e_cg_cn/wallet/wallet/get",
                 headers=headers, timeout=15)
    return r.json()


def main() -> int:
    """主流程：加载配置 → 会话校验 → webLogin → gamer/login → wallet。"""
    cfg = load_json("config.json")
    sess = requests.Session()
    sess.cookies.update(get_cookie_jar())

    log(f"=== 云原神签到开始（直连） uid={cfg['uid']} ===")

    # 1) 会话校验（Cookie 失效时提前告知，但先尝试完整链路）
    ok = verify_session(sess, cfg)
    if not ok:
        log("⚠ webVerifyForGame 返回登录失效 —— Cookie 可能已过期")

    # 2) webLogin 换 combo_token
    wl = web_login(sess, cfg)
    if not wl or not wl["combo_token"]:
        log("✗ webLogin 失败（retcode != 0）：Cookie 已失效，请用浏览器兜底重新登录后更新 cookies.json")
        return 1
    log(f"✓ webLogin OK open_id={wl['open_id']}")

    # 3) gamer/api/login（核心：今日登录赠时）
    res = cg_login(sess, cfg, wl["open_id"], wl["combo_token"])
    retcode = res.get("retcode")
    if retcode == 0:
        log("✓ gamer/api/login OK（今日登录已记录）")
    elif retcode == -100:
        log("✗ gamer/api/login 登录失效（-100）：Cookie 过期或 si 失效，"
            "请用浏览器兜底方案重新登录，并按 README 更新 cookies.json / config.json 的 si")
        return 1
    else:
        log(f"✗ gamer/api/login 失败 retcode={retcode} message={res.get('message')}")
        return 1

    # 4) wallet 留档
    w = get_wallet(sess, cfg, wl["open_id"], wl["combo_token"])
    if w.get("retcode") == 0:
        ft = (w.get("data") or {}).get("free_time") or {}
        log(f"✓ wallet OK 免费时长={ft.get('free_time')} 分钟 / "
            f"今日已发={ft.get('send_freetime')} / 上限={ft.get('free_time_limit')}")
    else:
        log(f"✗ wallet 读取失败 retcode={w.get('retcode')}（不影响签到结果）")

    log("=== 云原神签到完成（直连） ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
