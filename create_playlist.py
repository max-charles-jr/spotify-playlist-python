import os
import re
import unicodedata

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Set this to the ID from the existing playlist's Spotify URL.
PLAYLIST_ID = "1Np6XavRdoHvUvsuGT3qXb"

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")

REDIRECT_URI = "http://127.0.0.1:27228"
SCOPE = "playlist-read-private playlist-modify-private"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# Search for tracks to append to the existing playlist.
songs_to_find = [
    "Rochelle Jordan Crave (Club Mix)",
    "Lucky Daye Nowhere Fast",
    "Jhene Aiko So Good (feat. Kendrick Lamar)",
    "Momo Boyd Oops",
    "Tone Stith Pageant Stage",
    "Kenyon Dixon Talk You Through It",
    "Chris Brown track:Obvious"    
]

# Search strings for tracks to remove from the playlist (same format as above).
# Matching is done against the tracks already in the playlist.
songs_to_remove = [   
]

# Set True to print what would be removed/added without changing the playlist.
DRY_RUN = False

def normalize_track_text(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def get_track_identity(track):
    identifiers = set()
    for candidate in (track, track.get("linked_from") or {}):
        for key in ("id", "uri"):
            if candidate.get(key):
                identifiers.add(candidate[key])

    isrc = track.get("external_ids", {}).get("isrc")
    artists = track.get("artists") or []
    title = normalize_track_text(track.get("name") or "")
    primary_artist = normalize_track_text(artists[0].get("name") or "") if artists else ""
    metadata = (title, primary_artist) if title and primary_artist else None
    return identifiers, isrc, metadata


def tracks_match(left, right):
    left_identifiers, left_isrc, left_metadata = left
    right_identifiers, right_isrc, right_metadata = right

    if left_identifiers & right_identifiers:
        return True
    if left_isrc and right_isrc:
        return left_isrc == right_isrc
    return left_metadata is not None and left_metadata == right_metadata


def get_playlist_track_identities(playlist_id):
    track_identities = []
    # No `fields` filter: a filter naming `track(...)` silently returns nothing
    # if the API calls that key `item` instead.
    response = sp.playlist_items(playlist_id, limit=100)

    while response:
        for entry in response["items"]:
            # Newer Spotify API versions use "item"; older ones use "track".
            track = entry.get("item") or entry.get("track")
            if track:
                track_identities.append((get_track_identity(track), track.get("uri")))

        if not response.get("next"):
            break
        response = sp.next(response)

    return track_identities


existing_track_identities = get_playlist_track_identities(PLAYLIST_ID)
print(f"Playlist currently has {len(existing_track_identities)} readable track(s).")
if not existing_track_identities:
    raise SystemExit("Could not read any existing tracks; aborting to avoid adding duplicates.")

# Remove tracks first.
uris_to_remove = []
for song in songs_to_remove:
    tracks = sp.search(q=song, type="track", limit=1)["tracks"]["items"]
    if not tracks:
        print(f"Could not find '{song}' on Spotify; nothing to remove.")
        continue
    identity = get_track_identity(tracks[0])
    matches = [uri for existing, uri in existing_track_identities
               if uri and tracks_match(identity, existing)]
    if not matches:
        print(f"Not in playlist, skipping removal: {tracks[0]['name']} by {tracks[0]['artists'][0]['name']}")
        continue
    uris_to_remove.extend(matches)
    print(f"Will remove: {tracks[0]['name']} by {tracks[0]['artists'][0]['name']}")

if uris_to_remove:
    uris_to_remove = list(dict.fromkeys(uris_to_remove))
    if not DRY_RUN:
        sp.playlist_remove_all_occurrences_of_items(PLAYLIST_ID, uris_to_remove)
        removed = set(uris_to_remove)
        existing_track_identities = [(i, u) for i, u in existing_track_identities if u not in removed]
    print(f"{'Would remove' if DRY_RUN else 'Removed'} {len(uris_to_remove)} track(s).")

track_uris_to_add = []
for song in songs_to_find:
    result = sp.search(q=song, type="track", limit=1)
    tracks = result["tracks"]["items"]
    if not tracks:
        continue

    track = tracks[0]
    track_identity = get_track_identity(track)
    if any(tracks_match(track_identity, existing) for existing, _ in existing_track_identities):
        print(f"Skipping already present track: {tracks[0]['name']} by {tracks[0]['artists'][0]['name']}")
        continue

    track_uris_to_add.append(track["uri"])
    existing_track_identities.append((track_identity, track["uri"]))
    print(f"Found: {tracks[0]['name']} by {tracks[0]['artists'][0]['name']}")

if track_uris_to_add:
    if not DRY_RUN:
        sp.playlist_add_items(PLAYLIST_ID, track_uris_to_add)
    print(f"{'Would add' if DRY_RUN else 'Added'} {len(track_uris_to_add)} new track(s) to the existing playlist.")
else:
    print("All matching tracks are already in the playlist; no changes were made.")