"""agenda tests: source loading, graceful degradation, and ordering."""
import json
from datetime import date, datetime, time, timedelta

from typer.testing import CliRunner

from agenda import cli as cli_mod
from agenda import sources

runner = CliRunner()


class FakeTask:
    """Mirrors msl.parse.Task: `due` is a datetime, never a bare date."""

    def __init__(self, title, due, subject="", completed=False):
        self.title = title
        self.due = datetime.combine(due, time.min) if isinstance(due, date) \
            and not isinstance(due, datetime) else due
        self.subject = subject
        self.completed = completed

    @property
    def overdue(self):
        return bool(self.due) and self.due.date() < date.today() and not self.completed

    def to_dict(self):
        return {"title": self.title, "due": self.due.isoformat(), "subject": self.subject}


class FakeClass:
    def __init__(self, title, start, end):
        self.title = title
        self.start = start
        self.end = end
        self.kind = "CLASS"

    @property
    def time_label(self):
        return "8:50 AM – 9:35 AM"


def test_outstanding_merges_three_sources(monkeypatch):
    today = date.today()
    monkeypatch.setattr(sources, "classroom_missing",
                        lambda: sources.Sourced({"items": [
                            {"title": "Essay", "course": "English", "due": today.isoformat()}]}))
    monkeypatch.setattr(sources, "skyward_outstanding",
                        lambda: sources.Sourced([{"title": "Lab", "course": "Bio"}]))
    monkeypatch.setattr(sources, "msl_tasks",
                        lambda: sources.Sourced([FakeTask("Task", today + timedelta(days=3), "Math")]))
    r = runner.invoke(cli_mod.app, ["outstanding", "--json"])
    assert r.exit_code == 0, r.output
    rows = json.loads(r.stdout)
    assert {x["source"] for x in rows} == {"classroom", "skyward", "msl"}


def test_outstanding_sorted_by_date_with_undated_last(monkeypatch):
    today = date.today()
    monkeypatch.setattr(sources, "classroom_missing",
                        lambda: sources.Sourced({"items": [
                            {"title": "Far", "course": "C", "due": (today + timedelta(days=9)).isoformat()},
                            {"title": "Near", "course": "C", "due": today.isoformat()}]}))
    monkeypatch.setattr(sources, "skyward_outstanding",
                        lambda: sources.Sourced([{"title": "Undated", "course": "S"}]))
    monkeypatch.setattr(sources, "msl_tasks", lambda: sources.Sourced([]))
    r = runner.invoke(cli_mod.app, ["outstanding", "--json"])
    rows = json.loads(r.stdout)
    assert [x["title"] for x in rows] == ["Near", "Far", "Undated"]


def test_dry_sources_do_not_crash(monkeypatch):
    """A broken source must not take down the whole view."""
    monkeypatch.setattr(sources, "classroom_missing",
                        lambda: sources.Sourced(None, error="not signed in", ok=False))
    monkeypatch.setattr(sources, "skyward_outstanding",
                        lambda: sources.Sourced([], error="login failed", ok=False))
    monkeypatch.setattr(sources, "msl_tasks",
                        lambda: sources.Sourced([FakeTask("T", date.today(), "Math")]))
    monkeypatch.setattr(sources, "msl_week", lambda: sources.Sourced([]))
    r = runner.invoke(cli_mod.app, ["today"])
    assert r.exit_code == 0, r.output
    assert "not signed in" in r.output
    assert "login failed" in r.output


def test_today_lists_classes_and_due_work(monkeypatch):
    today = date.today()
    monkeypatch.setattr(sources, "msl_week",
                        lambda: sources.Sourced([FakeClass("Geometry", None, None)]))
    monkeypatch.setattr(sources, "msl_tasks",
                        lambda: sources.Sourced([FakeTask("Due today", today, "Geo"),
                                                 FakeTask("Later", today + timedelta(days=9), "Geo")]))
    monkeypatch.setattr(sources, "classroom_missing", lambda: sources.Sourced({"items": []}))
    monkeypatch.setattr(sources, "skyward_outstanding", lambda: sources.Sourced([]))
    r = runner.invoke(cli_mod.app, ["today"])
    assert r.exit_code == 0, r.output
    assert "Geometry" in r.output
    assert "Due today" in r.output
    assert "Later" not in r.output, "only today's work belongs in a daily view"


def test_today_json_marks_failed_sources(monkeypatch):
    monkeypatch.setattr(sources, "msl_week", lambda: sources.Sourced([], error="x", ok=False))
    monkeypatch.setattr(sources, "msl_tasks", lambda: sources.Sourced([]))
    monkeypatch.setattr(sources, "classroom_missing",
                        lambda: sources.Sourced(None, error="nope", ok=False))
    monkeypatch.setattr(sources, "skyward_outstanding", lambda: sources.Sourced([]))
    r = runner.invoke(cli_mod.app, ["today", "--json"])
    data = json.loads(r.stdout)
    assert data["sources"]["classroom"] is False
    assert "classroom" in data["errors"]


def test_grades_failure_exits_3(monkeypatch):
    monkeypatch.setattr(sources, "skyward_grades",
                        lambda: sources.Sourced(None, error="boom", ok=False))
    r = runner.invoke(cli_mod.app, ["grades"])
    assert r.exit_code == 3
    assert "boom" in r.output


def test_help():
    r = runner.invoke(cli_mod.app, ["--help"])
    assert r.exit_code == 0
    for cmd in ("today", "outstanding", "grades"):
        assert cmd in r.output
