"""Install local test guards before pytest or test modules import application code."""
import builtins
import io
import os
from pathlib import Path
import socket
import urllib.request


_INSTALLED = False
_ROOT = Path(__file__).resolve().parents[1]
_ORIGINAL_OPEN = builtins.open
_ORIGINAL_IO_OPEN = io.open
_ORIGINAL_OS_OPEN = os.open


def _prohibited(file) -> bool:
    if isinstance(file, int):
        return False
    try:
        path = Path(os.fspath(file)).resolve(strict=False)
    except (TypeError, ValueError, OSError):
        return False
    name = path.name.casefold()
    if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
        return True
    parts = {part.casefold() for part in path.parts}
    if "careflow_whatsapp" in parts or any("careflow-client-artifacts" in part for part in parts):
        return True
    if path == (_ROOT / "profiles" / "scheduleflow.json"):
        return False  # This repository fixture is synthetic, not client data.
    return any(path.is_relative_to(_ROOT / folder) for folder in
               ("profiles", "reports", "evals", "data", "releases", "patches", "sql"))


def _guard_open(original):
    def guarded(file, *args, **kwargs):
        if _prohibited(file):
            raise PermissionError("Prohibited credential or client-artifact path in tests")
        return original(file, *args, **kwargs)
    return guarded


def _blocked(*args, **kwargs):
    raise AssertionError("Credential-file loading and network access are disabled in tests")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for name in ("GEMINI_API_KEY", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                 "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SECRET_KEY",
                 "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "CareFlow_ANALYTICS_RO_URL"):
        os.environ[name] = ""
    builtins.open = _guard_open(_ORIGINAL_OPEN)
    io.open = _guard_open(_ORIGINAL_IO_OPEN)
    os.open = _guard_open(_ORIGINAL_OS_OPEN)
    socket.getaddrinfo = _blocked
    socket.create_connection = _blocked
    socket.socket.connect = _blocked
    socket.socket.connect_ex = _blocked
    socket.socket.sendto = _blocked
    urllib.request.urlopen = _blocked

    import dotenv
    import dotenv.main
    dotenv.load_dotenv = _blocked
    dotenv.dotenv_values = _blocked
    dotenv.main.load_dotenv = _blocked
    dotenv.main.dotenv_values = _blocked

    # Test-module imports bind this mocked loader. The fallback guard above
    # also prevents a forgotten direct file read from reaching client data.
    from _synthetic_profiles import care_profile
    from founderreach import profiles
    real_loader = profiles.load_profile

    def synthetic_loader(identifier, directory=None):
        if identifier == "careflow" and directory is None:
            return care_profile()
        if directory is None:
            return real_loader(identifier)
        return real_loader(identifier, directory)

    profiles.load_profile = synthetic_loader
