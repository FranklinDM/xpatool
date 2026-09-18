import json
from pathlib import Path
from typing import cast

from models import AddonMetadata, KnownAppInfo, WorkspaceConfig

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "xpatool" / "config.json"
DEFAULT_CACHE_PATH = Path.home() / ".config" / "xpatool" / "cache.json"
APPS_JSON_PATH = Path(__file__).parent / "apps.json"


def load_default_known_apps() -> dict[str, KnownAppInfo]:
    if APPS_JSON_PATH.is_file():
        try:
            with APPS_JSON_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError):
            pass
    return {}


DEFAULT_KNOWN_APPS: dict[str, KnownAppInfo] = load_default_known_apps()


def load_config(config_file: str | Path | None = None) -> WorkspaceConfig:
    path = Path(config_file) if config_file else DEFAULT_CONFIG_PATH
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    raw_dirs = data.get("addon_directories", [])
                    return WorkspaceConfig(
                        addon_directories=[str(d) for d in raw_dirs]
                        if isinstance(raw_dirs, list)
                        else [],
                        proxies_dir=str(data.get("proxies_dir", "")),
                        known_apps=data.get("known_apps", DEFAULT_KNOWN_APPS),
                    )
        except (OSError, json.JSONDecodeError):
            pass
    return WorkspaceConfig(
        addon_directories=[],
        proxies_dir="",
        known_apps=DEFAULT_KNOWN_APPS,
    )


def save_config(config: WorkspaceConfig, config_file: str | Path | None = None) -> None:
    path = Path(config_file) if config_file else DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_addon_cache(cache_file: str | Path | None = None) -> dict[Path, AddonMetadata]:
    path = Path(cache_file) if cache_file else DEFAULT_CACHE_PATH
    cache: dict[Path, AddonMetadata] = {}
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for path_str, meta in data.items():
                        p = Path(path_str)
                        if p.is_dir() and isinstance(meta, dict):
                            cache[p] = cast(AddonMetadata, meta)
        except (OSError, json.JSONDecodeError):
            pass
    return cache


def save_addon_cache(
    cache: dict[Path, AddonMetadata], cache_file: str | Path | None = None
) -> None:
    path = Path(cache_file) if cache_file else DEFAULT_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {str(p): meta for p, meta in cache.items()}
    with path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
