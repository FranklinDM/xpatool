import xml.etree.ElementTree as ET
from pathlib import Path

from models import AddonMetadata, TargetApplication

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "em": "http://www.mozilla.org/2004/em-rdf#",
}

ET.register_namespace("", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
ET.register_namespace("em", "http://www.mozilla.org/2004/em-rdf#")


class InstallManifestParser:
    def __init__(self, target_dir: str | Path) -> None:
        self.target_dir = Path(target_dir).resolve()
        found_path = self._find_manifest_path(self.target_dir)
        if not found_path:
            raise FileNotFoundError(
                f"install.rdf not found in {self.target_dir} or {self.target_dir / 'src'}"
            )
        self.manifest_path: Path = found_path
        self.tree = ET.parse(self.manifest_path)
        self.root = self.tree.getroot()

    def _find_manifest_path(self, target_dir: Path) -> Path | None:
        direct = target_dir / "install.rdf"
        if direct.is_file():
            return direct

        ignored_parts = {".git", ".github", "_profile", "_proxies"}
        for match in sorted(
            target_dir.rglob("install.rdf"), key=lambda p: len(p.parts)
        ):
            if not ignored_parts.intersection(match.parts):
                return match
        return None

    def get_source_dir(self) -> Path:
        return self.manifest_path.parent

    def get_metadata(self) -> AddonMetadata:
        addon_id_elem = self.root.find(".//em:id", NS)
        version_elem = self.root.find(".//em:version", NS)
        name_elem = self.root.find(".//em:name", NS)
        type_elem = self.root.find(".//em:type", NS)

        addon_id = (
            addon_id_elem.text.strip()
            if (addon_id_elem is not None and addon_id_elem.text)
            else ""
        )
        version = (
            version_elem.text.strip()
            if (version_elem is not None and version_elem.text)
            else ""
        )
        name = (
            name_elem.text.strip() if (name_elem is not None and name_elem.text) else ""
        )
        addon_type = (
            type_elem.text.strip()
            if (type_elem is not None and type_elem.text)
            else "2"
        )

        targets = self.get_target_applications()

        return AddonMetadata(
            id=addon_id,
            version=version,
            name=name,
            type=addon_type,
            targets=targets,
            manifest_path=str(self.manifest_path),
            source_dir=str(self.get_source_dir()),
        )

    def get_target_applications(self) -> list[TargetApplication]:
        targets: list[TargetApplication] = []
        for target_node in self.root.findall(".//em:targetApplication", NS):
            desc = target_node.find("Description", NS)
            if desc is None:
                desc = target_node.find("rdf:Description", NS)
            if desc is None:
                desc = target_node

            id_el = desc.find("em:id", NS)
            min_el = desc.find("em:minVersion", NS)
            max_el = desc.find("em:maxVersion", NS)

            guid = id_el.text.strip() if (id_el is not None and id_el.text) else ""
            min_v = min_el.text.strip() if (min_el is not None and min_el.text) else ""
            max_v = max_el.text.strip() if (max_el is not None and max_el.text) else ""

            if guid:
                targets.append(
                    TargetApplication(
                        id=guid,
                        minVersion=min_v,
                        maxVersion=max_v,
                    )
                )
        return targets

    def update_max_versions(
        self, version_updates: dict[str, str]
    ) -> list[tuple[str, str, str]]:
        changes: list[tuple[str, str, str]] = []
        for target_node in self.root.findall(".//em:targetApplication", NS):
            desc = target_node.find("Description", NS)
            if desc is None:
                desc = target_node.find("rdf:Description", NS)
            if desc is None:
                desc = target_node

            id_el = desc.find("em:id", NS)
            if id_el is None or not id_el.text:
                continue

            guid = id_el.text.strip().lower()
            if guid in version_updates:
                new_max = version_updates[guid]
                max_el = desc.find("em:maxVersion", NS)
                old_max = (
                    max_el.text.strip() if (max_el is not None and max_el.text) else ""
                )
                if max_el is None:
                    max_el = ET.SubElement(
                        desc, "{http://www.mozilla.org/2004/em-rdf#}maxVersion"
                    )
                max_el.text = new_max
                changes.append((guid, old_max, new_max))

        if changes:
            self.save()
        return changes

    def update_version(self, new_version: str) -> None:
        version_elem = self.root.find(".//em:version", NS)
        if version_elem is not None:
            version_elem.text = new_version
            self.save()

    def save(self) -> None:
        self.tree.write(self.manifest_path, encoding="utf-8", xml_declaration=True)
