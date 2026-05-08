# Hermes NexTalk Bot

> Standalone Docker service that acts as an AI assistant in Nextcloud Talk rooms — polling conversations, responding with Claude, and managing per-room memory.

---

## Features

- 🛡️ **Bulletproof supervision** via s6-overlay — services auto-restart on failure, no cron hacks
- 🌐 **Web UI on port 7861** — manage everything through a browser, no SSH required
- 📊 **Per-room poll levels** — L1 (2 min) through L4 (24 hr), configured per room
- 🧠 **Per-room memory files** — persistent `.md` context files, auto-updated by Claude Haiku after every exchange
- 💾 **Daily backups at 2am** — automatic snapshots with 5-version rolling history per memory file
- 🚨 **Urgent mode** — `panic` / `spiral` keywords trigger 15-second polling instantly
- 👶 **Safety escalation for kids rooms** — keyword detection triggers immediate Telegram alerts to the parent
- 🔐 **bcrypt-secured web UI** — no plain-text passwords stored
- ⚙️ **Live config editing** — change credentials and room settings via web UI without restarting the container
- 🔒 **All credentials in `.env`** — never baked into source or image layers

---

## Quick Start

```bash
git clone https://github.com/ajaywood/hermes-nexttalk-bot.git
cd hermes-nexttalk-bot
cp .env.example .env
# Edit .env with your values
nano .env
docker compose up -d
```

Then open **http://your-server-ip:7861**

---

## Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Anthropic API key | `sk-ant-...` |
| `NC_URL` | **Yes** | Nextcloud base URL | `https://nextcloud.example.com` |
| `NC_USER` | **Yes** | Nextcloud bot username | `hermes` |
| `NC_PASS` | **Yes** | Nextcloud bot app password | `xxxxx` |
| `TELEGRAM_BOT_TOKEN` | **Yes** | Telegram bot token for safety alerts | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | **Yes** | Your Telegram user ID | `7496944648` |
| `WEBUI_PASSWORD` | **Yes** | Web UI login password | `changeme` |
| `TZ` | No | Timezone for backup scheduling | `Australia/Adelaide` |

> 💡 Copy `.env.example` to `.env` and fill in your values. The `.env` file is never committed to source control.

---

## Web UI

Access the web UI at **http://your-server-ip:7861** after starting the container.

### Dashboard
- Live poller status indicator (up/down/urgent)
- Room table showing each room's poll level, last poll time, and message count
- Live scrolling log tail — see what the bot is doing in real time

### Configuration
- Edit Nextcloud and Anthropic credentials without restarting
- Adjust polling intervals and thresholds
- Add, remove, or reconfigure rooms (poll level, urgent_capable, kids_room flag)

### Memory
- View and edit each room's `.md` memory file directly in the browser
- Trigger manual backups
- Restore from any of the last 5 backup versions per file

---

## Poll Levels

| Level | Interval | Use Case |
|---|---|---|
| **L1** | 2 min | Urgent/personal rooms (Mind & Growth, kids rooms) |
| **L2** | 15 min | Active rooms (Family Circle, Health) |
| **L3** | 60 min | Low-traffic rooms (Business, Projects) |
| **L4** | 24 hr | Daily digest / archive rooms |

Poll levels are configured per room in the web UI and stored in `/data/config.json`.

---

## Urgent Mode

In rooms configured with `urgent_capable: true`, the poller watches for distress keywords in messages from the primary user.

**Trigger keywords:** `panic`, `urgent`, `help me`, `spiral`

When triggered:
- The room immediately switches to **15-second polling**
- Claude's system prompt shifts to short, grounding, supportive replies
- The urgent state is logged and visible in the dashboard

**Return to normal** when the user types a calm keyword (`ok`, `calm`, `better`, `thanks`, etc.) or after **10 minutes of silence**, at which point polling drops back to L1.

> Urgent mode only activates for the configured primary user — it won't fire on messages from other participants.

---

## Memory System

Each room maintains a dedicated `.md` memory file that gives Claude persistent context across conversations.

- **Location:** `/data/memory/<room-token>.md`
- **Loaded** as system context before every Claude response
- **Auto-updated** by Claude Haiku after each exchange — summaries, facts, and preferences are written back automatically
- **Daily backups** run at 2am (respects `TZ`) into `/data/backups/YYYY-MM-DD/`
- **Rolling history:** the last 5 backup versions are kept per file; older versions are pruned automatically
- **Fully editable** via the Memory tab in the web UI — make manual corrections or seed new context at any time

---

## Unraid Setup

1. **Install Community Applications** from the Unraid App Store if not already installed
2. Open the **Docker** tab → **Add Container**, or place a `docker-compose.yml` in a share and run it via terminal
3. **Map the data volume:**
   - Container path: `/data`
   - Host path: `/mnt/user/appdata/hermes-nexttalk-bot`
4. **Expose port** `7861` (host) → `7861` (container)
5. **Create your `.env` file** in the same directory as `docker-compose.yml`
6. **Start the container:**
   ```bash
   docker compose up -d
   ```

The `/mnt/user/appdata/hermes-nexttalk-bot` directory will contain `memory/`, `backups/`, `logs/`, `state/`, and `config.json` after first run.

---

## Updating

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Your `/data` volume is bind-mounted and untouched by updates — all memory files, config, and state are preserved.

---

## Migrating from the Old Daemon

If you're coming from the previous standalone daemon setup, migrate your data before starting the container for the first time:

1. **Copy memory files** from their old location into:
   ```
   /mnt/user/appdata/hermes-nexttalk-bot/memory/
   ```

2. **Copy poll state** into:
   ```
   /mnt/user/appdata/hermes-nexttalk-bot/state/poll_state.json
   ```

3. Start the container — it will pick up existing state and memory automatically:
   ```bash
   docker compose up -d
   ```

No data transformation is needed; the file formats are compatible.

---

## Troubleshooting

| Symptom | Steps to resolve |
|---|---|
| **Poller showing "down"** | Check `/data/logs/poller.log` for errors; verify Nextcloud credentials are correct in the web UI Configuration tab |
| **Memory not updating** | Verify your `ANTHROPIC_API_KEY` is valid; check logs for Claude API errors (rate limits, quota, etc.) |
| **Safety alerts not sending** | Confirm `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are correct in the web UI; ensure your bot has been started by the target user |
| **Container not starting** | Run `docker logs hermes-nexttalk-bot` to see s6-overlay startup errors; check that `.env` is present and well-formed |
| **Web UI not loading** | Verify port `7861` is not blocked by your server firewall or Unraid's network settings; check `docker logs hermes-nexttalk-bot` for webui service errors |

---

## Architecture

```
python:3.12-slim
└── s6-overlay (PID 1)
    ├── poller      — polls Nextcloud Talk, calls Claude, updates memory
    └── webui       — Flask app serving the management interface on :7861
```

- **Base image:** `python:3.12-slim` kept minimal and auditable
- **Init system:** `s6-overlay` as PID 1 — both services are supervised and auto-restarted on crash
- **No database** — config lives in `/data/config.json`, memory in `/data/memory/*.md`, state in `/data/state/poll_state.json`
- **Single volume** — everything in `/data`, bind-mounted to `/mnt/user/appdata/hermes-nexttalk-bot` on Unraid
- **Config hot-reload** — the web UI writes to `config.json` and signals the poller to reload without a container restart

---

## License

MIT — see [LICENSE](LICENSE) for details.
