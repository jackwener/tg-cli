"""Data commands — export, purge."""

import json

import click
from rich.console import Console

from ..db import MessageDB

console = Console()


@click.group("data", invoke_without_command=True)
def data_group():
    """Data management commands (registered at top-level)."""
    pass


@data_group.command("export")
@click.argument("chat")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("-o", "--output", "output_file", help="Output file path")
@click.option("--hours", type=int, help="Only export last N hours")
def export(chat: str, fmt: str, output_file: str | None, hours: int | None):
    """Export messages from CHAT to text or JSON."""
    db = MessageDB()
    chat_id = db.resolve_chat_id(chat)

    if chat_id is None:
        console.print(f"[red]Chat '{chat}' not found in database.[/red]")
        db.close()
        return

    if hours:
        msgs = db.get_recent(chat_id=chat_id, hours=hours, limit=100000)
    else:
        msgs = db.get_recent(chat_id=chat_id, hours=None, limit=100000)
    db.close()

    if not msgs:
        console.print(f"[yellow]No messages found for '{chat}'.[/yellow]")
        return

    if fmt == "json":
        content = json.dumps(msgs, ensure_ascii=False, indent=2, default=str)
    else:
        lines = []
        for msg in msgs:
            ts = (msg.get("timestamp") or "")[:19]
            sender = msg.get("sender_name") or "Unknown"
            text = msg.get("content") or ""
            lines.append(f"[{ts}] {sender}: {text}")
        content = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]✓[/green] Exported {len(msgs)} messages to {output_file}")
    else:
        console.print(content)


@data_group.command("purge")
@click.argument("chat")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def purge(chat: str, yes: bool):
    """Delete all stored messages for CHAT."""
    db = MessageDB()
    chat_id = db.resolve_chat_id(chat)

    if chat_id is None:
        console.print(f"[red]Chat '{chat}' not found in database.[/red]")
        db.close()
        return

    if not yes:
        count = db.count(chat_id)
        if not click.confirm(f"Delete {count} messages from chat {chat_id}?"):
            db.close()
            return

    deleted = db.delete_chat(chat_id)
    db.close()
    console.print(f"[green]✓[/green] Deleted {deleted} messages")
