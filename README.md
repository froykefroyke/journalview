journalview
=========

A small CLI utility to inspect systemd journal boot logs (journalctl) and profile service startup times.

What it does
------------
- Reads journal entries for a specific boot (via journalctl -b <boot> -o json) or from a test file on non-Linux systems.
- Presents a human-friendly table (using Rich) showing:
  - Time (YYYY-MM-DD HH:MM:SS)
  - ServiceName
  - Message
  - Elapsed (time since previous displayed log)
  - Status (mapped from PRIORITY and color-coded)
  - SvcTotal (time since first log for this service)
  - Total (time since boot start)
- Provides a summary mode that lists, per service, the first-seen time and the duration between first and last log for that service.
- Supports filtering by service names (also matches <name>.service units automatically).
- Colorizes Status and Elapsed columns to highlight slow or error conditions.

Windows / Test mode
-------------------
On Windows or when journalctl is not available, journalview reads newline-delimited JSON from tests/journal_logs/journal.json (the same format produced by journalctl -o json). This allows development and testing without a Linux journal.

API
---
The JournalCtl class separates data collection from presentation:
- collect_data(entries) -> structured rows (timestamps and timedeltas preserved)
- get_summary_data(entries) -> per-service summary
- print_table(rows) and print_summary_table(summary_rows) -> render using Rich
This separation makes it easy to export results as JSON/YAML in the future by consuming the collected data.

Installation
------------
- Python 3.8+
- Recommended packages: click, rich
- Optional: trogon (used for TUI integration in this repository)

You can install requirements with pip:

pip install click rich

Usage
-----
Run the CLI from the package root, for example:

python -m journalview.journalview view --service all
python -m journalview.journalview view -s sshd -b 0
python -m journalview.journalview view -s sshd --summary

Options
-------
- --service / -s : one or more service identifiers to filter (default: all)
- --boot / -b    : boot index (0..N) to inspect
- --summary / -S : show per-service summary instead of the detailed table

Notes
-----
- The tool expects journalctl JSON output format. The test-file used for Windows should contain one JSON object per line.
- Matching of services is exact; pass the systemd unit name (or the syslog identifier). The code also attempts to match the provided name with a ".service" suffix.

License
-------
MIT
