---
name: tg-cli
description: CLI skill for Telegram to sync chats, search messages, filter keywords, and monitor groups from the terminal
author: jackwener
version: "1.0.0"
tags:
  - telegram
  - tg
  - chat
  - monitor
  - cli
---

# tg-cli Skill

CLI tool for Telegram — sync chats, search messages, filter keywords, send messages, and monitor groups.

## Prerequisites

```bash
# Install (requires Python 3.10+)
uv tool install kabi-tg-cli
# Or: pipx install kabi-tg-cli
```

## Authentication

Uses your Telegram account (MTProto). You must provide your own Telegram app credentials.

```bash
export TG_API_ID=123456
export TG_API_HASH=your_telegram_app_hash
# Or create a .env file with the same variables
tg chats              # First run: enter phone + verification code
tg whoami             # Check current user
```

## Command Reference

### Telegram Operations

```bash
tg chats                          # List joined chats
tg chats --type group             # Filter by type
tg status                         # Check auth/session status
tg status --yaml                  # Structured auth status
tg whoami                         # Show current user info
tg whoami --yaml                  # Preferred structured output for agents
tg history CHAT -n 1000           # Fetch historical messages
tg sync CHAT                      # Incremental sync (only new)
tg sync-all                       # Low-level sync for all current dialogs
tg refresh                        # Recommended daily refresh entrypoint
tg listen                         # Real-time listener
tg listen --persist               # Reconnect automatically for a near-live cache
tg info CHAT                      # Chat details
tg send CHAT "Hello!"             # Send a message
```

### Search & Query

```bash
tg search "Rust"                     # Search stored messages
tg search "Rust" -c "牛油果" --yaml  # Filter by chat + preferred YAML output
tg search "Rust|Golang" --regex      # Regex search
tg search "Rust" --sync-first --yaml # Refresh before querying
tg recent --hours 24 -n 20 --yaml    # Browse latest messages
tg recent --hours 24 --sync-first    # Refresh before browsing recent
tg filter "Rust,Golang,Java"         # Multi-keyword filter (today)
tg filter "招聘,remote" --hours 48   # Filter last N hours
tg today --sync-first                # Refresh before reading today's messages
tg stats --sync-first                # Refresh before aggregate stats
tg top -c "牛油果" --hours 24 --sync-first
tg timeline --by hour --sync-first   # Activity bar chart
```

### Data Management

```bash
tg export CHAT -f json -o out.json   # Export messages
tg export CHAT --hours 24            # Export last 24 hours
tg purge CHAT -y                     # Delete stored messages
```

## Structured Output

Major commands support `--json` and `--yaml` for machine-readable output.
AI agents should prefer `--yaml` unless a strict JSON parser is required:

```bash
tg search "Rust" --yaml
tg status --yaml
tg whoami --yaml
tg today --yaml
tg filter "招聘" --hours 48 --yaml
```

When stdout is not a TTY, `tg-cli` defaults to YAML automatically.
Use `OUTPUT=yaml|json|rich|auto` to override the default output mode.
All machine-readable output uses the envelope documented in [SCHEMA.md](./SCHEMA.md).

## Refresh Model

`tg-cli` is local-first. Query commands read from the local SQLite cache by default.

- Use `tg refresh` as the normal entrypoint before analysis.
- Use `--sync-first` when a single query should refresh before reading.
- Use `tg listen --persist` if you want a near-real-time local cache.
- Keep `tg sync-all` for lower-level scripts or schedulers.

## Common Patterns for AI Agents

```bash
# Quick daily workflow
tg refresh --yaml                    # Refresh everything
tg today --sync-first --yaml         # See today's messages
tg filter "Rust,Golang" --hours 24 --sync-first --yaml

# Search and export for analysis
tg search "招聘" -n 100 --yaml > jobs.yaml
tg filter "远程,remote,Web3" --hours 72 --yaml > filtered.yaml

# Send messages
tg send "GroupName" "Hello from CLI!"
```

## Debugging

```bash
tg -v sync-all       # Debug logging for troubleshooting
tg -v refresh        # See refresh behavior across dialogs
tg -v stats          # See SQL queries and timing
```

## Error Handling

- Commands exit with code 0 on success, non-zero on failure
- Error messages are prefixed with ✗ or shown in red
- Chat names are fuzzy-matched (partial name works)
- `refresh` and `sync-all` gracefully skip chats that can't be found

## Scheduling

Examples live in the repository:

- `examples/tg-refresh.cron`
- `examples/systemd/tg-refresh.service`
- `examples/systemd/tg-refresh.timer`

## Safety Notes

- Do not ask users to share phone numbers or verification codes in chat logs.
- Session data is stored locally and never uploaded.
