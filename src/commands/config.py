from pathlib import Path

import click
from rich.console import Console

from core.config import load_config, save_config
from core.proxies import get_default_proxies_dir
from utils.resolver import get_all_addons

console = Console()


@click.group(name="config", help="Manage XPATool configuration.")
def config_grp() -> None:
    pass


@config_grp.command(name="list", help="Display active configuration.")
def config_list() -> None:
    config = load_config()
    dirs = config.get("addon_directories", [])

    console.print("[bold]Configured Add-on Directories:[/bold]")
    if dirs:
        for d in dirs:
            console.print(f"  • {d}")
    else:
        console.print("  [dim](none configured)[/dim]")

    proxies_dir = config.get("proxies_dir", "")
    default_display = str(get_default_proxies_dir().relative_to(Path.cwd()))
    console.print(
        f"\n[bold]Default Proxies Dir:[/bold] {proxies_dir or f'[dim](default: ./{default_display})[/dim]'}"
    )


@config_grp.command(name="add-dir", help="Add directory to search for add-ons.")
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def config_add_dir(directory: str) -> None:
    resolved = str(Path(directory).resolve())
    config = load_config()
    dirs = config.get("addon_directories", [])

    if resolved not in dirs:
        dirs.append(resolved)
        config["addon_directories"] = dirs
        save_config(config)
        console.print(f"[green]✓ Added directory:[/green] {resolved}")
        get_all_addons(rescan=True)
    else:
        console.print(f"[yellow]Directory already configured:[/yellow] {resolved}")


@config_grp.command(
    name="remove-dir", help="Remove directory from add-on search paths."
)
@click.argument("directory", type=click.Path())
def config_remove_dir(directory: str) -> None:
    resolved = str(Path(directory).resolve())
    config = load_config()
    dirs = config.get("addon_directories", [])

    if resolved in dirs:
        dirs.remove(resolved)
        config["addon_directories"] = dirs
        save_config(config)
        console.print(f"[green]✓ Removed directory:[/green] {resolved}")
        get_all_addons(rescan=True)
    else:
        console.print(
            f"[yellow]Directory not found in configuration:[/yellow] {resolved}"
        )


@config_grp.command(
    name="set-proxies-dir", help="Set default directory for generated proxy files."
)
@click.argument("directory", type=click.Path())
def config_set_proxies_dir(directory: str) -> None:
    resolved = str(Path(directory).resolve())
    config = load_config()
    config["proxies_dir"] = resolved
    save_config(config)
    console.print(f"[green]✓ Set default proxies directory:[/green] {resolved}")
