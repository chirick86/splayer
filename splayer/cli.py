import argparse
import sys
from .auth import setup, authenticate
from .device import get_current, get_last, force_current
from .player import play, pause, toggle, next_track, previous_track, set_volume, change_volume, print_volume
from .catalog import (
    parse_spotify_reference,
    print_default_search,
    print_artist_search,
    print_album_search,
    print_track_search,
    print_uri_lookup,
)
from .status import print_status
from .queue import show_queue, add_queue
from .playlist import (
    print_playlists,
    create_playlist,
    print_playlist_tracks,
    add_track_to_playlist,
    add_album_to_playlist,
    add_uris_to_playlist,
    add_to_active_playlist,
    add_current_track_to_playlist,
    set_default_playlist,
    play_playlist,
)


VERSION = "0.1.0"


def cmd_play(args):
    play()


def cmd_pause(args):
    pause()


def cmd_toggle(args):
    toggle()


def cmd_next(args):
    next_track()


def cmd_previous(args):
    previous_track()


def cmd_status(args):
    print_status()


def cmd_search(args):
    if args.uri:
        print_uri_lookup(args.uri)
    elif args.artist:
        print_artist_search(args.artist)
    elif args.album:
        print_album_search(args.album)
    elif args.track:
        print_track_search(args.track)
    elif args.query:
        query = " ".join(args.query).strip()
        parsed = parse_spotify_reference(query)

        if parsed:
            if parsed["source"] == "url":
                print_uri_lookup(parsed["uri"])
            else:
                print_uri_lookup(query)
        else:
            print_default_search(query)


def cmd_volume(args):
    if args.value:
        if args.value.startswith("+") or args.value.startswith("-"):
            change_volume(int(args.value))
        else:
            set_volume(int(args.value))
    elif args.up:
        change_volume(10)
    elif args.down:
        change_volume(-10)
    else:
        print_volume()


def cmd_auth(args):
    if args.client_id and args.client_secret and args.redirect_uri:
        setup(
            args.client_id,
            args.client_secret,
            args.redirect_uri
        )
        print("Credentials saved")
    else:
        print("Starting authentication")
    authenticate()
    print("Authentication successful")


def cmd_list(args):
    if args.new:
        create_playlist(args.new)
    elif args.default:
        set_default_playlist(args.default)
    elif args.add:
        if args.playlist:
            add_track_to_playlist(args.playlist, args.add)
        else:
            add_to_active_playlist(args.add)
    elif args.add_album:
        add_album_to_playlist(args.playlist, args.add_album)
    elif args.tracks:
        print_playlist_tracks(args.tracks)
    elif args.add_uris:
        uri_source = args.add_uris[0] if len(
            args.add_uris) == 1 else args.add_uris
        add_uris_to_playlist(args.playlist, uri_source)
    elif args.add_current:
        add_current_track_to_playlist(args.add_current)
    elif args.playlist:
        play_playlist(args.playlist)
    else:
        print_playlists()


def cmd_queue(args):
    if args.add:
        add_queue(args.add)
    else:
        show_queue()


def cmd_device(args):
    if args.force:
        device = force_current()
        print("Forced device:")
        print(device["name"])
        return

    if args.last:
        device = get_last()
    else:
        device = get_current()

    if device:
        print(device["name"])
        print(device["type"])
    else:
        print("No active device")


# ----------------
# MAIN FUNCTION
# ----------------
def main():
    parser = argparse.ArgumentParser(
        prog="splayer",
        description="Spotify command line player",
        epilog=(
            "Tip: run 'splayer <command> -h' to see help for any command.\n"
            "Playlist help examples: 'splayer list -h' or 'splayer list --help'"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION
    )
    subparsers = parser.add_subparsers(dest="command")

    # ----------------
    # control
    # ----------------
    p = subparsers.add_parser(
        "play",
        help="Start playback"
    )
    p.set_defaults(func=cmd_play)

    p = subparsers.add_parser("pause", help="Pause playback")
    p.set_defaults(func=cmd_pause)

    p = subparsers.add_parser("toggle", help="Toggle playback")
    p.set_defaults(func=cmd_toggle)

    p = subparsers.add_parser("next", aliases=["n"], help="Next track")
    p.set_defaults(func=cmd_next)

    p = subparsers.add_parser(
        "previous", aliases=["prev"], help="Previous track")
    p.set_defaults(func=cmd_previous)

    p = subparsers.add_parser("vol", aliases=["v"], help="Volume control")
    volume = p.add_mutually_exclusive_group()
    volume.add_argument("--up", action="store_true", help="Increase volume")
    volume.add_argument("--down", action="store_true", help="Decrease volume")
    p.add_argument("value", nargs="?",
                   help="Set volume or change by amount (+10/-10)")
    p.set_defaults(func=cmd_volume)

    # ----------------
    # auth
    # ----------------
    p = subparsers.add_parser(
        "auth", aliases=["a"], help="Spotify authentication")
    p.add_argument("--client-id", dest="client_id")
    p.add_argument("--client-secret", dest="client_secret")
    p.add_argument("--redirect-uri", dest="redirect_uri")
    p.set_defaults(func=cmd_auth)

    # ----------------
    # search
    # ----------------
    p = subparsers.add_parser(
        "search",
        aliases=["s"],
        help="Search Spotify catalog",
        description=(
            "Search Spotify catalog by artist, album, track, or exact URI.\n\n"
            "If you pass plain text after the command, it will be treated as a default Spotify search query.\n"
            "If that plain text is a Spotify URI or Spotify URL, the command will show exact info instead of searching.\n"
            "Use --uri only with a Spotify URI. Use --artist, --album, or --track "
            "with an artist/album/track name, Spotify URL, or Spotify URI."
        ),
        epilog=(
            "Examples:\n"
            "  splayer s Nirvana - Rape me\n"
            "  splayer s --artist nirvana\n"
            "  splayer s --album https://open.spotify.com/album/...\n"
            "  splayer s --track spotify:track:...\n"
            "  splayer s --uri spotify:artist:..."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    search_actions = p.add_mutually_exclusive_group()
    search_actions.add_argument(
        "--uri",
        metavar="<uri>",
        help="Lookup an exact Spotify URI only",
    )
    search_actions.add_argument(
        "--artist",
        metavar="<artistname|url|uri>",
        help="Search artists or resolve an exact artist URL/URI",
    )
    search_actions.add_argument(
        "--album",
        metavar="<albumname|url|uri>",
        help="Search albums or resolve an exact album URL/URI",
    )
    search_actions.add_argument(
        "--track",
        metavar="<trackname|url|uri>",
        help="Search tracks or resolve an exact track URL/URI",
    )
    p.add_argument(
        "query",
        nargs="*",
        help="Default Spotify search query when no sub-argument is supplied",
    )
    p.set_defaults(func=cmd_search)

    # ----------------
    # playlist
    # ----------------
    p = subparsers.add_parser(
        "list",
        aliases=["l"],
        help="Playlist operations",
        epilog=(
            "Examples:\n"
            "  splayer list BEST\n"
            "  splayer list -h\n"
            "  splayer list --help"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    playlist_actions = p.add_mutually_exclusive_group()
    playlist_actions.add_argument(
        "--new", metavar="NAME", help="Create a private playlist")
    playlist_actions.add_argument(
        "--default", metavar="PLAYLIST", help="Set default playlist by index, name, or URI")
    playlist_actions.add_argument(
        "--add", metavar="QUERY", help="Add track(s) by name, URL, or URI; supports: splayer list <playlist> --add <query>")
    playlist_actions.add_argument(
        "--add-album",
        metavar="ALBUM",
        help="Add album by album name, URL, or URI to the active or selected playlist",
    )
    playlist_actions.add_argument(
        "--tracks", metavar="PLAYLIST", help="Show tracks in a playlist by index, name, or URI")
    playlist_actions.add_argument(
        "--add-current", metavar="PLAYLIST", help="Add the current track to a playlist")
    playlist_actions.add_argument(
        "--add-uris",
        "-add-uris",
        nargs="+",
        metavar="URI|FILE",
        help="Add track URIs from a file path or inline sequence to the active or selected playlist",
    )
    p.add_argument(
        "playlist",
        nargs="?",
        help="Play playlist by index, name, or URI when no option is used",
    )
    p.set_defaults(func=cmd_list)

    # ----------------
    # queue
    # ----------------
    p = subparsers.add_parser("queue", aliases=["q"], help="Queue control")
    p.add_argument("--add", help="Add track to queue by name, URL, or URI")
    p.set_defaults(func=cmd_queue)

    # ----------------
    # status
    # ----------------
    p = subparsers.add_parser(
        "status",
        aliases=["info", "i"],
        help="Show current Spotify status"
    )
    p.set_defaults(func=cmd_status)

    # ----------------
    # device
    # ----------------
    p = subparsers.add_parser(
        "device", aliases=["d"], help="Device management")
    p.add_argument("--last", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_device)

    args = parser.parse_args()

    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
