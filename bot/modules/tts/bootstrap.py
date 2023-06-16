from modules.tts.session import SessionManager


# extension entry
async def setup(bot):
    for vc in bot.voice_clients:
        await vc.cleanup()
        await vc.disconnect()

    await bot.add_cog(SessionManager())


# extension exit
async def teardown(bot):
    pass
