# WorkBuddy 每日自动签到

基于 [88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) 方案搭建，并做了**持久化增强**（token 自动续期 + OAuth 轮询登录 + JWT 字段补全）。纯 Python 标准库零依赖，每日签到 100 积分 + 成长中心全套任务。

## 账号信息

- 每日签到奖励：100 积分（连续签到有额外奖励）

## 文件清单

| 文件 | 说明 |
|---|---|
| `signin.py` | 主脚本（上游 1801 行 + 持久化增强 290 行 = 2091 行） |
| `workbuddy-desktop.info` | 账号凭证（accessToken / refreshToken / uid / nickname / expiresAt），**敏感** |
| `run_checkin.sh` | 每日签到运行入口（封装环境变量，签到 + 成长中心） |
| `relogin.sh` | 凭证过期后重新授权登录入口 |
| `signin.log` | 签到日志（追加） |

## 在上游基础上做的持久化增强

上游脚本的短板：**不处理 refreshToken，accessToken 过期后必须重新登录桌面端**。我们做了以下增强：

### 1. token 自动续期（核心）
- 新增 `refresh_access_token()`：调用 `POST /v2/plugin/auth/token/refresh`（头 `X-Refresh-Token`），用 refreshToken 换新 accessToken
- 新增 `save_session()`：原子回写凭据文件（临时文件 + os.replace，避免写一半损坏）
- 新增 `should_refresh()`：距过期 ≤24 小时（或无 expiresAt）时主动刷新
- **401 兜底**：请求层收到 401 时自动刷新 token 并重试一次，刷新失败才报认证错误
- refreshToken 是轮换链，每次刷新产生新值，自动回写，不会断链

### 2. OAuth 轮询登录命令 `login`
- 完全不依赖 WorkBuddy 桌面端，云电脑/服务器环境可自洽
- 流程：`POST /v2/plugin/auth/state?platform=desktop` 生成登录链接 → 浏览器打开登录 → 后台轮询 `GET /v2/plugin/auth/token?state=...`（每 5 秒，最多 5 分钟）→ 自动写凭据文件
- 自动从 JWT payload 解析补全 uid（sub）、nickname、expiresAt（轮询接口可能不返回这些字段）

### 3. accessToken 有效期
- 从 JWT 解析确认：**约 28 天**（exp - iat = 2419200 秒）
- 配合自动续期，理论上**永不过期**（只要 refreshToken 不被服务端作废）

## 使用方法

### 手动签到（签到 + 成长中心）
```bash
cd /home/user/Doubao/chats/38445668168009986/WorkBuddy签到
./run_checkin.sh
```

### 凭证过期后重新登录
当 refreshToken 也失效（用户改密码/踢设备/服务端作废）时：
```bash
./relogin.sh
```
脚本会打印 OAuth 登录链接，在任意浏览器打开完成登录，后台自动轮询捕获新凭证并覆盖保存。

### 单步调试命令
```bash
python3 signin.py status   # 仅查签到状态
python3 signin.py claim    # 仅领取签到（幂等）
python3 signin.py auto     # 签到 + 成长中心（默认）
python3 signin.py doctor   # 离线检查凭据格式
```
（以上命令需先 `export WORKBUDDY_AUTH_FILE=/path/to/workbuddy-desktop.info`，或直接用 run_checkin.sh）

## 签到原理（直连方案）

1. 脚本加载凭据文件（`WORKBUDDY_AUTH_FILE` 指向工作区）。
2. 主动刷新：若 accessToken 距过期 ≤24h，用 refreshToken 续期并回写。
3. 调用 `POST /v2/billing/meter/checkin-activity-status` 查询今日签到状态。
4. 若未签，调用 `POST /v2/billing/meter/daily-checkin` 领取积分。
5. 成长中心：派 Buddy 旅行、领任务、补登、连登奖励兑换、抽奖、开 Buddy 盲盒。
6. 401 时自动刷新 token 重试；当日已签则跳过。

接口域名：`https://copilot.tencent.com`（国内 CodeBuddy）

## 浏览器兜底方案

当直连方案完全失效（接口大幅变更、refreshToken 也失效且刷新失败）：
1. 运行 `./relogin.sh`，用浏览器打开 OAuth 链接重新登录授权。
2. 登录成功后凭证自动刷新，直连恢复。
3. 极端情况下可在浏览器手动打开 https://www.codebuddy.cn 登录后手动签到。

## 长期持久化保障

- ✅ **accessToken 自动续期**：距过期 24h 内主动刷新，401 兜底刷新，理论永不过期
- ✅ **refreshToken 轮换链自动回写**：原子写入，不会断链
- ✅ **OAuth 轮询登录**：完全不依赖桌面端，云电脑自洽
- ✅ **当日跳过**：已签账号零请求，减少被风控概率
- ✅ **所有文件在工作区**：过 12 点重置不丢失
- ⚠️ **唯一失效场景**：用户改密码、主动踢设备、或服务端作废 refreshToken——此时运行 `./relogin.sh` 重新登录即可

## 定时任务

- 任务名称：**WorkBuddy每日自动签到**
- 执行时间：每天 10:30（Asia/Shanghai）
- 执行内容：运行 `run_checkin.sh`（签到 + 成长中心），结果写入 `signin.log`
- 与「咸鱼单机」「云原神」「TRAE」三个签到任务同时段执行

## 安全提醒

- `workbuddy-desktop.info` 包含 accessToken 和 refreshToken，**请勿外传或提交到公开仓库**。
- 定时任务的 query 中不包含任何 token、密码或验证码。
- refreshToken 是轮换链，**禁止在多处同时刷新同一账号**（会导致链断）。

## 依赖

- Python 3.6+（标准库，无需 pip install 任何包）
- 网络可访问 `copilot.tencent.com` / `www.codebuddy.cn`
