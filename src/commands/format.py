import sys
from pathlib import Path

import click
from rich.console import Console

from parsers.xul_formatter import XULFormatter
from utils.resolver import resolve_addon_targets

console = Console()


SUPPORTED_EXTENSIONS = {".xul", ".xml", ".xhtml", ".rdf"}
IGNORED_DIR_NAMES = {".git", ".github", "_profile", "_proxies", "node_modules", ".venv"}


@click.command(
    name="format",
    help="Format XUL and XML files while preserving entity references and DOCTYPEs.",
)
@click.argument("targets", nargs=-1, required=False)
@click.option(
    "-a",
    "--all",
    "all_addons",
    is_flag=True,
    help="Format all discovered add-ons in configured directories.",
)
@click.option(
    "-w",
    "--write",
    "in_place",
    is_flag=True,
    help="Edit files in-place instead of printing to stdout.",
)
@click.option(
    "-c",
    "--check",
    "check_only",
    is_flag=True,
    help="Check if files are formatted without writing.",
)
@click.option(
    "--tab-width",
    "tab_width",
    default=4,
    show_default=True,
    type=int,
    help="Number of spaces per indentation level.",
)
@click.option(
    "--use-tabs/--no-tabs",
    "use_tabs",
    default=False,
    help="Indent lines with tabs instead of spaces.",
)
@click.option(
    "--print-width",
    "print_width",
    default=100,
    show_default=True,
    type=int,
    help="Specify the line length that the formatter will wrap on.",
)
@click.option(
    "--align-attributes/--no-align-attributes",
    "align_attributes",
    default=False,
    help="Align wrapped attributes to the tag name column.",
)
def format_cmd(
    targets: tuple[str, ...],
    all_addons: bool,
    in_place: bool,
    check_only: bool,
    tab_width: int,
    use_tabs: bool,
    print_width: int,
    align_attributes: bool,
) -> None:
    formatter = XULFormatter(
        indent_size=1 if use_tabs else tab_width,
        indent_char="\t" if use_tabs else " ",
        max_attrs_per_line=1,
        max_line_length=print_width,
        align_attributes=align_attributes,
    )

    def collect_from_dir(directory: Path) -> list[Path]:
        found: list[Path] = []
        for p in directory.rglob("*"):
            if any(part in IGNORED_DIR_NAMES for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(p.resolve())
        return found

    file_paths: set[Path] = set()

    if all_addons:
        addon_dirs = resolve_addon_targets(all_addons=True)
        for ad in addon_dirs:
            file_paths.update(collect_from_dir(ad))
    elif targets:
        for t in targets:
            # 1. Check if wildcard pattern
            if any(ch in t for ch in ("*", "?", "[", "]")):
                for m in Path.cwd().glob(t):
                    if any(part in IGNORED_DIR_NAMES for part in m.parts):
                        continue
                    if m.is_file() and m.suffix.lower() in SUPPORTED_EXTENSIONS:
                        file_paths.add(m.resolve())
                    elif m.is_dir():
                        file_paths.update(collect_from_dir(m))
                continue

            # 2. Check if file or existing directory path
            p = Path(t).resolve()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                file_paths.add(p)
                continue
            if p.is_dir():
                file_paths.update(collect_from_dir(p))
                continue

            # 3. Resolve as add-on ID or name
            resolved_addons = resolve_addon_targets(target=t)
            for ad in resolved_addons:
                file_paths.update(collect_from_dir(ad))
    else:
        # Default scan in cwd
        file_paths.update(collect_from_dir(Path.cwd()))

    if not file_paths:
        console.print("[yellow]No XUL/XML files found to format.[/yellow]")
        return

    unformatted_count = 0
    for fp in sorted(file_paths):
        try:
            content = fp.read_text(encoding="utf-8")
            formatted = formatter.format(content)

            if check_only:
                if content != formatted:
                    console.print(f"[red]Needs formatting:[/red] {fp}")
                    unformatted_count += 1
                else:
                    console.print(f"[green]✓ OK:[/green] {fp}")
            elif in_place:
                if content != formatted:
                    fp.write_text(formatted, encoding="utf-8")
                    console.print(f"[green]✓ Formatted:[/green] {fp}")
                else:
                    console.print(f"[dim]Unchanged:[/dim] {fp}")
            else:
                sys.stdout.write(formatted)
        except (OSError, UnicodeDecodeError) as e:
            console.print(f"[red]✗ Failed to process {fp}:[/red] {e}")

    if check_only and unformatted_count > 0:
        sys.exit(1)
