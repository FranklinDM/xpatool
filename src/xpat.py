#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from config import DEFAULT_KNOWN_APPS, load_config, save_config
from core.locales import get_addon_locales, sync_locales
from core.packager import build_xpi
from core.proxies import generate_proxies, get_default_proxies_dir
from parsers.install_manifest import InstallManifestParser
from utils.resolver import get_all_addons, resolve_addon_targets

console = Console()


@click.group(
    name="xpat",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="XPAT — Cross Platform Add-on Tools",
)
def cli() -> None:
    pass


@cli.command(
    name="list",
    help="List discovered add-ons in configured directories.",
)
@click.option(
    "-r",
    "--rescan",
    is_flag=True,
    help="Force filesystem rescan instead of loading cache.",
)
def list_addons(rescan: bool) -> None:
    config = load_config()
    dirs = config.get("addon_directories", [])

    if not dirs:
        console.print(
            "[yellow]No add-on directories configured.[/yellow]\n"
            "Use [bold]xpat config add-dir <path>[/bold] to add directories."
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


@cli.command(
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
    known = config.get("known_apps", DEFAULT_KNOWN_APPS)
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
        except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as e:
            console.print(f"[red]✗ Build failed for {addon_path}:[/red] {e}")

    if success_count == 0:
        sys.exit(1)


@cli.command(
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
    known = config.get("known_apps", DEFAULT_KNOWN_APPS)
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
        except (OSError, ET.ParseError, ValueError) as e:
            console.print(f"[red]✗ Failed to update {addon_path}:[/red] {e}")


@cli.command(
    name="sync-locales",
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
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Sync locales for all discovered add-ons.",
)
def sync_locales_cmd(target: str | None, base_locale: str, all_addons: bool) -> None:
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

            report = sync_locales(src_dir, base_locale=base_locale)
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
        except (OSError, ET.ParseError, ValueError) as e:
            console.print(f"[red]✗ Failed to sync locales for {addon_path}:[/red] {e}")


@cli.command(
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
        except (OSError, ET.ParseError, ValueError) as e:
            console.print(
                f"[red]✗ Failed to generate proxy for {addon_path}:[/red] {e}"
            )


@cli.group(name="config", help="Manage XPAT configuration.")
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
