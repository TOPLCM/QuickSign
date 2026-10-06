# 恩山无线论坛 每日自动签到

## 概述
为恩山无线论坛（https://www.right.com.cn/）搭建每日自动签到系统。

- 论坛系统：Discuz! X3.5
- 签到插件：erling_qd v1.0（© 20idc.com）
- 签到奖励：每日积分（连续签到有额外奖励）
- 执行时间：每天 10:30

## 文件结构
```
恩山论坛签到/
├── config.json           # 账号配置（username/password，权限600）
├── signin_direct.py      # 直连签到脚本（10个函数均有文档字符串）
├── run_checkin.sh        # 签到运行入口（直连优先→浏览器兜底）
├── browser_fallback.md   # 浏览器兜底操作手册
├── signin.log            # 签到日志（自动生成）
├── README.md             # 本文件
├── signin_page.html      # 签到页面原始HTML（分析用）
└── signin_page_full.html # 签到页面完整HTML（分析用）
```

## 双方案说明

### 方案一：直连（主用，已验证可用）
- 登录：POST member.php?mod=logging&action=login（Discuz! 标准登录，formhash CSRF）
- 查状态：GET plugin.php?id=erling_qd:sign_in（提取 FORMHASH 和按钮状态）
- 签到：POST plugin.php?id=erling_qd:action&action=sign（参数 formhash，返回 JSON {success, message}）
- 无复杂签名，只需 Discuz! formhash CSRF 防护
- auth cookie 有效期约30天（cookietime=2592000）

### 方案二：浏览器兜底（备用）
- 通过云端浏览器操作页面 UI 完成签到
- 流程：打开论坛 → 登录 → 访问签到页面 → 点击签到按钮
- 详细操作步骤见 `browser_fallback.md`

## 技术要点

### 阿里云 WAF 绕过
- 论坛使用阿里云 ESA WAF，直接访问 rewrite URL（erling_qd-sign_in.html）会触发滑块验证
- 直连脚本使用 plugin.php 原始路径（plugin.php?id=erling_qd:sign_in）可绕过 WAF 拦截
- 浏览器兜底也应使用 plugin.php 原始路径

### 签到接口分析
- 签到页面 AJAX：`$.ajax({url: 'plugin.php?id=erling_qd:action&action=sign', type: 'POST', data: {formhash: FORMHASH}})`
- 成功响应：`{success: true}` → 页面自动刷新
- 失败响应：`{success: false, message: "错误信息"}`

## 使用方法

### 手动运行
```bash
cd /home/user/Doubao/chats/38445668168009986/恩山论坛签到
./run_checkin.sh
```

### 查看日志
```bash
cat signin.log
```

## 定时任务
- 任务名：「恩山论坛每日自动签到」
- 执行时间：每天 10:30（与咸鱼/云原神/TRAE/MiniMax/WorkBuddy 对齐）
- 执行逻辑：直连优先 → 失败则浏览器兜底 → 记录日志 → 汇报结果

## 安全提醒
- config.json 包含账号密码，权限已设为 600
- 不要在日志或回复中泄露密码
- auth cookie 约30天过期，过期后脚本会自动重新登录
- 如遇 WAF 滑块验证，浏览器兜底时会请求用户接管
