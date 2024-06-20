import base64
import zipfile

import common.config as config
import common.helper as helper
import discord
import discord.app_commands as app
import openai
import os

from .models.input import GptiInputModel
from .models.output import GptiOutputModel
from .views.gptiview import GptiJobView
from PIL import Image
from common.cog import DroppyCog
from common.exception import DroppyBotError
from discord.ext import commands
from fuzzywuzzy import fuzz
from io import BytesIO
from typing import Optional, Union


class GPTIHandler(DroppyCog):
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
        self.endpoint = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_KEY"], base_url=os.environ["OPENAI_API"]
        )
        self.endpoint_alt = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_ALT_KEY"], base_url=os.environ["OPENAI_ALT_API"]
        )

        # self.help_info["GPTI"] = self.generate_help_info

    def calculate_generate_cost(self, input_model: GptiInputModel):
        cost = 1.0 if input_model.model == self.config.gpti.models.advanced else 0.5

        if input_model.quality == "hd":
            cost += 1.0

        if input_model.size != str(self.config.gpti.dimensions.square):
            cost += 1.0

        return cost

    def sanitize_input_model(self, input_model: GptiInputModel):
        if input_model.model == self.config.gpti.models.default:
            input_model.quality = None
            input_model.style = None
            input_model.size = self.config.gpti.dimensions.square

    def convert_webp(self, image_in: BytesIO):
        image = Image.open(image_in).convert("RGB")
        if image.format == "WEBP":
            image_out = BytesIO()
            image.save(image_out, self.config.gpti.output)
            image_out.seek(0)
            return image_out
        image_in.seek(0)
        return image_in

    async def create_gpti_generation(
        self,
        ref: discord.Message,
        input_model: GptiInputModel,
        author: discord.User,
        *,
        alt: bool = False,
    ):
        """
        Make actual gpti request with openAI endpoint or alt endpoint

        Return image base64
        """

        if not input_model.prompt:
            raise DroppyBotError("Empty Prompt")

        locale = self.get_ctx_locale(ref)

        self.sanitize_input_model(input_model)
        cost = self.calculate_generate_cost(input_model)

        endpoint = self.endpoint_alt if alt else self.endpoint

        helper.latency_start(ref.id)
        # request for image completion
        try:
            response = await endpoint.images.generate(
                **input_model.model_dump(exclude_none=True), response_format="b64_json"
            )
        except openai.BadRequestError:
            feedback = self.translate("gpt_content_blocked", locale)
            raise DroppyBotError(feedback)

        # get perf latency
        latency = f"⏱️ {helper.latency_end(ref.id)}ms"

        image = response.data[0]
        data = base64.b64decode(image.b64_json)
        image_io = self.convert_webp(BytesIO(data))
        base_name = helper.timestamp_now()
        image_name = f"{base_name}.{self.config.gpti.output}"
        image_file = discord.File(image_io, image_name, description=input_model.prompt)

        ref = await ref.add_files(image_file)
        url = ref.attachments[-1].url

        prompt_block = helper.codeblock(input_model.prompt)
        self.log(ref, f"{str(input_model)} {latency}\n{prompt_block}\n{url}", author)

        return GptiOutputModel(
            cost=cost, url=url, latency=latency, revised=image.revised_prompt
        )

    @commands.hybrid_command(description="gpti_desc")
    @app.rename(prompt="gpti_prompt")
    @app.describe(prompt="gpti_prompt_desc")
    @helper.sanitize
    @DroppyCog.failsafe_ref(
        DroppyCog.config.gpti.painting_indicator, force_ephemeral=False
    )
    async def gpti(self, ctx: commands.Context, *, prompt: Optional[str]):
        """
        Generate an image with dalle, but is it worth it
        """

        ref = await self.get_ctx_ref(ctx)
        locale = self.get_ctx_locale(ctx)

        embed = helper.as_embed("", ctx.author, footer_append=None)
        prompt_field = self.translate("gpti_prompt", locale)
        embed.add_field(name=prompt_field, value=helper.codeblock(prompt), inline=False)
        await ref.edit(
            embed=embed,
            view=GptiJobView(self, prompt or "", locale),
        )
