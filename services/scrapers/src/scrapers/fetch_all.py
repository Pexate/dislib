"""
Combined fetcher — pulls an artist's data from MusicBrainz, Discogs, and
Last.fm in one pass and writes a single merged JSON record per artist.

The conflicts later gets handled in the merge step.
"""

import sys
import json
import time
from pathlib import Path

from scrapers import musicbrainz_client as mbz
from scrapers import discogsdb_client as dgs
from scrapers import lastfm_client as lfm


OUTPUT_DIR = Path("./raw_metadata")


def fetch_artist(name):
    print(f"Fetching '{name}'...")
    record = {"artist_query": name, "sources": {}}

    try:
        record["sources"]["musicbrainz"] = mbz.fetch_artist_full(name)
    except Exception as e:
        print(f"  musicbrainz failed: {e}")
        record["sources"]["musicbrainz"] = None
    time.sleep(1)

    try:
        record["sources"]["discogs"] = dgs.fetch_artist_full(name)
    except Exception as e:
        print(f"  discogs failed: {e}")
        record["sources"]["discogs"] = None
    time.sleep(1)

    try:
        record["sources"]["lastfm"] = lfm.fetch_artist_full(name)
    except Exception as e:
        print(f"  lastfm failed: {e}")
        record["sources"]["lastfm"] = None
    time.sleep(1)

    return record


def main(artist_names):
    OUTPUT_DIR.mkdir(exist_ok=True)

    for name in artist_names:
        record = fetch_artist(name)
        safe_name = "".join(c if c.isalnum() else "_" for c in name.lower())
        out_path = OUTPUT_DIR / f"{safe_name}.json"
        out_path.write_text(json.dumps(record, indent=2))
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_all.py \"Artist One\" \"Artist Two\" ...")
        sys.exit(1)
    main(sys.argv[1:])
