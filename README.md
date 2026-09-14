# crust-punk-recsys

Monorepo for the crust punk recommendation system: metadata scrapers,
audio/tag ML pipeline, API server, and the web client that does
client-side audio feature extraction.

## Structure

```
crust-punk-recsys/
├── pyproject.toml              # uv workspace root (Python services)
├── package.json                # pnpm workspace root (JS apps)
├── pnpm-workspace.yaml
├── services/
│   ├── scrapers/                # MusicBrainz / Discogs / Last.fm clients
│   │   ├── pyproject.toml
│   │   └── src/scrapers/
│   │       ├── musicbrainz_client.py
│   │       ├── discogs_client.py
│   │       ├── lastfm_client.py
│   │       └── fetch_all.py
│   ├── ml-pipeline/              # feature extraction, embeddings, index, two-tower model
│   │   ├── pyproject.toml
│   │   └── src/ml_pipeline/
│   └── api/                      # FastAPI server
│       ├── pyproject.toml
│       └── src/api/main.py
├── apps/
│   └── web/                      # React app: essentia.js client-side extraction, UMAP/D3 similarity map
│       ├── package.json
│       └── src/extractFeatures.js
└── data/
    ├── raw_metadata/              # scraper output (gitignored)
    └── processed/                 # cached feature vectors / trained index (gitignored)
```

Why this split: `services/*` are independent Python packages (each with
its own dependencies) tied together by a single **uv workspace**, so you
install once at the root and every service shares a lockfile but keeps
its own dependency list. `apps/web` is a separate **pnpm workspace** for
the JS/browser side, since it has nothing to do with the Python
dependency graph.

## Install

### Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+
- [`pnpm`](https://pnpm.io/) — `npm install -g pnpm`

### 1. Python services (scrapers, ml-pipeline, api)

From the repo root:

```bash
uv sync
```

This reads the root `pyproject.toml` workspace config, installs all
three services and their combined dependencies into a single `.venv`,
and creates a lockfile (`uv.lock`).

**Note on `essentia`:** it's a C++ library with Python bindings and can
be finicky to install via plain pip on some systems (missing system
libs like `libyaml`, `fftw`, `taglib` are common culprits). If `uv sync`
fails specifically on `essentia`, install system dependencies first:

```bash
# Debian/Ubuntu
sudo apt-get install build-essential libyaml-dev libfftw3-dev \
  libavcodec-dev libavformat-dev libavutil-dev libavresample-dev \
  libsamplerate0-dev libtag1-dev libchromaprint-dev

# macOS (Homebrew)
brew install libyaml fftw ffmpeg libsamplerate taglib chromaprint
```
Then re-run `uv sync`.

Activate the environment when running scripts directly:

```bash
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
```

Or just prefix commands with `uv run`, which handles activation for you:

```bash
uv run --package scrapers python services/scrapers/src/scrapers/fetch_all.py "Amebix"
uv run --package api uvicorn api.main:app --reload --app-dir services/api/src
```

### 2. Web app (React + essentia.js)

```bash
pnpm install
pnpm dev:web
```

This installs `apps/web`'s dependencies (React, essentia.js, Meyda,
D3, Plotly) and starts the Vite dev server.

### 3. Environment variables (API credentials)

Create a `.env` file at the repo root (already gitignored):

```bash
DISCOGS_TOKEN=your_token_here
LASTFM_API_KEY=your_key_here
LASTFM_API_SECRET=your_secret_here
```

MusicBrainz needs no key, just a descriptive User-Agent — edit the
`CONTACT` email constant in `services/scrapers/src/scrapers/musicbrainz_client.py`.

Load the `.env` file before running scraper scripts (e.g. via
`python-dotenv`, or `export $(cat .env | xargs)` on macOS/Linux).

## Typical workflow

1. `uv run --package scrapers python services/scrapers/src/scrapers/fetch_all.py "Band A" "Band B"` → writes JSON to `data/raw_metadata/`
2. Run the ml-pipeline scripts (once built out) to extract audio features, build tag embeddings, and construct the similarity index → writes to `data/processed/`
3. `uv run --package api uvicorn api.main:app --reload --app-dir services/api/src` → serves recommendations
4. `pnpm dev:web` → web client for uploads + similarity visualization, talking to the API
