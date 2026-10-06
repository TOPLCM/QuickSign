# MiniMax Agent 浏览器兜底签到操作手册

## 概述
由于 /minimax-cloud/api/ 所有接口均需要签名（invalid signature），直连方案暂不可用。
浏览器兜底通过操作页面 UI 完成签到，不依赖签名逆向。

## 签到入口
- 站点：https://agent.minimax.cn/
- 签到入口：左下角用户头像 → hover 展开菜单 → 「每日签到」→ hover 展开签到面板
- 签到面板显示：7天周期积分奖励，今日签到按钮

## 操作步骤（cron 执行时按此操作）

### 1. 打开页面并检查登录态
```
bu.navigate("https://agent.minimax.cn/")
bu.wait_for_load(timeout=15)
```
检查登录态：
- 页面左下角显示用户名 → 已登录
- 页面跳转到 account.minimax.cn 或显示登录按钮 → 未登录

### 2. 未登录时的登录流程（需用户接管）
如果未登录：
1. 打开 https://account.minimax.cn/unified-login
2. 选择「账号密码登录」tab
3. 输入账号和密码（从 config.json 读取）
4. 勾选用户协议
5. 点击「登录」按钮
6. 出现腾讯防水墙滑块验证 → **调用 interaction.request_action 请求用户接管**
7. 用户完成滑块后，等待登录成功跳转回 agent.minimax.cn
8. 确认左下角显示用户名

### 3. 打开签到面板
```python
# hover 左下角用户头像
bu.hover(user_avatar_ref)
# 等待菜单展开，找到「每日签到」
bu.find("每日签到")
# hover 「每日签到」展开签到面板
bu.hover(daily_signin_ref)
# 等待签到面板加载（约2秒）
time.sleep(2)
```

### 4. 检查签到状态并签到
签到面板中找到今日对应的签到按钮：
- 按钮显示「今日已签到」且 disabled → 今日已签到，任务成功
- 按钮显示「签到」或「领取」且可点击 → 点击完成签到
  ```python
  bu.click(signin_button_ref)
  time.sleep(2)
  # 确认按钮变为「今日已签到」
  ```
- 签到面板未加载或显示异常 → 刷新页面重试

### 5. 记录结果
将执行结果追加写入 signin.log：
```
[YYYY-MM-DD HH:MM:SS] BROWSER_FALLBACK 签到成功/今日已签到/失败原因
```

## 注意事项
- 浏览器会话可能过期（BU_SESSION_STALE），先调用 bu.resync()
- 滑块验证无法自动完成，必须请求用户接管
- 签到面板是 hover 展开，不是点击跳转
- 今日已签到时按钮 disabled，不会发请求
- Cookie _token 有效期约40天（至2026-11-15），过期后需重新登录
