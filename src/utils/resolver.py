import xml.etree.ElementTree as ET
from pathlib import Path

from config import load_addon_cache, load_config, save_addon_cache
from models import AddonMetadata
from parsers.install_manifest import InstallManifestParser
from utils.scanner import scan_addons_in_directories


def get_all_addons(rescan: bool = False) -> dict[Path, AddonMetadata]:
    """Get all discovered add-ons with metadata, using cache or scanning."""
    config = load_config()
    cache = load_addon_cache()

    if rescan or (not cache and config.get("addon_directories", [])):
        dirs = [Path(d) for d in config.get("addon_directories", [])]
        found_dirs = scan_addons_in_directories(dirs)
        new_cache: dict[Path, AddonMetadata] = {}
        for d in found_dirs:
            try:
                meta = InstallManifestParser(d).get_metadata()
                new_cache[d] = meta
            except (OSError, ET.ParseError, ValueError):
                continue
        save_addon_cache(new_cache)
        return new_cache

    return cache


def has_manifest(path: Path) -> bool:
    """Check if directory contains install.rdf directly or under src/."""
    return (path / "install.rdf").is_file() or (path / "src" / "install.rdf").is_file()


def resolve_addon_targets(
    target: str | None = None,
    all_addons: bool = False,
    rescan: bool = False,
) -> list[Path]:
    """Resolve a target name, path, or --all into a list of valid add-on paths."""
    if all_addons:
        addons_dict = get_all_addons(rescan=rescan)
        return sorted(addons_dict.keys())

    if target:
        direct_path = Path(target).resolve()
        if direct_path.is_dir() and has_manifest(direct_path):
            return [direct_path]

        addons_dict = get_all_addons(rescan=rescan)
        target_lower = target.lower()

        # 1. Exact folder name match
        matches = [p for p in addons_dict if p.name.lower() == target_lower]
        if matches:
            return matches

        # 2. Exact metadata ID or name match
        for p, meta in addons_dict.items():
            addon_id = meta.get("id", "").lower()
            addon_name = meta.get("name", "").lower()
            if target_lower in (addon_id, addon_name):
                return [p]

        # 3. Substring match on folder name or addon name
        matches = [
            p
            for p, meta in addons_dict.items()
            if target_lower in p.name.lower()
            or target_lower in meta.get("name", "").lower()
            or target_lower in meta.get("id", "").lower()
        ]
        if matches:
            return [matches[0]]

        return [direct_path]

    cwd = Path.cwd().resolve()
    if has_manifest(cwd):
        return [cwd]

    addons_dict = get_all_addons(rescan=rescan)
    if addons_dict:
        return sorted(addons_dict.keys())

    return []
