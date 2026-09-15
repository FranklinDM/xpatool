from core.locales import get_addon_locales, sync_locales
from core.packager import build_xpi
from core.proxies import generate_proxies

__all__ = [
    "build_xpi",
    "generate_proxies",
    "get_addon_locales",
    "sync_locales",
]
