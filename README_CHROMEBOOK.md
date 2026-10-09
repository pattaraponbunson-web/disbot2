# Discord AI Bot: Chromebook Setup

This project can be created, configured, and deployed entirely in a browser. You do not need Linux Mode, a local terminal, or a local Python installation.

## A. Create the files on GitHub

1. Sign in to GitHub and create a new repository. A private repository is a good choice for a bot project.
2. Open the repository and press `.` (period) to launch GitHub's browser-based editor. If that shortcut is unavailable, choose **Code** and open the repository in a Codespace.
3. Create these files in the repository root: `bot.py`, `requirements.txt`, `.gitignore`, `.env.example`, and `README_CHROMEBOOK.md`.
4. Paste in the complete contents for each file and commit the changes to the repository.
5. Do not put real credentials in `.env.example`, source files, or GitHub commits. The `.gitignore` excludes `.env` and SQLite database files, but hosting secrets should be entered in the host's settings instead.

## B. Get the bot credentials

### Discord bot token

1. In a browser, open the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
2. Open **Bot**, create the bot user, and use **Reset Token** to reveal a token. Copy it somewhere private; treat it like a password.
3. On the bot page, enable **Message Content Intent** under privileged gateway intents, then save the change. The bot needs this because it reads messages that mention it.
4. Open **OAuth2 > URL Generator**, select the `bot` scope, and grant only the permissions it needs, such as **View Channels**, **Send Messages**, **Read Message History**, and **Use External Emojis** only if desired.
5. Open the generated invite URL in your browser and add the bot to your server. Do not share the token or generated URL if it contains sensitive parameters.

### NVIDIA API key

1. Open [NVIDIA Build](https://build.nvidia.com/) and sign in or create an account.
2. Create an API key using NVIDIA's current account/API-key page and copy it privately. API access, model availability, and usage limits may depend on NVIDIA's current terms and account eligibility.

## C. Deploy on Bot-Hosting.net

The bot is a standard Python application: Bot-Hosting.net's Python runtime reads `requirements.txt` when it starts, so no web server or extra hosting-specific source code is needed. The panel and plan limits can change; check the current resource allowance and free-subscription rules before relying on continuous uptime. See the provider's [Create a Deployment](https://bot-hosting.net/docs/guides/create-a-deployment), [Set Up a Deployment](https://bot-hosting.net/docs/guides/set-up-a-deployment), and [Clone a GitHub Repository](https://bot-hosting.net/docs/guides/clone-a-github-repository) guides for current screenshots and panel labels.

1. Open [Bot-Hosting.net](https://bot-hosting.net/) in your browser, create an account, and open the default project.
2. Click **New Deployment** and choose **Application**. Choose **GitHub** as the source, connect GitHub if prompted, and select the `pattaraponbunson-web/disbot2` repository and `main` branch. If the repository is private, connect a GitHub account that can access it.
3. Select the **Python** runtime, choose the available resources, and launch the deployment.
4. Open the deployment panel's **Startup** tab. Set **Entry File (STARTUP_FILE)** to `bot.py` and save. Keep the Python runtime's default startup behavior; it installs packages listed in `requirements.txt` when starting.
5. Add `DISCORD_TOKEN` and `NVIDIA_API_KEY` using the panel's environment/startup variable controls if available. If the panel does not provide custom environment variables, create a `.env` file in the deployment's root **Files** area containing those two assignments. Add the values only in the host panel; never commit them to GitHub. The bot already loads both environment variables and `.env` through `python-dotenv`.
6. Start the deployment and open **Console** to check for `Logged in as ...`. If startup fails, confirm the entry file is `bot.py`, `requirements.txt` is in the root, and both credentials are set. Then mention the bot in Discord or message it directly.
7. When updating from GitHub, use the GitHub sync in the **Files** tab and choose **Merge** to update matching project files while retaining host-only files. **Replace all files** removes existing files, which can delete `.env` and `chat_history.db`.

Keep `DISCORD_TOKEN` and `NVIDIA_API_KEY` private. If either is exposed, revoke it with its provider and replace it in the hosting panel.

### SQLite storage note

The bot creates `chat_history.db` beside `bot.py` by default. The database lives in the deployment's files; keep backups if the chat history matters. Syncing with **Replace all files** or deleting the deployment can remove it. Do not commit the database to GitHub. If the host offers persistent storage, you can set `CHAT_HISTORY_DB` to a writable path on it.

## Commands and behavior

- Mention the bot in a server channel, or message it directly, to chat.
- Run `!reset` in a channel to clear that channel's saved history.
- The bot stores the latest conversation messages in SQLite and sends long responses in Discord-safe chunks.