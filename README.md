# tg-cli

[![CI](https://github.com/jackwener/tg-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jackwener/tg-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kabi_tg_cli)](https://pypi.org/project/kabi-tg-cli/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Telethon-powered Telegram CLI for local-first sync, search, export, and agent-friendly retrieval.

[English](#english) | [中文](#中文)

## English

tg-cli uses your own Telegram account over MTProto, not the Bot API. It syncs messages into local
SQLite so humans and AI agents can query the same cache quickly with `--json` or `--yaml`.

## Features

- Sync Telegram dialogs into a local SQLite cache
- Search by keyword or regex, with chat, sender, and time filters
- Browse recent messages, today's messages, top senders, and timelines
- Export messages as text, JSON, or YAML
- Keep a near-real-time cache with `tg listen --persist`
- Prefer YAML for AI agents when a strict JSON parser is not required

## Installation

```bash
# Recommended: uv tool
uv tool install kabi-tg-cli

# Or: pipx / pip
pipx install kabi-tg-cli
pip install kabi-tg-cli
```

Install from GitHub:

```bash
uv tool install git+https://github.com/jackwener/tg-cli.git
```

Install from source:

```bash
git clone git@github.com:jackwener/tg-cli.git
cd tg-cli
uv sync --extra dev
```

## Quick Start

```bash
# Apply for your own Telegram app credentials first:
# https://my.telegram.org/apps
export TG_API_ID=123456
export TG_API_HASH=your_telegram_app_hash

# First login
tg chats

# Check the current account
tg whoami

# Refresh the local cache
tg refresh

# Read and search
tg today
tg recent --hours 24 --limit 20 --yaml
tg search "Rust" --hours 48
tg filter "Rust,Golang,remote" --hours 48 --sync-first --yaml

# Keep a near-real-time cache
tg listen --persist
```

## Refresh Model

tg-cli is intentionally local-first:

- `tg refresh` is the recommended daily entrypoint
- `tg sync-all` is the lower-level primitive for scripts and schedulers
- `--sync-first` refreshes before a single query
- `tg listen --persist` reconnects automatically for a near-live cache

Most query commands read from local SQLite, not directly from Telegram.

## Usage

```bash
# Sync
tg refresh
tg sync-all --yaml
tg sync "GroupName"

# Search / browse
tg search "Rust"
tg search "Rust|Golang" --regex --hours 72
tg recent --hours 24 --limit 20 --yaml
tg today --sync-first
tg top --hours 24 --sync-first
tg timeline --by hour --sync-first

# Export
tg export "GroupName" -f yaml -o messages.yaml

# Send
tg send "GroupName" "Hello!"
```

## Scheduling

If you do not want to run `tg refresh` manually, use a scheduler.

### cron

See [examples/tg-refresh.cron](https://github.com/jackwener/tg-cli/blob/main/examples/tg-refresh.cron).

### systemd user timer

See:

- [tg-refresh.service](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.service)
- [tg-refresh.timer](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.timer)

Typical flow:

```bash
mkdir -p ~/.config/systemd/user
cp examples/systemd/tg-refresh.service ~/.config/systemd/user/
cp examples/systemd/tg-refresh.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tg-refresh.timer
```

## Use as AI Agent Skill

tg-cli ships with a [`SKILL.md`](./SKILL.md) for AI agent integration.

### Agent Output Recommendation

If an AI agent needs machine-readable output, prefer `--yaml` first:

- `--yaml` is usually more token-efficient than pretty-printed JSON
- It is still easy to parse for agents and scripts
- Keep `--json` for `jq`, strict JSON-only tooling, or exact downstream schemas

Recommended agent workflow:

```bash
tg refresh --yaml
tg chats --yaml
tg recent --hours 24 --sync-first --yaml
tg search "keyword" --chat "GroupName" --sync-first --yaml
```

### Claude Code / Antigravity

```bash
mkdir -p .agents/skills
git clone git@github.com:jackwener/tg-cli.git .agents/skills/tg-cli
```

### OpenClaw / ClawHub

```bash
clawhub install tg-cli
```

## Troubleshooting

- `Missing TG_API_ID / TG_API_HASH`
  - Apply for your own app credentials at [my.telegram.org/apps](https://my.telegram.org/apps).
- `No messages today`
  - Run `tg refresh` first, or use `tg today --sync-first`.
- `Chat '...' not found in database`
  - Run `tg refresh` first, or use the numeric `chat_id` from `tg chats --yaml`.
- Repeatedly running `sync-all`
  - Prefer `tg refresh` for daily use, `--sync-first` for single queries, or `tg listen --persist`.

## 中文

`tg-cli` 是一个基于 Telethon 的 Telegram CLI。它不是 Bot API 工具，而是使用你自己的
Telegram 账号走 MTProto，把消息同步到本地 SQLite，方便你在终端里做搜索、筛选、导出，
也方便 AI agent 直接把它当作本地 retrieval tool 调用。

## 功能特性

- 同步 Telegram dialogs 到本地 SQLite
- 支持关键词搜索和 regex 搜索，可按 chat、sender、时间窗口过滤
- 支持 `recent`、`today`、`top`、`timeline` 等本地分析命令
- 支持导出为 text、JSON、YAML
- 支持 `tg listen --persist`，维持近实时本地缓存
- 支持 `--json` / `--yaml`，其中 AI agent 更推荐 `--yaml`

## 安装

```bash
# 推荐：uv tool
uv tool install kabi-tg-cli

# 或者：pipx / pip
pipx install kabi-tg-cli
pip install kabi-tg-cli
```

从 GitHub 安装：

```bash
uv tool install git+https://github.com/jackwener/tg-cli.git
```

从源码安装：

```bash
git clone git@github.com:jackwener/tg-cli.git
cd tg-cli
uv sync --extra dev
```

## 快速开始

```bash
# 先去 https://my.telegram.org/apps 申请自己的 app credentials
export TG_API_ID=123456
export TG_API_HASH=your_telegram_app_hash

# 首次登录
tg chats

# 检查当前账号
tg whoami

# 刷新本地缓存
tg refresh

# 浏览和搜索
tg today
tg recent --hours 24 --limit 20 --yaml
tg search "Rust" --hours 48
tg filter "招聘,remote,Web3" --hours 48 --sync-first --yaml

# 保持近实时缓存
tg listen --persist
```

## 刷新模型

`tg-cli` 是 local-first 设计：

- `tg refresh`
  - 推荐的日常入口，刷新所有当前 dialogs
- `tg sync-all`
  - 更底层的同步原语，适合脚本和调度器
- `--sync-first`
  - 单次查询前先刷新，适合 `today`、`search`、`recent`
- `tg listen --persist`
  - 常驻监听并自动重连，适合做近实时本地缓存

大多数查询命令默认读本地 SQLite，而不是每次都直接请求 Telegram。

## 使用示例

```bash
# 同步
tg refresh
tg sync-all --yaml
tg sync "群名"

# 搜索 / 浏览
tg search "Rust"
tg search "Rust|Golang" --regex --hours 72
tg recent --hours 24 --limit 20 --yaml
tg today --sync-first
tg top --hours 24 --sync-first
tg timeline --by hour --sync-first

# 导出
tg export "群名" -f yaml -o messages.yaml

# 发送消息
tg send "群名" "Hello!"
```

## 定时刷新

如果你不想每次手动执行 `tg refresh`，可以配合调度器。

### cron

参考 [examples/tg-refresh.cron](https://github.com/jackwener/tg-cli/blob/main/examples/tg-refresh.cron)。

### systemd user timer

参考：

- [tg-refresh.service](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.service)
- [tg-refresh.timer](https://github.com/jackwener/tg-cli/blob/main/examples/systemd/tg-refresh.timer)

典型流程：

```bash
mkdir -p ~/.config/systemd/user
cp examples/systemd/tg-refresh.service ~/.config/systemd/user/
cp examples/systemd/tg-refresh.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tg-refresh.timer
```

## 作为 AI Agent Skill 使用

`tg-cli` 自带 [`SKILL.md`](./SKILL.md)，方便 AI agent 自动学习并调用。

### Agent 输出建议

如果下游不是严格要求 JSON，优先使用 `--yaml`：

- `--yaml` 通常比 pretty-printed JSON 更省 token
- 对 agent 和脚本来说依然容易解析
- 只有在 `jq` 或严格 JSON-only tooling 场景下再优先用 `--json`

推荐的 agent 调用顺序：

```bash
tg refresh --yaml
tg chats --yaml
tg recent --hours 24 --sync-first --yaml
tg search "keyword" --chat "GroupName" --sync-first --yaml
```

### Claude Code / Antigravity

```bash
mkdir -p .agents/skills
git clone git@github.com:jackwener/tg-cli.git .agents/skills/tg-cli
```

### OpenClaw / ClawHub

```bash
clawhub install tg-cli
```

## 常见问题

- 缺少 `TG_API_ID` / `TG_API_HASH`
  - 去 [my.telegram.org/apps](https://my.telegram.org/apps) 申请自己的 app credentials
- `No messages today`
  - 先执行 `tg refresh`，或直接使用 `tg today --sync-first`
- `Chat '...' not found in database`
  - 先执行 `tg refresh`，或用 `tg chats --yaml` 找到准确的 `chat_id`
- 为什么总要先同步
  - 因为 `tg-cli` 是 local-first 设计，大多数查询命令默认读本地 SQLite，不直接查 Telegram

## License

Apache-2.0
