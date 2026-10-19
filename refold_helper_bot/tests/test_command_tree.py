"""Load every cog into an offline bot and build the slash-command payloads."""
import asyncio, json, sys

async def main():
    import RefoldHelperBot as rb
    from cogs import COGS
    bot = rb.RefoldHelperBot()
    failed = []
    for cog in COGS:
        try:
            await bot.load_extension(cog)
        except Exception as e:
            failed.append((cog, repr(e)))
    payload = [c.to_dict(bot.tree) for c in bot.tree.get_commands()]
    names = sorted(p['name'] for p in payload)
    print("cogs loaded:", sorted(bot.cogs), "failed:", failed)
    print(f"{len(payload)} top-level commands:", names)
    for p in payload:
        if p.get('options') and p['options'][0].get('type') == 1:
            print(f"  /{p['name']}:", [o['name'] for o in p['options']])
    print("hash:", bot._command_tree_hash()[:12])
    # Payload size sanity: Discord caps a command at 8000 chars of names/descriptions
    big = [(p['name'], len(json.dumps(p))) for p in payload if len(json.dumps(p)) > 7000]
    print("oversized:", big)
    for cog in list(bot.extensions):
        try:
            await bot.unload_extension(cog)
        except Exception:
            pass
    await bot.close()
    sys.exit(1 if failed else 0)

asyncio.run(main())
