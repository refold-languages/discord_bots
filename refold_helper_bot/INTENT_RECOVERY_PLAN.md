# Refold Helper Bot — Privileged Intents

**App:** Refold Helper Bot (`937526025817042975`)
**Updated:** 2026-10-19

| Intent | Status | Needed? |
|---|---|---|
| Message Content | Denied | **No** — removed from the bot permanently |
| Guild Members | Not granted | Optional — every feature has a fallback; worth re-applying |
| Guild Presences | Not requested | No — nothing reads presence |

---

## 1. What happened

1. **Aug 2026:** all three intents were removed after the annual re-review
   window (introduced 2026-06-10 for apps with 10,000+ users) lapsed unnoticed.
   Commit 216a849 made intents opt-in so the bot could connect at all.
2. **By Oct 2026:** the re-application was **denied**. Discord rejects Message
   Content requests when slash commands, buttons or modals could do the job,
   and treats moderation that duplicates AutoMod as "generally not a
   compelling use case" — at the time the bot had 77 `!` prefix commands.

## 2. What changed in the bot

The bot no longer depends on Message Content at all:

- **Commands:** all 77 prefix commands were consolidated into ~43 slash
  commands. CSV uploads are file attachments, API keys go through a modal,
  and confirmations use buttons.
- **Spam:** content filtering runs as Discord AutoMod rules (`/automod setup`).
  The bot acts on AutoMod's alerts (who, where, which pattern — no text
  needed) with the same policy as before: ban only members who joined minutes
  ago. A content-free detector (rapid channel hopping) covers bursts; the
  honeypot is unchanged.
- **Removed:** the deleted-message log (it can't work without content).
- **Data:** moderation records are pruned to 90 days / 5,000 entries.

Guild Members is optional:

| Feature | With Members | Without |
|---|---|---|
| Cross-server language roles | Automatic on join/leave | "Sync my roles" button / `/syncroles` |
| Course enrollment | Automatic on join + roster load | "Get my course role" button / `/enroll`, plus a slow background lookup |
| Reaction roles, honeypot, AutoMod escalation | Works | Works |

## 3. Re-applying for Guild Members only

Do **not** request Message Content or Presences again. Before submitting:

- [ ] Read the denial notice (Developer Portal or email) and address its stated reason.
- [ ] Publish a privacy policy and link it in the Developer Portal. It must cover:
      AutoMod use, what a moderation record contains (user ID/name, channel, reason,
      matched pattern), 90-day retention, and that only staff can see records.
- [ ] Record a short video: someone joins a language server → their main-server role
      appears automatically (with `INTENT_GUILD_MEMBERS=true` on a test deployment
      below the threshold, or show the event-driven code path).
- [ ] Make sure the Developer Portal contact email is one that is actually read.

### Draft justification

> Refold runs a main community server plus separate servers for each target
> language (10,000+ members in total). The bot keeps membership state
> consistent across them:
>
> 1. **Cross-server role synchronization.** When a member joins or leaves a
>    language server, the matching role in the main server is added or
>    removed. That role controls channel access across the community. Only
>    `GUILD_MEMBER_ADD`/`REMOVE` events tell us this happened; today members
>    have to press a button, and many never do.
> 2. **Course enrollment.** Students on a course roster get their course role
>    when they join the course server. Without join events we look up
>    pending students one at a time, within the member-search rate limit,
>    which can take hours.
>
> **Data handling.** Member data from the gateway is held only in memory while
> the bot runs. We store two things: course enrollment records (the student's
> Discord username, as provided by the course roster, plus their user ID) and
> moderation records (user ID, username, channel and reason), which are kept
> for 90 days. We never store avatars or profile data. We don't use Message
> Content or Presences, and all commands are slash commands.

After approval, set `INTENT_GUILD_MEMBERS=true` and restart; the event-driven
paths take over automatically, with no code change.

## 4. Don't let it lapse again

Approved access must be re-applied for **every year**, within 90 days of
Discord's notice. Set a reminder about 11 months after approval.
