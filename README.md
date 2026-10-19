# discord_bots

| Bot | Status |
|---|---|
| [`refold_helper_bot/`](refold_helper_bot/README.md) | Active. Main community bot (formerly the Spanish bot). Runs without privileged intents. |
| `grammar_bot/` | Active. DeepSeek grammar Q&A via `/grammar` and the "Ask Grammar Bot" message menu. Runs without privileged intents. |
| `refold_coaching_bot/` | Not running. Still requests `Intents.all()` and would fail to connect without approved intents. |
| `subs_bot/` | Not running. Same `Intents.all()` problem. |

`qa_chat_bot` and `refold-archive-bot` (2022, discord.py 1.x / discord.js v12)
were retired; they remain in git history.

Discord now requires approval for privileged intents (Message Content, Guild
Members, Presences) once an app can reach 10,000 users, with annual
re-review. Bots here are designed to need none of them.
