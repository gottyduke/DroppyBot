import base64
import common.helper as helper
import discord
import discord.app_commands as app
import openai
import os

from .help import generate_help_info
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
    def __init__(self):
        self.endpoint = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_KEY"], base_url=os.environ["OPENAI_API"]
        )
        self.endpoint_alt = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_ALT_KEY"], base_url=os.environ["OPENAI_ALT_API"]
        )

        self.help_info["GPTI"] = generate_help_info

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

    def get_image_name(self, input_model: GptiInputModel):
        base_name = helper.timestamp_now()
        base_name += f"_{input_model.size}"

        if input_model.quality:
            base_name += f"_{input_model.quality}"
        if input_model.style:
            base_name += f"_{input_model.style}"

        return f"{base_name}.{self.config.gpti.output}"

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

        locale = DroppyCog.ctx_locales.get(
            str(author.id), discord.Locale.american_english
        )

        self.sanitize_input_model(input_model)
        cost = self.calculate_generate_cost(input_model)

        endpoint = self.endpoint_alt if alt else self.endpoint

        helper.latency_start(ref.id)
        # request for image completion
        try:
            response = await endpoint.images.generate(
                **input_model.model_dump(exclude_none=True), response_format="b64_json"
            )
        except:
            feedback = self.translate("gpt_content_blocked", locale)
            raise DroppyBotError(feedback)

        # get perf latency
        latency = f"⏱️ {helper.latency_end(ref.id)}ms"

        image = response.data[0]
        data = base64.b64decode(image.b64_json)
        image_io = self.convert_webp(BytesIO(data))
        image_name = self.get_image_name(input_model)
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
