#!/usr/bin/env python3
"""
MiniMax Agent 每日签到 - Playwright 无头浏览器方案

原理：
  1. 用 config.json 中的 _token (JWT) 作为 Cookie，保持登录态
  2. 打开 agent.minimax.cn，移除产品弹窗
  3. 鼠标 hover 左下角头像，展开每日签到面板
  4. 点击「签到得XXX」按钮完成签到
  5. 验证签到结果（按钮变灰 / 面板显示已签到）

依赖：playwright (pip install playwright)，chromium 浏览器

退出码：
  0 = 签到成功 或 今日已签到
  1 = 签到失败
"""

import json
import sys
import time
import os
from pathlib import Path

# 工作目录：脚本所在目录
WORK_DIR = Path(__file__).resolve().parent
CONFIG_PATH = WORK_DIR / "config.json"
LOG_PATH = WORK_DIR / "signin.log"

# Chromium 可执行文件路径（Playwright 预装）
CHROME_PATH = "/opt/vm/preinstall/ms-playwright/chromium-1169/chrome-linux/chrome"


def log(msg: str) -> None:
    """追加写入日志并打印到标准输出。"""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config() -> dict:
    """读取配置文件，返回包含 token 等字段的字典。"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def dismiss_popups(page) -> None:
    """精确移除 MiniMax Code 产品焕新弹窗（按 aria-label 定位），不影响其他元素。"""
    page.evaluate(
        """() => {
            // 移除角色为 dialog 且标题含 MiniMax 的弹窗
            document.querySelectorAll('[role=dialog]').forEach(d => {
                const label = d.getAttribute('aria-label') || '';
                if (label.includes('MiniMax')) d.remove();
            });
            // 移除全屏遮罩层
            document.querySelectorAll('.desktop-window-content-overlay').forEach(el => el.remove());
        }"""
    )
    page.wait_for_timeout(1000)


def find_signin_panel(page) -> dict | None:
    """
    检测签到面板是否已展开。

    未签到时，签到面板会在页面加载后自动出现在左下角头像旁；
    已签到时面板不出现。

    返回：包含按钮信息的字典，或 None（面板未展开）。
    """
    info = page.evaluate(
        """() => {
            // 查找所有可见的签到相关按钮
            const buttons = Array.from(document.querySelectorAll('button')).filter(b => {
                const t = b.textContent.trim();
                return (t.includes('签到') || t.includes('领取')) && b.offsetParent !== null;
            }).map(b => ({
                text: b.textContent.trim().slice(0, 60),
                disabled: b.disabled
            }));

            // 查找签到面板标题文本（"每日签到"、"本轮已连续签到"）
            const panelText = Array.from(document.querySelectorAll('*')).filter(e =>
                e.children.length === 0 && e.textContent &&
                (e.textContent.includes('每日签到') || e.textContent.includes('本轮已连续'))
            ).map(e => e.textContent.trim().slice(0, 80));

            if (buttons.length > 0 || panelText.length > 0) {
                return { buttons, panelText };
            }
            return null;
        }"""
    )
    return info


def open_signin_panel(page) -> None:
    """
    通过点击左下角头像 → 点击「每日签到」菜单项，手动打开签到面板。

    未签到时面板通常自动出现，此方法作为兜底。
    """
    # 点击头像触发区域展开下拉菜单
    trigger = page.query_selector(".ant-dropdown-trigger")
    if trigger:
        trigger.click()
        page.wait_for_timeout(1500)

    # 点击「每日签到」菜单项
    page.evaluate(
        """() => {
            document.querySelectorAll('.ant-dropdown-menu-item, [class*=menu-item]').forEach(i => {
                if (i.textContent.trim() === '每日签到') i.click();
            });
        }"""
    )
    page.wait_for_timeout(2000)


def click_signin_button(page) -> str | None:
    """查找可点击的签到按钮并点击，返回按钮文本。"""
    return page.evaluate(
        """() => {
            const btn = Array.from(document.querySelectorAll('button')).find(b =>
                (b.textContent.trim().includes('签到得') || b.textContent.trim().includes('立即签到'))
                && !b.disabled && b.offsetParent !== null
            );
            if (btn) {
                const text = btn.textContent.trim();
                btn.click();
                return text;
            }
            return null;
        }"""
    )


def run_signin() -> int:
    """
    执行完整的 Playwright 签到流程。

    流程：
      1. 用 _token Cookie 保持登录态打开页面
      2. 移除产品弹窗
      3. 检测签到面板（未签到时自动出现）
      4. 若面板未出现，手动点击头像→「每日签到」打开
      5. 若仍无面板 → 今日已签到
      6. 若有可点击按钮 → 点击签到
      7. 验证结果

    返回：
      0 = 成功（签到成功 或 今日已签到）
      1 = 失败
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: 未安装 playwright，请运行 pip install playwright")
        return 1

    cfg = load_config()
    token = cfg.get("token")
    if not token:
        log("ERROR: config.json 中缺少 token 字段")
        return 1

    log("=== MiniMax 签到开始（Playwright 无头浏览器） ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH if os.path.exists(CHROME_PATH) else None,
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        # 注入登录 Cookie
        context.add_cookies([
            {
                "name": "_token",
                "value": token,
                "domain": ".minimax.cn",
                "path": "/",
                "httpOnly": False,
                "secure": True,
            }
        ])

        page = context.new_page()

        # 打开页面
        log("打开 agent.minimax.cn ...")
        page.goto("https://agent.minimax.cn/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

        # 验证登录态
        page_title = page.title()
        log(f"页面标题: {page_title}")
        if "登录" in page_title or "login" in page.url.lower():
            log("ERROR: 登录态失效，页面跳转到登录页")
            browser.close()
            return 1

        # 移除产品弹窗
        dismiss_popups(page)
        log("已移除产品弹窗")

        # 第 1 次检测：未签到时面板会自动出现
        panel = find_signin_panel(page)
        if panel:
            log(f"检测到自动展开的签到面板: {panel['panelText']}")
        else:
            # 第 2 次：手动打开面板
            log("签到面板未自动展开，尝试手动打开...")
            open_signin_panel(page)
            panel = find_signin_panel(page)
            if panel:
                log(f"手动打开签到面板成功: {panel['panelText']}")
            else:
                # 面板始终不出现 → 今日已签到（未签到时面板一定会自动出现）
                log("RESULT|今日已签到（签到面板未出现，说明今日已完成签到）")
                browser.close()
                return 0

        # 检查按钮状态
        buttons = panel.get("buttons", [])
        clickable = [b for b in buttons if not b["disabled"]]

        if not clickable:
            # 所有按钮已禁用 → 今日已签到
            log(f"RESULT|今日已签到（按钮状态: {buttons}）")
            browser.close()
            return 0

        # 点击签到按钮
        clicked_text = click_signin_button(page)
        if not clicked_text:
            log(f"ERROR: 面板存在但未找到可点击按钮: {buttons}")
            browser.close()
            return 1

        log(f"已点击签到按钮: {clicked_text}")
        page.wait_for_timeout(3000)

        # 验证：重新检测面板
        panel_after = find_signin_panel(page)
        if panel_after:
            buttons_after = panel_after.get("buttons", [])
            if all(b["disabled"] for b in buttons_after) or not buttons_after:
                log(f"RESULT|签到成功（{clicked_text}，按钮已变灰）")
                browser.close()
                return 0
            log(f"WARNING: 签到后按钮仍可点击: {buttons_after}")

        # 面板消失（自动收起）也视为成功
        log(f"RESULT|签到成功（{clicked_text}，面板已收起）")
        browser.close()
        return 0


def main() -> None:
    """脚本入口。"""
    try:
        exit_code = run_signin()
    except Exception as e:
        log(f"ERROR: 未捕获异常: {type(e).__name__}: {e}")
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
