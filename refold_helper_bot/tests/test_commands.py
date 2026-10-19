import asyncio, types
from discord import app_commands

fails = []
def check(name, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": got {got!r}, want {want!r}"))
    if not ok: fails.append(name)

class Resp:
    def __init__(self): self.sent = []; self._done = False
    def is_done(self): return self._done
    async def send_message(self, content=None, **kw): self._done = True; self.sent.append((content, kw))
    async def defer(self, **kw): self._done = True
class Followup:
    def __init__(self): self.sent = []
    async def send(self, content=None, **kw): self.sent.append((content, kw))

def fake_interaction(user_id=1):
    import discord
    class FakeInteraction(discord.Interaction):
        # Shadow the base class's slots/properties so plain attributes can be set.
        response = followup = user = guild_id = guild = channel_id = command = None
    i = FakeInteraction.__new__(FakeInteraction)
    i.response = Resp(); i.followup = Followup()
    i.user = types.SimpleNamespace(id=user_id, mention=f'<@{user_id}>')
    i.guild_id = 42; i.guild = None; i.channel_id = 7
    i.command = types.SimpleNamespace(name='x', qualified_name='x')
    return i

async def main():
    import RefoldHelperBot as rb, discord
    from utils.interactions import respond, read_text_attachment
    from utils.error_handler import error_handler
    bot = rb.RefoldHelperBot()
    for c in ('cogs.moderation', 'cogs.fun', 'cogs.admin'):
        await bot.load_extension(c)
    mod = bot.get_cog('Moderation'); fun = bot.get_cog('Fun')

    i = fake_interaction()
    await mod.rule.callback(mod, i, None, None)
    check("rule all lists 4 rules", i.response.sent[0][0].count('**') // 2, 4)

    i = fake_interaction()
    member = types.SimpleNamespace(mention='<@9>')
    await mod.rule.callback(mod, i, app_commands.Choice(name='2', value=2), member)
    check("rule 2 addressed", i.response.sent[0][0].startswith('Hey <@9>, please remember Rule 2:\n**2. Be welcoming'), True)

    i = fake_interaction()
    await mod.faq.callback(mod, i, app_commands.Choice(name='2', value=2))
    check("faq 2", i.response.sent[0][0].startswith('**FAQ#2**'), True)

    i = fake_interaction()
    await fun.roll.callback(fun, i, 'banana', '+0')
    check("roll invalid is ephemeral", i.response.sent[0][1].get('ephemeral'), True)

    i = fake_interaction()
    await fun.roll.callback(fun, i, '3d1', '+2')
    check("roll 3d1 +2 = 5", 'you got a 5!' in i.response.sent[0][0], True)

    # respond() switches to followup once answered
    i = fake_interaction()
    await respond(i, 'a'); await respond(i, 'b', ephemeral=True)
    check("respond uses followup second", (len(i.response.sent), i.followup.sent[0]), (1, ('b', {'ephemeral': True})))

    # admin allowlist check rejects strangers with a CheckFailure
    admin = bot.get_cog('Admin')
    i = fake_interaction(user_id=123)
    try:
        allowed = all([await chk(i) for chk in admin.sync.checks])
    except app_commands.CheckFailure:
        allowed = False
    check("sync rejects non-allowlisted user", allowed, False)

    # error handler: wrapped invoke error is unwrapped and reported ephemerally
    from utils.error_handler import ValidationError
    i = fake_interaction()
    err = app_commands.CommandInvokeError(types.SimpleNamespace(name='x', qualified_name='x'), ValidationError('bad'))
    await error_handler.handle_command_error(i, err)
    check("invoke error -> ephemeral user message", (i.response.sent[0][0].startswith('❌ Invalid input'), i.response.sent[0][1]), (True, {'ephemeral': True}))

    i = fake_interaction()
    await error_handler.handle_command_error(i, app_commands.CheckFailure("Course commands are not enabled in this server."))
    check("check failure message", i.response.sent[0][0], "❌ You can't use this command here.")

    # CSV attachment reader
    class Att:
        def __init__(self, data): self.data = data; self.size = len(data)
        async def read(self): return self.data
    check("csv BOM stripped", await read_text_attachment(Att('﻿a,b\n1,2'.encode('utf-8'))), 'a,b\n1,2')
    for label, att in (("oversized", Att(b'x' * 11)), ("non-utf8", Att(b'\xff\xfe\x00'))):
        try:
            await read_text_attachment(att, max_bytes=10); r = 'no error'
        except ValueError: r = 'ValueError'
        check(f"csv {label} rejected", r, 'ValueError')

    await bot.close()
    print("FAILURES:", fails)

asyncio.run(main())
