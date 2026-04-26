# Deployment

1. Copy files to `/opt/seromod/seromod`.
2. Create `.env` with the required production values.
3. Run `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. Build the dashboard with `cd dashboard && npm install && npm run build`.
5. Leave `dashboard/.env` without `VITE_API_SECRET_KEY` for production builds. The dashboard now prompts for the access key at runtime instead of embedding it in the bundle.
6. Set `FORCE_HTTPS=true`, `TRUSTED_PROXY=127.0.0.1`, and `TRUST_PROXY_COUNT=1` in `.env` when deploying behind nginx on the same host.
7. Optionally set `ALLOWED_DASHBOARD_IPS` and `ALLOWED_GUILD_IDS` to reduce dashboard blast radius.
8. Copy `deploy/seromod.service` to `/etc/systemd/system/seromod.service`.
9. Copy `deploy/nginx-seromod.conf` into your nginx site configuration, replace the TLS certificate paths, and point `root` to `dashboard/dist`.
10. Run `sudo systemctl daemon-reload && sudo systemctl enable --now seromod`.
11. Run `sudo nginx -t && sudo systemctl reload nginx`.
12. Expose only ports 80 and 443 publicly. Keep the Waitress API bound behind nginx and firewall off direct internet access to port 5000.

## Zero-Cost Production Stack (April 2026)

| Service | Provider | Free Tier |
|---|---|---|
| Bot + Flask API | Oracle Cloud Always Free | 4 ARM OCPUs, 24GB RAM, 200GB block, 10TB/mo egress |
| PostgreSQL | Supabase | 500MB DB, pauses after 7 days inactivity* |
| Redis (rate limit + cache) | Upstash | 500K commands/mo, 256MB |
| Dashboard (static) | Cloudflare Pages | Unlimited bandwidth, global CDN |
| HTTPS + DDoS | Cloudflare (free) | Proxy your Oracle VM's IP |

*Supabase free tier pauses after 7 days of inactivity.
Any real traffic will prevent this. On launch day it will not pause.
If you need guaranteed uptime before you have traffic, upgrade to Pro ($25/mo).

### Oracle VM Setup
Oracle ARM capacity in some regions fills up quickly.
If provisioning fails, try: Frankfurt, London, or Singapore.
Indian cards have known rejection issues on signup - use a Wise virtual card.

### Cloudflare Pages Dashboard Deploy
1. Push dashboard/ to a GitHub repo (separate or monorepo)
2. Connect to Cloudflare Pages
3. Build command: npm run build
4. Build output: dist
5. Add env vars: VITE_API_URL=https://your-oracle-vm-domain.com

### Supabase Connection Pooling
Use Supabase's built-in PgBouncer (Transaction mode) for the connection string:
postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
This is mandatory for the asyncpg pool to work correctly with Supabase's
shared infrastructure.
