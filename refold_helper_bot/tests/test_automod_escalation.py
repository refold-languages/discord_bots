import asyncio, types
from datetime import datetime, timedelta, timezone
fails = []
def check(name, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": got {got!r}, want {want!r}"))
    if not ok: fails.append(name)

async def main():
    import discord, RefoldHelperBot as rb
    from services import enforcement_state
    from services.automod_service import SCAM_RULE_NAME
    bot = rb.RefoldHelperBot()
    await bot.load_extension('cogs.antispam')
    cog = bot.get_cog('AntiSpam')

    # Serialization of what /automod setup would send
    for spec in cog.automod_service.build_rule_specs(555):
        cog._to_trigger(spec).to_metadata_dict()
        [a.to_dict() for a in cog._to_actions(spec)]
    check("automod payloads serialize", True, True)

    calls = []
    class Partial:
        def __init__(self, mid): self.id = mid
        async def delete(self): calls.append(('delete', self.id))
        async def add_reaction(self, e): calls.append(('react', e))
    class Channel:
        id = 77; name = 'general'
        def get_partial_message(self, mid): return Partial(mid)
        async def send(self, **kw): calls.append(('log', kw['embed'].title))
    channel = Channel()
    class Guild:
        id = 1; name = 'G'; owner_id = 999
        def get_channel_or_thread(self, cid): return channel
        async def ban(self, user, **kw): calls.append(('ban', user.id))
        async def fetch_member(self, uid): raise discord.NotFound(types.SimpleNamespace(status=404, reason='x'), 'gone')
    guild = Guild()
    cog.spam_service.is_enabled_for_guild = lambda gid: True
    bot.get_channel = lambda cid: channel   # mod-log channel
    enforcement_state.set_enabled(True); enforcement_state.set_test_mode(False)

    def member(uid, joined_min, staff=False):
        perms = types.SimpleNamespace(administrator=staff, ban_members=False, kick_members=False,
                                      manage_messages=False, manage_guild=False)
        return types.SimpleNamespace(id=uid, bot=False, guild_permissions=perms,
                                     joined_at=datetime.now(timezone.utc) - timedelta(minutes=joined_min),
                                     __str__=lambda self: f"user{uid}")
    def execution(m, action=discord.AutoModRuleActionType.send_alert_message, rule_id=5,
                  trigger=discord.AutoModRuleTriggerType.keyword):
        return types.SimpleNamespace(action=types.SimpleNamespace(type=action), rule_trigger_type=trigger,
                                     guild=guild, member=m, user_id=getattr(m, 'id', 4242), rule_id=rule_id,
                                     channel_id=77, message_id=88, matched_keyword='(?i)free\\s+nitro', content='')
    cog._automod_rule_names = {5: SCAM_RULE_NAME, 6: 'Some admin rule'}

    calls.clear(); await cog.on_automod_action(execution(member(1, 2)))
    check("new member hit -> ban + delete + log", [c[0] for c in calls], ['ban', 'delete', 'log'])
    calls.clear(); await cog.on_automod_action(execution(member(2, 600)))
    check("established member -> nothing", calls, [])
    calls.clear(); await cog.on_automod_action(execution(member(3, 2, staff=True)))
    check("staff -> nothing", calls, [])
    calls.clear(); await cog.on_automod_action(execution(member(4, 2), action=discord.AutoModRuleActionType.block_message))
    check("non-alert execution ignored", calls, [])
    calls.clear(); await cog.on_automod_action(execution(member(5, 2), rule_id=6))
    check("other rule ignored", calls, [])
    calls.clear(); await cog.on_automod_action(execution(None))
    check("member already gone -> nothing", calls, [])
    enforcement_state.set_test_mode(True)
    calls.clear(); await cog.on_automod_action(execution(member(6, 2)))
    check("test mode -> react + [TEST] log only", [c[0] for c in calls], ['react', 'log'])
    enforcement_state.set_test_mode(False); enforcement_state.set_enabled(False)
    calls.clear(); await cog.on_automod_action(execution(member(7, 2)))
    check("kill switch -> nothing", calls, [])
    enforcement_state.set_enabled(True)
    await bot.close()
    print("FAILURES:", fails)
asyncio.run(main())
