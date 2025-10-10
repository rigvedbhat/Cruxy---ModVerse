# Cruxy – The AI Powered Discord Community Manager

[Python Downloads](https://www.python.org/downloads/)
[discord.py](https://github.com/Rapptz/discord.py)
[MIT License](https://opensource.org/licenses/MIT)

Cruxy is an intelligent, multi-functional Discord bot that combines automation and artificial intelligence to handle community management, moderation, and engagement tasks. It transforms natural language instructions into fully structured Discord setups, making server management faster, smarter, and simpler.

---

## About the Project

Creating a Discord server often involves repetitive steps such as creating roles, channels, and assigning permissions. Cruxy automates all of it. With simple slash commands, you can instruct it to design, configure, and even moderate your community server intelligently.

Cruxy is built for server owners who want to focus on growing their communities rather than managing configurations.

---

## Key Features

* **AI Powered Server Builder**
  The `/buildserver` command generates complete Discord servers based on your input theme. It:

  * Creates relevant roles and permissions
  * Builds categories and channels logically
  * Shows a confirmation preview before applying

* **Conversational AI**
  Mention `@Cruxy` to start context aware conversations powered by Google Gemini (Generative AI).

* **Automated Moderation**
  Automatically detects and deletes profanity, issues warnings, and kicks users after repeated violations.

* **Event Scheduling**
  The `/event` command helps you organize events and notifies users before start time.

* **Leveling System**
  Users earn XP for participation, level up over time, and retain progress via persistent storage.

* **Admin Tools**
  Commands for managing warnings, resetting data, setting AFK status, syncing commands, and more.

---

## Built With

* **Python 3.10+**
* **discord.py** – Discord API integration
* **google-generativeai** – Gemini model for AI interactions
* **aiosqlite** – Asynchronous SQLite operations
* **python-dotenv** – Environment variable management
* **better-profanity** or **profanity-check** – Profanity filtering
* **asyncio, json, datetime, random** – Core Python modules used internally

---

## Prerequisites

Before installation, ensure the following:

### 1. Python

Install Python 3.10 or higher.

```bash
python --version
```

### 2. Discord Application

* Create a new application in the [Discord Developer Portal](https://discord.com/developers/applications).
* Under **Bot Settings**, enable:

  * **SERVER MEMBERS INTENT**
  * **MESSAGE CONTENT INTENT**
* Copy your **bot token** for later.

### 3. Google AI Studio API Key

Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 4. Environment Variables

Create a `.env` file in the project root with the following:

```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Install Dependencies

Install the required Python packages.

```bash
pip install discord.py google-generativeai aiosqlite python-dotenv better-profanity
```

If you maintain a `requirements.txt`, you can instead run:

```bash
pip install -r requirements.txt
```

---

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/rigvedbhat/Cruxy---ModVerse.git
   cd Cruxy---ModVerse
   ```

2. **Configure Environment Variables**
   Ensure your `.env` file has valid tokens and keys.

3. **Run the Bot**

   ```bash
   python bot.py
   ```

You should see a console message indicating successful connection and cog loading.

---

## Usage

Cruxy uses Discord’s slash commands. Some examples:

* **Build a server**

  ```
  /buildserver theme: A futuristic tech startup server
  ```

* **Chat with the AI**

  ```
  @Cruxy What are the best community engagement ideas?
  ```

* **Schedule an event**

  ```
  /event name: Team Meeting date: 2025-10-15 time: 18:00 description: Weekly progress check
  ```

* **Check level**

  ```
  /level
  ```

* **Sync commands manually (Owner only)**

  ```
  !sync
  ```

---

## Roadmap

* Natural language server modification
* Web dashboard for multi-server management
* Cross-platform community management (Slack, Telegram)
* Public server template library

---

## Troubleshooting

* **Bot not responding:** Ensure intents are enabled in the Discord Developer Portal.
* **Gemini AI not working:** Verify `GEMINI_API_KEY` in `.env` and confirm access to the Gemini API.
* **Permission issues:** Check if the bot has Administrator privileges or necessary permissions in server settings.

---

## Contact

**Developer:** Rigved M. Bhat
**Email:** [rigvedmb2@gmail.com](mailto:rigvedmb2@gmail.com)
**Bot Invite:** [Invite Cruxy](https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=8&integration_type=0&scope=bot)

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
