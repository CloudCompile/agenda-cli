"""agenda — today across Skyward, Classroom and MyStudyLife."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from . import sources

app = typer.Typer(help="One view across Skyward, Classroom and MyStudyLife.",
                  no_args_is_help=True, add_completion=False,
                  context_settings={"help_option_names": ["-h", "--help"]})
console = Console()
err = Console(stderr=True)


def _due(value: Any) -> Text:
    if not value:
        return Text("—", style="dim")
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return Text(str(value), style="dim")
    delta = (value - date.today()).days
    label = value.strftime("%a %b %-d")
    if delta < 0:
        return Text(f"{label} · {-delta}d late", style="bold red")
    if delta == 0:
        return Text(f"{label} · today", style="bold yellow")
    if delta <= 7:
        return Text(f"{label} · {delta}d", style="yellow")
    return Text(label)


@app.command()
def today(
    json_out: bool = typer.Option(False, "--json"),
):
    """What's happening today: classes, due work, and anything outstanding."""
    classes = sources.msl_week()
    tasks = sources.msl_tasks()
    missing = sources.classroom_missing()
    sky = sources.skyward_outstanding()

    def as_date(value):
        """Task due values may be a datetime or a bare date.

        datetime subclasses date, so check it first or the comparison against
        date.today() silently never matches.
        """
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    due_today = [t for t in (tasks.items if tasks.ok else [])
                 if as_date(t.due) == date.today()]
    overdue = [t for t in (tasks.items if tasks.ok else []) if t.overdue]

    if json_out:
        payload = {
            "classes": [c.__dict__ for c in classes.items] if classes.ok else [],
            "due_today": [t.to_dict() for t in due_today],
            "overdue": [t.to_dict() for t in overdue],
            "sources": {
                "msl": classes.ok and tasks.ok,
                "classroom": missing.ok,
                "skyward": sky.ok,
            },
            "errors": {n: r.error for n, r in
                       (("msl", classes), ("classroom", missing), ("skyward", sky)) if not r.ok},
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False,
                              default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o)))
        return

    console.print(Text(date.today().strftime("%A, %B %-d"), style="bold"))
    console.print()

    console.print(Text("Classes", style="dim"))
    if not classes.ok:
        console.print(f"[dim]  unavailable: {classes.error}[/]")
    elif not classes.items:
        console.print("[dim]  nothing scheduled[/]")
    else:
        t = Table(box=None, pad_edge=False, show_header=False)
        t.add_column(style="dim", no_wrap=True)
        t.add_column()
        for c in classes.items:
            t.add_row(c.time_label, c.title)
        console.print(t)
    console.print()

    if overdue or due_today:
        console.print(Text("Due for you", style="dim"))
        t = Table(box=None, pad_edge=False, header_style="dim")
        t.add_column("Due", no_wrap=True)
        t.add_column("Task")
        t.add_column("Course", style="dim")
        for task in sorted(overdue + due_today, key=lambda x: x.due):
            t.add_row(_due(as_date(task.due)), task.title, task.subject)
        console.print(t)
        console.print()

    counts = []
    if missing.ok:
        n = len(missing.items["items"])
        counts.append(f"[yellow]{n}[/] missing in Classroom")
    if sky.ok:
        counts.append(f"[cyan]{len(sky.items)}[/] ungraded in Skyward")
    if counts:
        console.print(Text("Also outstanding: " + "  ·  ".join(counts)))
    for name, r in (("classroom", missing), ("skyward", sky)):
        if not r.ok:
            console.print(f"[dim]{name}: {r.error}[/]")


@app.command("outstanding")
def outstanding(
    json_out: bool = typer.Option(False, "--json"),
):
    """Everything not done, from all three systems, by due date."""
    missing = sources.classroom_missing()
    sky = sources.skyward_outstanding()
    tasks = sources.msl_tasks()

    rows: list[dict[str, Any]] = []
    if missing.ok:
        for i in missing.items["items"]:
            rows.append({"source": "classroom", "due": i.get("due"), "title": i.get("title"),
                         "course": i.get("course"), "url": i.get("url", "")})
    if sky.ok:
        for i in sky.items:
            rows.append({"source": "skyward", "due": None, "title": i["title"],
                         "course": i["course"], "url": ""})
    if tasks.ok:
        for t in tasks.items:
            rows.append({"source": "msl", "due": t.due, "title": t.title,
                         "course": t.subject, "url": ""})
    order = {"msl": 0, "classroom": 1, "skyward": 2}

    def key(r):
        d = r["due"]
        if isinstance(d, datetime):
            d = d.date()
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d[:10])
            except ValueError:
                d = None
        r["due"] = d
        return (d is None, d or date.max, order[r["source"]], r["title"].lower())

    rows.sort(key=key)
    if json_out:
        typer.echo(json.dumps(rows, indent=2, default=lambda o: o.isoformat()
                              if hasattr(o, "isoformat") else str(o)))
        return
    console.print(Text("Everything outstanding", style="bold"))
    console.print()
    t = Table(box=None, pad_edge=False, header_style="dim")
    t.add_column("Due", no_wrap=True)
    t.add_column("", width=1, style="dim")
    t.add_column("Item")
    t.add_column("Course", style="dim")
    for r in rows:
        mark = {"msl": "▸", "classroom": "C", "skyward": "S"}[r["source"]]
        t.add_row(_due(r["due"]), mark, r["title"][:64], (r["course"] or "")[:28])
    console.print(t)
    if rows:
        console.print(Text("▸ planner task   C classroom missing   S ungraded in gradebook",
                           style="dim"))
    for name, r in (("classroom", missing), ("skyward", sky), ("msl", tasks)):
        if not r.ok:
            console.print(f"[dim]{name}: {r.error}[/]")


@app.command()
def grades(
    json_out: bool = typer.Option(False, "--json"),
):
    """Skyward grades (delegates to skyward's own view)."""
    g = sources.skyward_grades()
    if not g.ok:
        err.print(f"[red]skyward: {g.error}[/]")
        raise typer.Exit(3)
    data = g.items
    if json_out:
        typer.echo(json.dumps(data, indent=2, default=lambda o: o.isoformat()
                              if hasattr(o, "isoformat") else (asdict(o) if is_dataclass(o) else str(o))))
        return
    console.print(Text(data["student"].name or "student", style="bold"), end="")
    if data["student"].school:
        console.print(Text(f"  ·  {data['student'].school}", style="dim"))
    else:
        console.print()
    console.print()
    classes = data["classes"]
    terms: list[str] = []
    for c in classes:
        for k in c.grades:
            if k not in terms:
                terms.append(k)
    t = Table(box=None, pad_edge=False, header_style="dim")
    t.add_column("#", style="dim", justify="right")
    t.add_column("Course")
    t.add_column("Teacher", style="dim")
    for term in terms:
        t.add_column(term, justify="center")
    for c in classes:
        t.add_row(c.period or "", c.name, c.teacher or "",
                  *[c.grades.get(x, "") or "–" for x in terms])
    console.print(t)
    gpa = data["gpa"]
    if gpa and (gpa.unweighted or gpa.rank):
        line = []
        if gpa.unweighted:
            line.append(f"GPA {gpa.unweighted:.2f}")
        if gpa.rank:
            line.append(f"rank {gpa.rank}")
        console.print()
        console.print(Text("  ·  ".join(line), style="dim"))


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)
