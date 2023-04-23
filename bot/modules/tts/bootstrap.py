from modules.tts.session import SessionManager


# extension entry
async def setup(bot):
    await bot.add_cog(SessionManager())
    pass


# extension exit
async def teardown(bot):
    pass
