import argparse
import coloredlogs
import datetime
import ics
import logging
import pathlib
import sqlite3
import sys

APPLE_EPOCH = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)


def apple_ts(ts):
    if ts is None:
        return None

    try:
        return APPLE_EPOCH + datetime.timedelta(seconds=float(ts))
    except:
        return None


argparse = argparse.ArgumentParser(description="Export an Apple Calendar to ICS")
argparse.add_argument("--verbose", "-v", action="count", help="Enable verbose logging")
argparse.add_argument(
    "db_file",
    default=str(
        pathlib.Path.home()
        / "Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb"
    ),
    metavar="PATH",
    help="Path to Calendar.sqlitedb",
)
argparse.add_argument(
    "--list", action="store_true", help="List available calendars and exit"
)
argparse.add_argument("--calendar", metavar="ID", help="Calendar ID")
argparse.add_argument(
    "--out",
    metavar="FILE",
    default="-",
    help="Output .ics file path, default to - (stdout)",
)
args = argparse.parse_args()

if args.verbose and args.verbose == 1:
    coloredlogs.install(level=logging.INFO)
elif args.verbose and args.verbose >= 2:
    coloredlogs.install(level=logging.DEBUG)
else:
    coloredlogs.install(level=logging.WARNING)

db_path = pathlib.Path(args.db_file)
if not db_path.exists():
    logging.error(f"Database not found: {db_path}")
    sys.exit(1)

db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
db.row_factory = sqlite3.Row

# List mode only prints calendars and exits
if args.list:
    rows = db.execute("""
        SELECT c.ROWID, c.title, s.name AS store,
               c.external_id, c.type
        FROM Calendar c
        JOIN Store s ON c.store_id = s.ROWID
        ORDER BY s.name, c.title
        """).fetchall()

    if not rows:
        print("No calendars found.")
        sys.exit(0)

    print(f"\n{'ID':>5}  {'Store':<35} {'Type':<12} {'Title'}")
    print("─" * 80)
    last_store = None
    for r in rows:
        if r["store"] != last_store:
            print()
            last_store = r["store"]
        cal_type = r["type"] or ""
        print(f"{r['ROWID']:>5}  {r['store']:<35} {cal_type:<12} {r['title']}")
    print()
    sys.exit(0)

row = db.execute(
    "SELECT ROWID FROM Calendar WHERE ROWID = ?", (args.calendar,)
).fetchone()
if not row:
    logging.error(f"No calendar with ROWID {args.calendar}. Run --list to see options.")
    sys.exit(1)

events = db.execute(
    """
SELECT ci.*,
        l.title  AS loc_title,
        l.address AS loc_address
FROM CalendarItem ci
LEFT JOIN Location l ON l.item_owner_id = ci.ROWID
WHERE ci.calendar_id = ?
    AND ci.entity_type != 1   -- skip tasks/reminders
    AND ci.hidden = 0
ORDER BY ci.start_date
""",
    (args.calendar,),
).fetchall()

logging.info(f"Exporting {len(events)} events from calendar ID {args.calendar}")
cal = ics.Calendar()
for e in events:
    event = ics.Event()
    event.uid = f"{e['ROWID']}@applecal"
    event.name = e["summary"] or "No Title"
    event.begin = apple_ts(e["start_date"])
    event.end = apple_ts(e["end_date"])
    event.created = apple_ts(e["creation_date"])
    event.last_modified = apple_ts(e["last_modified"])
    event.description = e["description"] or ""

    if e["loc_title"] or e["loc_address"]:
        location_parts = []
        if e["loc_title"]:
            location_parts.append(e["loc_title"])
        if e["loc_address"]:
            location_parts.append(e["loc_address"])
        event.location = ", ".join(location_parts)

    cal.events.add(event)

output_path = args.out
if output_path == "-":
    print(cal.serialize())
else:
    with open(output_path, "w") as f:
        f.write(cal.serialize())

logging.info(f"Exported {len(cal.events)} events to {output_path}")
