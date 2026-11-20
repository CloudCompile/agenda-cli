"""Load data from the three sibling CLIs.

Each lives in its own checkout (sibling directories under ~/ by default), so
this adds them to sys.path rather than depending on three published packages.
Point `SKYWARD_HOME`, `MSL_HOME` or `CLASSROOM_HOME` at a checkout elsewhere.
Everything is optional: a missing or unconfigured source degrades to a note,
never a crash.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


def _add(path: str) -> bool:
    p = Path(os.environ.get(f"{path.upper()}_HOME") or (Path.home() / path)).expanduser()
    if not (p / path).is_dir():
        return False
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return True


@dataclass
class Sourced:
    items: list[Any] = field(default_factory=list)
    error: str = ""
    ok: bool = True


def _skyward() -> tuple[Any, Any]:
    if not _add("skyward"):
        raise RuntimeError("skyward not found (set SKYWARD_HOME)")
    from skyward import client as sky_client, parse as sky_parse  # type: ignore
    return sky_client, sky_parse


def _msl():
    if not _add("msl"):
        raise RuntimeError("msl not found (set MSL_HOME)")
    from msl import client as msl_client, parse as msl_parse  # type: ignore
    return msl_client, msl_parse


def _classroom():
    if not _add("classroom"):
        raise RuntimeError("classroom not found (set CLASSROOM_HOME)")
    from classroom import identity, scrape  # type: ignore
    from classroom import cdp, profile as cprofile
    return cdp, cprofile, identity, scrape


def skyward_outstanding() -> Sourced:
    """Ungraded assignments from the gradebook."""
    try:
        sky, parse = _skyward()
        c = sky.SkywardClient()
        c.login(sky.resolve_credentials(prompt=False))
        classes = parse.parse_gradebook(c.gradebook())
        items = [{"source": "skyward", "course": cl.name, "title": a.name,
                  "due": None, "term": a.term, "period": cl.period}
                 for cl in classes for a in cl.assignments if not a.grade]
        return Sourced(items)
    except Exception as e:               # noqa: BLE001
        return Sourced([], error=str(e), ok=False)


def skyward_grades() -> Sourced:
    try:
        sky, parse = _skyward()
        c = sky.SkywardClient()
        c.login(sky.resolve_credentials(prompt=False))
        gb = c.gradebook()
        classes = parse.parse_gradebook(gb)
        try:
            gpa = c.gpa()
        except Exception:                # noqa: BLE001 - gpa is optional
            gpa = None
        return Sourced({"student": parse.parse_student(gb), "classes": classes, "gpa": gpa})
    except Exception as e:               # noqa: BLE001
        return Sourced(None, error=str(e), ok=False)


def classroom_missing() -> Sourced:
    try:
        cdp, cprofile, identity, scrape = _classroom()
        browser = cprofile.Browser(port=int(__import__("os").environ.get("CLASSROOM_CDP_PORT", "9351")))
        browser.json("/json/version")
        tab = cdp.work_tab(browser, cdp.WORK_TAB_URL, settle=3)
        ident = identity.verify(tab)
        items = [{"source": "classroom", "course": a.course, "title": a.title,
                  "due": a.due, "url": a.url}
                 for a in scrape.missing(tab)]
        return Sourced({"email": ident.email, "items": items})
    except Exception as e:               # noqa: BLE001
        return Sourced(None, error=str(e), ok=False)


def msl_tasks() -> Sourced:
    try:
        mc, parse = _msl()
        c = mc.MSLClient()
        c.ensure_session()
        return Sourced(parse.open_tasks(parse.parse_tasks(c.tasks())))
    except Exception as e:               # noqa: BLE001
        return Sourced([], error=str(e), ok=False)


def msl_week() -> Sourced:
    """Today's classes from MSL."""
    try:
        mc, parse = _msl()
        c = mc.MSLClient()
        c.ensure_session()
        today = date.today()
        items = parse.parse_calendar(c.calendar(today, today))
        # the calendar mixes classes, tasks and events; a class list wants
        # only CLASS (and shows tasks through the task list instead)
        return Sourced([o for o in parse.on_day(items, today) if o.kind == "CLASS"])
    except Exception as e:               # noqa: BLE001
        return Sourced([], error=str(e), ok=False)
