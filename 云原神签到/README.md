# 云原神每日自动签到

为 https://ys.mihoyo.com/cloud/ 实现每日自动签到（每日登录网页自动获得 15 分钟云游戏时长）。

## 签到机制

云原神网页加载时，在登录态有效的前提下会**自动**完成登录链并记录「今日登录」、发放当日赠时，
无需任何手动点击。登录链（已通过抓包与逆向确认）：

```
webVerifyForGame           会话校验（可选步骤，提前发现 Cookie 失效）
  └─ combo/granter/login/webLogin      换 combo_token（登录态来自 Cookie ltoken_v2/ltuid_v2）
       └─ gamer/api/login              云游戏登录（核心：记录今日登录 → 发赠时）
            └─ wallet/wallet/get       读取免费时长，留档确认
```

服务端按「每日首次登录」发放赠时，接口幂等：重复调用 `gamer/api/login` 返回 `retcode=0`，
不会重复发放，可安全每日多次运行。

## 文件清单

| 文件 | 用途 |
|---|---|
| `signin_direct.py` | 直连方案：HTTP API 重放登录链，无需浏览器 |
| `browser_fallback.py` | 浏览器兜底方案：打开页面自动签到；登录态丢失时提示人工接管 |
| `cookies.json` | 登录态 Cookie（HttpOnly，含 ltoken_v2/ltuid_v2 等 19 条，来自浏览器 CDP 导出） |
| `config.json` | 站点/账号/设备常量/si 缓存（**含明文密码，勿外传**） |
| `signin.log` | 运行日志（追加） |
| `ref_js/` | 主应用/登录 SDK JS 源码参考（web.b959658b.js、combo-web.182d5437.js 等） |

## 直连方案（signin_direct.py）

每日由定时任务触发；也可手动运行：

```bash
python3 signin_direct.py
```

输出示例（signin.log）：

```
✓ webLogin OK open_id=313878000
✓ gamer/api/login OK（今日登录已记录）
✓ wallet OK 免费时长=261 分钟 / 今日已发=0 / 上限=600
```

### 失效处理

| 症状 | 原因 | 处理 |
|---|---|---|
| `webLogin 失败（retcode != 0）` / `-100` | Cookie 过期 | 运行浏览器兜底重新登录后自动更新 cookies.json |
| `gamer/api/login -100` 且 Cookie 有效 | `config.json` 中 `si` 过期 | 浏览器打开一次云原神页面，从网络请求 `x-rpc-combo_token` 提取新 `si` 字段更新 config.json |

## 浏览器兜底方案（browser_fallback.py）

在 browser-use 环境（`computer_use_tool` plane="bu"）中执行：

```bash
python3 browser_fallback.py
```

- 打开云原神页面 → 等待登录链自动完成（约 14 秒）→ 检测到主界面（含「免费时长/AID」）即成功，
  并自动导出最新 Cookie 覆盖 `cookies.json`；
- 检测到登录界面（短信/密码登录、验证码）→ 保持页面停留，**人工接管**浏览器完成
  滑块 / 图标点击 / 短信验证码，接管成功后脚本自动导出 Cookie；
- 直连方案失效时由定时任务自动切换到此方案；登录态恢复后直连继续优先使用。

### 人工接管步骤

1. 定时任务运行兜底方案时会弹出接管请求；用户接管浏览器；
2. 若出现「请拖动滑块完成拼图」：手动拖动滑块；
3. 若出现「请在下图依次点击」：按提示依次点击图标；
4. 若出现「请输入短信验证码」：点击「获取验证码」→ 输入手机收到的验证码 → 「下一步」；
5. 进入主界面（看到 AID/免费时长）后交回控制权，脚本自动导出 Cookie。

## 定时任务

- 任务名：**云原神每日自动签到**
- 触发：每日 10:30（与咸鱼单机签到错峰）
- query 不含任何密码 / Cookie / 验证码（安全约束）
- 运行逻辑：优先直连 `signin_direct.py`；失败则执行浏览器兜底；兜底需人工接管时通知用户

## 安全提醒

- `config.json` 含**明文密码**，请勿外传或提交到公开仓库；
- `cookies.json` 等效于登录凭证，同样妥善保管；
- 定时任务 query 中不写入任何敏感信息。
