# MiniMax Agent 浏览器兜底签到操作手册

## 概述
由于 `/minimax-cloud/api/` 所有接口均需要签名（invalid signature），直连方案暂不可用。
浏览器兜底通过 **Playwright 无头浏览器**操作页面 UI 完成签到，不依赖签名逆向，也不依赖 computer_use_tool。

## 签到入口
- 站点：https://agent.minimax.cn/
- 签到入口：左下角用户头像 → 点击展开菜单 → 「每日签到」→ 展开签到面板
- 签到面板显示：7天周期积分奖励，今日签到按钮
- **关键行为**：未签到时，签到面板会在页面加载后自动出现在左下角头像旁；已签到时面板不出现

## 自动化方案（Playwright）

### 脚本
- 主脚本：`signin_playwright.py`
- 入口：`run_checkin.sh`（直连失败后自动调用 Playwright）

### 原理
1. 从 `config.json` 读取 `_token`（JWT），作为 Cookie 注入浏览器，保持登录态
2. 打开 `https://agent.minimax.cn/`，等待页面加载
3. 用 JS 精确移除「MiniMax Code 产品焕新」弹窗（按 `aria-label` 定位）
4. 检测签到面板：
   - 未签到时面板自动出现 → 查找「签到得XXX」按钮并点击
   - 面板未出现 → 点击左下角头像 → 点击「每日签到」菜单项手动打开
   - 手动打开后仍无面板 → 视为今日已签到
5. 点击签到按钮后等待 3 秒，重新检测面板验证结果

### 依赖
- Python 包：`playwright`（已预装）
- Chromium：`/opt/vm/preinstall/ms-playwright/chromium-1169/chrome-linux/chrome`

### 登录态失效处理
如果 `_token` 过期（页面跳转到登录页），脚本返回失败。需要重新登录获取新 token：
1. 在浏览器中打开 https://agent.minimax.cn/ 完成登录
2. 从浏览器 Cookie 中复制 `_token` 值
3. 更新 `config.json` 中的 `token` 字段
4. token 有效期约 40 天

## 手动签到（应急）
如果自动化脚本失败，可手动完成：
1. 浏览器打开 https://agent.minimax.cn/ 并登录
2. 页面加载后，左下角会自动出现签到面板（未签到时）
3. 点击「签到得XXX」按钮完成签到
4. 或点击左下角头像 → 「每日签到」打开面板
