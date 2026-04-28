#!/bin/bash
set -e
cd /mnt/user/media/dev-projects/cinescope

# Load env vars
export $(grep -v '^#' .env | xargs)

git pull

docker build -t cinescope-backend .

docker stop cinescope && docker rm cinescope

docker run -d \
  --name='cinescope' \
  --net='bridge' \
  --restart=unless-stopped \
  --user=root \
  --add-host=host.docker.internal:host-gateway \
  -e TZ="America/Chicago" \
  -e PLEX_URL="$PLEX_URL" \
  -e PLEX_TOKEN="$PLEX_TOKEN" \
  -e RADARR_URL="$RADARR_URL" \
  -e RADARR_API_KEY="$RADARR_API_KEY" \
  -v '/mnt/user/appdata/cinescope/data':'/data':'rw' \
  -p 8000:8000 \
  cinescope-backend

echo "Done — checking logs..."
sleep 2
docker logs cinescope --tail 20