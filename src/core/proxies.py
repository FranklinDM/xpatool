import platform
from pathlib import Path


def get_default_proxies_dir(base_dir: str | Path | None = None) -> Path:
    """Get the default proxies directory with the current OS name."""
    base = Path(base_dir).resolve() if base_dir else Path.cwd()
    os_name = platform.system().lower()
    return base / "_proxies" / os_name


def generate_proxies(
    addon_id: str,
    source_dir: str | Path,
    proxies_dir: str | Path | None = None,
) -> tuple[str, str]:
    """
    Generates a proxy pointer file for the current OS.
    File named after addon_id, containing absolute path to source directory.
    """
    if not addon_id:
        raise ValueError("Addon ID cannot be empty")

    abs_src = Path(source_dir).resolve()
    target_dir = (
        Path(proxies_dir).resolve() if proxies_dir else get_default_proxies_dir()
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    proxy_file = target_dir / addon_id
    with proxy_file.open("w", encoding="utf-8") as f:
        f.write(str(abs_src))

    return str(proxy_file), str(abs_src)
