# Refold Helper Bot — Privileged Intent Recovery Plan

**App:** Refold Helper Bot (`937526025817042975`)
**Status:** Guild Members, Guild Presences, Message Content — all revoked
**Date:** 2026-08-03

---

## 1. What actually happened

Read the notice carefully — this is **not a rejection**:

> "As previously notified, your app's access to privileged intents was due for review.
> **Since we did not receive your request within the submission window**, your app's
> privileged intents have been removed."

Discord introduced **annual re-application** for privileged intents. Every approved app
must re-justify its intents each year, with a 90-day window after notice. The window
lapsed with no submission, so access was auto-revoked administratively.

**Nobody at Discord ever evaluated or disliked your reasons.** There is no denial to
appeal and no black mark on the app. You simply need to file the request. Reapplication
is available immediately with no cooldown.

This is the single most important fact in this document, because it changes the strategy
entirely: the job is *"submit a strong first application"*, not *"overturn a rejection."*

### Why the bot is completely dead rather than partially degraded

`RefoldHelperBot.py:39`:

```python
intents = discord.Intents.all()   # requests ALL THREE privileged intents
intents.members = True            # redundant — .all() already set this
```

When a bot requests a privileged intent it hasn't been granted, Discord rejects the
gateway handshake outright (close code **4014 — Disallowed Intents**; discord.py surfaces
this as `PrivilegedIntentsRequired`). The connection never opens, so *every* feature dies
— including the ~60% of the bot that needs no privileged intent at all.

**This is why one paperwork lapse took down the whole bot.** Fixing that line alone
restores a large chunk of functionality today, before Discord approves anything.

---

## 2. Scale check — what rules apply to you

As of **June 10, 2026**, Discord split two previously-conflated thresholds:

| Requirement | Threshold | Applies to you? |
|---|---|---|
| **Bot verification** (ID check, app review) | 100+ servers | **No** — few servers |
| **Privileged intent review** | 10,000+ unique users | **Yes** — Refold servers exceed this |

The threshold moved from "100 servers" to "10,000 unique users across all servers." A
handful of large servers now trips it where it previously wouldn't. You need intent
review, but you do *not* need the heavier bot-verification process. That's the easier of
the two paths.

---

## 3. Feature → intent dependency map

Audited across all 11 cogs and 12 services.

### Guild Presences — **required by nothing**

Zero usages. No `on_presence_update`, no `member.status`, no activity reads. (The
`.status` hits in `course.py` / `homework.py` are enrollment-state fields, unrelated to
Discord presence.)

`Intents.all()` has been silently requesting this for years. **Requesting an intent you
demonstrably don't use is one of the most-cited reasons applications get rejected.**
Dropping it is free and materially improves approval odds for the other two.

### Guild Members — genuinely required

| Feature | Location |
|---|---|
| Cross-server role sync | `cogs/roles.py:33,48` (`fetch_member` across guilds) |
| Join/leave handlers | `cogs/roles.py:55,63`, `cogs/course.py:683` |
| Reaction roles | `cogs/roles.py:90,119,148,173` (`get_member` — cache-dependent) |
| Member enumeration | `cogs/admin.py:112`, `cogs/course.py:657`, `cogs/roles.py:218` |
| Course enrollment on join | `cogs/course.py:683` |

### Message Content — genuinely required, but the justification needs care

| Feature | Location | Slash-command replaceable? |
|---|---|---|
| Anti-spam detection engine | `cogs/antispam.py:175` | **No** — passive scanning |
| Honeypot content logging | `cogs/honeypot.py:90` | **No** — passive |
| Auto-thread naming | `cogs/community.py:197` | **No** — passive |
| Deleted-message mod log | `cogs/moderation.py:154` | **No** — passive |
| Homework CSV ingest | `cogs/homework.py:111` | Yes — file upload param |
| **~40 `!` prefix commands** | all cogs | **Yes — and this is the problem** |

---

## 4. The one real risk to approval

Discord's published review policy is explicit:

> "If your bot's functionality can be achieved via Slash Commands or Buttons, your
> application for this privileged intent will be rejected."
>
> "If you applied saying 'I need it for a `!help` command,' you will be rejected."

The bot currently has **~40 prefix commands** and the reviewer can see them. If the
application reads as "we need message content for our `!` commands," it gets denied —
this time on the merits, which is a much worse position than today.

**The winning framing:** Message Content is justified *exclusively* by the passive
moderation pipeline — anti-spam heuristics, the scam honeypot, deleted-message audit
logging. Automated content moderation is the canonical **accepted** use case, precisely
because a slash command cannot scan a message nobody invoked it on.

The prefix commands must not appear in the justification at all. Better still, migrate
them, so the claim "our command surface is slash-native; message content is used only for
moderation" is verifiably true if the reviewer inspects the app.

---

## 5. The plan

### Phase 0 — Bring the bot partially back online (today, ~30 min, no Discord approval needed)

Replace `Intents.all()` with an explicit, degradable intent set.

```python
intents = discord.Intents.default()   # no privileged intents
intents.message_content = _want("MESSAGE_CONTENT")
intents.members         = _want("GUILD_MEMBERS")
# presence intentionally never requested — nothing uses it
```

Gate each privileged intent behind an env var (default **off**) so the bot connects
successfully right now, and flip them on the moment Discord approves — no code change,
no redeploy risk.

**Working immediately after this change, with zero intents granted:**
- All reaction-role assignment (switch `get_member` → `payload.member`, which the gateway
  supplies on guild reactions without the members intent)
- The honeypot **ban** itself — it triggers on *posting in a channel*, not on content;
  only the logged message text goes blank
- Every scheduled task: daily/weekly threads, YouTube monitoring, course automation
- All slash commands (interactions carry full data regardless of intents)

**Still broken until approval:** anti-spam engine, prefix commands, auto-thread naming,
deleted-message logging, join/leave automation, cross-server role sync.

Also add a startup guard: catch `PrivilegedIntentsRequired`, log which intent is missing,
and skip loading the cogs that depend on it rather than crashing the process. A single
future paperwork lapse should degrade the bot, never kill it.

### Phase 1 — Migrate prefix commands to slash commands (the approval-critical work)

Convert the ~40 `@commands.command()` handlers to `@app_commands.command()`. Most are
trivial static responders (`cogs/moderation.py`, `cogs/fun.py`, `cogs/resources.py`) —
mechanical conversions. The genuinely interactive ones (`course.py`, `homework.py`,
`admin.py`) need modals/buttons instead of the `wait_for('reaction_add')` confirmation
pattern at `course.py:139` and `homework.py:338`.

Convert the homework CSV ingest (`homework.py:111`) to a slash command with an
`attachment` parameter — that removes one more Message Content dependency.

Run both surfaces in parallel during transition so nothing breaks for users mid-migration.

**Why this is not optional:** it's what converts the application from "probably denied"
to "routine approval," and it's the difference between depending on Message Content for
everything versus only for moderation.

### Phase 2 — Tighten the data story before applying

Discord asks explicitly how you handle message data. Two gaps to close first:

1. **`services/spam_detection_service.py:458`** — `record_action()` reads the full JSON
   record list, appends, and writes it back with **no cap and no expiry**. Message content
   (truncated to 1000 chars) accumulates indefinitely. Add a retention window (90 days is
   defensible for a moderation audit log) and a hard record cap. You cannot honestly state
   a retention policy on the form until this exists.
2. **Publish a privacy policy** and link it in the Developer Portal. Discord requires one.
   It must disclose: message scanning for spam, what's retained when an action fires,
   retention duration, and who can access the logs.

Both are prerequisites for an accurate application, and #1 is a real (if slow-burning)
data-hygiene problem regardless of Discord.

### Phase 3 — Submit the application

Developer Portal → your app → **Bot** → privileged intents section → submit request.
Apply for **Guild Members** and **Message Content** only. Leave Guild Presences off.

Attach evidence — screenshots or a short screen recording of the mod-log embeds showing
the anti-spam engine catching a scam post, and the honeypot channel. Discord's docs
explicitly invite screenshots/video, and reviewers weigh demonstrated behavior heavily.

---

## 6. Draft justification text

Adapt the specifics, but keep the shape: concrete mechanism → why interactions can't do
it → explicit data handling.

### Message Content

> Refold Helper Bot provides automated content moderation for the Refold language-learning
> community (10,000+ members across our main server and per-language servers).
>
> Message Content is used by three passive moderation systems that cannot be implemented
> with slash commands, because they must evaluate messages no user has invoked a command on:
>
> 1. **Anti-spam detection.** Every member message is scored by a heuristic engine that
>    detects scam links, cross-channel duplicate-text flooding from newly-joined accounts,
>    and mass-mention abuse. Confirmed scam patterns are banned; ambiguous cases receive a
>    short timeout, a message removal, and an explanatory DM, and are escalated to human
>    staff in a mod-log channel for review and reversal.
> 2. **Scam honeypot.** Hidden channels that legitimate members never post in. Message
>    content is logged with the ban record so staff can audit and reverse false positives.
> 3. **Deleted-message audit log.** Deleted messages are mirrored to a staff-only channel
>    so moderators can investigate harassment and scam campaigns after the fact.
>
> **Data handling.** Message content is evaluated in memory and discarded. Content is
> persisted only when an automated enforcement action fires, truncated to 1000 characters,
> stored solely so human staff can audit and reverse false positives, retained for 90 days,
> and then deleted. It is never used for analytics, training, profiling, or any purpose
> beyond moderation review, and is never shared with third parties.
>
> Our user-facing command surface is implemented entirely as slash commands. We do not use
> Message Content for command parsing.

*(That last line must be true before you send it — see Phase 1.)*

### Guild Members

> Refold runs a main community server plus separate servers for each target language, and
> the bot keeps membership state consistent across them:
>
> 1. **Cross-server role synchronization.** When a member joins or leaves a language
>    server, their corresponding role in the main server is added or removed, which drives
>    channel access across the community.
> 2. **Reaction-role self-assignment.** Members pick language and interest roles by
>    reacting to pinned messages; we resolve the member and modify their roles.
> 3. **Course enrollment.** On join, members with a pending enrollment are automatically
>    granted their course roles and added to the correct cohort.
> 4. **Anti-spam accuracy.** Account age and server-join recency are primary signals in
>    the spam heuristics. Without them the engine cannot distinguish a brand-new throwaway
>    scam account from an established member, which would substantially increase false
>    positives against legitimate users.
>
> **Data handling.** Member data is held in the in-memory gateway cache for the bot's
> runtime only. We persist user IDs alone — never usernames, avatars, or profile data —
> and only for course enrollment records and moderation audit logs.

### Guild Presences

Do not apply. Nothing uses it.

---

## 7. Sequencing and expectations

| Phase | Effort | Blocks on Discord? |
|---|---|---|
| 0 — explicit intents + graceful degradation | ~30 min | No — do today |
| 1 — slash command migration | 1–2 days | No |
| 2 — retention policy + privacy policy | ~half day | No |
| 3 — submit application | ~1 hour | Yes — then wait |

Do 0 immediately to stop the bleeding. Do 1 and 2 before submitting — they're what make
the application succeed. Review turnaround is typically days to a few weeks.

Note that approved access must be **re-applied for annually**. Set a calendar reminder now
for ~11 months out, and make sure the Developer Portal contact email is one you actually
read — the 90-day warning notice is what was missed this time.

---

## 8. Sources

- [Getting Started with Privileged Intent Review — Discord Developer Docs](https://docs.discord.com/developers/gateway/getting-started-with-privileged-intent-review)
- [Message Content Intent Review Policy — Discord Developer Support](https://support-dev.discord.com/hc/en-us/articles/5324827539479-Message-Content-Intent-Review-Policy)
- [Discord Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)
- [Discord Developer Terms of Service](https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service)
- [How Do I Get My App Verified? — Discord Developer Support](https://support-dev.discord.com/hc/en-us/articles/23926564536471-How-Do-I-Get-My-App-Verified)
- [Message Content is Now a Privileged Intent — discord-api-docs Discussion #5412](https://github.com/discord/discord-api-docs/discussions/5412)
- [Gateway Intents — discord.js guide](https://discordjs.guide/legacy/popular-topics/intents)
- [Discord Privileged Intents Update (2026): The New 10,000 User Rule](https://blogs.arkcore.arkdevlabs.com/discord-privileged-intents-10000-user-update)
