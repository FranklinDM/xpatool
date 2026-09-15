from collections.abc import Sequence
from pathlib import Path


def scan_addons_in_directories(directories: Sequence[Path]) -> list[Path]:
    addons: list[Path] = []
    ignored_parts = {".git", ".github", "_profile", "_proxies", "build-xpi"}

    for root_dir in directories:
        root = root_dir.resolve()
        if not root.is_dir():
            continue

        direct_manifest = root / "install.rdf"
        if direct_manifest.is_file():
            addons.append(root)
            continue

        for rdf in root.rglob("install.rdf"):
            if ignored_parts.intersection(rdf.parts):
                continue
            addon_dir = rdf.parent
            if addon_dir.name == "src":
                addon_dir = addon_dir.parent
            if addon_dir not in addons:
                addons.append(addon_dir)

    return sorted(addons)
