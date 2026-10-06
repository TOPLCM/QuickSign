# 原神每日签到（基于 MiyoQian）

## 概述
基于开源项目 [MiyoQian（米游签）](https://github.com/Marchen-orz/MiyoQian) 改造，专为米游社《原神》每日社区签到。

- 项目：MiyoQian v0.1.0
- 签到游戏：原神（genshin）
- 登录方式：米游社 APP 扫码登录
- 执行时间：每天 10:30

> 原始项目 README 见 `README.original.md`

## 文件结构
```
原神签到/
├── config.yaml              # 配置文件（只启用原神，关闭云游戏/米游币/内置调度）
├── data/
│   └── credentials.yaml     # 登录凭证（cookie/stoken，敏感信息）
├── logs/
│   └── miyouqian.log        # 签到日志
├── miyouqian/               # 项目核心代码
├── main.py                  # CLI 入口
├── run_checkin.sh           # 签到运行入口（包装脚本）
├── README.md                # 本文件
├── README.original.md       # 原项目完整文档
├── pyproject.toml           # 项目依赖
├── uv.lock                  # 依赖锁定
└── .venv/                   # Python 虚拟环境
```

## 双方案说明

### 方案一：CLI 直连（主用，已验证可用）
- 调用 `uv run python main.py run --game genshin`
- 自动完成：获取绑定角色 → 查询签到状态 → 执行签到 → 输出奖励
- 不启动 Web 服务，适合 cron 定时触发
- 凭证有效期：米游社 cookie/stoken 通常较长，过期后需重新扫码

### 方案二：浏览器兜底（备用）
- 如 CLI 模式失败（凭证过期、接口变更等），可通过浏览器手动签到
- 米游社签到页面：https://bbs.mihoyo.com/ys/
- 登录后进入「我的」→ 签到页面手动签到

## 使用方法

### 手动运行
```bash
cd /home/user/Doubao/chats/38445668168009986/MiyoQian
./run_checkin.sh
```

### 查看配置摘要
```bash
uv run python main.py show
```

### 查看日志
```bash
cat logs/miyouqian.log
```

### 重新扫码登录（凭证过期时）
```bash
uv run python main.py login --account main
# 用米游社 APP 扫描生成的二维码
```

## 定时任务
- 任务名：「米游社原神每日签到」
- 执行时间：每天 10:30
- 执行逻辑：运行 run_checkin.sh → 记录日志 → 汇报结果

## 技术要点

### 为什么用 CLI 模式而不是 Web 控制台？
- Web 控制台需要程序持续运行，当前环境是任务触发式，不适合长期驻留
- CLI 模式每次触发执行一次，更可靠、更省资源
- 关闭了项目内置调度器（schedule.enable: false），统一用外部 cron

### 配置裁剪
- 只启用 `game_checkin: true`（游戏社区签到）
- 关闭 `cloud_game_checkin`（云游戏签到，已有独立的云原神签到）
- 关闭 `bbs_tasks`（米游币任务，避免风控）
- 游戏只选 `genshin`（原神）
- 关闭内置调度器，用外部 cron

### 依赖
- Python 3.11+，httpx、PyYAML、qrcode、loguru、pyfiglet、Pillow
- 包管理用 uv，虚拟环境在 .venv/

## 安全提醒
- `data/credentials.yaml` 包含登录凭证（cookie/stoken），请勿公开
- 扫码登录二维码有效期短（约2分钟），需及时扫描
- 米游社凭证过期后需重新扫码登录
- 使用自动化工具存在账号风控风险，请低频使用
