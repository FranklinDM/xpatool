from typing import Literal, TypedDict


class KnownAppInfo(TypedDict):
    name: str
    code: str
    default_max_version: str


class TargetApplication(TypedDict):
    id: str
    minVersion: str
    maxVersion: str


class AddonMetadata(TypedDict):
    id: str
    version: str
    name: str
    type: str
    targets: list[TargetApplication]
    manifest_path: str
    source_dir: str


class WorkspaceConfig(TypedDict):
    addon_directories: list[str]
    proxies_dir: str
    known_apps: dict[str, KnownAppInfo]


class PropertyEntryBase(TypedDict):
    type: Literal["property", "comment", "raw"]
    raw: str


class PropertyEntry(PropertyEntryBase, total=False):
    key: str
    separator: str
    value: str


class DtdEntryBase(TypedDict):
    type: Literal["entity", "comment", "raw"]
    raw: str


class DtdEntry(DtdEntryBase, total=False):
    name: str
    value: str


class ChromeLocaleEntry(TypedDict):
    package: str
    locale: str
    path: str
    resolved_path: str


# Type alias for locale sync reports: locale -> { relative_filepath: [added_keys] }
LocaleSyncReport = dict[str, dict[str, list[str]]]
