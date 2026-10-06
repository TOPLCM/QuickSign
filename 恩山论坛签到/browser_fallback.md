# 恩山无线论坛 浏览器兜底签到操作手册

## 概述
直连脚本失败时（如 WAF 拦截、登录异常），通过云端浏览器操作页面 UI 完成签到。

## 签到入口
- 站点：https://www.right.com.cn/forum/forum.php
- 签到页面：https://www.right.com.cn/forum/plugin.php?id=erling_qd:sign_in
- 首页导航：顶部菜单 →「已签到」链接（erling_qd-sign_in.html）

## 操作步骤（cron 执行时按此操作）

### 1. 打开论坛并检查登录态
```
bu.navigate("https://www.right.com.cn/forum/forum.php")
bu.wait_for_load(timeout=15)
```
检查登录态：
- 页面顶部显示用户名或「退出」链接 → 已登录
- 显示「登录」「注册」按钮 → 未登录

### 2. 未登录时的登录流程
1. 点击顶部「登录」按钮，打开登录弹窗
2. 在用户名输入框填入 config.json 中的 username
3. 在密码输入框填入 password
4. 勾选「下次自动登录」（如有）
5. 点击「登录」按钮
6. 如出现阿里云 WAF 滑块验证 → **调用 interaction.request_action 请求用户接管**
7. 登录成功后确认顶部显示用户名

### 3. 打开签到页面
直接访问签到页面（避免 rewrite URL 被 WAF 拦截）：
```
bu.navigate("https://www.right.com.cn/forum/plugin.php?id=erling_qd:sign_in")
bu.wait_for_load(timeout=15)
```

### 4. 检查签到状态并签到
签到页面中找到 `#signin-btn` 按钮：
- 按钮显示「已签到」且 disabled → 今日已签到，任务成功
- 按钮显示「签到」且可点击 → 点击完成签到
  ```python
  bu.click(signin_button_ref)
  time.sleep(3)
  # 页面会自动刷新，确认按钮变为「已签到」
  ```
- 签到页面被 WAF 拦截（显示阿里云滑块验证）→ 请求用户接管完成验证后重试

### 5. 记录结果
将执行结果追加写入 signin.log：
```
[YYYY-MM-DD HH:MM:SS] BROWSER_FALLBACK 签到成功/今日已签到/失败原因
```

## 注意事项
- 阿里云 WAF 可能拦截 rewrite URL（erling_qd-sign_in.html），使用 plugin.php 原始路径更稳定
- 签到按钮点击后页面会自动刷新（AJAX 成功后 location.reload()）
- 签到统计：今日积分、连续签到天数、总签到天数
- Discuz! auth cookie 有效期约 30 天（cookietime=2592000）
- 浏览器会话可能过期（BU_SESSION_STALE），先调用 bu.resync()
