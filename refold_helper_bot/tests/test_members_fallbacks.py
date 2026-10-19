import asyncio, types
fails = []
def check(name, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": got {got!r}, want {want!r}"))
    if not ok: fails.append(name)

async def main():
    import discord, RefoldHelperBot as rb
    from services import RoleService, CourseService
    from services.course_service import StudentRecord

    rs = RoleService(); rs.initialize()
    mapping = rs.get_synced_guild_roles()
    jp, es, kr = 778787713012727809, 667734565309382657, 778788342929031188
    check("mapping excludes main server, ints", (all(isinstance(v, int) for v in mapping.values()), mapping[jp]), (True, 775883964266840066))
    add, remove = rs.plan_role_sync({jp: True, es: False, kr: None}, {780905794001698836, 780905858715615262})
    check("plan: add JP, remove ES, keep KR (unknown)", (add, remove), ({775883964266840066}, {780905794001698836}))
    check("plan: nothing when in sync", rs.plan_role_sync({jp: True}, {775883964266840066}), (set(), set()))

    hm = CourseService.handle_matches
    check("handle exact", hm('alice', username='Alice', display='alice'), True)
    check("handle with @", hm('@alice', username='alice', display='alice'), True)
    check("legacy tag", hm('alice#1234', username='alice', display='alice'), True)
    check("different user", hm('alicex', username='alice', display='alice'), False)

    bot = rb.RefoldHelperBot()
    await bot.load_extension('cogs.course'); await bot.load_extension('cogs.roles')
    course = bot.get_cog('Course')
    cs = course.course_service
    cs._students = [StudentRecord(email='a@x', name='Alice', discord_handle='@Alice', course_name='LUYL')]
    cs._courses = {'luyl': types.SimpleNamespace(name='LUYL', role_id=55)}
    cs.get_course = lambda n: cs._courses.get(n.lower())

    added = []
    role = types.SimpleNamespace(id=55, mention='<@&55>')
    class Member:
        def __init__(self, name): self.name = name; self.id = 9; self.roles = []; self.bot = False
        def __str__(self): return self.name
        async def add_roles(self, r, reason=None): added.append((self.name, r.id)); self.roles.append(r)
    guild = types.SimpleNamespace(id=1093991079197560912, get_role=lambda rid: role if rid == 55 else None)
    sent = []
    async def _rec(content=None, **kw): sent.append(content)
    resp = types.SimpleNamespace(send_message=_rec)
    def interaction(name):
        return types.SimpleNamespace(guild=guild, user=Member(name), response=resp)

    await course.self_enroll(interaction('bob'))
    check("unknown user told no pending enrollment", (added, 'couldn\'t find' in sent[-1]), ([], True))
    await course.self_enroll(interaction('alice'))
    check("roster student gets course role", (added, sent[-1].startswith('✅ Welcome to **LUYL**')), ([('alice', 55)], True))
    check("student marked enrolled with id", (cs._students[0].status, cs._students[0].discord_id), ('enrolled', 9))
    await course.self_enroll(interaction('alice'))
    check("second press: already enrolled -> no pending", 'couldn\'t find' in sent[-1], True)

    # Background resolver is a no-op when the members intent is on
    bot._connection._intents.members = True
    called = []
    bot.get_guild = lambda gid: called.append(gid)
    await course.resolve_pending_students.coro(course)
    check("resolver skipped with members intent", called, [])

    await bot.close()
    print("FAILURES:", fails)
asyncio.run(main())
