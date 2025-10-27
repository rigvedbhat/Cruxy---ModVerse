# Cruxy – The AI Powered Discord Community Manager

[Python Downloads](https://www.python.org/downloads/) | [Node.js Downloads](https://nodejs.org/) | [discord.py](https://github.com/Rapptz/discord.py)

Cruxy is an intelligent, multi-functional Discord bot that combines automation and artificial intelligence to handle community management, moderation, and engagement. It transforms natural language instructions into fully structured Discord setups and is now manageable from a sleek web dashboard.

-----

## About the Project

Managing a Discord server often involves repetitive tasks like creating roles and channels. Cruxy automates this with simple slash commands and now offers a React-based web dashboard for even easier control. It's built for server owners who want to focus on growing their communities rather than handling manual configurations.

-----

## Key Features

  * **AI-Powered Server Builder**
    The `/buildserver` command generates complete Discord servers based on your input theme.

  * **Conversational AI**
    Mention `@Cruxy` to start context-aware conversations powered by Google Gemini.

  * **Web Dashboard**
    A modern, responsive React dashboard to manage your bot's settings from your browser.

      * Select which server you want to manage.
      * Use the AI Manager to build or edit your server with natural language.
      * Configure AutoMod settings like profanity filters and warning limits in real-time.

  * **Advanced Automated Moderation**

      * Detects and warns for profanity.
      * Customizable warning limits and punishments (mute, kick, or ban).

  * **Event Scheduling & Leveling System**
    Organize events with `/event` and reward user participation with an XP and leveling system.

-----

## Built With

  * **Python 3.10+**
  * **discord.py** – For Discord Bot integration.
  * **Flask** – Powers the backend API server.
  * **React** – For the frontend web dashboard.
  * **Tailwind CSS** – For styling the dashboard.
  * **google-generativeai** – For all AI functionalities.
  * **aiosqlite** – For asynchronous database operations.

-----

## Prerequisites & Installation

### 1\. System Requirements

  * Install **Python 3.10 or higher**.
  * Install **Node.js LTS** (which includes npm).

### 2\. Discord & API Keys

  * Create a **Discord Bot Application** in the [Discord Developer Portal](https://discord.com/developers/applications) and enable the `SERVER MEMBERS`, `MESSAGE CONTENT`, and `PRESENCE` intents. Copy your bot token.
  * Obtain a **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3\. Environment Variables

Create a `.env` file in the project root (`D:\AI Porject\DC bot`):

```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 4\. Install Dependencies

  * **Backend (Python):** Open a terminal in the project root and run:

    ```bash
    pip install -r requirements.txt
    ```

  * **Frontend (Node.js):** Navigate into the `dashboard` directory and run:

    ```bash
    cd dashboard
    npm install
    ```

-----

## Running the Project

You'll need to run the backend and frontend in two separate terminals.

**Terminal 1: Start the Backend**
Make sure you are in the project's root directory (`D:\AI Porject\DC bot`) and your virtual environment is active.

```bash
python bot.py
```

This command starts both the Discord bot and the API server on `http://127.0.0.1:5000`.

**Terminal 2: Start the Frontend Dashboard**
Open a new terminal and navigate to the `dashboard` directory.

```bash
cd dashboard
npm run dev
```

Your web dashboard will now be running at **http://localhost:5173**. Open this address in your web browser to use it.

-----

## Usage

  * **Discord Commands:** Use slash commands like `/buildserver`, `/serveredit`, and `/event` directly in Discord.
  * **Web Dashboard:** Open `http://localhost:5173` in your browser. Select a server and manage its settings through the user-friendly interface.

-----

## Troubleshooting

  * **Bot not responding in Discord:** Ensure all required intents are enabled in the Discord Developer Portal.
  * **Dashboard shows a connection error:** Make sure the backend (`python bot.py`) is running before you start the frontend.
  * **`ModuleNotFoundError` in Python:** Ensure you have installed all packages from `requirements.txt`.

-----

## Contact

**Developer:** Rigved M. Bhat
**Email:** [rigvedmb2@gmail.com](mailto:rigvedmb2@gmail.com)
**Bot Invite:** [Invite Cruxy](https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=8&integration_type=0&scope=bot)

-----

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.
