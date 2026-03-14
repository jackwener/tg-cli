"""Data commands — export, purge."""

import click

from ..console import console
from ..db import MessageDB
from ._chat import resolve_chat_id_or_print
from ._output import default_structured_format, dump_structured, error_payload


@click.group("data")
def data_group():
    """Data management commands (registered at top-level)."""


@data_group.command("export")
@click.argument("chat")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json", "yaml"]), default="text")
@click.option("-o", "--output", "output_file", help="Output file path")
@click.option("--hours", type=int, help="Only export last N hours")
def export(chat: str, fmt: str, output_file: str | None, hours: int | None):
    """Export messages from CHAT to text, JSON, or YAML."""
    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat_id is None:
            return

        if hours:
            msgs = db.get_recent(chat_id=chat_id, hours=hours, limit=100000)
        else:
            msgs = db.get_recent(chat_id=chat_id, hours=None, limit=100000)

    if not msgs:
        structured_fmt = (
            fmt
            if fmt in {"json", "yaml"}
            else default_structured_format(as_json=False, as_yaml=False)
        )
        if structured_fmt in {"json", "yaml"} and output_file is None:
            payload = error_payload("no_messages", f"No messages found for '{chat}'.")
            click.echo(dump_structured(payload, fmt=structured_fmt))
            raise SystemExit(1) from None
        console.print(f"[yellow]No messages found for '{chat}'.[/yellow]")
        return

    if fmt in {"json", "yaml"}:
        content = dump_structured(msgs, fmt=fmt)
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
    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat_id is None:
            return

        if not yes:
            count = db.count(chat_id)
            if not click.confirm(f"Delete {count} messages from chat {chat_id}?"):
                return

        deleted = db.delete_chat(chat_id)
    console.print(f"[green]✓[/green] Deleted {deleted} messages")
