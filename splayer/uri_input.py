from pathlib import Path

from .catalog import ensure_spotify_uri


_SCRIPT_DIR = Path(__file__).resolve().parent


def _read_uri_file(file_path):
    uris = []

    with file_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            uris.append(value)

    return uris


def _resolve_uri_file(source):
    path = Path(source).expanduser()
    candidates = []

    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append(_SCRIPT_DIR / path)
        candidates.append(Path.cwd() / path)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def load_track_uris(source):
    if isinstance(source, str):
        file_path = _resolve_uri_file(source)
        raw_items = _read_uri_file(file_path) if file_path else [source]
    elif isinstance(source, (list, tuple)):
        raw_items = list(source)
    else:
        try:
            raw_items = list(source)
        except TypeError:
            raw_items = [source]

    uris = []
    for item in raw_items:
        value = str(item).strip()
        if not value:
            continue
        uris.append(
            ensure_spotify_uri(value, allowed_types=(
                "track", "album", "artist"))
        )

    if not uris:
        raise ValueError("No Spotify URIs provided")

    return uris


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]
