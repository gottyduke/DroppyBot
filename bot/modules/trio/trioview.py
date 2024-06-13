import asyncio
import discord
from discord.ext import commands

from shared import CogBase


class TrioViewBase(discord.ui.View):
    def __init__(self, trio):
        super().__init__(timeout=None)
        self.trio = trio


class TrioJobView(TrioViewBase):
    def get_field(self, embeds: list, name: str):
        for e in embeds:
            for f in e.fields:
                if f.name == name:
                    return f.value.replace("```", "").strip()
        return ""

    def get_artifact(self, ctx: discord.Message):
        ref = self.get_field(ctx.embeds, "Ref")
        return [a for a in self.trio.user_artifacts if a.cache == ref][0]

    @discord.ui.button(
        label="Regenerate",
        custom_id="trio-button-job-redo",
        style=discord.ButtonStyle.primary,
        emoji="🖌️",
    )
    @CogBase.failsafe(CogBase.config.trio.generating_indicator)
    async def regenerate_batch(self, ctx: discord.Interaction, button: discord.Button):
        button.disabled = True
        await ctx.message.edit(view=self)

        ref = await CogBase.get_ctx_ref(ctx)

        template = self.get_field(ctx.message.embeds, "Template")
        prompts = self.get_field(ctx.message.embeds, "Prompts")

        regenerate_task = asyncio.create_task(
            self.trio.generate_from_template(ctx, template, prompts)
        )
        await regenerate_task

        button.disabled = False
        await ctx.message.edit(view=self)

    @discord.ui.button(
        label="Remix!",
        custom_id="trio-button-image-remix",
        style=discord.ButtonStyle.success,
        emoji="🎨",
        disabled=True,  # TODO
    )
    @CogBase.failsafe(CogBase.config.trio.remixing_indicator)
    async def remix_batch(self, ctx: discord.Interaction, button: discord.Button):
        button.disabled = True
        await ctx.message.edit(view=self)

        ref = await CogBase.get_ctx_ref(ctx)

        embed = ctx.message.embeds[0]
        embed.description = CogBase.config.trio.remixing_indicator
        await ref.edit(embed=embed)

        artifact = self.get_artifact(ctx.message)
        input_model = artifact.input_model
        input_model["params"]["seed"] = int(sum(artifact.seeds) / len(artifact.seeds))

        remix_task = asyncio.create_task(
            self.trio.create_and_poll_jobs(ref, input_model)
        )
        completion_time = await remix_task
        embed.fields[2].value = completion_time
        embed.description = CogBase.config.trio.remixing_completed
        await ref.edit(embed=embed, view=self)

        button.disabled = False
        await ctx.message.edit(view=self)

    @discord.ui.button(
        label="Download",
        custom_id="trio-button-job-artifact",
        style=discord.ButtonStyle.secondary,
        emoji="📩",
    )
    async def download_artifact(self, ctx: discord.Interaction, button: discord.Button):
        artifact = self.get_artifact(ctx.message)
        template = self.get_field(ctx.message.embeds, "Template")
        cache = self.trio.fetch_cache(artifact)
        await ctx.response.send_message(
            file=discord.File(cache, f"{template}_{artifact.timestamp}.zip"),
            ephemeral=True,
            silent=True,
        )


class TrioControlView(TrioViewBase):
    def __init__(self, trio, task: asyncio.Task):
        super().__init__(trio)
        self.task = task

    @discord.ui.button(
        label="Stop Generation",
        custom_id="trio-button-control-stop",
        style=discord.ButtonStyle.danger,
    )
    async def stop_job(self, ctx: discord.Interaction, button: discord.Button):
        self.task.cancel()
        embed = ctx.message.embeds[0]
        embed.description = self.trio.config.trio.cancelled_indicator
        await ctx.message.edit(embed=embed, view=None)
