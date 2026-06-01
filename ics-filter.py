import argparse
import coloredlogs
import datetime
import icalendar
import recurring_ical_events
import logging
import markdownify
import re
import requests
import requests_cache
import sys
import yaml

argparse = argparse.ArgumentParser(description="Generate filtered ICS files")
argparse.add_argument("--verbose", "-v", action="count", help="Enable verbose logging")
argparse.add_argument("config_file", help="Path to the YAML configuration file")
args = argparse.parse_args()

if args.verbose and args.verbose == 1:
    coloredlogs.install(level=logging.INFO)
elif args.verbose and args.verbose >= 2:
    coloredlogs.install(level=logging.DEBUG)
else:
    coloredlogs.install(level=logging.WARNING)

try:
    with open(args.config_file, "r") as f:
        config = yaml.safe_load(f)
except Exception as e:
    logging.error(f"Failed to read configuration file: {e}")
    sys.exit(1)

if any("url" in input for input in config.get("inputs", [])):
    logging.info("URL inputs detected, initializing requests cache")
    requests_cache.install_cache(
        "ics-filter.cache.sqlite",
        expire_after=config.get("settings", {}).get("url_refresh_seconds", 1800),
    )

start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
    days=config.get("settings", {}).get("past_days", 14)
)
end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
    days=config.get("settings", {}).get("future_days", 28)
)

outputs = {}
for output in config.get("outputs", []):
    name = output.get("name")
    path = output.get("path")

    if not name:
        logging.error("Output missing 'name' field")
        continue

    if not path:
        logging.error(f"No path specified for output: {name}")
        continue

    outputs[name] = {
        "path": path,
        "calendar": icalendar.Calendar(),
    }

    logging.info(f"Initialized output: {name} -> {path}")

for input in config.get("inputs", []):
    name = input.get("name", "Unnamed Input")
    logging.info(f"Processing input: {name}")

    if "path" in input and "url" in input:
        logging.warning(f"Both 'path' and 'url' specified.")

    if "path" in input:
        try:
            with open(input["path"], "r") as f:
                calendar = icalendar.Calendar.from_ical(f.read())
            logging.info(f"Loaded calendar from {input['path']}")
        except Exception as e:
            logging.error(f"Failed to read calendar from {input['path']}: {e}")
            continue

    elif "url" in input:
        try:
            response = requests.get(input["url"])
            response.raise_for_status()
            calendar = icalendar.Calendar.from_ical(response.text)
            logging.info(f"Fetched calendar from {input['url']}")
        except Exception as e:
            logging.error(f"Failed to fetch calendar from {input['url']}: {e}")
            continue

    else:
        logging.error(f"No valid source specified for input: {name}")
        continue

    events = recurring_ical_events.of(calendar).between(start_time, end_time)
    for event in events:
        event_name = event.get("summary", "Unnamed Event")
        event_start_time = event.get("dtstart").dt
        event_end_time = event.get("dtend").dt

        try:
            if event_end_time < start_time or event_start_time > end_time:
                # logging.debug(f"Event '{event_name}' is outside the date range, skipping")
                continue
        except TypeError:
            if event_end_time < start_time.date() or event_start_time > end_time.date():
                # logging.debug(f"Event '{event_name}' is outside the date range, skipping")
                continue

        logging.debug(
            f"Evaluating event: {event_name} ({event_start_time} - {event_end_time})"
        )

        matched_rules = []

        for rule in input.get("rules", []):
            rule_name = rule.get("name")
            matched = False

            for field, pattern in rule.get("match", {}).items():
                field_value = event.get(field)
                if field_value and re.search(pattern, str(field_value)):
                    matched = True
                    logging.debug(
                        f"Event '{event_name}' matched rule '{rule_name}' on field '{field}' with pattern '{pattern}'"
                    )
                    break

            if matched:
                matched_rules.append(rule)

        if not matched_rules and "default" in input:
            logging.debug(f"No rules matched for event '{event_name}'")
            matched_rules = [input.get("default")]

        for matched_rule in matched_rules:
            if matched_rule.get("exclude", False):
                logging.debug(
                    f"Event '{event.name}' excluded by rule '{matched_rule.get('name', 'Unnamed Rule')}'"
                )
                continue

            rule_name = matched_rule.get("name", "Unnamed Rule")

            rewrite = matched_rule.get("rewrite", {})
            for field, action in rewrite.items():
                if "pattern" in action and "replace" in action:
                    original_value = event.get(field, "")
                    new_value = re.sub(
                        action["pattern"], action["replace"], str(original_value)
                    )
                    event[field] = new_value
                    logging.debug(
                        f"Rewrote event '{event.name}' field '{field}' from '{original_value}' to '{new_value}'"
                    )

            if config.get("settings", {}).get("html_to_markdown", False):
                for field in ["description", "summary"]:
                    original_value = event.get(field, "")
                    if original_value:
                        new_value = markdownify.markdownify(
                            str(original_value), heading_style="ATX"
                        )
                        event[field] = new_value
                        logging.debug(
                            f"Converted HTML to Markdown for event '{event_name}' field '{field}'"
                        )

            output_names = matched_rule.get("output")
            if not output_names:
                logging.warning(f"No output specified for rule '{rule_name}'")
                continue

            if not isinstance(output_names, list):
                output_names = [output_names]

            for output_name in output_names:
                if output_name in outputs:
                    # if event in outputs[output_name]["calendar"]:
                    #     continue

                    outputs[output_name]["calendar"].add_component(event)

                    logging.info(
                        f"Added event '{event_name}' to output '{output_name}'"
                    )
                else:
                    logging.warning(f"No valid output specified for rule '{rule_name}'")

for output_name, output_data in outputs.items():
    try:
        with open(output_data["path"], "w") as f:
            f.write(str(output_data["calendar"]))
        logging.info(
            f"Wrote {len(output_data['calendar'].events)} events to {output_data['path']}"
        )
    except Exception as e:
        logging.error(
            f"Failed to write output '{output_name}' to {output_data['path']}: {e}"
        )
