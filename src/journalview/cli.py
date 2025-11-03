#!/usr/bin/env python3
import sys
import os
from trogon import tui
import click
from typing import Optional, Tuple
from journalview.journalctl import JournalCtl, Priority

@tui(trogon_ready=True)
@click.group()
@click.pass_context
def cli(ctx) -> None:
    """A CLI tool to view journal logs of boot time."""
    ctx.ensure_object(dict)
    ctx.obj['default_command'] = 'view'


@cli.command()
@click.pass_context 
@click.option('--boot', '-b', type=click.Choice([str(i) for i in range(JournalCtl.get_available_boots())], case_sensitive=False),
              help="Choose the boot number from the list of available boots.")
@click.option('--summary', '-S', is_flag=True, default=False,
              help="Show summary table with per-service first time and end duration.")
@click.option('--priority', '-p',
              type=click.Choice([p.name.lower() for p in Priority], case_sensitive=False),
              default=None,
              help="Filter logs by priority level (name like 'info').")
@click.option('--groups', '-g', multiple=True, type=click.Choice(JournalCtl.get_available_groups(), case_sensitive=False), help="Choose from defined service groups in groups/*.yaml files.")
@click.option('--service', '-s', multiple=True, type=click.Choice(JournalCtl.get_available_services(), case_sensitive=False), default=[],
              help="Choose from a list of available services that run during boot. Default is 'all'. If you pass a plain name, the code will also match corresponding '<name>.service' systemd units.")
def view(ctx, boot: Optional[str], summary: bool, service: Tuple[str, ...], priority: Optional[str], groups: Tuple[str, ...]) -> None:
    """View journal logs for the specified services and boot number."""
    jt = JournalCtl(ctx.obj.get("trogon", None) != None, boot, service, summary, priority, groups)
    jt.view()


@cli.command(name='man', help='Open documentation man page in markdown viewer.')
@click.pass_context
def man(ctx):
    """Open documentation man page."""
    from markdown_viewer import MarkdownScreen

    # make documentation path relative to the real location of this file (resolve symlinks)
    real_file = os.path.realpath(__file__)
    base_dir = os.path.abspath(os.path.dirname(real_file))
    readme_path = os.path.abspath(os.path.normpath(os.path.join(base_dir, 'documentation', 'man.md')))
    app = ctx.obj.get("trogon", None)
    if app is not None:
        if os.path.exists(readme_path):
            app.call_from_thread(app.push_screen, MarkdownScreen(markdown_file=readme_path))
    else:
        if os.path.exists(readme_path):
            os.execvp("markdown_viewer", ["markdown_viewer", readme_path])
        else:
            print(f"man page not found at {readme_path}")


def main():
    if len(sys.argv) == 1:
        # if no arguments are provided, default to tui
        sys.argv.append('tui')
        os.environ['TERM'] = 'xterm-256color'  # Ensure terminal supports colors
    cli()

if __name__ == '__main__':
    main()