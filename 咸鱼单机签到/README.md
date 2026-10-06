# 咸鱼单机 每日自动签到系统

目标站点：https://www.xianyudanji.gg（ripro-v2 主题，WordPress）

## 系统构成（双方案：直连为主，浏览器兜底）

| 文件 | 作用 |
|---|---|
| `signin_direct.py` | **直连方案（主路径）**：纯 HTTP 请求完成登录+签到，无需浏览器 |
| `config.json` | 配置：站点、账号、密码、Cookie/日志路径、重试次数（**含明文密码，请勿外传**） |
| `cookies.json` | 登录后自动生成的 WordPress 认证 Cookie 缓存（有效期约 14 天，到期自动重新登录） |
| `signin.log` | 每次执行结果日志（追加写入） |
| `README.md` | 本文档 |

定时任务（cron）：每天 10:30 触发 → 先跑直连脚本；直连失败时由执行端用云端浏览器（computer_use_tool / plane=bu）走登录+签到兜底。

## 直连方案原理（已逆向并实测验证）

站点登录被一道"滑块验证码"（自定义插件，非腾讯官方验证码）保护，无图片缺口、只做轨迹行为分析：

1. GET 首页 → 从内联脚本 `rscConfig` 取滑块验证码 nonce（每次页面加载都变化）
2. POST `admin-ajax.php` `action=rsc_get_token` → 拿到验证 token
3. 生成拟人化拖动轨迹（快速起步+缓速收尾+微抖动+偶发回退），POST `action=rsc_verify` → 服务器会话标记验证通过
4. POST `action=user_login`（username/password/rememberme=1）→ 拿到 `wordpress_logged_in_*` Cookie（14 天）
5. GET `/user` → 从「每日签到」按钮提取 `data-nonce`
6. POST `action=user_qiandao&nonce=...` → 完成签到；若已签到返回「今日已签到」，幂等安全

## 手动运行

```bash
python3 /home/user/Doubao/chats/38445668168009986/咸鱼单机签到/signin_direct.py
```

- 退出码 `0` = 成功（签到成功 或 今日已签到）；`1` = 失败（登录被拒/验证码最终失败/页面结构变化）
- 输出格式 `RESULT|摘要`，日志在 `signin.log`

## 浏览器兜底操作手册（直连失败时由执行端按此执行）

1. `bu.navigate("https://www.xianyudanji.gg/")`，点击页头「登录」按钮（`.login-btn`）打开登录弹窗
2. 填 `input[name="username"]` 与 `input[name="password"]`（密码从 `config.json` 读取，不写入任何输出）
3. 用 `bu.js` 读取 `.rsc-slider` 的 `getBoundingClientRect()`，换算为视口 0-1000 归一化坐标；用 `bu.drag` 从滑块起点拖到 `.rsc-container` 轨道右端；等待 `window.is_qq_captcha_verify === true`
4. 点击「立即登录」（`button` 含文本"立即登录"），等待页面刷新；确认页头不再有「登录」链接
5. `bu.navigate("https://www.xianyudanji.gg/user")`，检查 `.go-user-qiandao` 按钮：
   - 已 disabled 或文案为「今日已签到」→ 今日已签到，成功
   - 可点击 → 点击完成签到，等待成功提示
   - 页面出现登录弹窗 → 登录态丢失，报告失败
6. 结果追加写入 `signin.log`

## 长期可用性保障

- **Cookie 复用**：`wordpress_logged_in_*` 14 天有效期内直接复用，脚本自动判断过期并重新登录
- **验证码容错**：直连最多重试 6 次，每次轨迹随机化；仍失败则浏览器兜底（真实鼠标拖动，轨迹天然拟人）
- **幂等**：当天已签到再执行会返回「今日已签到」，不会产生副作用
- **兜底**：若站点改动 AJAX 接口导致直连失效，浏览器兜底（纯 UI 操作）仍可工作；修复直连需同步更新 `signin_direct.py` 中的 action 名/nonce 提取逻辑（改动点集中在 `parse_nonce`、`login`、`sign_in`）

## 管理

- 修改执行时间：告知助手调整定时任务即可（如改为 08:00）
- 修改账号密码：编辑 `config.json` 的 `username`/`password`，并删除 `cookies.json` 强制重新登录
- 查看历史：`tail -50 signin.log`
- 暂停/恢复/删除任务：告知助手即可
