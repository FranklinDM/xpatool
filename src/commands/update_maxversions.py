import sys

import click
import lxml.etree as ET
from rich.console import Console

from core.config import load_config
from parsers.install_manifest import InstallManifestParser
from utils.resolver import resolve_addon_targets

console = Console()


@click.command(
    name="update-maxversions",
    help="Update targetApplication maxVersions in install.rdf.",
)
@click.argument("target", required=False)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Update all discovered add-ons.",
)
def update_maxversions_cmd(target: str | None, all_addons: bool) -> None:
    targets = resolve_addon_targets(target=target, all_addons=all_addons)
    if not targets:
        console.print("[red]No target add-ons found to update.[/red]")
        sys.exit(1)

    config = load_config()
    known = config.get("known_apps", {})
    updates = {guid: info["default_max_version"] for guid, info in known.items()}

    for addon_path in targets:
        try:
            manifest = InstallManifestParser(addon_path)
            changes = manifest.update_max_versions(updates)
            addon_name = manifest.get_metadata().get("name", addon_path.name)
            if changes:
                console.print(f"[green]✓ Updated maxVersions for {addon_name}:[/green]")
                for guid, old_v, new_v in changes:
                    console.print(f"    • {guid}: {old_v} -> {new_v}")
            else:
                console.print(f"[dim]• {addon_name}: All maxVersions up to date.[/dim]")
        except (OSError, ET.LxmlError, ValueError) as e:
            console.print(f"[red]✗ Failed to update {addon_path}:[/red] {e}")
