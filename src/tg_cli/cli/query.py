"""Query commands — search, stats, top, timeline, today, filter."""

from collections import defaultdict

import click
from rich.table import Table

from ..console import console
from ..db import MessageDB


@click.group("query", invoke_without_command=True)
def query_group():
    """Query and analysis commands (registered at top-level)."""
    pass


@query_group.command("search")
@click.argument("keyword")
@click.option("-c", "--chat", help="Filter by chat name")
@click.option("-n", "--limit", default=50, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(keyword: str, chat: str | None, limit: int, as_json: bool):
    """Search messages by KEYWORD."""
    import json

    with MessageDB() as db:
        chat_id = db.resolve_chat_id(chat) if chat else None
        results = db.search(keyword, chat_id=chat_id, limit=limit)

    if as_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return

    if not results:
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

    console.print(f"\n[dim]Found {len(results)} messages[/dim]")


@query_group.command("stats")
def stats():
    """Show message statistics per chat."""
    with MessageDB() as db:
        chats = db.get_chats()
        total = db.count()

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
@click.option("-n", "--limit", default=20, help="Top N senders")
def top(chat: str | None, hours: int | None, limit: int):
    """Show most active senders."""
    with MessageDB() as db:
        chat_id = db.resolve_chat_id(chat) if chat else None
        results = db.top_senders(chat_id=chat_id, hours=hours, limit=limit)

    if not results:
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
def timeline(chat: str | None, hours: int | None, granularity: str):
    """Show message activity over time as a bar chart."""
    with MessageDB() as db:
        chat_id = db.resolve_chat_id(chat) if chat else None
        results = db.timeline(chat_id=chat_id, hours=hours, granularity=granularity)

    if not results:
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
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def today(chat: str | None, as_json: bool):
    """Show today's messages, grouped by chat."""
    import json

    with MessageDB() as db:
        chat_id = db.resolve_chat_id(chat) if chat else None
        msgs = db.get_today(chat_id=chat_id)

    if as_json:
        click.echo(json.dumps(msgs, ensure_ascii=False, indent=2, default=str))
        return

    if not msgs:
        console.print("[yellow]No messages today.[/yellow]")
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
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def filter_msgs(keywords: str, chat: str | None, hours: int | None, as_json: bool):
    """Filter messages by KEYWORDS (comma-separated, OR logic).

    Examples:
        tg filter "Rust,Golang,Java"
        tg filter "招聘,remote,远程" --hours 48
        tg filter "Rust" --chat "牛油果" --json
    """
    import json
    import re

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keyword_list:
        console.print("[red]Please provide at least one keyword.[/red]")
        return

    with MessageDB() as db:
        chat_id = db.resolve_chat_id(chat) if chat else None

        if hours:
            msgs = db.get_recent(chat_id=chat_id, hours=hours, limit=100000)
        else:
            msgs = db.get_today(chat_id=chat_id)

    # Filter messages containing ANY of the keywords (case-insensitive)
    pattern = re.compile("|".join(re.escape(k) for k in keyword_list), re.IGNORECASE)
    matched = [m for m in msgs if m.get("content") and pattern.search(m["content"])]

    if not matched:
        console.print(f"[yellow]No messages matching: {', '.join(keyword_list)}[/yellow]")
        return

    if as_json:
        click.echo(json.dumps(matched, ensure_ascii=False, indent=2, default=str))
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
