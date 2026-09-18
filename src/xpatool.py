#!/usr/bin/env python3
import click

from commands.build import build_cmd
from commands.config import config_grp
from commands.list import list_cmd
from commands.locale import locale_grp
from commands.proxy import proxy_cmd
from commands.update_maxversions import update_maxversions_cmd


@click.group(
    name="xpatool",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="XPATool — Cross Platform Add-on Tool",
)
def cli() -> None:
    pass


cli.add_command(list_cmd)
cli.add_command(build_cmd)
cli.add_command(update_maxversions_cmd)
cli.add_command(locale_grp)
cli.add_command(proxy_cmd)
cli.add_command(config_grp)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
