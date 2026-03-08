# tg-cli


Uses your own Telegram account (MTProto), not a Bot. Built-in API credentials — just install and login.

## Quick Start

```bash
# Install
pip install tg-cli
# or
uv tool install tg-cli

# Login (first run) — enter phone + verification code
tg chats

# Check who you are
tg whoami

# Sync all groups at once
tg sync-all

# See today's messages
tg today

# Search
tg search "Rust"

# Filter by keywords (comma-separated, OR logic)
tg filter "Rust,Golang,Java" --hours 48

# Send a message
tg send "GroupName" "Hello!"
```

## Commands

### Telegram (`tg ...`)

| Command | Description |
|---------|-------------|
| `tg chats [--type group]` | List joined chats |
| `tg whoami [--json]` | Show current user info |
| `tg history CHAT -n 1000` | Fetch historical messages |
| `tg sync CHAT` | Incremental sync (only new messages) |
| `tg sync-all` | Sync ALL chats in database (single connection) |
| `tg listen [CHATS...]` | Real-time listener |
| `tg info CHAT` | Show detailed chat info |
| `tg send CHAT "msg"` | Send a message |

### Query

| Command | Description |
|---------|-------------|
| `search KEYWORD [-c NAME] [--json]` | Search stored messages |
| `filter KEYWORDS [-c NAME] [--hours N]` | Multi-keyword filter (OR logic, highlighted) |
| `stats` | Show message statistics |
| `top [-c NAME] [--hours 24]` | Most active senders |
| `timeline [-c NAME] [--by day\|hour]` | Message activity bar chart |
| `today [-c NAME] [--json]` | Show today's messages by chat |


| Command | Description |
|---------|-------------|
| `export CHAT [-f text\|json] [-o FILE] [--hours N]` | Export messages |
| `purge CHAT [-y]` | Delete stored messages |

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable debug logging |
| `--version` | Show version |

## Setup

```bash
pip install tg-cli  # or: uv tool install tg-cli
tg chats         # login with phone number
```

That's it. Built-in API credentials work for most users.

**Optional:**
- Custom API credentials: set `TG_API_ID` and `TG_API_HASH` env vars
- Custom data dir: `DATA_DIR=./data` or `DB_PATH=./data/messages.db`

## Architecture

```
src/tg_cli/
├── cli/
│   ├── main.py      # Click CLI entry point + verbose
│   ├── tg.py        # Telegram: chats, sync, whoami, send
│   ├── query.py     # Query: search, filter, stats, today, top, timeline
├── client.py        # Telethon client (connection reuse)
├── config.py        # Config (built-in API credentials)
├── db.py            # SQLite message store
```

## License

MIT
