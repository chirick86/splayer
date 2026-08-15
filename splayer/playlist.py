import time

from .catalog import resolve_spotify_uri, resolve_track_uris_for_add
from .config import load_config, update_config
from .spotify import ensure_device, get_client, spotify_call
from .uri_input import chunked, load_track_uris


def get_current_playlist(playback=None, sp=None):
    if playback is None:
        sp = sp or get_client()
        playback = spotify_call(sp.current_playback)

    if not playback:
        return None

    context = playback.get("context")

    if not context or context.get("type") != "playlist":
        return None

    return context


def get_playlist_info(playlist_uri, sp=None):
    sp = sp or get_client()
    return spotify_call(sp.playlist, playlist_uri, fields="name,uri")


def get_playlists(sp=None):
    sp = sp or get_client()
    playlists = []
    results = spotify_call(sp.current_user_playlists)

    while results:
        playlists.extend(results.get("items", []))

        if not results.get("next"):
            break

        results = spotify_call(sp.next, results)

    return playlists


def resolve_playlist(playlist_ref, sp=None):
    sp = sp or get_client()
    playlists = get_playlists(sp)

    if not playlists:
        return None

    if playlist_ref.isdigit():
        index = int(playlist_ref) - 1
        if 0 <= index < len(playlists):
            return playlists[index]
        raise ValueError("Playlist index out of range")

    for playlist in playlists:
        if playlist["uri"] == playlist_ref:
            return playlist

    for playlist in playlists:
        if playlist["name"].lower() == playlist_ref.lower():
            return playlist

    raise ValueError("Playlist not found")


def get_playlist_tracks(playlist_ref, sp=None):
    sp = sp or get_client()
    playlist = resolve_playlist(playlist_ref, sp)

    if not playlist:
        return None, []

    tracks = []
    results = spotify_call(
        sp.playlist_items,
        playlist["uri"],
        additional_types=("track",)
    )

    while results:
        tracks.extend(results.get("items", []))

        if not results.get("next"):
            break

        results = spotify_call(sp.next, results)

    return playlist, tracks


def print_playlists():
    sp = get_client()
    current_playlist = get_current_playlist(sp=sp)
    current_uri = current_playlist["uri"] if current_playlist else None
    default_uri = get_default_playlist_uri()
    playlists = get_playlists(sp)

    if not playlists:
        print("No playlists found")
        return

    for index, playlist in enumerate(playlists, 1):
        labels = []
        if playlist["uri"] == current_uri:
            labels.append("current")
        if playlist["uri"] == default_uri:
            labels.append("default")

        suffix = f" ({', '.join(labels)})" if labels else ""
        print(f'{index}. {playlist["name"]}{suffix}')


def print_playlist_tracks(playlist_ref):
    sp = get_client()
    playlist, tracks = get_playlist_tracks(playlist_ref, sp)

    if not playlist:
        print("No playlists found")
        return

    print(playlist["name"])

    if not tracks:
        print("No tracks found")
        return

    for index, item in enumerate(tracks, 1):
        track = item.get("track") if item else None

        if not track:
            continue

        artists = ", ".join(artist["name"]
                            for artist in track.get("artists", []))
        print(f'{index}. {artists} - {track["name"]}')


def _chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _select_target_playlist(sp):
    current_context = get_current_playlist(sp=sp)
    current = get_playlist_info(
        current_context["uri"], sp=sp
    ) if current_context else None
    default_uri = get_default_playlist_uri()
    default_playlist = get_playlist_info(
        default_uri, sp=sp) if default_uri else None

    if current and default_playlist and current["uri"] != default_playlist["uri"]:
        print("Choose target playlist for add:")
        print(
            f'c - current: {current.get("name", current.get("uri"))}')
        print(
            f'd - default: {default_playlist.get("name", default_playlist.get("uri"))}')
        while True:
            try:
                answer = input("Select [c/d]: ").strip().lower()
            except EOFError:
                answer = "c"

            if answer == "c":
                return current
            if answer == "d":
                return default_playlist

            print("Please enter c or d")

    if current:
        return current
    if default_playlist:
        return default_playlist

    return None


def _resolve_target_playlist(sp, playlist_ref=None):
    if playlist_ref:
        return resolve_playlist(playlist_ref, sp)
    return _select_target_playlist(sp)


def add_track_to_playlist(playlist_ref, track_ref):
    sp = get_client()
    playlist = _resolve_target_playlist(sp, playlist_ref)

    if not playlist:
        print("No target playlist selected")
        return

    track_uris = resolve_track_uris_for_add(track_ref, sp=sp)

    for chunk in _chunked(track_uris, 100):
        spotify_call(sp.playlist_add_items, playlist["uri"], chunk)

    print(f'Added {len(track_uris)} track(s) to playlist: {playlist["name"]}')


def add_album_to_playlist(playlist_ref, album_ref):
    sp = get_client()
    playlist = _resolve_target_playlist(sp, playlist_ref)

    if not playlist:
        print("No target playlist selected")
        return

    album_uri = resolve_spotify_uri(album_ref, "album", sp=sp)
    track_uris = resolve_track_uris_for_add(album_uri, sp=sp)

    for chunk in _chunked(track_uris, 100):
        spotify_call(sp.playlist_add_items, playlist["uri"], chunk)

    print(
        f'Added album ({len(track_uris)} track(s)) to playlist: {playlist["name"]}')


def add_uris_to_playlist(playlist_ref, uri_source):
    sp = get_client()
    playlist = _resolve_target_playlist(sp, playlist_ref)

    if not playlist:
        print("No target playlist selected")
        return

    source_uris = load_track_uris(uri_source)
    track_uris = []
    seen = set()
    skipped_sources = []

    for source_uri in source_uris:
        try:
            resolved_uris = resolve_track_uris_for_add(source_uri, sp=sp)
        except ValueError as exc:
            skipped_sources.append((source_uri, str(exc)))
            continue

        for track_uri in resolved_uris:
            if track_uri in seen:
                continue
            seen.add(track_uri)
            track_uris.append(track_uri)

    if skipped_sources:
        print(f"Skipped {len(skipped_sources)} source URI(s):")
        for source_uri, reason in skipped_sources:
            print(f"- {source_uri}: {reason}")

    if not track_uris:
        print("No track URIs resolved from provided sources")
        return

    total = len(track_uris)
    print("adding uris...")

    chunks = list(chunked(track_uris, 100))
    for index, chunk in enumerate(chunks):
        spotify_call(sp.playlist_add_items, playlist["uri"], chunk)
        added = min((index + 1) * 100, total)
        print(f"\radded {added}/{total}", end="", flush=True)
        if index < len(chunks) - 1:
            time.sleep(1)

    print()

    print(f'Added {len(track_uris)} track(s) to playlist: {playlist["name"]}')


def add_to_active_playlist(track_ref):
    add_track_to_playlist(None, track_ref)


def add_current_track_to_playlist(playlist_ref):
    sp = get_client()
    playback = spotify_call(sp.current_playback)

    if not playback or not playback.get("item"):
        print("No current track found")
        return

    track = playback["item"]
    add_track_to_playlist(playlist_ref, track["uri"])


def create_playlist(name):
    name = name.strip()

    if not name:
        raise ValueError("Playlist name cannot be empty")

    sp = get_client()
    user = spotify_call(sp.current_user)

    if not user:
        return

    playlist = spotify_call(
        sp.current_user_playlist_create,
        name,
        public=False
    )

    if playlist:
        print(f'Created playlist: {playlist["name"]}')


def get_default_playlist_uri():
    config = load_config()
    return config.get("default_playlist_uri")


def set_default_playlist(playlist_ref):
    sp = get_client()
    playlist = resolve_playlist(playlist_ref, sp)

    if not playlist:
        print("Playlist not found")
        return

    update_config({"default_playlist_uri": playlist["uri"]})
    print(f'Set default playlist: {playlist["name"]}')


def play_playlist(playlist_ref):
    sp = get_client()
    playlist = resolve_playlist(playlist_ref, sp)

    if not playlist:
        print("Playlist not found")
        return

    device = ensure_device()

    if device:
        spotify_call(sp.start_playback, device_id=device,
                     context_uri=playlist["uri"])
    else:
        spotify_call(sp.start_playback, context_uri=playlist["uri"])

    print(f'Playing playlist: {playlist["name"]}')
