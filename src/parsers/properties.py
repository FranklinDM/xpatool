import re
from pathlib import Path

from models import PropertyEntry


class PropertiesParser:
    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.entries: list[PropertyEntry] = []
        self.keys: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self.entries.clear()
        self.keys.clear()
        if not self.filepath.is_file():
            return

        with self.filepath.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped or stripped.startswith(("#", "!")):
                self.entries.append({"type": "comment", "raw": line})
                i += 1
                continue

            full_line = line
            while full_line.rstrip("\r\n").endswith("\\") and i + 1 < len(lines):
                i += 1
                full_line += lines[i]

            match = re.search(r"(\s*[^\s:=]+)(\s*[:=]\s*)(.*)", full_line, re.DOTALL)
            if match:
                key = match.group(1).strip()
                separator = match.group(2)
                value = match.group(3).rstrip("\r\n")
                self.entries.append(
                    {
                        "type": "property",
                        "key": key,
                        "separator": separator,
                        "value": value,
                        "raw": full_line,
                    }
                )
                self.keys[key] = value
            else:
                self.entries.append({"type": "raw", "raw": full_line})
            i += 1

    def add_property(self, key: str, value: str, comment: str | None = None) -> None:
        if comment:
            self.entries.append({"type": "comment", "raw": f"\n# {comment}\n"})
        self.entries.append(
            {
                "type": "property",
                "key": key,
                "separator": "=",
                "value": value,
                "raw": f"{key}={value}\n",
            }
        )
        self.keys[key] = value

    def save(self, filepath: str | Path | None = None) -> None:
        path = Path(filepath) if filepath else self.filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for entry in self.entries:
                if entry["type"] in ("comment", "raw"):
                    f.write(entry["raw"])
                elif entry["type"] == "property":
                    k = entry.get("key", "")
                    sep = entry.get("separator", "=")
                    v = entry.get("value", "")
                    f.write(f"{k}{sep}{v}\n")
