import asyncio, types, json, os, tempfile
from datetime import datetime, timedelta, timezone

fails = []
def check(name, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": got {got!r}, want {want!r}"))
    if not ok: fails.append(name)

async def main():
    import discord
    from services.automod_service import (AutoModService, SCAM_RULE_NAME, TRIGGER_KEYWORD,
                                          TRIGGER_SPAM, TRIGGER_MENTION_SPAM)
    from services import SpamDetectionService, ACTION_BAN, ACTION_TIMEOUT, ACTION_NONE
    from services.base_service import BaseService
    from config.constants import ANTISPAM_WORD_FILTER_PATTERNS

    am = AutoModService(); am.initialize()
    specs = am.build_rule_specs(555)
    check("3 rule specs", [s['trigger_type'] for s in specs], [TRIGGER_KEYWORD, TRIGGER_MENTION_SPAM, TRIGGER_SPAM])
    scam = specs[0]
    check("scam rule alert-only to channel", scam['actions'], [{'type': 2, 'channel_id': 555}])
    check("scam patterns case-insensitive", all(p.startswith('(?i)') for p in scam['trigger']['regex_patterns']), True)
    check("scam pattern count", len(scam['trigger']['regex_patterns']), len(ANTISPAM_WORD_FILTER_PATTERNS))
    check("escalating rule detection", (am.is_escalating_rule(SCAM_RULE_NAME), am.is_escalating_rule('Mod rule'), am.is_escalating_rule(None)), (True, False, False))

    # Rust-regex compatibility proxy: patterns compile in Python and match the canonical scams
    import re
    pats = [re.compile(p) for p in scam['trigger']['regex_patterns']]
    for text in ("FREE NITRO here", "https://discord.gift/abc", "t.me/scam"):
        check(f"pattern matches {text!r}", any(p.search(text) for p in pats), True)

    # Reconciliation
    existing = [(1, SCAM_RULE_NAME, 1), (2, 'Admins spam rule', 3), (3, 'Block slurs', 1)]
    steps = am.plan_reconciliation(existing, specs)
    check("reconcile ops", [(op, rid) for op, rid, _, _ in steps], [('update', 1), ('create', None), ('skip', None)])

    # Spec -> discord.py objects (as the cog builds them)
    from cogs.antispam import AntiSpam
    for spec in specs:
        trig = AntiSpam._to_trigger(spec); acts = AntiSpam._to_actions(spec)
        check(f"to_dict ok: {spec['name']}", (trig.type.value, [a.type.value for a in acts]),
              (spec['trigger_type'], [a['type'] for a in spec['actions']]))
    check("block action carries custom message", AntiSpam._to_actions(specs[1])[0].custom_message is not None, True)

    # Metadata-only engine
    svc = SpamDetectionService(); svc.initialize()
    base = dict(guild_id=1, channel_id=10, image_count=0, content='', account_age_days=1.0,
                joined_minutes_ago=2.0, has_roles=False, content_available=False)
    # New member, empty messages in 5 channels fast -> timeout (never ban)
    actions = []
    for i in range(5):
        d = svc.evaluate(user_id=100, message_id=i, timestamp=1000 + i, **{**base, 'channel_id': 10 + i})
        actions.append(d['action'])
    check("channel hop -> soft timeout on 4th channel", actions[:4], [ACTION_NONE, ACTION_NONE, ACTION_NONE, ACTION_TIMEOUT])
    check("channel hop purges the burst", len(d['message_refs']) >= 1, True)
    # Same burst from a member with a role -> nothing
    acts = [svc.evaluate(user_id=101, message_id=i, timestamp=2000 + i, **{**base, 'channel_id': 10 + i, 'has_roles': True})['action'] for i in range(6)]
    check("role holder never actioned for hopping", set(acts), {ACTION_NONE})
    # Image-ish signals with content off never fire (even with image_count passed)
    acts = [svc.evaluate(user_id=102, message_id=i, timestamp=3000 + i, **{**base, 'image_count': 4})['action'] for i in range(3)]
    check("no image detectors without content", set(acts), {ACTION_NONE})
    # Content-path detectors can't fire on empty content; only real @everyone from new member bans
    d = svc.evaluate(user_id=103, message_id=1, timestamp=4000, mentions_everyone=True, **base)
    check("genuine @everyone from new member still bans", d['action'], ACTION_BAN)
    d = svc.evaluate(user_id=104, message_id=1, timestamp=5000, mentions_everyone=True, **{**base, 'joined_minutes_ago': 600})
    check("@everyone from older member no ban", d['action'], ACTION_NONE)
    # Content mode unchanged: channel hop detector not used there
    acts = [svc.evaluate(user_id=105, message_id=i, timestamp=6000 + i, **{**base, 'channel_id': 10 + i, 'content': f'hello number {i}', 'content_available': True})['action'] for i in range(6)]
    check("content mode: distinct texts in many channels not actioned", set(acts), {ACTION_NONE})

    # AutoMod hit decision
    check("automod hit new member -> ban", svc.evaluate_automod_hit(matched_keyword='(?i)free\\s+nitro', joined_minutes_ago=1.0)['action'], ACTION_BAN)
    check("automod hit reason strips (?i)", '/free\\s+nitro/' in svc.evaluate_automod_hit(matched_keyword='(?i)free\\s+nitro', joined_minutes_ago=1.0)['reasons'][0], True)
    check("automod hit established -> none", svc.evaluate_automod_hit(matched_keyword='x', joined_minutes_ago=60.0)['action'], ACTION_NONE)
    check("automod hit unknown join -> none", svc.evaluate_automod_hit(matched_keyword='x', joined_minutes_ago=None)['action'], ACTION_NONE)

    # Retention
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    recs = [{'timestamp': (now - timedelta(days=d)).isoformat().replace('+00:00', 'Z'), 'n': d} for d in (200, 95, 89, 1)]
    recs.append({'timestamp': 'garbage', 'n': 'bad'})
    kept = BaseService.prune_records(recs, max_age_days=90, max_records=5000, now=now)
    check("prune by age keeps <90d + unparseable", [r['n'] for r in kept], [89, 1, 'bad'])
    check("prune by count keeps newest", [r['n'] for r in BaseService.prune_records(recs, max_age_days=9999, max_records=2, now=now)], [1, 'bad'])
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat().replace('+00:00', 'Z')
    with open(svc._record_path, 'w') as f:
        json.dump([{'timestamp': old}, {'timestamp': datetime.now(timezone.utc).isoformat()}], f)
    check("prune_action_records drops 1", svc.prune_action_records(), 1)
    svc.record_action({'timestamp': old})  # an already-expired record is pruned on write
    check("record_action applies retention", len(svc.get_action_records()), 1)

    print("FAILURES:", fails)

asyncio.run(main())
