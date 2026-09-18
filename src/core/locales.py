from pathlib import Path

from models import LocaleSyncReport
from parsers.chrome_manifest import ChromeManifestParser, find_chrome_manifest
from parsers.dtd import DtdParser
from parsers.properties import PropertiesParser


def get_addon_locales(source_dir: Path) -> list[str]:
    manifest_path = find_chrome_manifest(source_dir)
    if not manifest_path:
        return []
    parser = ChromeManifestParser(manifest_path)
    seen: set[str] = set()
    result: list[str] = []
    for entry in parser.locales:
        loc = entry["locale"]
        if loc not in seen:
            seen.add(loc)
            result.append(loc)
    return sorted(result)


def sync_locales(source_dir: Path, base_locale: str = "en-US") -> LocaleSyncReport:
    manifest_path = find_chrome_manifest(source_dir)
    if not manifest_path:
        return {}

    parser = ChromeManifestParser(manifest_path)
    by_package: dict[str, dict[str, Path]] = {}
    for entry in parser.locales:
        pkg = entry["package"]
        loc = entry["locale"]
        loc_path = Path(entry["resolved_path"])
        if loc_path.is_dir():
            if pkg not in by_package:
                by_package[pkg] = {}
            by_package[pkg][loc] = loc_path

    report: LocaleSyncReport = {}

    for pkg, locales_map in by_package.items():
        if base_locale not in locales_map:
            continue

        base_dir = locales_map[base_locale]
        for loc, target_dir in locales_map.items():
            if loc == base_locale:
                continue

            if loc not in report:
                report[loc] = {}

            for file in base_dir.rglob("*"):
                if not file.is_file():
                    continue

                rel_path = file.relative_to(base_dir)
                target_file = target_dir / rel_path

                if file.suffix == ".dtd":
                    added = _sync_dtd_file(file, target_file)
                    if added:
                        report[loc][str(rel_path)] = added

                elif file.suffix == ".properties":
                    added = _sync_properties_file(file, target_file)
                    if added:
                        report[loc][str(rel_path)] = added

    return report


def _sync_dtd_file(base_file: Path, target_file: Path) -> list[str]:
    base_dtd = DtdParser(base_file)
    target_dtd = DtdParser(target_file) if target_file.is_file() else DtdParser("")

    missing: list[str] = []
    for key, val in base_dtd.keys.items():
        if key not in target_dtd.keys:
            target_dtd.add_entity(key, val)
            missing.append(key)

    if missing:
        target_dtd.save(target_file)
    return missing


def _sync_properties_file(base_file: Path, target_file: Path) -> list[str]:
    base_prop = PropertiesParser(base_file)
    target_prop = (
        PropertiesParser(target_file) if target_file.is_file() else PropertiesParser("")
    )

    missing: list[str] = []
    for key, val in base_prop.keys.items():
        if key not in target_prop.keys:
            target_prop.add_property(key, val)
            missing.append(key)

    if missing:
        target_prop.save(target_file)
    return missing
