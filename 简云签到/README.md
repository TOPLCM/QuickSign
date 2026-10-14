# 简云每日自动签到

## 概述
为简云（https://www.jianidc.com/）搭建每日自动签到系统，领取优惠券。

- 签到奖励：累计签到解锁优惠券（3元/5元减免券、9折折扣券等）
- 执行时间：每天 10:30
- 登录方式：邮箱密码（无需验证码）

## 文件结构
```
简云签到/
├── config.json           # 账号配置（权限600，不提交）
├── signin_direct.py      # 直连签到脚本
├── run_checkin.sh        # 签到运行入口
├── browser_fallback.md   # 浏览器兜底操作手册
├── README.md             # 本文件
└── signin.log            # 签到日志（自动生成，不提交）
```

## 方案说明

### 直连方案（当前主用）
- GET /login 获取 CSRF token
- POST /login?action=email 邮箱密码登录（无需验证码）
- GET 签到页从内联JS的 initialSummary 提取签到状态
- 未签到时 POST /addons?_plugin=90&_controller=index&_action=checkin 完成签到
- 签到后重新获取状态验证

### 浏览器兜底
- 直连失败时按 browser_fallback.md 手动操作
- 邮箱登录无需验证码，流程简单

## 接口说明

| 接口 | 方法 | 用途 |
|------|------|------|
| /login | GET | 获取CSRF token |
| /login?action=email | POST | 邮箱登录（email, password, token） |
| /addons?_plugin=90&_controller=index&_action=signin | GET | 签到页（含状态数据） |
| /addons?_plugin=90&_controller=index&_action=checkin | POST | 执行签到 |

## 使用方法

### 手动运行
```bash
cd 简云签到
./run_checkin.sh
```

### 查看日志
```bash
cat signin.log
```

## 安全提醒
- config.json 包含账号密码，权限已设为 600，不提交到 Git
- 不在日志或回复中泄露密码
- 登录态基于 JWT cookie，每次运行重新登录
