# Deployment

1. Copy files to `/opt/seromod/seromod`.
2. Create `.env` from `.env.example`.
3. Run `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. Run `sudo cp deploy/seromod.service /etc/systemd/system/`.
5. Run `sudo systemctl daemon-reload`.
6. Run `sudo systemctl enable --now seromod`.
7. Build the dashboard with `cd dashboard && npm install && npm run build`.
8. Serve `dashboard/dist` with nginx or any static host.
