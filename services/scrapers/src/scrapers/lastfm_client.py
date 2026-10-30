"""
Last.fm metadata fetcher.
"""

from config import SCRAPERS_DIR
import pylast
import time
import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(SCRAPERS_DIR / ".env")


# --- Setup -------------------------------------------------------------

API_KEY = os.environ.get("LASTFM_API_KEY")
API_SECRET = os.environ.get("LASTFM_API_SECRET")
USERNAME = os.environ.get("LASTFM_USERNAME")
PASSWORD = os.environ.get("LASTFM_PASSWORD")

network = pylast.LastFMNetwork(
    api_key=API_KEY, api_secret=API_SECRET, username=USERNAME, password_hash=pylast.md5(PASSWORD)
)


# --- Fetchers ------------------------------------------------------------

def get_artist_tags(artist_name, min_weight=10):
    """
    Fetch top tags for an artist. Each tag has a 'weight' (0-100) showing
    how strongly it applies — filter low-weight tags out, they're often
    noise from a single user's idiosyncratic tagging.
    """
    artist = network.get_artist(artist_name)
    top_tags = artist.get_top_tags(limit=20)
    return [
        {"name": t.item.get_name(), "weight": int(t.weight)}
        for t in top_tags
        if int(t.weight) >= min_weight
    ]


def get_album_tags(artist_name, album_name, min_weight=5):
    """
    Fetch top tags for a specific album/release. Last.fm doesn't tag
    releases as heavily as it tags artists or tracks, so results can be
    sparse — treat a low/empty result as normal, not an error, and fall
    back to artist-level tags for that release.
    """
    try:
        album = network.get_album(artist_name, album_name)
        top_tags = album.get_top_tags(limit=20)
        return [
            {"name": t.item.get_name(), "weight": int(t.weight)}
            for t in top_tags
            if int(t.weight) >= min_weight
        ]
    except pylast.WSError:
        return []


def get_artist_releases(artist_name, limit=20, min_weight=5):
    """Fetch an artist's top albums and the tags for each album."""
    artist = network.get_artist(artist_name)
    releases = []

    for top_album in artist.get_top_albums(limit=limit):
        album = top_album.item
        album_name = album.get_name()
        try:
            album_tags = get_album_tags(
                artist_name, album_name, min_weight=min_weight
            )
        except pylast.WSError:
            album_tags = []

        releases.append({
            "title": album_name,
            "tags": album_tags,
        })
        time.sleep(0.3)

    return releases


def get_track_tags(artist_name, track_name, min_weight=10):
    """Fetch top tags for a specific track."""
    track = network.get_track(artist_name, track_name)
    top_tags = track.get_top_tags(limit=20)
    return [
        {"name": t.item.get_name(), "weight": int(t.weight)}
        for t in top_tags
        if int(t.weight) >= min_weight
    ]


def get_similar_artists(artist_name, limit=15):
    """
    Fetch similar artists
    """
    artist = network.get_artist(artist_name)
    similar = artist.get_similar(limit=limit)
    return [
        {"name": s.item.get_name(), "match": round(s.match, 3)}
        for s in similar
    ]


def fetch_artist_full(artist_name):
    """Convenience function: pull artist and release tags plus similar artists."""
    try:
        tags = get_artist_tags(artist_name)
        time.sleep(0.3)
        releases = get_artist_releases(artist_name)
        time.sleep(0.3)
        similar = get_similar_artists(artist_name)
    except pylast.WSError as e:
        print(f"  lastfm error for {artist_name}: {e}")
        return None

    return {
        "source": "lastfm",
        "name": artist_name,
        "tags": tags,
        "releases": releases,
        "similar_artists": similar,
    }