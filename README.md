# QuickSign · 快签

> 让 AI Agent 帮你完成每日签到。支持挂载在豆包、千问、OpenClaw 等具备 Agent 能力的工具的定时任务上。

## 支持的平台

| 平台 | 网址 | 登录方式 | 直连 | 浏览器兜底 | 持久化 |
|---|---|---|---|---|---|
| 咸鱼单机 | [xianyudanji.gg](https://www.xianyudanji.gg/) | 账号密码+滑块 | ✅ | ✅ | 约30天 |
| 云原神 | [ys.mihoyo.com/cloud](https://ys.mihoyo.com/cloud/) | 账号密码+验证码 | ✅ | ✅ | 约30天 |
| TRAE | [trae.cn](https://www.trae.cn/) | 网页授权 | ✅ | - | **长期**（token自动续期） |
| WorkBuddy | [workbuddy.cn](https://www.workbuddy.cn/) | 微信扫码 | ✅ | - | **长期**（token自动续期） |
| MiniMax Agent | [agent.minimax.cn](https://agent.minimax.cn/) | 账号密码+滑块 | ⚠️ | ✅ | 约40天 |
| 恩山论坛 | [right.com.cn](https://www.right.com.cn/) | 账号密码 | ✅ | ✅ | 约30天 |
| 原神（米游社） | [bbs.mihoyo.com/ys](https://bbs.mihoyo.com/ys/) | APP扫码 | ✅ | - | 约15-30天 |

## 快速开始（3步）

### 第1步：告诉 AI 你要签到哪个平台
对 AI 说："帮我搭建 XX 平台的每日自动签到"

### 第2步：完成首次登录
根据平台不同，登录方式分为三类：

- **账号密码登录**（咸鱼单机/云原神/恩山论坛/MiniMax）：告诉 AI 账号和密码即可，遇到滑块/验证码 AI 会请你协助
- **扫码登录**（WorkBuddy/原神）：AI 生成二维码，用对应 APP 扫码即可
- **网页授权登录**（TRAE）：AI 打开授权页，你在浏览器中登录授权

### 第3步：AI 自动创建定时任务
登录完成后，AI 会保存登录态并创建每日定时任务（默认每天 10:30）。之后每天自动执行，无需干预。

## 持久化说明

### 长期可用（几乎不需要干预）
- **TRAE**、**WorkBuddy**：token 自动续期，登录态稳定

### 需要定期重新登录（约每月一次）
- **咸鱼单机**、**云原神**、**恩山论坛**：Cookie 约 30 天
- **MiniMax**：token 约 40 天
- **原神**：stoken 约 15-30 天

登录态过期时，AI 会通知你，说一声"重新登录 XX 平台"即可。

## 目录结构

```
QuickSign/
├── 咸鱼单机签到/          # 每个平台一个独立文件夹
│   ├── config.json        # 凭证配置（不提交Git，权限600）
│   ├── signin_direct.py   # 直连签到脚本
│   ├── run_checkin.sh     # 运行入口（AI调用这个）
│   ├── browser_fallback.md # 浏览器兜底方案
│   └── README.md          # 平台详细文档
├── 云原神签到/
├── TRAE签到/
├── WorkBuddy签到/
├── MiniMax签到/
├── 恩山论坛签到/
├── 原神签到/
├── .github/workflows/ci.yml  # 自动代码检查
├── licenses/              # 用到的开源项目许可证
├── LICENSE                # 本项目 MIT 许可证
└── .gitignore             # 敏感文件保护
```

## 开源致谢

本项目站在以下开源项目的肩膀上：

| 项目 | 用途 | 许可证 |
|---|---|---|
| [L0NE-6/Trae-AutoCheckin](https://github.com/L0NE-6/Trae-AutoCheckin) | TRAE 签到核心脚本（token续期/设备签名/9074换号） | MIT |
| [88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) | WorkBuddy 签到核心脚本（OAuth登录/成长中心任务） | MIT |
| [Marchen-orz/MiyoQian](https://github.com/Marchen-orz/MiyoQian) | 原神签到核心（米游社API/扫码登录），已裁剪为仅原神 | 未指定 |

各项目完整许可证见 [`licenses/`](./licenses/) 目录。

## 许可证

本项目采用 **MIT License** 开源，详见 [LICENSE](./LICENSE)。

## 设计理念

- **直连优先**：能用 API 直连的绝不依赖浏览器，稳定高效
- **浏览器兜底**：直连失败时自动切换浏览器方案，确保签到成功率
- **凭证本地化**：所有账号密码/token/cookie 只存在本地配置文件，不写进代码
- **AI 友好**：每个项目都有清晰的运行入口和失败处理逻辑，适合 Agent 定时调用
