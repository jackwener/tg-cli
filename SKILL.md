---
name: tg-cli
description: CLI skill for Telegram — monitor group chats, search messages, AI analysis, send messages, and filter keywords from the terminal
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

A CLI tool for interacting with Telegram. Monitor group chats, search messages, send messages, filter by keywords, and generate AI summaries.

## Prerequisites

```bash
# Install (requires Python 3.10+)
uv tool install tg-cli
# Or: pip install tg-cli
```

## Authentication

Uses your Telegram account (MTProto). Built-in API credentials — just login with phone number.

```bash
tg chats              # First run: enter phone + verification code
tg whoami             # Check current user
```

## Command Reference

### Telegram Operations (`tg ...`)

```bash
tg chats                          # List joined chats
tg chats --type group             # Filter by type
tg whoami                         # Show current user info
tg whoami --json                  # JSON output
tg history CHAT -n 1000           # Fetch historical messages
tg sync CHAT                      # Incremental sync (only new)
tg sync-all                       # Sync ALL chats (single connection)
tg listen                         # Real-time listener
tg info CHAT                      # Chat details
tg send CHAT "Hello!"             # Send a message
```

### Search & Query

```bash
tg search "Rust"                     # Search stored messages
tg search "Rust" -c "牛油果" --json  # Filter by chat + JSON
tg filter "Rust,Golang,Java"         # Multi-keyword filter (today)
tg filter "招聘,remote" --hours 48   # Filter last N hours
tg stats                             # Message statistics per chat
tg top -c "牛油果" --hours 24        # Most active senders
tg timeline --by hour                # Activity bar chart
tg today                             # Today's messages by chat
```

### Data & AI

```bash
tg export CHAT -f json -o out.json   # Export messages
tg export CHAT --hours 24            # Export last 24 hours
tg purge CHAT -y                     # Delete stored messages
tg analyze CHAT --hours 24           # AI analysis (Claude)
tg summary                           # AI daily digest
```

## JSON Output

Major commands support `--json` for machine-readable output:

```bash
tg search "Rust" --json | jq '.[0].content'
tg whoami --json | jq '.username'
tg today --json | jq 'length'
tg filter "招聘" --hours 48 --json
```

## Common Patterns for AI Agents

```bash
# Quick daily workflow
tg sync-all                       # Sync everything
tg today                             # See today's messages
tg filter "Rust,Golang" --hours 24   # Filter job posts
tg summary                           # AI daily digest

# Search and export for analysis
tg search "招聘" -n 100 --json > jobs.json
tg filter "远程,remote,Web3" --hours 72 --json > filtered.json

# Send messages
tg send "GroupName" "Hello from CLI!"
```

## Verbose Mode

```bash
tg -v tg sync-all    # Debug logging for troubleshooting
tg -v stats          # See SQL queries and timing
```

## Error Handling

- Commands exit with code 0 on success, non-zero on failure
- Error messages are prefixed with ✗ or shown in red
- Chat names are fuzzy-matched (partial name works)
- `sync-all` gracefully skips chats that can't be found
