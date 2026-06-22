# HTTPS with DuckDNS + Docker Caddy

Public hostname: **`telehealthapp.duckdns.org`** ([Caddyfile](./Caddyfile)). Caddy terminates TLS and routes `/api/*` to the `backend` service and all other paths to `frontend`.

## One-shot VM checklist

1. **DuckDNS** — Point `telehealthapp.duckdns.org` at the VM’s current **external IP** (update after IP changes).
2. **GCP firewall** — Allow **TCP 80** and **443** to the VM. Do **not** expose **3000** or **8000** to the internet once Caddy is in use (optional SSH tunnel for local debug only).
3. **Images** — Rebuild and push the **frontend** image with  
   `NEXT_PUBLIC_API_URL=https://telehealthapp.duckdns.org`  
   (this value is inlined at **build** time; see [frontend/Dockerfile](../../frontend/Dockerfile)).  
   `next.config.mjs` also uses that URL for `serverActions.allowedOrigins` when `NEXTAUTH_URL` is unset at build time.
4. **Runtime env** (compose / `.env` on the VM):
   - `NEXTAUTH_URL=https://telehealthapp.duckdns.org`
   - `ALLOWED_ORIGINS=https://telehealthapp.duckdns.org`
5. **Start stack** from the repo root on the VM (add `-f docker-compose.gcp-vm.override.yml` if you use bundled Postgres):

   ```bash
   docker compose -f docker-compose.prod.yml -f docker-compose.gcp-vm.override.yml -f docker-compose.caddy.yml up -d
   ```

   Or use the helper script (same compose files):

   ```bash
   USE_GCP_VM_OVERRIDE=1 USE_CADDY=1 bash scripts/gcp-vm-run-stack.sh
   ```

   Omit `USE_GCP_VM_OVERRIDE=1` if you use external Postgres only. Set `BACKEND_IMAGE`, `FRONTEND_IMAGE`, secrets, `NEXTAUTH_URL`, and `ALLOWED_ORIGINS` as usual before running.

6. **Verify** — Open `https://telehealthapp.duckdns.org`. Optional: `curl -I https://telehealthapp.duckdns.org` and `curl -I https://telehealthapp.duckdns.org/api/v1/docs`.

Do not run another daemon on the host bound to **80** or **443** while the Caddy container is running.

## Site does not load (timeout / connection refused)

From your laptop, `dig +short telehealthapp.duckdns.org` should return the VM’s **external** IP. If DNS is correct but **https** never connects, the usual cause is **GCP firewall**: nothing must block **TCP 80** (Let’s Encrypt HTTP-01) and **TCP 443** (HTTPS) to the VM.

1. **VM network tags** — The firewall rule must apply to your instance. If you used `scripts/gcp-setup.sh`, the tag is **`telehealth-server`**. Ensure the VM has that tag (Compute Engine → VM → Edit → **Networking** → Network tags).

2. **Open ports on an existing rule** (example project `tele-health-495910`, rule name `allow-telehealth-app` — adjust if yours differs):

   ```bash
   gcloud compute firewall-rules describe allow-telehealth-app --project=tele-health-495910
   gcloud compute firewall-rules update allow-telehealth-app --project=tele-health-495910 \
     --allow=tcp:22,tcp:80,tcp:443
   ```

   If the rule does not exist yet:

   ```bash
   gcloud compute firewall-rules create allow-telehealth-https \
     --project=tele-health-495910 \
     --direction=INGRESS --priority=1000 --network=default --action=ALLOW \
     --rules=tcp:80,tcp:443 \
     --source-ranges=0.0.0.0/0 \
     --target-tags=telehealth-server
   ```

   (Add `tcp:22` to the same rule or keep SSH on a separate rule.)

3. **On the VM** — Caddy must be up and bound to the host:

   ```bash
   docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'caddy|443|80'
   curl -sI http://127.0.0.1:80/ -H 'Host: telehealthapp.duckdns.org'
   ```

## Artifact Registry: `Unauthenticated request` on `docker compose pull`

1. On your **laptop** (project Owner/Editor), grant the VM’s service account **Artifact Registry Reader** (replace `ZONE` with your VM zone, e.g. `asia-south1-a`):

   ```bash
   GCP_PROJECT_ID=tele-health-495910 INSTANCE_NAME=telehealth-vm ZONE=YOUR_ZONE \
     bash scripts/gcp-grant-vm-artifact-registry-reader.sh
   ```

2. On the **VM**, configure Docker to use gcloud for that registry, then re-run the stack:

   ```bash
   bash scripts/gcp-vm-configure-docker-registry.sh
   ```

3. If you use **`sudo docker compose`**, copy credentials for root (see `scripts/gcp-vm-bootstrap.sh`) or add your user to the `docker` group and avoid sudo.
