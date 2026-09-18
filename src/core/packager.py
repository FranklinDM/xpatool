import os
import re
import zipfile
from pathlib import Path

from config import DEFAULT_KNOWN_APPS
from parsers.install_manifest import InstallManifestParser


def build_xpi(
    source_dir: str | Path,
    output_dir: str | Path | None = None,
    package_name: str | None = None,
    ref_type: str | None = None,
    commit_sha: str | None = None,
    app_map: dict[str, str] | None = None,
    write_github_output: bool = False,
) -> tuple[str, str, bool]:
    src_path = Path(source_dir).resolve()
    manifest = InstallManifestParser(src_path)
    meta = manifest.get_metadata()

    base_version = meta["version"]
    if not base_version:
        raise ValueError("Could not find <em:version> in install.rdf")

    is_prerelease = bool(re.search(r"[0-9](a|b|rc)[0-9]+$", base_version))

    resolved_ref_type = (
        ref_type if ref_type is not None else os.environ.get("REF_TYPE", "")
    )
    resolved_sha = commit_sha if commit_sha is not None else os.environ.get("SHA", "")
    short_sha = resolved_sha[:7] if resolved_sha else "dev"

    if resolved_ref_type == "tag":
        final_version = base_version
        print(f"Tagged release detected. Keeping version: {final_version}")
    else:
        final_version = f"{base_version}.{short_sha}"
        print(f"Non-tag build detected. Updating version to: {final_version}")

    default_apps_mapping = {
        guid: info["code"] for guid, info in DEFAULT_KNOWN_APPS.items()
    }
    apps_mapping = app_map if app_map is not None else default_apps_mapping

    detected_apps: list[str] = []
    for target in meta["targets"]:
        guid = target["id"].lower()
        if guid in apps_mapping and apps_mapping[guid] not in detected_apps:
            detected_apps.append(apps_mapping[guid])

    app_suffix = "+".join(detected_apps) if detected_apps else "unknown"

    if not package_name:
        package_name = os.environ.get("PACKAGE_NAME", "")
        if not package_name:
            addon_id = meta.get("id", "")
            if addon_id:
                package_name = addon_id.split("@")[0]
            else:
                package_name = "addon"

    xpi_filename = f"{package_name}-{final_version}-{app_suffix}.xpi"
    out_path = Path(output_dir).resolve() if output_dir else Path.cwd()
    xpi_filepath = out_path / xpi_filename

    print(f"Building: {xpi_filename}")

    manifest_data = manifest.get_manifest_bytes(version=final_version)
    manifest_resolved = manifest.manifest_path.resolve()

    with zipfile.ZipFile(xpi_filepath, "w", zipfile.ZIP_DEFLATED) as xpi:
        for file in src_path.rglob("*"):
            if not file.is_file():
                continue
            if ".git" in file.parts or ".github" in file.parts:
                continue
            if file.resolve() == xpi_filepath.resolve():
                continue
            arcname = file.relative_to(src_path).as_posix()
            if file.resolve() == manifest_resolved:
                xpi.writestr(arcname, manifest_data)
            else:
                xpi.write(file, arcname)

    if write_github_output and "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out_file:
            out_file.write(f"xpi_filename={xpi_filename}\n")
            out_file.write(f"is_prerelease={'true' if is_prerelease else 'false'}\n")

    return str(xpi_filepath), final_version, is_prerelease
