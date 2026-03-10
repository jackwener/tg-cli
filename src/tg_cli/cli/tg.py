"""Telegram subcommands — chats, history, sync, refresh, listen, info, whoami, status, send."""

import asyncio
import time

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..client import connect, fetch_history, get_chat_info, list_chats, listen
from ..console import console
from ..db import MessageDB
from ._chat import resolve_chat_id_or_print
from ._output import (
    default_structured_format,
    dump_structured,
    emit_structured,
    error_payload,
    structured_output_options,
    success_payload,
)
from ._sync import sync_all_dialogs, sync_chat_dialog


def _parse_chat(chat: str) -> str | int:
    """Parse a chat argument: return int if numeric, else the original string."""
    try:
        return int(chat)
    except ValueError:
        return chat


def _telegram_user_payload(me) -> dict[str, str | int]:
    """Normalize Telegram user info for structured agent output."""
    name = " ".join(part for part in [me.first_name, me.last_name] if part).strip()
    return {
        "id": me.id,
        "name": name,
        "username": me.username or "",
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "phone": me.phone or "",
    }


@click.group("tg")
def tg_group():
    """Telegram operations — connect, fetch, sync, listen."""
    pass


@tg_group.command("chats")
@click.option("--type", "chat_type", help="Filter by type: user, group, supergroup, channel")
@structured_output_options
def tg_chats(chat_type: str | None, as_json: bool, as_yaml: bool):
    """List joined Telegram chats."""

    async def _run():
        async with connect() as client:
            return await list_chats(client, chat_type)

    chats = asyncio.run(_run())
    if emit_structured(chats, as_json=as_json, as_yaml=as_yaml):
        return

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
@structured_output_options
def tg_history(chat: str, limit: int, as_json: bool, as_yaml: bool):
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
                        progress.update(task, description=f"Stored {count} messages...")

                    count = await fetch_history(
                        client, _parse_chat(chat), limit=limit, db=db, on_progress=on_progress
                    )
                return count

    count = asyncio.run(_run())
    payload = {"stored": count, "chat": chat}
    if emit_structured(payload, as_json=as_json, as_yaml=as_yaml):
        return
    console.print(f"\n[green]\u2713[/green] Stored {count} messages from {chat}")


@tg_group.command("sync")
@click.argument("chat")
@click.option("-n", "--limit", default=5000, help="Max messages per sync")
@structured_output_options
def tg_sync(chat: str, limit: int, as_json: bool, as_yaml: bool):
    """Incremental sync — fetch only new messages from CHAT."""

    async def _run():
        with MessageDB() as db:
            # Resolve chat_id to get last_msg_id
            chat_id = resolve_chat_id_or_print(db, chat, allow_missing=True)
            matches = db.find_chats(chat)
            if len(matches) > 1:
                resolve_chat_id_or_print(db, chat)
                return None
            last_id = db.get_last_msg_id(chat_id) if chat_id else 0
        if last_id:
            console.print(f"Syncing from msg_id > {last_id}...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task_id = progress.add_task(f"Syncing {chat}...", total=None)

            def on_progress(count: int):
                progress.update(task_id, description=f"Stored {count} new messages...")

            return await sync_chat_dialog(chat, limit=limit, on_progress=on_progress)

    count = asyncio.run(_run())
    if count is None:
        return
    payload = {"synced": count, "chat": chat}
    if emit_structured(payload, as_json=as_json, as_yaml=as_yaml):
        return
    console.print(f"\n[green]\u2713[/green] Synced {count} new messages from {chat}")


@tg_group.command("sync-all")
@click.option("-n", "--limit", default=5000, help="Max messages per chat")
@structured_output_options
def tg_sync_all(limit: int, as_json: bool, as_yaml: bool):
    """Sync all currently available Telegram dialogs with a single connection."""

    async def _run():
        on_chat_done = None
        if not as_json and not as_yaml:
            console.print("Syncing all available chats...")

            def _on_chat_done(name: str, new_count: int, total: int):
                if new_count > 0:
                    console.print(f"  [green]✓[/green] {name}: +{new_count} (total: {total})")
                else:
                    console.print(f"  [dim]✓ {name}: no new messages[/dim]")

            on_chat_done = _on_chat_done

        return await sync_all_dialogs(limit=limit, on_chat_done=on_chat_done)

    results = asyncio.run(_run())
    total_new = sum(results.values())
    payload = {"new_messages": total_new, "chats": len(results), "results": results}
    if emit_structured(payload, as_json=as_json, as_yaml=as_yaml):
        return
    console.print(f"\n[green]✓[/green] Synced {total_new} new messages across {len(results)} chats")


@tg_group.command("refresh")
@click.option("-n", "--limit", default=5000, help="Max messages per chat")
@structured_output_options
def tg_refresh(limit: int, as_json: bool, as_yaml: bool):
    """Refresh the local cache from all current Telegram dialogs."""

    async def _run():
        on_chat_done = None
        if not as_json and not as_yaml:
            console.print("Refreshing local cache...")

            def _on_chat_done(name: str, new_count: int, total: int):
                if new_count > 0:
                    console.print(f"  [green]✓[/green] {name}: +{new_count} (total: {total})")
                else:
                    console.print(f"  [dim]✓ {name}: no new messages[/dim]")

            on_chat_done = _on_chat_done

        return await sync_all_dialogs(limit=limit, on_chat_done=on_chat_done)

    results = asyncio.run(_run())
    total_new = sum(results.values())
    updated = [
        name
        for name, count in sorted(results.items(), key=lambda item: (-item[1], item[0]))
        if count > 0
    ]
    payload = {
        "new_messages": total_new,
        "chats": len(results),
        "updated_chats": updated,
        "results": results,
    }
    if emit_structured(payload, as_json=as_json, as_yaml=as_yaml):
        return

    console.print(f"\n[green]✓[/green] Refreshed {len(results)} chats, {total_new} new messages.")
    if updated:
        console.print(f"[dim]Most recently updated: {', '.join(updated[:5])}[/dim]")


@tg_group.command("listen")
@click.argument("chats", nargs=-1)
@click.option("--persist", is_flag=True, help="Reconnect automatically if the connection drops")
@click.option(
    "--retry-seconds",
    default=5,
    show_default=True,
    help="Reconnect delay when using --persist",
)
def tg_listen(chats: tuple[str, ...], persist: bool, retry_seconds: int):
    """Real-time listener for new messages. Optionally specify CHATS to filter."""
    parsed: list[str | int] | None = None
    if chats:
        parsed = []
        for c in chats:
            try:
                parsed.append(int(c))
            except ValueError:
                parsed.append(c)

    async def _run_once():
        async with connect() as client:
            return await listen(client, chats=parsed)

    while True:
        try:
            result = asyncio.run(_run_once())
        except click.ClickException:
            raise
        except Exception as exc:
            if not persist:
                raise
            console.print(
                f"[yellow]Listener disconnected: {exc}. Retrying in {retry_seconds}s...[/yellow]"
            )
            time.sleep(retry_seconds)
            continue

        if not persist or result == "stopped":
            break

        console.print(
            f"[yellow]Listener disconnected. Reconnecting in {retry_seconds}s...[/yellow]"
        )
        time.sleep(retry_seconds)


@tg_group.command("info")
@click.argument("chat")
@structured_output_options
def tg_info(chat: str, as_json: bool, as_yaml: bool):
    """Show detailed info about CHAT."""

    async def _run():
        async with connect() as client:
            return await get_chat_info(client, _parse_chat(chat))

    info = asyncio.run(_run())
    if not info:
        console.print(f"[red]Could not find chat: {chat}[/red]")
        return

    if emit_structured(info, as_json=as_json, as_yaml=as_yaml):
        return

    table = Table(title="Chat Info", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    for k, v in info.items():
        table.add_row(k, v)

    console.print(table)


@tg_group.command("whoami")
@structured_output_options
def tg_whoami(as_json: bool, as_yaml: bool):
    """Show current logged-in user info."""

    async def _run():
        async with connect() as client:
            me = await client.get_me()
            return me

    fmt = default_structured_format(as_json=as_json, as_yaml=as_yaml)
    try:
        me = asyncio.run(_run())
    except Exception as exc:
        if fmt is not None:
            click.echo(dump_structured(error_payload("auth_error", str(exc)), fmt=fmt))
            raise SystemExit(1) from None
        raise click.ClickException(str(exc)) from exc

    info = _telegram_user_payload(me)

    if emit_structured(success_payload({"user": info}), as_json=as_json, as_yaml=as_yaml):
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


@tg_group.command("status")
@structured_output_options
def tg_status(as_json: bool, as_yaml: bool):
    """Show Telegram authentication status."""

    async def _run():
        async with connect() as client:
            me = await client.get_me()
            return {
                "authenticated": True,
                "id": me.id,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or "",
            }

    fmt = default_structured_format(as_json=as_json, as_yaml=as_yaml)
    try:
        info = asyncio.run(_run())
    except Exception as exc:
        if fmt is not None:
            click.echo(dump_structured(error_payload("auth_error", str(exc)), fmt=fmt))
            raise SystemExit(1) from None
        raise click.ClickException(str(exc)) from exc

    user = {key: value for key, value in info.items() if key != "authenticated"}
    if emit_structured(
        success_payload({"authenticated": True, "user": user}),
        as_json=as_json,
        as_yaml=as_yaml,
    ):
        return

    name = " ".join(part for part in [info["first_name"], info["last_name"]] if part).strip()
    console.print(f"[green]✓[/green] Authenticated as [bold]{name or info['id']}[/bold]")
    if info["username"]:
        console.print(f"[dim]@{info['username']}[/dim]")


@tg_group.command("send")
@click.argument("chat")
@click.argument("message")
@structured_output_options
def tg_send(chat: str, message: str, as_json: bool, as_yaml: bool):
    """Send a MESSAGE to CHAT (name, username, or numeric ID)."""

    async def _run():
        async with connect() as client:
            msg = await client.send_message(_parse_chat(chat), message)
            return msg

    msg = asyncio.run(_run())
    payload = {"sent": True, "msg_id": msg.id, "chat": chat}
    if emit_structured(payload, as_json=as_json, as_yaml=as_yaml):
        return
    console.print(f"[green]\u2713[/green] Message sent (id: {msg.id})")
