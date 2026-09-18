import sys

import click
import lxml.etree as ET
from rich.console import Console

from core.config import load_config
from core.proxies import generate_proxies, get_default_proxies_dir
from parsers.install_manifest import InstallManifestParser
from utils.resolver import resolve_addon_targets

console = Console()


@click.command(
    name="proxy",
    help="Generate development profile pointer proxy files.",
)
@click.argument("target", required=False)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(),
    help="Target proxies directory.",
)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Generate proxy files for all discovered add-ons.",
)
def proxy_cmd(target: str | None, output_dir: str | None, all_addons: bool) -> None:
    targets = resolve_addon_targets(target=target, all_addons=all_addons)
    if not targets:
        console.print("[red]No target add-ons found for proxy generation.[/red]")
        sys.exit(1)

    config = load_config()
    proxies_dir = (
        output_dir or config.get("proxies_dir") or str(get_default_proxies_dir())
    )

    for addon_path in targets:
        try:
            manifest = InstallManifestParser(addon_path)
            meta = manifest.get_metadata()
            addon_id = meta.get("id")
            if not addon_id:
                console.print(
                    f"[yellow]! {addon_path.name}: No ID in install.rdf.[/yellow]"
                )
                continue

            proxy_file, content = generate_proxies(
                addon_id=addon_id,
                source_dir=meta["source_dir"],
                proxies_dir=proxies_dir,
            )
            console.print(f"[green]✓ Proxy created:[/green] {proxy_file} -> {content}")
        except (OSError, ET.LxmlError, ValueError) as e:
            console.print(
                f"[red]✗ Failed to generate proxy for {addon_path}:[/red] {e}"
            )
