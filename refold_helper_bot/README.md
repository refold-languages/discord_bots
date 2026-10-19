# Refold Helper Bot

Community bot for the Refold language-learning servers: resources, rules/FAQs,
community projects, cross-server language roles, course enrollment and
homework, and spam protection (honeypot + Discord AutoMod).

It is built to run with **no privileged gateway intents**. Message Content was
denied by Discord and is never requested; Guild Members is optional (see
[`INTENT_RECOVERY_PLAN.md`](INTENT_RECOVERY_PLAN.md)).

## Running

```bash
pip install -r requirements.txt
BOT_TOKEN=... python RefoldHelperBot.py
```

| Env var | Default | Notes |
|---|---|---|
| `BOT_TOKEN` | — | Or pass the token as the first argument. |
| `INTENT_GUILD_MEMBERS` | `false` | Set `true` only once Discord has approved the intent, or the bot can't connect. |
| `DATA_DIR` | `./data` | JSON state, moderation records, command-sync fingerprint. |
| `MAIN_SERVER_ID` | main Refold server | |

Slash commands are synced to Discord automatically on startup when their
definitions change. Bot admins can force it with `/sync`.

## Inviting / permissions

Invite with both the `bot` and `applications.commands` scopes and this
permission set (`1409017834613`):

https://discord.com/oauth2/authorize?client_id=937526025817042975&scope=bot+applications.commands&permissions=1409017834613

On startup the bot logs every server where one of these permissions is
missing (`REQUIRED_BOT_PERMISSIONS` in `config/constants.py`).

## One-time setup per server

| Where | Run | Why |
|---|---|---|
| Every community server | `/automod setup alert_channel:#mod-log` | Installs the scam-link, mention-spam and spam AutoMod rules. The bot can't read message text, so AutoMod does the content scanning and the bot acts on its alerts. |
| Each language server's welcome channel | `/syncrolesbutton` | Without the Guild Members intent the bot doesn't see joins; members press the button to get the matching main-server role. |
| Course server welcome channel | `/course enrollbutton` | Students press it to get their course role from the roster. Pending students are also looked up in the background. |

Make sure the bot's role can **view** every course category: from
2026-11-16 Discord hides channels the bot can't view.

## Tests

```bash
tests/run.sh
```

Offline scripts: they build the bot without connecting to Discord, against a
temporary copy of `data/`.
