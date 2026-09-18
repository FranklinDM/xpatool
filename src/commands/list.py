import click
from rich.console import Console
from rich.table import Table

from core.config import load_config
from utils.resolver import get_all_addons

console = Console()


@click.command(
    name="list",
    help="List discovered add-ons in configured directories.",
)
@click.option(
    "-r",
    "--rescan",
    is_flag=True,
    help="Force filesystem rescan instead of loading cache.",
)
def list_cmd(rescan: bool) -> None:
    config = load_config()
    dirs = config.get("addon_directories", [])

    if not dirs:
        console.print(
            "[yellow]No add-on directories configured.[/yellow]\n"
            "Use [bold]xpatool config add-dir <path>[/bold] to add directories."
        )
        return

    addons = get_all_addons(rescan=rescan)
    if not addons:
        console.print(
            "[yellow]No valid add-ons discovered in configured directories.[/yellow]"
        )
        return

    table = Table(title=f"Discovered Add-ons ({len(addons)})")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("ID", style="green")
    table.add_column("Version", style="magenta")
    table.add_column("Path", style="dim")

    for idx, (p, meta) in enumerate(
        sorted(addons.items(), key=lambda x: x[1].get("name", "").lower()), 1
    ):
        table.add_row(
            str(idx),
            meta.get("name", p.name),
            meta.get("id", ""),
            meta.get("version", ""),
            str(p),
        )

    console.print(table)
