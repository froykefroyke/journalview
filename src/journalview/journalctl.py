import re
import click
import subprocess
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from rich.table import Table
from rich.console import Console
from rich.text import Text
from enum import IntEnum

class Priority(IntEnum):
	"""Standard syslog/journal priorities (numeric values)."""
	EMERG = 0
	PANIC = 0    # alias
	ALERT = 1
	CRITICAL = 2
	CRIT = 2     # alias
	ERROR = 3
	ERR = 3      # alias
	WARNING = 4
	WARN = 4     # alias
	NOTICE = 5
	INFO = 6
	DEBUG = 7

class JournalCtl:

    def __init__(self, boot: Optional[str], services: Tuple[str, ...], summary: bool = False, priority: Optional[str] = None) -> None:
        """Initialize JournalCtl for a specific boot and set of services."""
        self.boot: str = boot if boot is not None else '0'
        self.services: Tuple[str, ...] = services
        self.journal_dict: Dict[str, Any] = {}
        self.summary: bool = summary
        self.priority: Optional[str] = priority

    @staticmethod
    def get_available_boots() -> int:
        """Return the number of available boot logs. On Windows or when journalctl is not available,
        return a small mock count so CLI can run in test mode."""
        # If running on Windows, use test mode
        if sys.platform.startswith('win'):
            return 3
        try:
            # Run the journalctl command to fetch available boots
            result = subprocess.run(['journalctl', '--list-boots'], capture_output=True, text=True, check=True)
            # Count the number of non-empty lines in the output, each line represents a boot
            boots: List[str] = [line for line in result.stdout.strip().split('\n') if line.strip()]
            return len(boots)
        except FileNotFoundError:
            # journalctl not found (common on Windows) - use test mode
            return 3
        except subprocess.CalledProcessError as e:
            click.echo(f"Error fetching boot logs: {e}")
            return 0

    @staticmethod
    def get_boot_json(boot: str) -> List[Dict[str, Any]]:
        """Return a list of JSON objects for the specified boot (journalctl -b <boot> -o json).

        In test mode (Windows or when journalctl isn't available) this returns data read from
        tets/journal_logs/ojurnal.json or a small mock list so the CLI can function on non-Linux systems.
        """
        # Test mode on Windows: read from provided JSON file (newline-delimited JSON)
        if sys.platform.startswith('win'):
            test_path: str = 'tests/journal_logs/journal.json'
            try:
                entries: List[Dict[str, Any]] = []
                with open(test_path, 'r', encoding='utf-8') as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln:
                            continue
                        try:
                            entries.append(json.loads(ln))
                        except json.JSONDecodeError:
                            # skip malformed JSON lines
                            continue
                if entries:
                    return entries
                # empty file -> fallback mock
                return [{"_BOOT": str(boot), "MESSAGE": f"Test log entry for boot {boot}"}]
            except FileNotFoundError:
                # file not found -> fallback mock
                return [{"_BOOT": str(boot), "MESSAGE": f"Test log entry for boot {boot}"}]
            except Exception as e:
                click.echo(f"Error reading {test_path}: {e}")
                return [{"_BOOT": str(boot), "MESSAGE": f"Test log entry for boot {boot}"}]

        try:
            result = subprocess.run(['journalctl', '-b', str(boot), '-o', 'json'], capture_output=True, text=True, check=True)
            lines: List[str] = [ln for ln in result.stdout.split('\n') if ln.strip()]
            entries: List[Dict[str, Any]] = []
            for ln in lines:
                try:
                    entries.append(json.loads(ln))
                except json.JSONDecodeError:
                    # skip malformed JSON lines
                    continue
            return entries
        except FileNotFoundError:
            # journalctl not found -> fallback mock
            return [{"_BOOT": str(boot), "MESSAGE": f"Test log entry for boot {boot}"}]
        except subprocess.CalledProcessError as e:
            click.echo(f"Error fetching boot logs: {e}")
            return []

    @staticmethod
    def get_available_services(boot: str = '0') -> List[str]:
        """Discover available service identifiers from the journal for the given boot.

        Returns a sorted list of unique names (SYSLOG_IDENTIFIER, _SYSTEMD_UNIT, _COMM, UNIT).
        On Windows or when journalctl is not available, reads from tests/journal_logs/journal.json.
        """
        services: set = set()
        # Test mode on Windows -> read from file
        if sys.platform.startswith('win'):
            test_path: str = 'tests/journal_logs/journal.json'
            try:
                with open(test_path, 'r', encoding='utf-8') as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln:
                            continue
                        try:
                            entry = json.loads(ln)
                        except json.JSONDecodeError:
                            continue
                        for fld in ('SYSLOG_IDENTIFIER', '_SYSTEMD_UNIT', '_COMM', 'UNIT'):
                            val = entry.get(fld)
                            if val:
                                services.add(val)
                if services:
                    return sorted(services)
                return ['all']
            except FileNotFoundError:
                return ['all']
            except Exception:
                return ['all']

        try:
            result = subprocess.run(['journalctl', '-b', str(boot), '-o', 'json'], capture_output=True, text=True, check=True)
            for ln in result.stdout.split('\n'):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    entry = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                for fld in ('SYSLOG_IDENTIFIER', '_SYSTEMD_UNIT', '_COMM', 'UNIT'):
                    val = entry.get(fld)
                    if val:
                        services.add(val)
            if services:
                return ['all'] + sorted(services)
            return ['all']
        except FileNotFoundError:
            return ['all']
        except subprocess.CalledProcessError:
            return ['all']

    def _decode_journal_message(self, entry):
        """
        Decode the MESSAGE field of a journal entry.
    
        - If MESSAGE is a string, returns it as-is (stripping ANSI codes).
        - If MESSAGE is a list of byte values, decodes it to ASCII and strips ANSI codes.
        """
        msg = entry.get("MESSAGE")
        if msg is None:
            return ""
    
        # If MESSAGE is a list of bytes, convert to string
        if isinstance(msg, list):
            try:
                msg = bytes(msg).decode('ascii', errors='replace')
            except Exception as e:
                return f"<decode error: {e}>"
    
        # Strip ANSI escape sequences
        msg_clean = re.sub(r'\x1B\[[0-9;]*[A-Za-z]', '', msg)
    
        # Optionally strip other control chars (non-printable)
        msg_clean = ''.join(c if 32 <= ord(c) <= 126 else ' ' for c in msg_clean)
    
        return msg_clean.strip()

    def collect_data(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw journal entries and return a dict with rows and per-service timestamps.

        Returns:
            {
                'rows': List[Dict[str, Any]],
                'service_first': Dict[str, datetime],
                'service_last': Dict[str, datetime]
            }
        """
        rows: List[Dict[str, Any]] = []
        prev_ts: Optional[datetime] = None
        boot_start_ts: Optional[datetime] = None
        service_start: Dict[str, datetime] = {}
        service_first: Dict[str, datetime] = {}
        service_last: Dict[str, datetime] = {}
        reached_last_boot_log: bool = False
        # priority handling uses Priority enum; numeric journal PRIORITY fields
        # will be mapped to enum names when in 0..7 range. Values outside
        # that range or non-numeric values are compared as strings.

        for entry in entries:
            if reached_last_boot_log:
                break
            ts = self._extract_timestamp(entry)
            if ts is None:
                continue
            if boot_start_ts is None:
                boot_start_ts = ts

            msg = self._decode_journal_message(entry)
            if msg.startswith("Startup finished in"):
                # Handle the end of boot profiling
                reached_last_boot_log = True

            # apply service filter
            if not self._matches_service(entry):
                continue

            # apply priority filter (delegated to helper)
            if not self._filter_priority(entry):
                continue

            svc = entry.get('SYSLOG_IDENTIFIER') or entry.get('_SYSTEMD_UNIT') or entry.get('_COMM') or entry.get('UNIT') or 'unknown'
            if svc not in service_start:
                service_start[svc] = ts

            # Track first and last timestamp per service
            if svc not in service_first:
                service_first[svc] = ts
            service_last[svc] = ts

            # elapsed: since previous displayed entry or since boot start
            if prev_ts is not None:
                elapsed = ts - prev_ts
            else:
                elapsed = ts - boot_start_ts if boot_start_ts is not None else timedelta(0)

            total = ts - boot_start_ts if boot_start_ts is not None else timedelta(0)
            svc_total = ts - service_start[svc]

            # create status using Priority enum when possible
            pr = entry.get('PRIORITY')
            if pr is None:
                status = ''
            else:
                pr_str = str(pr)
                try:
                    pr_int = int(pr_str)
                    if 0 <= pr_int <= 7:
                        status = Priority(pr_int).name
                    else:
                        status = pr_str
                except Exception:
                    status = pr_str

            rows.append({
                'ts': ts,
                'time_str': ts.strftime('%Y-%m-%d %H:%M:%S'),
                'service': svc,
                'message': msg,
                'elapsed': elapsed,
                'total': total,
                'svc_total': svc_total,
                'status': status,
            })

            prev_ts = ts

        return {
            'rows': rows,
            'service_first': service_first,
            'service_last': service_last
        }

    def _status_style(self, status_val: Any) -> str:
        """Return a Rich style name for a given status value."""
        if status_val is None:
            return ''
        sval = str(status_val).upper()
        if sval == 'INFO' or sval == '6':
            return 'green'
        if sval in ('WARNING', 'NOTICE', '5'):
            return 'yellow'
        if sval in ('DEBUG', '7'):
            return 'dim'
        if sval == '':
            return ''
        # treat other values (ERROR, CRITICAL, EMERGENCY, ALERT, etc.) as red
        return 'red'

    def _elapsed_style(self, elapsed: Optional[timedelta]) -> str:
        """Return a style name for elapsed timedelta: green <=5s, yellow <=20s, red >20s."""
        if elapsed is None:
            return ''
        try:
            secs = float(elapsed.total_seconds())
        except Exception:
            return ''
        if secs > 20:
            return 'red'
        if secs > 5:
            return 'yellow'
        return 'green'

    def print_table(self, rows: List[Dict[str, Any]]) -> None:
        console = Console(markup=False)
        table = Table(show_header=True, header_style="bold")
        table.add_column("Time", style="dim", width=19)
        table.add_column("ServiceName", width=25)
        table.add_column("Message", overflow="fold")
        table.add_column("Elapsed", justify="right")
        table.add_column("Status", width=8)
        table.add_column("SvcTotal", justify="right")
        table.add_column("Total", justify="right")

        def fmt_hms(d: timedelta) -> str:
            total_secs = int(d.total_seconds())
            h = total_secs // 3600
            m = (total_secs % 3600) // 60
            s = total_secs % 60
            return f"{h}:{m:02d}:{s:02d}"

        for r in rows:
            elapsed = r['elapsed']
            elapsed_str = f"{elapsed.total_seconds():.3f}" if elapsed is not None else ''
            total_str = fmt_hms(r['total']) if r.get('total') is not None else '0:00:00'
            svc_total_str = fmt_hms(r['svc_total']) if r.get('svc_total') is not None else ''

            # determine elapsed style via helper
            elapsed_style = self._elapsed_style(elapsed)
            elapsed_text = Text(elapsed_str, style=elapsed_style)

            status_val = r.get('status', '')
            # determine status style via helper
            status_style = self._status_style(status_val)

            status_text = Text(str(status_val), style=status_style)

            table.add_row(r['time_str'], r['service'], r['message'], elapsed_text, status_text, svc_total_str, total_str)

        console.print(table)

    def print_summary_table(self, collected: Dict[str, Any]) -> None:
        """Print summary table using collected_data from collect_data."""
        console = Console(markup=False)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim", width=19)
        table.add_column("ServiceName", width=25)
        table.add_column("End Time", justify="right")

        def fmt_hms(d: timedelta) -> str:
            total_secs = int(d.total_seconds())
            h = total_secs // 3600
            m = (total_secs % 3600) // 60
            s = total_secs % 60
            return f"{h}:{m:02d}:{s:02d}"

        service_first = collected.get('service_first', {})
        service_last = collected.get('service_last', {})
        items = []
        for svc, first_ts in service_first.items():
            last_ts = service_last.get(svc, first_ts)
            items.append({'service': svc, 'first_ts': first_ts, 'last_ts': last_ts, 'duration': last_ts - first_ts})
        items.sort(key=lambda it: it['first_ts'])

        for it in items:
            table.add_row(it['first_ts'].strftime('%Y-%m-%d %H:%M:%S'), it['service'], fmt_hms(it['duration']))

        console.print(table)

    # helper wrappers so internal helpers can be reused by both data and printing
    def _matches_service(self, entry: Dict[str, Any]) -> bool:
        # If user requested all services, accept all entries
        if not self.services:
            return True
        candidates = [
            entry.get('SYSLOG_IDENTIFIER'),
            entry.get('_SYSTEMD_UNIT'),
            entry.get('_COMM'),
            entry.get('UNIT'),
        ]
        for svc in self.services:
            svc_variants = (svc, f"{svc}.service")
            for c in candidates:
                if c:
                    for variant in svc_variants:
                        if variant == c:
                            return True
        return False

    def _filter_priority(self, entry: Dict[str, Any]) -> bool:
        """Return True if the journal entry passes the priority filter (self.priority).

        Accepts priority names (case-insensitive) or numeric values.
        Numeric PRIORITY fields in 0..7 are mapped to Priority enum names.
        """
        if self.priority is None:
            return True

        pr = entry.get('PRIORITY')
        pr_str = str(pr) if pr is not None else ''

        # try to interpret numeric priority as enum name when possible
        try:
            pr_int = int(pr_str)
            if 0 <= pr_int <= 7:
                pr_name = Priority(pr_int).name.lower()
            else:
                pr_name = pr_str
        except Exception:
            pr_name = pr_str

        # compare provided filter (could be name or numeric string)
        filt = str(self.priority).lower()
        return filt == pr_name or str(self.priority) == pr_str

    def _extract_timestamp(self, entry: Dict[str, Any]) -> Optional[datetime]:
        ts_fields = ['__REALTIME_TIMESTAMP', '_SOURCE_REALTIME_TIMESTAMP', 'REALTIME_TIMESTAMP']
        for fld in ts_fields:
            val = entry.get(fld)
            if val is None:
                continue
            try:
                micros = int(val)
                return datetime.fromtimestamp(micros / 1_000_000)
            except Exception:
                continue
        return None

    def view(self) -> None:
        entries: List[Dict[str, Any]] = JournalCtl.get_boot_json(self.boot)
        if not entries:
            click.echo("No journal entries found for the selected boot.")
            return

        collected = self.collect_data(entries)
        if self.summary:
            self.print_summary_table(collected)
            return

        rows = collected['rows']
        self.journal_dict = {'boot': self.boot, 'services': self.services, 'rows': rows}
        self.print_table(rows)

