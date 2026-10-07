# MiniMax Agent 每日自动签到

## 概述
为 MiniMax Agent（https://agent.minimax.cn/）搭建每日自动签到系统，领取每日积分。

- 签到奖励：7天周期，第1-3/5-6天 800+400积分，第4/7天 2000+1000积分
- 执行时间：每天 10:30

## 文件结构
```
MiniMax签到/
├── config.json           # 登录态配置（token，权限600，不提交）
├── signin_direct.py      # 直连签到脚本（API需签名，暂不可用）
├── signin_playwright.py  # Playwright 无头浏览器签到（当前主用方案）
├── run_checkin.sh        # 签到运行入口（直连优先→Playwright兜底）
├── browser_fallback.md   # Playwright 方案说明文档
├── README.md             # 本文件
└── signin.log            # 签到日志（自动生成，不提交）
```

## 双方案说明

### 方案一：直连（暂不可用）
- `GET /minimax-cloud/api/v1/signin/status` — 查询签到状态
- `POST /minimax-cloud/api/v1/signin/claim` — 领取签到积分
- **限制**：所有 API 请求均需要签名（invalid signature），签名算法未破解
- 保留此脚本用于未来签名算法破解后切换

### 方案二：Playwright 无头浏览器（当前主用）
- 用 `_token`（JWT）作为 Cookie 注入浏览器，免登录打开页面
- 未签到时，签到面板会在页面加载后自动出现在左下角头像旁
- 直接点击「签到得XXX」按钮完成签到
- 已签到时面板不出现，脚本自动判断为「今日已签到」
- 不依赖签名逆向，不依赖云端浏览器（computer_use_tool），稳定可靠
- 依赖：Python `playwright` 包 + Chromium 浏览器

## 使用方法

### 手动运行
```bash
cd MiniMax签到
./run_checkin.sh
```

### 查看日志
```bash
cat signin.log
```

### 重新登录（token 过期时）
1. 浏览器打开 https://agent.minimax.cn/ 完成登录
2. 从浏览器 Cookie 中复制 `_token` 值
3. 更新 `config.json` 中的 `token` 字段
4. token 有效期约 40 天

## 定时任务
- 任务名：「MiniMax每日自动签到」
- 执行时间：每天 10:30
- 执行逻辑：运行 `run_checkin.sh` → 直连失败后自动切换 Playwright → 记录日志 → 汇报结果

## 安全提醒
- `config.json` 包含 token，权限已设为 600，不提交到 Git
- 不在日志或回复中泄露完整 token
- token 约 40 天过期，过期后需重新登录
