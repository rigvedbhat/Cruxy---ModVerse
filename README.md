# Cruxy - The AI-Powered Discord Community Manager

[](https://www.python.org/downloads/)
[](https://github.com/Rapptz/discord.py)
[](https://opensource.org/licenses/MIT)

Cruxy is a next-generation, multi-functional Discord bot that leverages the power of Large Language Models (LLMs) to automate the most complex aspects of server setup and management. It's designed to be an intelligent co-pilot for community managers, transforming natural language prompts into perfectly structured and permissioned Discord servers.

## About The Project

Setting up a new Discord server is a tedious process. Creating roles, categories, and dozens of channels, then painstakingly configuring permissions for each one, can take hours of manual work. Cruxy was built to solve this problem.

Instead of clicking through menus, you can simply tell Cruxy the kind of server you want, and it will generate a complete, ready-to-use server layout in seconds. It goes beyond simple templates by dynamically creating roles and permissions tailored to your specific theme, making it a truly intelligent setup tool.

## Key Features

  * **✨ AI-Powered Server Builder**: The flagship feature. Use the `/buildserver` command with a theme (e.g., "A server for a high-tech startup"), and Cruxy's AI will:
      * Invent relevant roles (e.g., `Founder`, `Developer`, `Investor`).
      * Design a complete structure of categories and channels.
      * Apply complex, logical permissions to restrict channels to their relevant roles.
      * Provide a full preview and confirmation step before making any changes.
  * **🤖 Conversational AI**: Mention `@Cruxy` with a question or a prompt to engage in a continuous, context-aware conversation powered by Google's Gemini model.
  * **🛡️ Automated Moderation**: A built-in system that automatically detects and deletes messages containing profanity. It implements a persistent, database-backed warning system that can automatically kick users who repeatedly break the rules.
  * **🎉 Event Scheduling**: Easily schedule server events with the `/event` command, which automatically sends a reminder to a designated channel just before the event starts.
  * **📈 Persistent Leveling System**: Rewards server activity by granting XP for messages. All user levels and XP are stored in a database, so progress is never lost.
  * **⚙️ Robust Admin Utilities**: Includes standard commands for checking warnings, resetting warnings, setting AFK statuses, and a basic, non-AI server setup command.

## Built With

  * [Python 3.10+](https://www.python.org/)
  * [discord.py](https://github.com/Rapptz/discord.py) - The primary library for interacting with the Discord API.
  * [Google Generative AI (Gemini)](https://ai.google.dev/) - The LLM powering the core AI features.
  * [aiosqlite](https://github.com/omnilib/aiosqlite) - Asynchronous database operations for a responsive bot.
  * [better\_profanity](https://pypi.org/project/better-profanity/) - For the automated moderation filter.
  * [python-dotenv](https://pypi.org/project/python-dotenv/) - For managing environment variables.

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

  * Python 3.10 or higher.
  * A Discord account and a new Discord Application.
  * A Google AI Studio API key.

### Installation

1.  **Clone the repository:**

    ```sh
    git clone https://github.com/your_username/Cruxy.git
    cd Cruxy
    ```

2.  **Install the required dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    Create a file named `.env` in the root of the project folder and add the following, replacing the placeholder text with your actual keys:

    ```env
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    GEMINI_API_KEY=YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE
    ```

      * You can get your `DISCORD_TOKEN` from the "Bot" page of your application in the [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications). Remember to enable the **Server Members Intent** and **Message Content Intent**.
      * You can get your `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/app/apikey).

4.  **Run the bot:**

    ```sh
    python bot.py
    ```

## Usage

Cruxy primarily uses Discord's built-in slash commands. Here are some of the main ones:

  * **Build a server with AI:**
    `/buildserver theme: A professional server for a Valorant esports team`

  * **Chat with the AI:**
    `@Cruxy How do I write a good README file for my project?`

  * **Schedule an event:**
    `/event name: Movie Night date: 2025-10-25 time: 18:30 description: We'll be watching The Matrix!`

  * **Check your level:**
    `/level`

## Roadmap

Cruxy is currently a Discord-specific prototype with a grander vision. Future plans include:

  * **Natural Language Server Editing:** A premium feature allowing admins to modify the server with commands like, "@Cruxy, create a private channel named \#alpha-testing for the @Developers role."
  * **Cross-Platform Support:** Refactoring the core logic into a platform-agnostic service that can manage communities on Slack, Telegram, and more from a single dashboard.
  * **Web Dashboard:** A central web interface for managing all aspects of the bot and connected communities.
  * **Community Template Library:** Allowing users to save and share their AI-generated server structures.

See the [open issues](placeholder) for a full list of proposed features (and known issues).

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

## Contact

Name - Rigved M. Bhat, Email - rigvedmb2@gmail.com

Bot Invite Link - https://discord.com/oauth2/authorize?client_id=1361039241760604261&permissions=8&integration_type=0&scope=bot
