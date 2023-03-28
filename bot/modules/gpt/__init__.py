from modules.gpt.chat import GPTHandler


### extension entry
async def setup(bot):
    await bot.add_cog(GPTHandler(bot))


### extension exit
async def teardown(bot):
    pass
