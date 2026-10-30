#!/bin/bash
# Rebuild and restart the single production container (port 8000, appdata database).
set -e
cd /mnt/user/media/dev-projects/cinescope

# Load env vars
set -a
source .env
set +a

# The checkout is owned by andrew, so git refuses it as root ("dubious
# ownership") unless told it's safe; then hand any new files back to the owner
owner=$(stat -c '%U:%G' .)
git -c safe.directory="$PWD" pull --ff-only
chown -R "$owner" .

docker build -t cinescope-backend .

# Only one CineScope should run. The dev compose container (cinescope-backend on
# :8585) has its own empty database, so remove it if it's still around.
docker rm -f cinescope-backend 2>/dev/null || true
docker rm -f cinescope 2>/dev/null || true

docker run -d \
  --name='cinescope' \
  --net='bridge' \
  --restart=unless-stopped \
  --user=root \
  --add-host=host.docker.internal:host-gateway \
  -e TZ="America/Chicago" \
  -e APP_ENV="production" \
  -e LOG_LEVEL="${LOG_LEVEL:-INFO}" \
  -e PLEX_URL="$PLEX_URL" \
  -e PLEX_TOKEN="$PLEX_TOKEN" \
  -e PLEX_MOVIE_LIBRARY="${PLEX_MOVIE_LIBRARY:-Movies}" \
  -e RADARR_URL="$RADARR_URL" \
  -e RADARR_API_KEY="$RADARR_API_KEY" \
  -e TMDB_API_TOKEN="$TMDB_API_TOKEN" \
  -v '/mnt/user/appdata/cinescope/data':'/data':'rw' \
  -p 8000:8000 \
  cinescope-backend

echo "Done — checking logs..."
sleep 2
docker logs cinescope --tail 20
