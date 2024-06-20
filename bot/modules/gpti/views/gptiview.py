import asyncio
from io import BytesIO
import zipfile
import common.config as config
import common.helper as helper
import discord
import discord.app_commands as app
import openai
import os

from ..models.input import GptiInputModel
from ..models.output import GptiOutputModel
from common.view import DroppyView, DroppyModal
from common.cog import DroppyCog
from common.exception import DroppyBotError
from discord.ext import commands
from typing import Optional, Union


class GptiEditPromptModal(DroppyModal):
    prompt = discord.ui.TextInput(label="Prompt", style=discord.TextStyle.paragraph)

    def __init__(self, *kargs, locale: discord.Locale, placeholder: str, **kwargs):
        super().__init__(*kargs, **kwargs)
        label = self.cog.translate("gpti_prompt", locale)
        title = self.cog.translate("gpti_edit_prompt", locale)

        self.prompt.placeholder = placeholder
        self.prompt.label = label
        self.title = title

    @DroppyCog.failsafe_ref(no_ref=True)
    async def on_submit(self, ctx: discord.Interaction):
        await self.view.update_prompt(ctx, self.prompt.value)


class GptiJobView(DroppyView):
    def __init__(self, gpti, prompt: str, locale: discord.Locale):
        super().__init__(gpti)

        self.locale = locale

        defaults = self.cog.config.gpti.defaults
        self.input_model = GptiInputModel(
            prompt=prompt,
            model=defaults.model,
            size=str(getattr(self.cog.config.gpti.dimensions, defaults.dimension)),
            quality=defaults.quality,
            style=defaults.style,
        )

        # buttons
        self.edit_prompt.label = self.cog.translate("gpti_edit_prompt", locale)
        self.request_generation.label = self.cog.translate(
            "gpti_request_generation", locale
        )
        self.link_button = discord.ui.Button(
            label=self.cog.translate("gpti_open_proxy", locale),
            style=discord.ButtonStyle.url,
        )
        self.remove_item(self.download_artifact)
        self.download_artifact.label = self.cog.translate(
            self.download_artifact.label, locale
        )

        # models
        for _, model in iter(self.cog.config.gpti.models):
            option = discord.SelectOption(label=model.upper(), value=model)
            if model == self.input_model.model:
                option.default = True
            self.select_model.append_option(option)

        # dimensions
        for dimension, value in iter(self.cog.config.gpti.dimensions):
            label = self.cog.translate(f"gpti_dimension_{dimension}", locale)
            value_str = str(value)
            option = discord.SelectOption(
                label=f"{label} ({value_str})", value=value_str
            )
            if value_str == self.input_model.size:
                option.default = True
            self.select_dimension.append_option(option)

        # qualities
        for _, value in iter(self.cog.config.gpti.qualities):
            label = self.cog.translate(f"gpti_quality_{value}", locale)
            option = discord.SelectOption(label=label, value=value)
            if value == self.input_model.quality:
                option.default = True
            self.select_quality.append_option(option)

        # styles
        for _, value in iter(self.cog.config.gpti.styles):
            label = self.cog.translate(f"gpti_style_{value}", locale)
            option = discord.SelectOption(label=label, value=value)
            if value == self.input_model.style:
                option.default = True
            self.select_style.append_option(option)

    def disable_advanced(self):
        self.select_quality.disabled = True
        self.input_model.quality = None

        self.select_style.disabled = True
        self.input_model.style = None

        self.select_dimension.disabled = True
        self.input_model.size = str(self.cog.config.gpti.dimensions.square)

    def enable_advanced(self):
        self.select_quality.disabled = False
        self.input_model.quality = self.get_default_value(self.select_quality)

        self.select_style.disabled = False
        self.input_model.style = self.get_default_value(self.select_style)

        self.select_dimension.disabled = False
        self.input_model.size = self.get_default_value(self.select_dimension)

    def set_everything(self, enable: bool):
        for item in self.children:
            try:
                item.disabled = not enable
            except:
                continue

    def get_default_value(self, select: discord.ui.Select):
        default = helper.first_if(select.options, lambda o: o.default)
        default = default or select.options[0]
        return default.value

    def set_current_default(self, select: discord.ui.Select):
        value = select.values[0]
        selected = helper.first_iequal(select.options, "value", value)
        for option in select.options:
            option.default = False
        selected.default = True

    async def update_prompt(self, ctx: discord.Interaction, prompt: str):
        self.input_model.prompt = prompt
        embed = ctx.message.embeds[0]
        embed.set_field_at(
            0, name=embed.fields[0].name, value=helper.codeblock(prompt), inline=False
        )
        await ctx.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="gpti_download_artifact",
        style=discord.ButtonStyle.secondary,
        emoji="📩",
    )
    @DroppyCog.failsafe_ref(custom_handler=True)
    async def download_artifact(
        self, ctx: discord.Interaction, button: discord.ui.Button
    ):
        zbuf = BytesIO()
        zip_base_name = ""
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            for image in ctx.message.attachments:
                sanitized_buf = BytesIO()
                await image.save(sanitized_buf)
                z.writestr(image.filename, sanitized_buf.getvalue())
                zip_base_name = os.path.splitext(image.filename)[0]
        zbuf.seek(0)
        zip_name = f"{zip_base_name}.zip"
        artifact = discord.File(zbuf, zip_name)
        await ctx.response.send_message(file=artifact, ephemeral=True, silent=True)

    @discord.ui.button(
        label="Prompt",
        style=discord.ButtonStyle.primary,
        emoji="📝",
    )
    @DroppyCog.failsafe_ref(custom_handler=True)
    async def edit_prompt(self, ctx: discord.Interaction, button: discord.Button):
        await ctx.response.send_modal(
            GptiEditPromptModal(
                self,
                "gpti_edit_prompt",
                locale=self.locale,
                placeholder=self.input_model.prompt,
            )
        )

    @discord.ui.button(
        label="Generate",
        style=discord.ButtonStyle.success,
        emoji="🖌️",
    )
    @DroppyCog.failsafe_ref(no_ref=True)
    @DroppyCog.allocated("gpti")
    async def request_generation(
        self, ctx: discord.Interaction, button: discord.Button
    ):
        self.locale = self.cog.get_ctx_locale(ctx)

        button.label = self.cog.translate(
            self.cog.config.gpti.painting_indicator, self.locale
        )
        self.set_everything(False)
        await ctx.message.edit(view=self)

        output: GptiOutputModel = await self.cog.create_gpti_generation(
            ctx.message,
            self.input_model,
            self.cog.get_ctx_author(ctx.message),
            alt=True,
        )

        self.remove_item(self.link_button)
        self.link_button.custom_id = None
        self.link_button.url = output.url
        self.add_item(self.link_button)

        self.remove_item(self.download_artifact)
        self.add_item(self.download_artifact)

        embed = ctx.message.embeds[0]
        embed.set_footer(text=output.latency)
        revised_field = self.cog.translate("gpti_revised_prompt", self.locale)
        if len(embed.fields) < 2:
            embed.add_field(name=revised_field, value="")
        embed.set_field_at(
            1, name=revised_field, value=helper.codeblock(output.revised), inline=False
        )

        button.label = self.cog.translate("gpti_request_generation", self.locale)
        self.set_everything(True)
        await ctx.message.edit(embed=embed, view=self)

        return output.cost

    @discord.ui.select()
    @DroppyCog.failsafe_ref(no_ref=True)
    async def select_model(self, ctx: discord.Interaction, select: discord.ui.Select):
        self.set_current_default(select)

        model = select.values[0]
        self.input_model.model = model

        if model == self.cog.config.gpti.models.default:
            self.disable_advanced()
            await ctx.message.edit(view=self)
        else:
            self.enable_advanced()
            await ctx.message.edit(view=self)

    @discord.ui.select()
    @DroppyCog.failsafe_ref(no_ref=True)
    async def select_dimension(
        self, ctx: discord.Interaction, select: discord.ui.Select
    ):
        self.set_current_default(select)
        self.input_model.size = select.values[0]

    @discord.ui.select()
    @DroppyCog.failsafe_ref(no_ref=True)
    async def select_quality(self, ctx: discord.Interaction, select: discord.ui.Select):
        self.set_current_default(select)
        self.input_model.quality = select.values[0]

    @discord.ui.select()
    @DroppyCog.failsafe_ref(no_ref=True)
    async def select_style(self, ctx: discord.Interaction, select: discord.ui.Select):
        self.set_current_default(select)
        self.input_model.style = select.values[0]
