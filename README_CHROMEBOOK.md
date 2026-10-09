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

## C. Deploy from GitHub using a web host

The steps below use a GitHub-connected Python worker such as Koyeb. Hosting dashboards and free-plan terms change over time. Check the current plan before deploying: do not assume a free instance is always available or remains awake 24/7. A bot needs a continuously running worker, and a sleeping or stopped service will appear offline.

1. Create an account with the host in your browser, then choose **Create Service** (or its equivalent) and connect your GitHub account.
2. Select this repository and branch. Choose a Python runtime/buildpack if asked.
3. Configure the service as a **Worker/Background Worker**, not as a web site that expects HTTP requests. Use this start command:

   ```text
   python bot.py
   ```

   The host should install dependencies from `requirements.txt` during deployment. If it asks for an install/build command, use `pip install -r requirements.txt`.
4. In the service's **Environment Variables**, **Secrets**, or **Configuration** page, add:
   - `DISCORD_TOKEN`: the token from the Discord Developer Portal
   - `NVIDIA_API_KEY`: the key from NVIDIA Build
   - Optionally, `NVIDIA_MODEL`: defaults to `meta/llama-3.3-70b-instruct`
5. Select a plan that supports an always-on worker, review any charges or usage limits, and deploy. Check the service logs for `Logged in as ...` to confirm the bot connected. Then mention the bot in a server channel or send it a direct message.
6. Keep `DISCORD_TOKEN` and `NVIDIA_API_KEY` only in the host's secret settings. If either is exposed, revoke it at its provider and create a replacement.

### SQLite storage note

The bot creates `chat_history.db` beside `bot.py` by default. Some hosts use temporary filesystems, so this database may be lost when a service is replaced or redeployed. If conversation history must survive deployments, attach a persistent disk/volume and set `CHAT_HISTORY_DB` to a writable file path on that mounted volume. Confirm that the selected host and plan support persistent storage; do not commit the database to GitHub.

### Other bot hosting panels

If you use a browser-based bot host such as Bot-Hosting.net instead, look for a Python service that can deploy from GitHub (or upload the repository files through its web panel), install `requirements.txt`, set the same environment variables, and run `python bot.py`. Verify that its current plan permits a continuously running Discord bot and provides persistent storage if you need history retained. A host's advertised free tier, uptime, and storage can change; check its current terms before relying on it for 24/7 operation.

## Commands and behavior

- Mention the bot in a server channel, or message it directly, to chat.
- Run `!reset` in a channel to clear that channel's saved history.
- The bot stores the latest conversation messages in SQLite and sends long responses in Discord-safe chunks.