import asyncio
import discord
import requests

from discord.ext import commands
from io import BytesIO
from shared import CogBase


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

        self.private_query = False

        self.help_info["GPTI"] = self.generate_help_info()

    @commands.hybrid_command()
    @CogBase.failsafe(CogBase.config.gpti.painting_indicator)
    async def gpti(self, ctx: commands.Context, *, prompt: str):
        """
        dalle-3
        """

        ref = await self.get_ctx_ref(ctx)

        embed = self.as_embed(self.config.gpti.painting_indicator, ctx.author)
        await ref.edit(embed=embed)

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
        input_model = {
            "prompt": prompt,
            "size": self.config.gpti.dimension.default,
            "n": quantity,
        }
        if quantity == 1:
            input_model["model"] = self.config.gpti.model.advanced
            input_model["quality"] = self.config.gpti.quality.hd
        else:
            input_model["model"] = self.config.gpti.model.default

        responses = await asyncio.to_thread(
            self.endpoint.images.generate, **input_model
        )
        embed.description = self.config.gpti.painting_completed
        revised = (
            responses.data[0].revised_prompt
            if responses.data[0].revised_prompt is not None
            else prompt
        )
        embed.add_field(name="Prompt", value=f"```\n{revised}\n```")
        await ref.edit(embed=embed)

        # if multi-creation
        url = {}
        for i, res in enumerate(responses.data):
            image = requests.get(res.url).content
            image_name = f"image_{i + 1}.jpg"
            image_file = discord.File(
                BytesIO(image),
                image_name,
                description=prompt,
            )
            display_task = asyncio.create_task(ctx.send(file=image_file, silent=True))
            url[f"[{image_name}]"] = display_task

        messages = await asyncio.gather(*url.values())
        links = " ".join(
            [
                f"{l}({messages[i].attachments[0].proxy_url})"
                for i, l in enumerate(url.keys())
            ]
        )
        if not self.private_query:
            self.log(ctx.message, f"gpti x{quantity}\n```\n{prompt}\n```\n{links}")

    @commands.command()
    async def gptip(self, ctx: commands.Context, *, prompt):
        self.private_query = True
        await self.gpti(ctx, prompt=prompt)
        self.private_query = False
