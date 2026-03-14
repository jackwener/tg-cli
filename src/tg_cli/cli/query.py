"""Query commands — search, stats, top, timeline, today, filter."""

import asyncio
from collections import defaultdict

import click
from rich.table import Table

from ..console import console
from ..db import MessageDB
from ._chat import resolve_chat_id_or_print
from ._output import emit_error, emit_structured, structured_output_options
from ._sync import sync_all_dialogs, sync_chat_dialog


@click.group("query")
def query_group():
    """Query and analysis commands (registered at top-level)."""


def _maybe_sync_first(chat: str | None, sync_first: bool, sync_limit: int) -> None:
    """Refresh local cache before running a query command."""
    if not sync_first:
        return

    if chat:
        with MessageDB() as db:
            matches = db.find_chats(chat)
        if len(matches) > 1:
            return
        asyncio.run(sync_chat_dialog(chat, limit=sync_limit))
        return

    asyncio.run(sync_all_dialogs(limit=sync_limit))


@query_group.command("search")
@click.argument("keyword")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("-s", "--sender", help="Filter by sender name")
@click.option("--hours", type=int, help="Only search messages within N hours")
@click.option("--regex", "use_regex", is_flag=True, help="Treat KEYWORD as a regex pattern")
@click.option("--sync-first", is_flag=True, help="Refresh local cache before searching")
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@click.option("-n", "--limit", default=50, help="Max results")
@structured_output_options
def search(
    keyword: str,
    chat: str | None,
    sender: str | None,
    hours: int | None,
    use_regex: bool,
    sync_first: bool,
    sync_limit: int,
    limit: int,
    as_json: bool,
    as_yaml: bool,
):
    """Search messages by KEYWORD with optional chat, sender, and time filters."""
    import re

    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return
        try:
            if use_regex:
                results = db.search_regex(
                    keyword, chat_id=chat_id, sender=sender, hours=hours, limit=limit
                )
            else:
                results = db.search(
                    keyword,
                    chat_id=chat_id,
                    sender=sender,
                    hours=hours,
                    limit=limit,
                )
        except re.error as exc:
            if emit_error("invalid_regex", f"Invalid regex pattern: {exc}"):
                raise SystemExit(1) from None
            console.print(f"[red]Invalid regex pattern: {exc}[/red]")
            return

    if results and emit_structured(results, as_json=as_json, as_yaml=as_yaml):
        return

    if not results:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print("[yellow]No messages found.[/yellow]")
        return

    for msg in results:
        ts = (msg.get("timestamp") or "")[:19]
        sender = msg.get("sender_name") or "Unknown"
        chat_name = msg.get("chat_name") or ""
        content = (msg.get("content") or "")[:200]
        console.print(
            f"[dim]{ts}[/dim] [cyan]{chat_name}[/cyan] | "
            f"[bold]{sender}[/bold]: {content}"
        )

    filters = []
    if chat:
        filters.append(f"chat={chat}")
    if sender:
        filters.append(f"sender={sender}")
    if hours:
        filters.append(f"hours={hours}")
    if use_regex:
        filters.append("mode=regex")
    suffix = f" ({', '.join(filters)})" if filters else ""
    console.print(f"\n[dim]Found {len(results)} messages{suffix}[/dim]")


@query_group.command("recent")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("-s", "--sender", help="Filter by sender name")
@click.option("--hours", type=int, default=24, show_default=True, help="Only show last N hours")
@click.option(
    "--sync-first",
    is_flag=True,
    help="Refresh local cache before reading recent messages",
)
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@click.option("-n", "--limit", default=50, help="Max messages")
@structured_output_options
def recent(
    chat: str | None,
    sender: str | None,
    hours: int,
    sync_first: bool,
    sync_limit: int,
    limit: int,
    as_json: bool,
    as_yaml: bool,
):
    """Show recent messages for browsing without a keyword search."""

    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return
        msgs = db.get_recent(chat_id=chat_id, sender=sender, hours=hours, limit=limit)

    if msgs and emit_structured(msgs, as_json=as_json, as_yaml=as_yaml):
        return

    if not msgs:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print("[yellow]No recent messages found.[/yellow]")
        return

    for msg in msgs:
        ts = (msg.get("timestamp") or "")[:19]
        sender_name = msg.get("sender_name") or "Unknown"
        chat_name = msg.get("chat_name") or ""
        content = (msg.get("content") or "")[:200].replace("\n", " ")
        console.print(
            f"[dim]{ts}[/dim] [cyan]{chat_name}[/cyan] | "
            f"[bold]{sender_name}[/bold]: {content}"
        )

    filters = [f"hours={hours}"]
    if chat:
        filters.append(f"chat={chat}")
    if sender:
        filters.append(f"sender={sender}")
    console.print(f"\n[dim]Showing {len(msgs)} recent messages ({', '.join(filters)})[/dim]")


@query_group.command("stats")
@click.option("--sync-first", is_flag=True, help="Refresh local cache before calculating stats")
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@structured_output_options
def stats(sync_first: bool, sync_limit: int, as_json: bool, as_yaml: bool):
    """Show message statistics per chat."""
    _maybe_sync_first(None, sync_first, sync_limit)

    with MessageDB() as db:
        chats = db.get_chats()
        total = db.count()

    if emit_structured({"total": total, "chats": chats}, as_json=as_json, as_yaml=as_yaml):
        return

    table = Table(title=f"Message Stats (Total: {total})")
    table.add_column("Chat ID", style="dim")
    table.add_column("Chat Name", style="bold")
    table.add_column("Messages", justify="right")
    table.add_column("First Message", style="dim")
    table.add_column("Last Message", style="dim")

    for c in chats:
        table.add_row(
            str(c["chat_id"]),
            c["chat_name"] or "—",
            str(c["msg_count"]),
            (c["first_msg"] or "")[:19],
            (c["last_msg"] or "")[:19],
        )

    console.print(table)


@query_group.command("top")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("--hours", type=int, help="Only count messages within N hours")
@click.option(
    "--sync-first",
    is_flag=True,
    help="Refresh local cache before calculating top senders",
)
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@click.option("-n", "--limit", default=20, help="Top N senders")
@structured_output_options
def top(
    chat: str | None,
    hours: int | None,
    sync_first: bool,
    sync_limit: int,
    limit: int,
    as_json: bool,
    as_yaml: bool,
):
    """Show most active senders."""
    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return
        results = db.top_senders(chat_id=chat_id, hours=hours, limit=limit)

    if results and emit_structured(results, as_json=as_json, as_yaml=as_yaml):
        return

    if not results:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print("[yellow]No sender data found.[/yellow]")
        return

    table = Table(title="Top Senders")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Sender", style="bold")
    table.add_column("Messages", justify="right")
    table.add_column("First", style="dim")
    table.add_column("Last", style="dim")

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r["sender_name"],
            str(r["msg_count"]),
            (r["first_msg"] or "")[:10],
            (r["last_msg"] or "")[:10],
        )

    console.print(table)


@query_group.command("timeline")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("--hours", type=int, help="Only show last N hours")
@click.option("--by", "granularity", type=click.Choice(["day", "hour"]), default="day")
@click.option(
    "--sync-first",
    is_flag=True,
    help="Refresh local cache before building the timeline",
)
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@structured_output_options
def timeline(
    chat: str | None,
    hours: int | None,
    granularity: str,
    sync_first: bool,
    sync_limit: int,
    as_json: bool,
    as_yaml: bool,
):
    """Show message activity over time as a bar chart."""
    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return
        results = db.timeline(chat_id=chat_id, hours=hours, granularity=granularity)

    if results and emit_structured(results, as_json=as_json, as_yaml=as_yaml):
        return

    if not results:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print("[yellow]No timeline data.[/yellow]")
        return

    max_count = max(r["msg_count"] for r in results)
    bar_width = 40

    for r in results:
        period = r["period"]
        count = r["msg_count"]
        bar_len = int(count / max_count * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        console.print(f"[dim]{period}[/dim] {bar} [bold]{count}[/bold]")


@query_group.command("today")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option(
    "--sync-first",
    is_flag=True,
    help="Refresh local cache before reading today's messages",
)
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@structured_output_options
def today(chat: str | None, sync_first: bool, sync_limit: int, as_json: bool, as_yaml: bool):
    """Show today's messages, grouped by chat."""
    from datetime import datetime

    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return
        msgs = db.get_today(chat_id=chat_id)
        latest_ts = db.get_latest_timestamp(chat_id=chat_id)

    if msgs and emit_structured(msgs, as_json=as_json, as_yaml=as_yaml):
        return

    if not msgs:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print("[yellow]No messages today.[/yellow]")
        if latest_ts:
            latest_local = datetime.fromisoformat(latest_ts).astimezone()
            console.print(
                "[dim]Latest local message is from "
                f"{latest_local.strftime('%Y-%m-%d %H:%M:%S %Z')}. "
                "Run 'tg refresh' to refresh.[/dim]"
            )
        else:
            console.print("[dim]Local database is empty. Run 'tg refresh' first.[/dim]")
        return

    # Group by chat
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in msgs:
        grouped[m.get("chat_name") or "Unknown"].append(m)

    for chat_name, chat_msgs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        console.print(f"\n[bold cyan]═══ {chat_name} ({len(chat_msgs)} msgs) ═══[/bold cyan]")
        for m in chat_msgs:
            ts = (m.get("timestamp") or "")[11:19]
            sender = m.get("sender_name") or "Unknown"
            content = (m.get("content") or "")[:200].replace("\n", " ")
            console.print(f"  [dim]{ts}[/dim] [bold]{sender[:15]}[/bold]: {content}")

    console.print(f"\n[green]Total: {len(msgs)} messages today[/green]")


@query_group.command("filter")
@click.argument("keywords")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("--hours", type=int, help="Only search last N hours (default: today)")
@click.option("--sync-first", is_flag=True, help="Refresh local cache before filtering")
@click.option(
    "--sync-limit",
    default=5000,
    show_default=True,
    help="Max messages per chat when using --sync-first",
)
@structured_output_options
def filter_msgs(
    keywords: str,
    chat: str | None,
    hours: int | None,
    sync_first: bool,
    sync_limit: int,
    as_json: bool,
    as_yaml: bool,
):
    """Filter messages by KEYWORDS (comma-separated, OR logic).

    Examples:
        tg filter "Rust,Golang,Java"
        tg filter "招聘,remote,远程" --hours 48
        tg filter "Rust" --chat "牛油果" --json
    """
    import re

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keyword_list:
        if emit_error("invalid_keywords", "Please provide at least one keyword."):
            raise SystemExit(1) from None
        console.print("[red]Please provide at least one keyword.[/red]")
        return

    _maybe_sync_first(chat, sync_first, sync_limit)

    with MessageDB() as db:
        chat_id = resolve_chat_id_or_print(db, chat)
        if chat and chat_id is None:
            return

        if hours:
            msgs = db.get_recent(chat_id=chat_id, hours=hours, limit=100000)
        else:
            msgs = db.get_today(chat_id=chat_id)

    # Filter messages containing ANY of the keywords (case-insensitive)
    pattern = re.compile("|".join(re.escape(k) for k in keyword_list), re.IGNORECASE)
    matched = [m for m in msgs if m.get("content") and pattern.search(m["content"])]

    if not matched:
        if emit_structured([], as_json=as_json, as_yaml=as_yaml):
            return
        console.print(f"[yellow]No messages matching: {', '.join(keyword_list)}[/yellow]")
        return

    if emit_structured(matched, as_json=as_json, as_yaml=as_yaml):
        return

    # Group by chat
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in matched:
        grouped[m.get("chat_name") or "Unknown"].append(m)

    for chat_name, chat_msgs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        console.print(f"\n[bold cyan]═══ {chat_name} ({len(chat_msgs)} matches) ═══[/bold cyan]")
        for m in chat_msgs:
            ts = (m.get("timestamp") or "")[:19]
            sender = m.get("sender_name") or "Unknown"
            content = (m.get("content") or "")[:300].replace("\n", " ")
            # Highlight keywords
            for kw in keyword_list:
                content = re.sub(
                    re.escape(kw),
                    f"[bold red]{kw}[/bold red]",
                    content,
                    flags=re.IGNORECASE,
                )
            console.print(
                f"  [dim]{ts}[/dim] [bold]{sender[:15]}[/bold]: ",
                end="",
            )
            console.print(content, markup=True, highlight=False)

    console.print(
        f"\n[green]Found {len(matched)} messages matching "
        f"'{', '.join(keyword_list)}' "
        f"(from {len(msgs)} total)[/green]"
    )
