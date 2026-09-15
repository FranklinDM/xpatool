import re
from pathlib import Path

from models import ChromeLocaleEntry


class ChromeManifestParser:
    def __init__(self, root_manifest_path: str | Path) -> None:
        self.root_manifest_path = Path(root_manifest_path).resolve()
        self.locales: list[ChromeLocaleEntry] = []
        self._parsed_files: set[Path] = set()
        self._parse_manifest_recursive(self.root_manifest_path)

    def _parse_manifest_recursive(self, manifest_file: Path) -> None:
        if not manifest_file.is_file() or manifest_file in self._parsed_files:
            return
        self._parsed_files.add(manifest_file)

        manifest_dir = manifest_file.parent
        try:
            with manifest_file.open("r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return

        lines = content.splitlines()
        for raw_line in lines:
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            parts = re.split(r"\s+", line)
            if not parts:
                continue

            directive = parts[0].lower()
            if directive == "manifest" and len(parts) >= 2:
                linked = parts[1]
                sub_manifest = (manifest_dir / linked).resolve()
                self._parse_manifest_recursive(sub_manifest)

            elif directive == "locale" and len(parts) >= 4:
                pkg_name = parts[1]
                locale_code = parts[2]
                raw_path = parts[3]

                clean_path = raw_path
                if clean_path.startswith("jar:"):
                    clean_path = clean_path.split("!", 1)[-1].lstrip("/")

                resolved = (manifest_dir / clean_path).resolve()
                self.locales.append(
                    ChromeLocaleEntry(
                        package=pkg_name,
                        locale=locale_code,
                        path=raw_path,
                        resolved_path=str(resolved),
                    )
                )


def find_chrome_manifest(directory: Path) -> Path | None:
    direct = directory / "chrome.manifest"
    if direct.is_file():
        return direct

    ignored_parts = {".git", ".github", "_profile", "_proxies"}
    for match in sorted(directory.rglob("chrome.manifest"), key=lambda p: len(p.parts)):
        if match.is_file() and not ignored_parts.intersection(match.parts):
            return match
    return None
