# CineScope 🎬

Personal media intelligence — monitors your Plex library and discovers interesting films from curated sources. Review suggestions and send approved picks to Radarr.

---

## Architecture

```
cinescope/
├── backend/
│   ├── app/
│   │   ├── main.py              ← FastAPI app + startup
│   │   ├── api/routes/          ← HTTP endpoints (library, suggestions, queue, sources)
│   │   ├── core/
│   │   │   ├── config.py        ← All settings from env vars
│   │   │   └── scheduler.py     ← Background job runner
│   │   ├── db/
│   │   │   └── database.py      ← DB engine + session factory
│   │   ├── models/
│   │   │   ├── film.py          ← Film table
│   │   │   └── source.py        ← Source + Suggestion tables
│   │   ├── scrapers/
│   │   │   └── base.py          ← BaseScraper + Letterboxd/IMDb/Metacritic
│   │   └── services/
│   │       ├── plex_service.py      ← Plex library sync
│   │       ├── radarr_service.py    ← Radarr API integration
│   │       └── discovery_service.py ← Orchestrates scrapers → DB
│   ├── Dockerfile
│   └── requirements.txt
├── docker/
│   └── unraid-template.xml      ← Unraid Community Apps template
├── docker-compose.yml           ← Local development
├── docker-compose.prod.yml      ← Production overrides
└── .env.example                 ← Copy to .env and fill in
```

---

## Your Tasks (Implement These)

The backend scaffolding is complete and will run. These are the pieces you build:

### Task 1 — Plex Sync (`services/plex_service.py`)
Implement `sync_plex_library()`. The docstring gives you step-by-step instructions. This is your first real task — get Plex talking to the DB.

**Resources:**
- [plexapi docs](https://python-plexapi.readthedocs.io/en/latest/)
- [Finding your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

### Task 2 — IMDb Scraper (`scrapers/base.py`)
Implement `IMDbTrendingScraper.fetch()`. Study `LetterboxdScraper` first — your implementation should follow the same pattern. Open `https://www.imdb.com/chart/moviemeter/` in your browser, inspect the HTML, then write the parser.

**Tip:** Right-click any film on the page → Inspect → look at the element structure before writing any BeautifulSoup code.

### Task 3 — Suggestion Action (`api/routes/suggestions.py`)
In `action_suggestion()`, update `film.status` based on `body.action`. One line of code per case, but you need to understand how to load and update a related model.

### Task 4 — Radarr Integration (`services/radarr_service.py`)
Implement `add_to_radarr()`. The docstring tells you exactly what JSON to POST. Study `get_radarr_movies()` in the same file — it's a working httpx example to learn from.

### Task 5 — Plex Status Check (`api/routes/sources.py`)
Add a Plex connection check to `integration_status()`, similar to `check_radarr_connection()` in radarr_service.py.

---

## Local Development Setup

### Prerequisites
- Docker Desktop installed
- Python 3.12+ (optional, for running without Docker)

### 1. Clone and configure
```bash
git clone https://github.com/your-username/cinescope
cd cinescope
cp .env.example .env
# Edit .env with your Plex URL, token, and Radarr key
```

### 2. Start with Docker Compose
```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs` ← **start here**

### 3. Running without Docker (for development)
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set env vars (or create .env in the backend/ directory)
export PLEX_TOKEN=your_token
export PLEX_URL=http://localhost:32400

uvicorn app.main:app --reload --port 8000
```

### 4. Verify it's working
```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}

curl http://localhost:8000/api/sources/integrations/status
# → {"radarr": {...}, "plex": {...}}
```

---

## Deploying to Unraid

### Option A: Docker Compose via Unraid terminal (quickest)
```bash
# SSH into Unraid
ssh root@your-unraid-ip

# Create appdata directory
mkdir -p /mnt/user/appdata/cinescope/data

# Clone the repo
cd /mnt/user/appdata
git clone https://github.com/your-username/cinescope

# Configure
cd cinescope
cp .env.example .env
nano .env   # fill in your values

# Start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Option B: Build and push to Docker Hub, then use Unraid UI
```bash
# On your dev machine — build and push
docker build -t your-dockerhub-username/cinescope-backend:latest ./backend
docker push your-dockerhub-username/cinescope-backend:latest

# On Unraid: Docker tab > Add Container
# Fill in fields from docker/unraid-template.xml
```

### Option C: Unraid Community Apps template
1. Edit `docker/unraid-template.xml` — replace `your-dockerhub-username` and `your-username`
2. Copy the file to `/boot/config/plugins/dockerMan/templates-user/` on your Unraid server
3. It will appear in your "Add Container" templates list

### Unraid volume mapping
| Container path | Unraid path (suggested) |
|---|---|
| `/data` | `/mnt/user/appdata/cinescope/data` |

### Finding your Plex token on Unraid
Your Plex token is the same regardless of where Plex runs. From any browser:
1. Go to `https://plex.tv` and sign in
2. Open any media item, click "..." → Get Info → View XML
3. Copy the `X-Plex-Token` value from the URL

---

## API Reference

Once running, visit `http://localhost:8000/docs` for the full interactive API.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/library/` | All Plex library films |
| `POST` | `/api/library/sync` | Trigger Plex sync |
| `GET` | `/api/suggestions/` | Pending suggestions |
| `POST` | `/api/suggestions/{id}/action` | Queue or dismiss |
| `GET` | `/api/queue/` | Approved films |
| `POST` | `/api/queue/{id}/send-to-radarr` | Send to Radarr |
| `GET` | `/api/sources/` | Discovery sources |
| `PATCH` | `/api/sources/{id}/toggle` | Enable/disable source |
| `GET` | `/api/sources/integrations/status` | Plex + Radarr status |

---

## Roadmap

- [ ] **Phase 1** (current): Backend + Plex sync + basic scraping
- [ ] **Phase 2**: Metacritic + A24 scrapers, TMDB enrichment (posters, overviews)
- [ ] **Phase 3**: React frontend (replace the prototype artifact)
- [ ] **Phase 4**: Radarr/Sonarr full integration, Telegram/Pushover notifications
- [ ] **Phase 5**: Scoring tuning, "for you" recommendations based on library taste
