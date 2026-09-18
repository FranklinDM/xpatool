import re
from pathlib import Path

from models import DtdEntry


class DtdParser:
    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.entities: list[DtdEntry] = []
        self.keys: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self.entities.clear()
        self.keys.clear()
        if not self.filepath.is_file():
            return

        with self.filepath.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Tokenize XML entity declarations: <!ENTITY entityName "entityValue">
        pattern = re.compile(
            r'(<!--.*?-->)|(<!ENTITY\s+([a-zA-Z0-9_.\-]+)\s+("([^"]*)"|\'([^\']*)\')\s*>)',
            re.DOTALL,
        )

        last_pos = 0
        for match in pattern.finditer(content):
            start, end = match.span()
            if start > last_pos:
                leading = content[last_pos:start]
                self.entities.append({"type": "raw", "raw": leading})

            comment_match = match.group(1)
            entity_match = match.group(2)

            if comment_match:
                self.entities.append({"type": "comment", "raw": comment_match})
            elif entity_match:
                entity_name = match.group(3)
                entity_val = (
                    match.group(5) if match.group(5) is not None else match.group(6)
                )
                self.entities.append(
                    {
                        "type": "entity",
                        "name": entity_name,
                        "value": entity_val,
                        "raw": entity_match,
                    }
                )
                self.keys[entity_name] = entity_val
            last_pos = end

        if last_pos < len(content):
            self.entities.append({"type": "raw", "raw": content[last_pos:]})

    def add_entity(self, name: str, value: str, comment: str | None = None) -> None:
        if comment:
            self.entities.append({"type": "comment", "raw": f"\n<!-- {comment} -->\n"})
        val_escaped = value.replace('"', "&quot;")
        self.entities.append(
            {
                "type": "entity",
                "name": name,
                "value": value,
                "raw": f'<!ENTITY {name} "{val_escaped}">\n',
            }
        )
        self.keys[name] = value

    def sort_entities(self) -> None:
        first_entity_idx = -1
        for i, entry in enumerate(self.entities):
            if entry["type"] == "entity":
                first_entity_idx = i
                break

        if first_entity_idx == -1:
            return

        header_entries = self.entities[:first_entity_idx]
        entity_entries: list[DtdEntry] = []
        for entry in self.entities[first_entity_idx:]:
            if entry["type"] == "entity":
                name = entry.get("name", "")
                value = entry.get("value", "")
                val_escaped = value.replace('"', "&quot;")
                entry["raw"] = f'<!ENTITY {name} "{val_escaped}">\n'
                entity_entries.append(entry)

        entity_entries.sort(key=lambda e: e.get("name", "").lower())
        self.entities = list(header_entries) + entity_entries

    def save(self, filepath: str | Path | None = None) -> None:
        path = Path(filepath) if filepath else self.filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for entry in self.entities:
                if entry["type"] in ("comment", "raw"):
                    f.write(entry["raw"])
                elif entry["type"] == "entity":
                    raw = entry.get("raw", "")
                    if not raw.endswith("\n"):
                        raw += "\n"
                    f.write(raw)
