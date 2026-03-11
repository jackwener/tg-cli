"""Telegram client with connection reuse and entity caching."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User

from .config import (
    get_api_hash,
    get_api_id,
    get_session_path,
)
from .console import console
from .db import MessageDB

log = logging.getLogger(__name__)


def _get_sender_name(sender: User | Channel | Chat | None) -> str | None:
    if sender is None:
        return None
    if isinstance(sender, User):
        parts = [sender.first_name or "", sender.last_name or ""]
        name = " ".join(p for p in parts if p)
        return name or sender.username or str(sender.id)
    return getattr(sender, "title", None) or str(sender.id)


@asynccontextmanager
async def connect() -> AsyncGenerator[TelegramClient, None]:
    """Async context manager for Telegram client — single connection, reuse within scope."""
    api_id = get_api_id()
    api_hash = get_api_hash()

    c = TelegramClient(get_session_path(), api_id, api_hash)
    await c.start()
    try:
        yield c
    finally:
        await c.disconnect()


async def list_chats(
    client: TelegramClient,
    chat_type: str | None = None,
) -> list[dict]:
    """List all dialogs (chats/groups/channels) the user has joined."""
    results = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        t = "unknown"
        if isinstance(entity, User):
            t = "user"
        elif isinstance(entity, Chat):
            t = "group"
        elif isinstance(entity, Channel):
            t = "channel" if entity.broadcast else "supergroup"

        if chat_type and t != chat_type:
            continue

        results.append(
            {
                "id": dialog.id,
                "name": dialog.name,
                "type": t,
                "unread": dialog.unread_count,
            }
        )
    return results


async def get_chat_info(client: TelegramClient, chat: str | int) -> dict | None:
    """Get detailed information about a chat."""
    try:
        entity = await client.get_entity(chat)
    except Exception as e:
        log.debug("get_chat_info failed for %s: %s", chat, e)
        return None

    info: dict[str, str] = {}
    info["Title"] = (
        getattr(entity, "title", None) or getattr(entity, "first_name", "") or str(chat)
    )
    info["ID"] = str(entity.id)

    if isinstance(entity, User):
        info["Type"] = "User"
        info["Username"] = f"@{entity.username}" if entity.username else "—"
        info["Phone"] = entity.phone or "—"
    elif isinstance(entity, Chat):
        info["Type"] = "Group"
        info["Members"] = str(getattr(entity, "participants_count", "?"))
    elif isinstance(entity, Channel):
        info["Type"] = "Channel" if entity.broadcast else "Supergroup"
        info["Username"] = f"@{entity.username}" if entity.username else "—"
        try:
            from telethon.tl.functions.channels import GetFullChannelRequest

            full = await client(GetFullChannelRequest(entity))
            info["Members"] = str(full.full_chat.participants_count or "?")
            if full.full_chat.about:
                info["Description"] = full.full_chat.about[:200]
        except Exception as e:
            info["Members"] = "?"
            log.debug("Failed to get full channel info: %s", e)

    return info


async def fetch_history(
    client: TelegramClient,
    chat: str | int,
    limit: int = 1000,
    db: MessageDB | None = None,
    on_progress: Callable[[int], None] | None = None,
    min_id: int = 0,
) -> int:
    """Fetch historical messages from a chat and store them in the database.

    Args:
        client: Connected TelegramClient instance
        chat: Group name, username, or numeric ID
        limit: Max messages to fetch
        db: Database instance (creates one if None)
        on_progress: Callback invoked every batch with current count
        min_id: Only fetch messages with id > min_id (for incremental sync)
    """
    owns_db = db is None
    if db is None:
        db = MessageDB()

    try:
        entity = await client.get_entity(chat)
        chat_name = (
            getattr(entity, "title", None) or getattr(entity, "first_name", None) or str(chat)
        )
        chat_id = entity.id

        # Pre-fetch participants for sender name cache
        sender_cache: dict[int, str] = {}
        try:
            async for user in client.iter_participants(entity):
                sender_cache[user.id] = _get_sender_name(user) or str(user.id)
        except Exception as e:
            log.debug("Failed to pre-fetch participants: %s", e)

        batch: list[dict] = []
        inserted_count = 0
        BATCH_SIZE = 200

        async for msg in client.iter_messages(entity, limit=limit, min_id=min_id):
            if msg.text is None and msg.message is None:
                continue

            sender_name = sender_cache.get(msg.sender_id) if msg.sender_id else None
            content = msg.text or msg.message or ""
            ts = msg.date
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            batch.append(
                dict(
                    chat_id=chat_id,
                    chat_name=chat_name,
                    msg_id=msg.id,
                    sender_id=msg.sender_id,
                    sender_name=sender_name,
                    content=content,
                    timestamp=ts or datetime.now(timezone.utc),
                )
            )

            if len(batch) >= BATCH_SIZE:
                inserted_count += db.insert_batch(batch)
                batch.clear()
                if on_progress:
                    on_progress(inserted_count)

        # Flush remaining
        if batch:
            inserted_count += db.insert_batch(batch)

        return inserted_count
    finally:
        if owns_db:
            db.close()


async def sync_all(
    client: TelegramClient,
    db: MessageDB,
    limit_per_chat: int = 5000,
    on_chat_done: Callable[[str, int, int], None] | None = None,
) -> dict[str, int]:
    """Sync all chats in the database using a single connection.

    Args:
        on_chat_done: Callback(chat_name, new_count, total_in_chat)

    Returns:
        dict mapping chat_name to new message count
    """
    results: dict[str, int] = {}
    stored_chats = {c["chat_id"]: c for c in db.get_chats()}
    dialog_cache: dict[int, tuple[object, str]] = {}
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            dialog_cache[entity.id] = (entity, dialog.name)
    except Exception as e:
        log.debug("Failed to build dialog cache: %s", e)

    for chat_id, (entity, dialog_name) in dialog_cache.items():
        chat_info = stored_chats.get(chat_id, {})
        chat_name = chat_info.get("chat_name") or dialog_name or str(chat_id)
        last_id = db.get_last_msg_id(chat_id) or 0

        try:
            count = await fetch_history(
                client,
                entity,
                limit=limit_per_chat,
                db=db,
                min_id=last_id,
            )
            results[chat_name] = count
            if on_chat_done:
                on_chat_done(chat_name, count, chat_info.get("msg_count", 0) + count)
        except Exception as e:
            console.print(f"  [red]✗ {chat_name}: {e}[/red]")
            results[chat_name] = 0

    return results


async def listen(
    client: TelegramClient,
    chats: list[str | int] | None = None,
    db: MessageDB | None = None,
):
    """Real-time listen for new messages in specified chats (or all chats)."""
    owns_db = db is None
    if db is None:
        db = MessageDB()

    try:
        me = await client.get_me()
        console.print(f"[green]✓[/green] Logged in as [bold]{me.first_name}[/bold] ({me.phone})")
        console.print("[dim]Listening for messages... Press Ctrl+C to stop.[/dim]")

        @client.on(events.NewMessage(chats=chats))
        async def handler(event):
            msg = event.message
            chat = await event.get_chat()
            sender = await event.get_sender()

            chat_name = (
                getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown"
            )
            sender_name = _get_sender_name(sender)
            content = msg.text or msg.message or ""

            ts = msg.date
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            db.insert_message(
                chat_id=chat.id,
                chat_name=chat_name,
                msg_id=msg.id,
                sender_id=msg.sender_id,
                sender_name=sender_name,
                content=content,
                timestamp=ts or datetime.now(timezone.utc),
            )

            time_str = ts.strftime("%H:%M:%S") if ts else "??:??:??"
            console.print(
                f"[dim]{time_str}[/dim] [cyan]{chat_name}[/cyan] | "
                f"[bold]{sender_name or 'Unknown'}[/bold]: {content[:200]}"
            )

        status = "disconnected"
        try:
            await client.run_until_disconnected()
        except KeyboardInterrupt:
            status = "stopped"
            console.print("\n[yellow]Stopped listening.[/yellow]")
        finally:
            db_count = db.count()
            console.print(f"[green]Total messages in DB: {db_count}[/green]")
        return status
    finally:
        if owns_db:
            db.close()
