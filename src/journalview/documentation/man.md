# JournalView — Boot Log Analysis Tool

JournalView is a command-line tool for analyzing systemd journal logs during system boot, helping you understand service startup times and troubleshoot boot issues.

---

## `journal-cli`

Main command for viewing and analyzing boot logs.

**Usage:**
```bash
journal-cli view [OPTIONS]
```

---

## `journal-cli view`

Display journal logs for specified services and boot sessions, with timing information and status indicators.

**Usage:**
```bash
journal-cli view [OPTIONS]
```

**Options:**

| Option | Description |
|--------|--------------|
| `--service, -s <name>` | Filter by one or more service names (default: all services). |
| `--groups, -g <group>` | Filter by predefined service groups from `/etc/journalview/groups/*.yaml`. |
| `--boot, -b <number>` | Select boot session by index (0 = current, 1 = previous, etc.). |
| `--summary, -S` | Show summary table with service start/end times instead of detailed logs. |
| `--priority, -p <level>` | Filter logs by priority: emerg, alert, crit, err, warning, notice, info, debug. |

**Examples:**

```bash
# View all boot logs
journal-cli view

# View logs for SSH service in current boot
journal-cli view --service sshd --boot 0

# Show summary of service startup times
journal-cli view --summary

# View only error and warning logs
journal-cli view --priority warning

# View logs for Linux system services group
journal-cli view --groups linux
```

---

## Service Groups

Service groups allow you to filter logs by logical categories instead of individual services. Groups are defined in YAML files located at `/etc/journalview/groups/`.

Example group configuration:

```yaml
groups:
  linux:
    - systemd
    - sshd
    - auditd
  gaia-os:
    - cpboot
    - zzzboot_profile
```

To use groups, specify them with `--groups`. This is useful for focusing on specific subsystems during troubleshooting.

---

## Understanding the Output

The tool displays a table with the following columns:

- **Time**: Timestamp of the log entry
- **ServiceName**: Name of the service that generated the log
- **Message**: The actual log message
- **Elapsed**: Time since the previous displayed log entry
- **Status**: Log priority level (color-coded: green=info, yellow=warning, red=error)
- **SvcTotal**: Time since this service first appeared in logs
- **Total**: Time since boot start

Color coding helps identify issues:
- Green: Normal operation
- Yellow: Warnings or slow operations (>5 seconds)
- Red: Errors or very slow operations (>20 seconds)

---

## Common Use Cases

1. **Check boot performance:**
   ```bash
   journal-cli view --summary
   ```
   → See which services take longest to start.

2. **Troubleshoot service failures:**
   ```bash
   journal-cli view --service systemd --priority err
   ```
   → Focus on error logs from systemd.

3. **Monitor specific subsystems:**
   ```bash
   journal-cli view --groups gaia-os
   ```
   → View logs only from Gaia-OS related services.

4. **Compare boot sessions:**
   ```bash
   journal-cli view --boot 1 --service sshd
   ```
   → Check SSH startup in the previous boot.

---

## Tips

- Use `--summary` for a quick overview of service timing.
- Combine filters (e.g., `--groups linux --priority warning`) to narrow down issues.
- Boot indices start from 0 (current) and increase for older boots.
- Service names are case-sensitive; use tab completion if available.

---

For more advanced usage or configuration, consult the system administrator.