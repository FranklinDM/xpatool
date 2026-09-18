import sys
import zipfile
from pathlib import Path

import click
import lxml.etree as ET
from rich.console import Console

from core.config import load_config
from core.packager import build_xpi
from parsers.install_manifest import InstallManifestParser
from utils.resolver import resolve_addon_targets

console = Console()


@click.command(
    name="build",
    help="Build .xpi package for an add-on or all discovered add-ons.",
)
@click.argument("target", required=False)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(),
    help="Directory to save the built .xpi package.",
)
@click.option(
    "-n",
    "--name",
    help="Custom base package name (defaults to add-on ID prefix).",
)
@click.option(
    "--tag/--no-tag",
    default=False,
    help="Build as tagged release (default: development build).",
)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Build all discovered add-ons.",
)
@click.option(
    "--github-output",
    is_flag=True,
    help="Write GitHub Actions output parameters (GITHUB_OUTPUT).",
)
def build_cmd(
    target: str | None,
    output_dir: str | None,
    name: str | None,
    tag: bool,
    all_addons: bool,
    github_output: bool,
) -> None:
    targets = resolve_addon_targets(target=target, all_addons=all_addons)
    if not targets:
        console.print("[red]No target add-ons found to build.[/red]")
        sys.exit(1)

    config = load_config()
    known = config.get("known_apps", {})
    app_map = {guid: info.get("code", "app") for guid, info in known.items()}

    ref_type = "tag" if tag else "branch"
    out_dir = output_dir or str(Path.cwd())

    success_count = 0
    for addon_path in targets:
        try:
            manifest = InstallManifestParser(addon_path)
            meta = manifest.get_metadata()
            pkg_name = name or (
                meta["id"].split("@")[0] if meta["id"] else addon_path.name
            )
            console.print(
                f"[bold blue]Building[/bold blue] {meta.get('name', addon_path.name)}…"
            )
            xpi_path, final_ver, is_prerelease = build_xpi(
                source_dir=meta["source_dir"],
                output_dir=out_dir,
                package_name=pkg_name,
                ref_type=ref_type,
                app_map=app_map,
                write_github_output=github_output,
            )
            pre_label = " [yellow](prerelease)[/yellow]" if is_prerelease else ""
            console.print(
                f"[green]✓ Built:[/green] {xpi_path} (v{final_ver}){pre_label}"
            )
            success_count += 1
        except (OSError, ValueError, ET.LxmlError, zipfile.BadZipFile) as e:
            console.print(f"[red]✗ Build failed for {addon_path}:[/red] {e}")

    if success_count == 0:
        sys.exit(1)
