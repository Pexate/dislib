"""
Discogs metadata fetcher.
"""

from config import SCRAPERS_DIR
import discogs_client
import time
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(SCRAPERS_DIR / ".env")


# --- Setup -------------------------------------------------------------

USER_TOKEN = os.environ.get("DISCOGS_TOKEN")

d = discogs_client.Client("dislib/0.1", user_token=USER_TOKEN)


# --- Fetchers ------------------------------------------------------------

def _normalize_name(name):
    """Normalize names for case- and punctuation-insensitive comparisons."""
    return re.sub(r"[^a-z0-9]", "", name.casefold())

def search_artist(name, limit=5):
    """Search for an artist by name."""
    results = d.search(name, type="artist")
    artists = list(results.page(0))
    normalized_name = _normalize_name(name)
    artists.sort(
        key=lambda artist: _normalize_name(getattr(artist, "name", ""))
        != normalized_name
    )
    return artists[:limit]


def get_artist_releases(artist_id, limit=100):
    """Get releases for an artist by their Discogs ID."""
    artist = d.artist(artist_id)
    releases = []
    for r in artist.releases:
        releases.append(r)
        if len(releases) >= limit:
            break
    return releases


def get_release_details(release_id):
    """
    Fetch genre/style/label/credit data for a specific release.
    """
    release = d.release(release_id)
    return {
        "source": "discogs",
        "id": release_id,
        "title": release.title,
        "artists": [
            {"id": artist.id, "name": artist.name}
            for artist in (release.artists or [])
        ],
        "year": getattr(release, "year", None),
        "genres": list(release.genres or []),
        "styles": list(release.styles or []),
        "labels": [l.name for l in (release.labels or [])],
        "country": getattr(release, "country", None),
    }


def _release_belongs_to_artist(details, artist_id):
    """Keep only releases credited to the selected Discogs artist."""
    return any(artist["id"] == artist_id for artist in details["artists"])


def fetch_artist_full(artist_name):
    """
    Convenience function: search for an artist, pull their releases and
    aggregate genre/style tags across them. Returns None if no match.
    """
    matches = search_artist(artist_name, limit=1)
    if not matches:
        return None
    
    artist = matches[0]

    releases = get_artist_releases(artist.id, limit=25)

    release_data = []
    all_styles = set()
    all_genres = set()

    for r in releases:
        time.sleep(1)  # respect rate limit
        try:
            details = get_release_details(r.id)
            if not _release_belongs_to_artist(details, artist.id):
                print(f"  skipped unrelated release {r.id}: {details['title']}")
                continue
            release_data.append(details)
            all_genres.update(details["genres"])
            all_styles.update(details["styles"])
        except Exception as e:
            # Some releases (compilations, credits-only entries) can 404
            # or lack full data — skip rather than crash the whole run.
            print(f"  skipped release {r.id}: {e}")
            continue

    return {
        "source": "discogs",
        "id": artist.id,
        "name": artist.name,
        "genres": sorted(all_genres),
        "styles": sorted(all_styles),
        "releases": release_data,
    }