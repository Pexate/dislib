"""
MusicBrainz metadata fetcher.
"""

import musicbrainzngs as mb
import time
import json


# --- Setup -------------------------------------------------------------

APP_NAME = "dislib"
APP_VERSION = "0.1"
CONTACT = "tonci.crljen@skole.hr"

mb.set_useragent(APP_NAME, APP_VERSION, CONTACT)


# --- Fetchers ------------------------------------------------------------

def search_artist(name, limit=5):
    """Search for an artist by name. Returns list of candidate matches."""
    result = mb.search_artists(artist=name, limit=limit)
    return result.get("artist-list", [])


def search_artists_by_tag(tag, limit=100):
    """
    Search for artists tagged with a given genre/tag using MusicBrainz's
    Lucene search syntax (tag:crust). Paginates through results.
    """
    artists = []
    offset = 0
    while True:
        result = mb.search_artists(query=f'tag:"{tag}"', limit=100, offset=offset)
        batch = result.get("artist-list", [])
        artists.extend(batch)
        if len(batch) < 100 or len(artists) >= limit:
            break
        offset += 100
        time.sleep(1)
    return [{"name": a["name"], "mbid": a["id"]} for a in artists[:limit]]


def get_artist_release_groups(artist_mbid, release_type="album"):
    """Get release groups (albums/EPs) for an artist by MusicBrainz ID."""
    release_groups = []
    offset = 0
    limit = 100
    while True:
        result = mb.browse_release_groups(
            artist=artist_mbid,
            release_type=[release_type],
            limit=limit,
            offset=offset,
        )
        batch = result.get("release-group-list", [])
        release_groups.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
        time.sleep(1)  # rate limit
    return release_groups


def get_release_group_tags(release_group_mbid):
    """Fetch tags for a specific release group."""
    result = mb.get_release_group_by_id(release_group_mbid, includes=["tags"])
    release_group = result.get("release-group", {})
    tags = [t["name"] for t in release_group.get("tag-list", [])]
    return {"tags": tags}


def get_artist_tags(artist_mbid):
    """Fetch tags for an artist (often more populated than per-release)."""
    result = mb.get_artist_by_id(artist_mbid, includes=["tags"])
    artist = result.get("artist", {})
    tags = [t["name"] for t in artist.get("tag-list", [])]
    return {"tags": tags}


def fetch_artist_full(artist_name, include_release_tags=True, max_release_groups=30):
    """
    Convenience function: search for an artist, then pull their release groups
    and tags. Returns None if no match found.

    When include_release_tags=True (default), each release gets its own
    tags fetched individually rather than just inheriting the artist's
    aggregate tags. One API call is made per release group, capped at
    max_release_groups.
    """
    matches = search_artist(artist_name, limit=1)
    if not matches:
        return None

    artist = matches[0]
    mbid = artist["id"]

    time.sleep(1)
    artist_tags = get_artist_tags(mbid)

    time.sleep(1)
    release_groups = get_artist_release_groups(mbid)

    if include_release_tags:
        release_data = enrich_release_groups_with_tags(
            release_groups, max_release_groups=max_release_groups
        )
    else:
        release_data = [
            {
                "mbid": group["id"],
                "title": group.get("title"),
                "date": group.get("first-release-date"),
                "primary_type": group.get("primary-type"),
            }
            for group in release_groups
        ]

    return {
        "source": "musicbrainz",
        "mbid": mbid,
        "name": artist.get("name"),
        "country": artist.get("country"),
        "artist_tags": artist_tags["tags"],
        "release_groups": release_data,
    }

def enrich_release_groups_with_tags(release_groups, max_release_groups=30):
    """
    Fetch tags for release groups returned by get_artist_release_groups.
    Capped because this is one API call per release group.
    """
    enriched = []
    for group in release_groups[:max_release_groups]:
        print("fetching release-group tags for:", group.get("title"), group["id"])
        time.sleep(1)
        try:
            tags = get_release_group_tags(group["id"])
        except Exception as e:
            tags = {"tags": []}
        enriched.append({
            "mbid": group["id"],
            "title": group.get("title"),
            "date": group.get("first-release-date"),
            "primary_type": group.get("primary-type"),
            "tags": tags["tags"],
        })
    return enriched
