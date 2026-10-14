# 简云浏览器兜底操作手册

## 适用场景
直连签到失败（网络错误、接口变更、登录异常等）时，使用浏览器手动完成签到。

## 操作步骤

### 1. 登录
浏览器访问：https://www.jianidc.com/login
- 选择「邮箱登录」
- 输入邮箱和密码
- 点击「登录」（邮箱登录无需验证码）

### 2. 进入签到页
登录后自动跳转到控制台，点击左侧边栏的「每日签到」，或直接访问：
https://www.jianidc.com/addons?_plugin=90&_controller=index&_action=signin

### 3. 完成签到
- 页面显示「每日签到领优惠券」
- 点击签到按钮（今日未签到时按钮可点击）
- 签到成功后显示「签到成功，本月已累计签到X天」
- 日历中今日日期标记为「已签」

## 签到奖励
- 累计第1天：3元减免券
- 累计第3天：5元减免券
- 累计第7天：5元减免券
- 累计第14天：通用9折折扣券
- 每月1日重新累计

## 接口说明（供自动化参考）

| 步骤 | 方法 | 接口 | 说明 |
|------|------|------|------|
| 登录页 | GET | /login | 获取CSRF token |
| 登录 | POST | /login?action=email | email, password, token |
| 签到页 | GET | /addons?_plugin=90&_controller=index&_action=signin | 含initialSummary状态数据 |
| 签到 | POST | /addons?_plugin=90&_controller=index&_action=checkin | 空body，返回JSON |
