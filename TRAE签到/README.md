# TRAE 每日自动签到

基于 [L0NE-6/Trae-AutoCheckin](https://github.com/L0NE-6/Trae-AutoCheckin) 方案搭建，纯 Python 标准库零依赖，支持 token 自动续期、9074 限流自动换设备号、当日跳过、多账号。

## 账号信息

- 产品线：Trae (IDE) 通用账号体系（Work 积分通用）
- 每日签到奖励：200 Work 专属积分（31 天有效期）

## 文件清单

| 文件 | 说明 |
|---|---|
| `trae_checkin.py` | 主签到脚本（上游，未修改） |
| `trae_credit_monitor.py` | 积分余额只读监控（上游，未修改） |
| `trae_sms_login.py` | 网页 OAuth 登录换 token（上游，未修改） |
| `trae_get_token.py` | 客户端 storage.json token 提取（备用，Linux 无客户端时不用） |
| `trae_sms_accounts.json` | 账号凭证（accessToken / refreshToken / uid / name），**敏感** |
| `device_identity.json` | 设备身份（ECDSA 密钥对 / device_id / machine_id），**敏感** |
| `device_identity.env` | 设备身份环境变量文件（被 run 脚本 source） |
| `device_private.pem` / `device_public.pem` | ECDSA P-256 密钥对原始文件 |
| `token_cache.json` | token 续期回写缓存（refreshToken 轮换链，自动维护） |
| `.trae_checkin_state.json` | 签到状态缓存（记录今日已签，自动维护） |
| `.trae_device_ids.json` | 设备号缓存（9074 自动换号用，自动维护） |
| `run_checkin.sh` | 每日签到运行入口（封装环境变量） |
| `run_monitor.sh` | 积分查询入口 |
| `relogin.sh` | 凭证过期后重新授权登录入口 |
| `checkin.log` | 签到日志（追加） |
| `monitor.log` | 积分查询日志（追加） |

## 使用方法

### 手动签到
```bash
cd /home/user/Doubao/chats/38445668168009986/TRAE签到
./run_checkin.sh
```

### 查询积分余额
```bash
./run_monitor.sh
```

### 凭证过期后重新登录
当 refreshToken 失效（续期失败、签到报认证错误）时：
```bash
./relogin.sh
```
脚本会打印授权 URL，用浏览器打开后完成手机号+验证码登录，登录成功自动回调并刷新 `trae_sms_accounts.json`。

## 定时任务

- 任务名称：**TRAE每日自动签到**
- 执行时间：每天 10:30（Asia/Shanghai）
- 执行内容：运行 `run_checkin.sh`，签到结果写入 `checkin.log` 并向用户汇报
- 与「咸鱼单机每日自动签到」「云原神每日自动签到」同时段执行

## 签到原理（直连方案）

1. 脚本加载 `TRAE_ACCOUNTS`（从 `trae_sms_accounts.json`）和设备身份（ECDSA 密钥）。
2. 调用 `POST /trae/api/v2/ug/checkin_credits/status` 查询今日签到状态。
3. 若未签，调用 `POST /trae/api/v2/ug/checkin_credits/claim` 领取积分。
4. accessToken 过期时，自动调用 `/trae/api/v3/oauth/ExchangeToken` 用 refreshToken 续期（带设备 ECDSA 签名证明），新 token 回写 `token_cache.json`。
5. 遇到 9074 限流（参与用户过多），自动生成全新设备号重签；仍失败则按账号记冷却（默认 55 分钟），冷却内零请求。
6. 当日已签则直接跳过，零请求。

## 浏览器兜底方案

当直连方案失败（接口大幅变更、token 完全失效且无法续期、风控升级等），使用云端浏览器手动兜底：

1. 用浏览器打开 https://www.trae.cn/ 并登录账号。
2. 进入 Trae Work，点击右下角头像 → 每日签到 → 领取。
3. 若登录态也失效，运行 `./relogin.sh` 重新走 OAuth 授权刷新凭证。

兜底操作由定时任务触发时的 agent 根据 `checkin.log` 中的失败原因判断执行，无需人工干预；极端情况下会提示用户接管浏览器完成验证。

## 长期持久化保障

- **refreshToken 链式续期**：每次续期产生新 refreshToken，旧值立即失效，脚本自动回写缓存，避免链断。
- **设备身份固定**：ECDSA 密钥对和 device_id 保存在工作区，续期签名始终同源，不会因设备变更导致 9074。
- **9074 自动换号**：设备号被服务端记住时自动换新，实测立刻成功。
- **当日跳过**：已签账号零请求，减少被风控概率。
- **所有文件在工作区**：工作区外环境过 12 点会重置，本目录所有产物（凭证/密钥/缓存/日志）均持久保留。

## 安全提醒

- `trae_sms_accounts.json`、`device_identity.json`、`device_private.pem` 包含敏感凭证，**请勿外传或提交到公开仓库**。
- 定时任务的 query 中不包含任何 token、密码或密钥。
- refreshToken 是轮换链，**禁止在多处同时刷新同一账号**（会导致链断）。
- 如需迁移到其他机器，需整体复制本目录，并确保新机器的网络出口不被 Trae 风控。

## 依赖

- Python 3.6+（标准库，无需 pip install 任何包）
- OpenSSL（仅首次生成设备密钥时需要，已生成后不再需要）
- 网络可访问 `api.trae.cn` / `www.trae.cn`
