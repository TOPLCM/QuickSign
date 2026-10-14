# 广西职业院校学生岗位实习每日自动签到

## 概述
为广西职业院校学生岗位实习管理系统搭建每日自动签到。

- 签到方式：API 直连 + 虚拟定位（传入公司坐标）
- 签到范围：公司坐标周围约 400 公里
- 执行时间：每天 10:30

## 文件结构
```
广西职业院校学生岗位实习签到/
├── config.json           # 账号配置（权限600，不提交）
├── signin_direct.py      # 直连签到脚本（含虚拟定位）
├── run_checkin.sh        # 签到运行入口
├── browser_fallback.md   # 浏览器兜底操作手册
├── README.md             # 本文件
└── signin.log            # 签到日志（自动生成，不提交）
```

## 方案说明

### 直连方案（主用）
- POST /api/studentapp/Login 账号密码登录，获取 JWT token
- POST /api/studentapp/Settings 获取签到设置（公司坐标、签到范围）
- POST /api/studentapp/Info 检查今日签到状态（SignToday 字段）
- 未签到时 POST /api/studentapp/Sign，传入 Lat/Lng 坐标完成签到
- 签到后重新获取状态验证

### 虚拟定位说明
本系统签到仅校验 API 请求中传入的经纬度参数，不校验真实 GPS 或 IP 位置。
config.json 中的 `sign_lat` 和 `sign_lng` 为签到坐标，可配置为任意坐标。
签到范围约 400 公里，同省坐标均可签到成功。

### 浏览器兜底
- 直连失败时按 browser_fallback.md 手动操作
- 浏览器签到需要授权定位权限

## 接口说明

| 接口 | 方法 | 用途 | 参数 |
|------|------|------|------|
| /api/studentapp/Login | POST | 登录 | UserName, Password |
| /api/studentapp/Info | POST | 学生信息/签到状态 | （空body，Bearer token） |
| /api/studentapp/Settings | POST | 签到设置 | （空body，Bearer token） |
| /api/studentapp/Sign | POST | 执行签到 | Lat, Lng（Bearer token） |
| /api/studentapp/SignLog | POST | 签到日志 | （空body，Bearer token） |

## 使用方法

### 手动运行
```bash
cd 广西职业院校学生岗位实习签到
./run_checkin.sh
```

### 修改签到定位
编辑 config.json 中的 `sign_lat` 和 `sign_lng` 字段，改为目标坐标。

### 查看日志
```bash
cat signin.log
```

## 安全提醒
- config.json 包含账号密码，权限已设为 600，不提交到 Git
- 不在日志或回复中泄露密码
- token 有效期 24 小时，每次运行重新登录获取
