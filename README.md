# CalFilter

Small scripts for working with calendar ICS files.

## Scripts

- `apple-cal-to-ics.py`: export one Apple Calendar (`Calendar.sqlitedb`) to a single `.ics` file
- `ics-filter.py`: route/filter/rewrite ICS events from one or more inputs into one or more output files using `config.yaml`

## Quick Start

```bash
uv sync
```

### 1) Export Apple Calendar to ICS

This assumes you have a copy of your Apple Calendar database (located at `~/Library/Group\ Containers/group.com.apple.calendar/Calendar.sqlitedb`). Copying and/or opening this file will likely run into permissions issues. You need to grant full disk access to the script running this (or terminal) or it will fail silently. 

List calendars in the Apple DB:

```bash
uv run apple-cal-to-ics.py --list Calendar.sqlitedb
```

Export one calendar by ID:

```bash
uv run apple-cal-to-ics.py Calendar.sqlitedb \
  --calendar 14 \
  --out ics/work.ics
```

### 2) Filter/route calendars

Use your config file:

```bash
uv run ics-filter.py config.yaml
```

Use the example config as a starting point:

```bash
cp config.yaml.example config.yaml
```
