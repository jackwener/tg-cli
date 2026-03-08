"""Telegram subcommands — chats, history, sync, sync-all, listen, info, whoami, send."""

import asyncio

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..client import connect, fetch_history, get_chat_info, list_chats, listen, sync_all
from ..console import console
from ..db import MessageDB


def _parse_chat(chat: str) -> str | int:
    """Parse a chat argument: return int if numeric, else the original string."""
    try:
        return int(chat)
    except ValueError:
        return chat


@click.group("tg")
def tg_group():
    """Telegram operations — connect, fetch, sync, listen."""
    pass


@tg_group.command("chats")
@click.option("--type", "chat_type", help="Filter by type: user, group, supergroup, channel")
def tg_chats(chat_type: str | None):
    """List joined Telegram chats."""

    async def _run():
        async with connect() as client:
            return await list_chats(client, chat_type)

    chats = asyncio.run(_run())
    table = Table(title="Telegram Chats")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Unread", justify="right")

    for c in chats:
        table.add_row(str(c["id"]), c["name"], c["type"], str(c["unread"]))

    console.print(table)
    console.print(f"\nTotal: {len(chats)} chats")


@tg_group.command("history")
@click.argument("chat")
@click.option("-n", "--limit", default=1000, help="Max messages to fetch")
def tg_history(chat: str, limit: int):
    """Fetch historical messages from CHAT (name, username, or numeric ID)."""

    async def _run():
        with MessageDB() as db:
            async with connect() as client:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Fetching messages from {chat}...", total=None)

                    def on_progress(count: int):
                        progress.update(task, description=f"Fetched {count} messages...")

                    count = await fetch_history(
                        client, _parse_chat(chat), limit=limit, db=db, on_progress=on_progress
                    )
                return count

    count = asyncio.run(_run())
    console.print(f"\n[green]✓[/green] Stored {count} messages from {chat}")


@tg_group.command("sync")
@click.argument("chat")
@click.option("-n", "--limit", default=5000, help="Max messages per sync")
def tg_sync(chat: str, limit: int):
    """Incremental sync — fetch only new messages from CHAT."""

    async def _run():
        with MessageDB() as db:
            # Resolve chat_id to get last_msg_id
            chat_id = db.resolve_chat_id(chat)
            last_id = db.get_last_msg_id(chat_id) if chat_id else 0
            if last_id:
                console.print(f"Syncing from msg_id > {last_id}...")

            async with connect() as client:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task_id = progress.add_task(f"Syncing {chat}...", total=None)

                    def on_progress(count: int):
                        progress.update(task_id, description=f"Fetched {count} new messages...")

                    count = await fetch_history(
                        client,
                        _parse_chat(chat),
                        limit=limit,
                        db=db,
                        on_progress=on_progress,
                        min_id=last_id or 0,
                    )
                return count

    count = asyncio.run(_run())
    console.print(f"\n[green]✓[/green] Synced {count} new messages from {chat}")


@tg_group.command("sync-all")
@click.option("-n", "--limit", default=5000, help="Max messages per chat")
def tg_sync_all(limit: int):
    """Sync ALL chats in the database with a single connection."""

    async def _run():
        with MessageDB() as db:
            chats = db.get_chats()
            if not chats:
                console.print("[yellow]No chats in database. Run 'tg history' first.[/yellow]")
                return {}

            console.print(f"Syncing {len(chats)} chats...")

            async with connect() as client:
                def on_chat_done(name: str, new_count: int, total: int):
                    if new_count > 0:
                        console.print(f"  [green]✓[/green] {name}: +{new_count} (total: {total})")
                    else:
                        console.print(f"  [dim]✓ {name}: no new messages[/dim]")

                return await sync_all(
                    client, db, limit_per_chat=limit, on_chat_done=on_chat_done
                )

    results = asyncio.run(_run())
    total_new = sum(results.values())
    console.print(f"\n[green]✓[/green] Synced {total_new} new messages across {len(results)} chats")


@tg_group.command("listen")
@click.argument("chats", nargs=-1)
def tg_listen(chats: tuple[str, ...]):
    """Real-time listener for new messages. Optionally specify CHATS to filter."""
    parsed: list[str | int] | None = None
    if chats:
        parsed = []
        for c in chats:
            try:
                parsed.append(int(c))
            except ValueError:
                parsed.append(c)

    async def _run():
        async with connect() as client:
            await listen(client, chats=parsed)

    asyncio.run(_run())


@tg_group.command("info")
@click.argument("chat")
def tg_info(chat: str):
    """Show detailed info about CHAT."""

    async def _run():
        async with connect() as client:
            return await get_chat_info(client, _parse_chat(chat))

    info = asyncio.run(_run())
    if not info:
        console.print(f"[red]Could not find chat: {chat}[/red]")
        return

    table = Table(title="Chat Info", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    for k, v in info.items():
        table.add_row(k, v)

    console.print(table)


@tg_group.command("whoami")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tg_whoami(as_json: bool):
    """Show current logged-in user info."""
    import json

    async def _run():
        async with connect() as client:
            me = await client.get_me()
            return me

    me = asyncio.run(_run())

    info = {
        "id": me.id,
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "username": me.username or "",
        "phone": me.phone or "",
    }

    if as_json:
        click.echo(json.dumps(info, ensure_ascii=False, indent=2))
        return

    name = " ".join(p for p in [me.first_name, me.last_name] if p)
    table = Table(title=f"👤 {name}")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="green")
    table.add_row("ID", str(me.id))
    table.add_row("Name", name)
    if me.username:
        table.add_row("Username", f"@{me.username}")
    if me.phone:
        table.add_row("Phone", f"+{me.phone}")

    console.print(table)


@tg_group.command("send")
@click.argument("chat")
@click.argument("message")
def tg_send(chat: str, message: str):
    """Send a MESSAGE to CHAT (name, username, or numeric ID)."""

    async def _run():
        async with connect() as client:
            msg = await client.send_message(_parse_chat(chat), message)
            return msg

    msg = asyncio.run(_run())
    console.print(f"[green]✓[/green] Message sent (id: {msg.id})")
