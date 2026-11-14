# Spotify Playlist Updater

A small Python script that adds and removes tracks on an existing Spotify playlist. You give it search strings like `"Artist Song Title"`. It finds each track, skips any already in the playlist (no duplicates), and applies the changes.

## Setup

1. **Create a Spotify app** at <https://developer.spotify.com/dashboard>. Add this Redirect URI: `http://127.0.0.1:27228`
2. **Install dependencies** (Python 3.9+):
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install spotipy
   ```
3. **Set your credentials** as environment variables:
   ```bash
   export SPOTIFY_CLIENT_ID="your-client-id"
   export SPOTIFY_CLIENT_SECRET="your-client-secret"
   ```

## Usage

Edit the song lists in the text files next to the script. Put one search string per line. Blank lines and lines starting with `#` are ignored.

| File | Purpose |
| --- | --- |
| `songs_to_find.txt` | Search strings for tracks to add |
| `songs_to_remove.txt` | Search strings for tracks to remove |

Two settings stay at the top of [create_playlist.py](create_playlist.py):

| Setting | Purpose |
| --- | --- |
| `PLAYLIST_ID` | ID of the playlist to update (the part of the playlist URL after `/playlist/`) |
| `DRY_RUN` | `True` prints the planned changes without modifying the playlist |

Then run:

```bash
python create_playlist.py
```

On the first run, a browser window opens so you can authorize the app. The token is cached in `.cache`, so later runs don't ask again. Don't commit that file.

Tips:
- Try with `DRY_RUN = True` first.
- Spotify search filters work in search strings, e.g. `"Chris Brown track:Obvious"`.
- Only the top search result is used for each string. Check the printed `Found:` lines to confirm the matches.

## How it works

- Reads the playlist's current tracks. If it can't read any, it aborts to avoid adding duplicates.
- Removes tracks from `songs_to_remove` that are actually in the playlist.
- Adds tracks from `songs_to_find` that aren't already there. Duplicates are detected by Spotify ID, then ISRC, then normalized title and artist.

## GitHub Actions

[.github/workflows/update_playlist.yml](.github/workflows/update_playlist.yml) runs the script manually (Actions tab → *Update playlist* → *Run workflow*).

Known problems with the workflow as written:
- It passes `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`, but the script reads `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`. Rename one side to match.
- The OAuth login needs a browser, which CI doesn't have. To make it work, generate the `.cache` token locally and restore it in the workflow, for example from a secret.
