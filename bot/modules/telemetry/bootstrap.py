from modules.telemetry.database import TelemetryHandler


# extension entry
async def setup(bot):
    await bot.add_cog(TelemetryHandler())


# extension exit
async def teardown(bot):
    pass
