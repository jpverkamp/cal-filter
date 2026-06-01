# CalFilter

Small script for working with calendar ICS files.

Use your config file:

## Config File

Top-level keys:

- settings: global behavior (date window, URL cache TTL, optional HTML to markdown)
- outputs: named output calendars and where to write them
- inputs: input calendars (local file or URL) with routing rules

Minimal structure:

```yaml
settings:
	url_refresh_seconds: 1800
	past_days: 14
	future_days: 90
	html_to_markdown: false

outputs:
	- name: Work
		path: ./output/work.ics
	- name: Personal
		path: ./output/personal.ics

inputs:
	- name: Local Calendar
		path: ./ics/source.ics
		rules:
			- name: Work Items
				match:
					summary: "(?i)work|meeting"
				rewrite: *strip_prefix
				output: Work
		default:
			output: Personal

	- name: Remote Calendar
		url: "https://calendar.example.com/private/basic.ics"
		rules:
			- name: Ignore noisy events
				exclude: true
				match:
					summary: "(?i)office hours|focus block"
			- name: Family Items
				match:
					summary: "(?i)family"
				output: Personal
```

## Field Reference

settings:

- url_refresh_seconds: cache TTL for URL inputs
- past_days: include events this many days in the past in generated files
- future_days: include events this many days in the future in generated files
- html_to_markdown: if true, converts summary and description from HTML to markdown

outputs items:

- name: output name used by rules
- path: output ICS file path

inputs items:

- name: optional display name for logs
- path or url: exactly one source, local or remote
- rules: ordered list of matching rules; all matching rules will be applied
- default: fallback rule used when no rules match

rules/default items:

- name: optional rule name for logs
- match: map of event field to regex pattern (any matching field marks the rule as matched)
- exclude: if true, matched events are dropped
- rewrite: map of field to pattern/replace transform
- output: single output name or list of output names

Notes:

- Rules are evaluated in order. Multiple rules can match and the same event can be written to multiple outputs.
- If no rules match and default is present, default is applied.
- Event fields used in match and rewrite should match ICS property names in your input, commonly summary, description, location, dtstart, dtend.


