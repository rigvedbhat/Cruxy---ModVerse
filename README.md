# Seromod - AI Powered Discord Community Manager

[Python Downloads](https://www.python.org/downloads/) | [Node.js Downloads](https://nodejs.org/) | [discord.py](https://github.com/Rapptz/discord.py)

Seromod is a Discord bot for automated community management, moderation, and AI-assisted server setup. It combines a Python `discord.py` bot, a Flask API server, an `aiosqlite` persistence layer, and a React + Vite dashboard.

## About The Project

Managing a Discord server often involves repetitive work like configuring channels, assigning roles, and moderating user behavior. Seromod streamlines those tasks through slash commands, AI-assisted automation, and a browser-based dashboard for server operators.

## Key Features

- AI-powered server building with `/buildserver`
- Natural language server changes with `/serveredit`
- Mention-based conversational AI for community engagement
- Dashboard-based AutoMod configuration
- Event scheduling, reminders, and lightweight leveling support
- Reaction roles and moderation utilities

## Built With

- Python 3.10+
- `discord.py`
- Flask
- React
- Vite
- Tailwind CSS
- `google-generativeai`
- `aiosqlite`

## Prerequisites

- Python 3.10 or higher
- Node.js LTS with npm
- A Discord bot application with the `SERVER MEMBERS`, `MESSAGE CONTENT`, and `PRESENCE` intents enabled
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Environment Setup

Create a `.env` file in the project root and fill in the required values:

```env
DISCORD_TOKEN=
GEMINI_API_KEY=
API_SECRET_KEY=
FLASK_ENV=development
ALLOWED_ORIGINS=http://localhost:5173
PORT=5000
SYNC_COMMANDS=false
```

Set `SYNC_COMMANDS=true` only when slash commands have changed and you want to push a one-time global sync.

For the dashboard, create `dashboard/.env` with:

```env
VITE_API_URL=http://localhost:5000
VITE_API_SECRET_KEY=
```

## Installation

Install backend dependencies from the project root:

```bash
pip install -r requirements.txt
```

Install dashboard dependencies:

```bash
cd dashboard
npm install
```

## Running The Project

Start the bot and API server from the project root:

```bash
python bot.py
```

Start the dashboard in a separate terminal:

```bash
cd dashboard
npm run dev
```

By default, the dashboard runs on `http://localhost:5173` and the API runs on the port defined by `PORT`.

## Bot Invite Permissions

The current invite link may use the broad Administrator flag. For production use, replace that with granular permissions:

- Manage Channels
- Manage Roles
- Kick Members
- Ban Members
- Send Messages
- Read Message History
- Add Reactions
- Embed Links
- Manage Messages

Invite link:

[Invite Seromod](https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=8&integration_type=0&scope=bot)

## Production Deployment

Production deployment steps are documented in [deploy/README.md](deploy/README.md).

## Troubleshooting

- Bot not responding in Discord: verify required intents and environment variables.
- Dashboard connection errors: make sure `python bot.py` is running and the API secret matches the dashboard env file.
- `ModuleNotFoundError`: reinstall backend dependencies with `pip install -r requirements.txt`.

## Contact

- Company: Seromod
- Email: [contact@seromod.dev](mailto:contact@seromod.dev)

## License

This project is proprietary and confidential. See `LICENSE` for details.
