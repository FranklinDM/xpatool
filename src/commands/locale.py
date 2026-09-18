import sys
from pathlib import Path

import click
import lxml.etree as ET
from rich.console import Console

from core.locales import get_addon_locales, sort_locales, sync_locales
from parsers.install_manifest import InstallManifestParser
from utils.resolver import resolve_addon_targets

console = Console()


@click.group(name="locale", help="Manage and synchronize add-on translation locales.")
def locale_grp() -> None:
    pass


@locale_grp.command(
    name="sync",
    help="Synchronize missing translation keys with base locale.",
)
@click.argument("target", required=False)
@click.option(
    "-b",
    "--base-locale",
    default="en-US",
    help="Base locale code (default: en-US).",
)
@click.option(
    "-s",
    "--sort",
    "sort_entries",
    is_flag=True,
    help="Sort translation keys alphabetically.",
)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Sync locales for all discovered add-ons.",
)
def locale_sync_cmd(
    target: str | None, base_locale: str, sort_entries: bool, all_addons: bool
) -> None:
    targets = resolve_addon_targets(target=target, all_addons=all_addons)
    if not targets:
        console.print("[red]No target add-ons found to synchronize.[/red]")
        sys.exit(1)

    for addon_path in targets:
        try:
            manifest = InstallManifestParser(addon_path)
            src_dir = Path(manifest.get_source_dir())
            locales = get_addon_locales(src_dir)
            addon_name = manifest.get_metadata().get("name", addon_path.name)

            if not locales:
                console.print(
                    f"[dim]• {addon_name}: No locales in chrome.manifest.[/dim]"
                )
                continue

            if base_locale not in locales:
                console.print(
                    f"[yellow]! {addon_name}: Base locale '{base_locale}' not found in chrome.manifest.[/yellow]"
                )
                continue

            report = sync_locales(src_dir, base_locale=base_locale, sort=sort_entries)
            if report:
                total_keys = sum(
                    len(keys) for files in report.values() for keys in files.values()
                )
                console.print(
                    f"[green]✓ {addon_name}: Synced {total_keys} missing keys across {len(report)} locale(s).[/green]"
                )
            else:
                console.print(
                    f"[dim]• {addon_name}: All locales up to date with {base_locale}.[/dim]"
                )
        except (OSError, ET.LxmlError, ValueError) as e:
            console.print(f"[red]✗ Failed to sync locales for {addon_path}:[/red] {e}")


@locale_grp.command(
    name="sort",
    help="Sort translation keys in .dtd and .properties files alphabetically.",
)
@click.argument("target", required=False)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Sort locales for all discovered add-ons.",
)
def locale_sort_cmd(target: str | None, all_addons: bool) -> None:
    targets = resolve_addon_targets(target=target, all_addons=all_addons)
    if not targets:
        console.print("[red]No target add-ons found for sorting locales.[/red]")
        sys.exit(1)

    for addon_path in targets:
        try:
            manifest = InstallManifestParser(addon_path)
            src_dir = Path(manifest.get_source_dir())
            addon_name = manifest.get_metadata().get("name", addon_path.name)
            sorted_files = sort_locales(src_dir)
            if sorted_files:
                file_count = sum(len(files) for files in sorted_files.values())
                console.print(
                    f"[green]✓ {addon_name}: Sorted keys across {file_count} file(s) in {len(sorted_files)} locale(s).[/green]"
                )
            else:
                console.print(
                    f"[dim]• {addon_name}: No locale files found to sort.[/dim]"
                )
        except (OSError, ET.LxmlError, ValueError) as e:
            console.print(f"[red]✗ Failed to sort locales for {addon_path}:[/red] {e}")
