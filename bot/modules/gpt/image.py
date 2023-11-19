from shared import CogBase

import discord
from discord.ext import commands


class GPTIHandler(CogBase, commands.Cog):
    def generate_help_info(self):
        help_info = [
            discord.Embed(
                color=discord.Color.blurple(),
                title="GPT图片生成",
                description="""
            使用DALL-E-3进行图片生成, powered by OpenAI
            
            图片链接将会在生成1小时后失效, 请酌情保存(右键图片, 保存图片)
            """,
            )
        ]
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="命令指南及其示例:",
                description=f"""
{self.compiled_gpti_cmd} : 给定文字prompt生成图片

            例如, 生成1张小猫抱着鱼狂奔的图片
            ```
{self.compiled_gpti_cmd} 小猫在集市中抱着一条鱼鱼狂奔, 背后人们穷追不舍!```
            """,
            )
        )
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="系列生成(多张):",
                description=f"""
{self.compiled_gpti_cmd} : 给定文字prompt生成多张类似风格的图片变种

            例如, 生成5张珠穆朗玛峰填平东非大裂谷的图片
            ```
{self.compiled_gpti_cmd} x5 珠穆朗玛峰填平东非大裂谷```
            """,
            )
        )
        return help_info

    def __init__(self):
        self.compiled_gpti_cmd = f"{self.bot.command_prefix}gpti"

        self.help_info["GPTI"] = self.generate_help_info()

    @commands.command()
    async def gpti(self, ctx: commands.Context, *, prompt: str):
        embed = self.as_embed(self.config.gpti.painting_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        # check for creation quantity
        tokenized_prompt = prompt.split(" ")
        quantity = 1
        if (
            len(tokenized_prompt) > 1
            and tokenized_prompt[0].startswith("x")
            and tokenized_prompt[0][1].isnumeric()
        ):
            quantity = int(tokenized_prompt[0][1])
            quantity = max(min(quantity, self.config.gpti.variation_max), 1)
            prompt = " ".join(tokenized_prompt[1:])

        # image creation
        responses = (
            self.endpoint.images.generate(
                model=self.config.gpti.model.advanced,
                prompt=prompt,
                size=self.config.gpti.dimension.default,
                quality="hd",
                n=quantity,
            )
            if quantity == 1
            else self.endpoint.images.generate(
                model=self.config.gpti.model.default,
                prompt=prompt,
                size=self.config.gpti.dimension.default,
                n=quantity,
            )
        )
        embed.description = self.config.gpti.painting_completed
        await message.edit(embed=embed)

        # if multi-creation
        url = []
        for res in responses.data:
            await ctx.send(
                embed=discord.Embed(color=ctx.author.color).set_image(url=res.url)
            )
            url.append(res.url)

        self.log(ctx.message, f"gpti x{quantity}```{prompt}```{url}")
