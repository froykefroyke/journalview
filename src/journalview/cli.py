#!/usr/bin/env python3
import sys
import os
from trogon import tui
import click
from typing import Optional, Tuple
from journalview.journalctl import JournalCtl


@tui()
@click.group()
@click.pass_context
def cli(ctx) -> None:
    """A CLI tool to view journal logs of boot time."""
    ctx.ensure_object(dict)
    ctx.obj['default_command'] = 'view'

@cli.command()
@click.option('--service', '-s', multiple=True, type=click.Choice(JournalCtl.get_available_services(), case_sensitive=False), default=[],
              help="Choose from a list of available services that run during boot. Default is 'all'. If you pass a plain name, the code will also match corresponding '<name>.service' systemd units.")
@click.option('--boot', '-b', type=click.Choice([str(i) for i in range(JournalCtl.get_available_boots())], case_sensitive=False),
              help="Choose the boot number from the list of available boots.")
@click.option('--summary', '-S', is_flag=True, default=False,
              help="Show summary table with per-service first time and end duration.")
def view(service: Tuple[str, ...], boot: Optional[str], summary: bool) -> None:
    """View journal logs for the specified services and boot number."""
    jt = JournalCtl(boot, service, summary)
    jt.view()

def main():
    cli()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # if no arguments are provided, default to tui
        sys.argv.append('tui')
        os.environ['TERM'] = 'xterm-256color'  # Ensure terminal supports colors
        main()