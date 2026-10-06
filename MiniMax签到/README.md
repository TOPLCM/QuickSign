# MiniMax Agent 每日自动签到

## 概述
为 MiniMax Agent（https://agent.minimax.cn/）搭建每日自动签到系统，领取每日积分。

- 签到奖励：7天周期，第1-3/5-6天 800+400积分，第4/7天 2000+1000积分
- 执行时间：每天 10:30

## 文件结构
```
MiniMax签到/
├── config.json           # 登录态配置（token/账号/密码，权限600）
├── signin_direct.py      # 直连签到脚本（status查询可用，claim待签名补全）
├── run_checkin.sh        # 签到运行入口（直连优先→浏览器兜底）
├── browser_fallback.md   # 浏览器兜底操作手册
├── analysis.md           # 接口分析文档
├── signin.log            # 签到日志（自动生成）
├── README.md             # 本文件
└── agent_js/             # 页面JS chunk（用于签名分析）
```

## 双方案说明

### 方案一：直连（当前部分可用）
- `GET /minimax-cloud/api/v1/signin/status` — 查询签到状态
- `POST /minimax-cloud/api/v1/signin/claim` — 领取签到积分
- **限制**：所有 API 请求均需要签名（invalid signature），签名算法待补全
- 登录态：Cookie `_token`（JWT，约40天有效，至2026-11-15）

### 方案二：浏览器兜底（当前主用）
- 通过云端浏览器操作页面 UI 完成签到
- 流程：打开页面 → 检查登录态 → hover用户头像 → 每日签到 → 点击签到按钮
- 不依赖签名逆向，可靠稳定
- 详细操作步骤见 `browser_fallback.md`

## 使用方法

### 手动运行
```bash
cd /home/user/Doubao/chats/38445668168009986/MiniMax签到
./run_checkin.sh
```

### 查看日志
```bash
cat signin.log
```

### 重新登录（token过期时）
1. 打开 https://agent.minimax.cn/
2. 走账号密码登录流程（使用 config.json 中配置的账号密码）
3. 完成腾讯防水墙滑块验证
4. 登录成功后，更新 config.json 中的 token

## 定时任务
- 任务名：「MiniMax每日自动签到」
- 执行时间：每天 10:30
- 执行逻辑：直连优先 → 失败则浏览器兜底 → 记录日志 → 汇报结果

## 待完成项
- [ ] 补全 POST /claim 签名算法（用 CDP 拦截页面内部请求分析）
- [ ] 直连方案完整可用后，切换为直连优先

## 安全提醒
- config.json 包含账号密码和 token，权限已设为 600
- 不要在日志或回复中泄露完整 token、密码
- token 约40天过期，过期后需重新登录
- 滑块验证无法自动完成，需用户接管
