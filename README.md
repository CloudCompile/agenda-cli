# agenda

[![tests](https://github.com/CloudCompile/agenda-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/CloudCompile/agenda-cli/actions/workflows/tests.yml)

One view across the three school systems these CLIs talk to:

| source | tool | knows |
| --- | --- | --- |
| Skyward | `skyward` | grades, and which gradebook slots are ungraded |
| Classroom | `classroom` | what was posted and what's marked missing |
| MyStudyLife | `msl` | your own planner: tasks, classes, exams |

```console
$ agenda today
Wednesday, November 18

Classes
8:50 AM – 9:35 AM    Found/Fitness
9:40 AM – 10:25 AM   WORLD HISTORY
...

Due for you
Due                   Task                  Course
Mon Nov 2 · 16d late  Blue packet due       World History
Wed Nov 18 · today    4.3 Proof Packet 1    Geometry H

Also outstanding: 10 missing in Classroom  ·  6 ungraded in Skyward
```

## Commands

| command | shows |
| --- | --- |
| `agenda today` | today's classes, work due today/overdue, and a count of what else is out |
| `agenda outstanding` | everything undone across all three, by due date |
| `agenda grades` | Skyward grades |

All take `--json`. In `outstanding`, each row is tagged:

```
▸  a task in your planner
C  missing in Classroom
S  ungraded in the Skyward gradebook
```

## Notes

The three overlap but don't agree, and the disagreements are the useful part
(`classroom crosscheck` shows the full comparison):

- Classroom says "turned in" only for work submitted *through Classroom*.
  Paper homework stays "missing" there forever.
- Skyward knows what the gradebook counts, including things Classroom never
  saw.
- MSL knows only what you typed into it.

A missing source degrades to a note instead of an error, so `agenda today`
still works when Classroom's browser session has expired.

## Install

`agenda` reads the other three tools in-process, so it needs their checkouts:

```console
$ git clone https://github.com/CloudCompile/skyward-cli     ~/skyward
$ git clone https://github.com/CloudCompile/msl-cli         ~/msl
$ git clone https://github.com/CloudCompile/classroom-cli   ~/classroom
$ git clone https://github.com/CloudCompile/agenda-cli      ~/agenda
$ cd ~/agenda && ./install.sh
```

If a checkout lives somewhere else, point `SKYWARD_HOME`, `MSL_HOME` or
`CLASSROOM_HOME` at it.

## See also

- [skyward-cli](https://github.com/CloudCompile/skyward-cli) — grades and assignments
- [classroom-cli](https://github.com/CloudCompile/classroom-cli) — Classroom posts, classwork, attachments
- [msl-cli](https://github.com/CloudCompile/msl-cli) — the planner
- [gsuite-cli](https://github.com/CloudCompile/gsuite-cli) — school Gmail, Drive, Docs, Calendar

## License

MIT — see [LICENSE](LICENSE).
